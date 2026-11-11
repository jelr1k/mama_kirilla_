from __future__ import annotations

from pathlib import Path, PurePath
import logging
import re
import time
from typing import Any

from core.alias_manager import AliasManager, DEFAULT_ACTION_ALIASES
from core.website_manager import WebsiteManager
from tools import applications
from tools.executor import ToolExecutor
from tools.paths import get_workspace_index
from core.target_resolver import TargetResolver
from tools.registry import TOOLS
from services.stark_protocols import StarkProtocols

from services.command_catalog import (
    ROUTER_COMMANDS,
    ASYNC_SYSTEM_COMMANDS,
    GENERIC_APPLICATION_TARGETS,
    CONTEXTUAL_SEARCH_ALIASES,
    FILE_SEARCH_CONTEXT_RE,
    ACTION_META,
    KEYWORD_TOOLS,
    command_definition_display,
    match_command_definition,
)
from services.router import (
    dispatch_media_command,
    dispatch_site_command,
    dispatch_protocol_command,
    dispatch_system_command,
    dispatch_jarvis_window_command,
    dispatch_file_command,
    dispatch_app_management_command,
    dispatch_ollama_control_command,
)

logger = logging.getLogger("jarvis.router")


class CommandRouter:
    """Определяет однозначные команды, которым не нужен LLM."""

    ROUTER_COMMANDS = ROUTER_COMMANDS
    ASYNC_SYSTEM_COMMANDS = ASYNC_SYSTEM_COMMANDS
    _GENERIC_APPLICATION_TARGETS = GENERIC_APPLICATION_TARGETS
    _CONTEXTUAL_SEARCH_ALIASES = CONTEXTUAL_SEARCH_ALIASES
    _FILE_SEARCH_CONTEXT_RE = FILE_SEARCH_CONTEXT_RE
    _EXACT_AUTO_REPLIES = (
        (re.compile(r"^ал+о[!?.,…\s]*$", re.IGNORECASE), "ало да, вас не слышно"),
    )

    @classmethod
    def _definition_display(cls, command_id: str) -> list[str]:
        return command_definition_display(command_id)

    @classmethod
    def _match_definition(cls, command_id: str, text: str) -> re.Match | None:
        return match_command_definition(command_id, text)

    def __init__(
        self,
        config,
        ollama_manager,
        alias_manager: AliasManager | None = None,
        website_manager: WebsiteManager | None = None,
        event_bus=None,
        protocols_manager=None,
        steam_manager=None,
        app_indexer=None,
    ):
        self.config = config
        self.ollama_manager = ollama_manager
        self.alias_manager = alias_manager or AliasManager()
        self.website_manager = website_manager or WebsiteManager(event_bus=event_bus)
        self.events = event_bus
        self.protocols_manager = protocols_manager
        if steam_manager is None:
            try:
                from core.steam_manager import SteamManager
                steam_manager = SteamManager.get_instance()
            except Exception:
                steam_manager = None
        self.steam_manager = steam_manager
        if app_indexer is None:
            try:
                from core.app_indexer import AppIndexer
                app_indexer = AppIndexer.get_instance(event_bus=event_bus)
            except Exception:
                app_indexer = None
        self.app_indexer = app_indexer
        self.target_resolver = TargetResolver(self.alias_manager, get_workspace_index)
        self.ui_actions = {}
        logger.debug("router_created")

    def set_ui_actions(self, actions: dict[str, callable] | None) -> None:
        """Registers abstract application-window actions, without knowing the UI framework."""
        self.ui_actions = dict(actions or {})

    def _executor(self) -> ToolExecutor:
        return ToolExecutor(self.config, set(TOOLS), self.alias_manager, event_bus=self.events)

    @classmethod
    def _is_contextual_file_search(cls, alias: str, target: str) -> bool:
        if alias not in cls._CONTEXTUAL_SEARCH_ALIASES:
            return True
        return bool(cls._FILE_SEARCH_CONTEXT_RE.search(target))

    @classmethod
    def _contains_action_alias(cls, text: str, action: str, alias: str) -> bool:
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return False
        if action != "search" or alias not in cls._CONTEXTUAL_SEARCH_ALIASES:
            return True
        target = text[match.end():].lstrip(" ,:;—-\t")
        return cls._is_contextual_file_search(alias, target)

    def _has_multiple_actions(self, text: str) -> bool:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return False
        matches = []
        for action, defaults in DEFAULT_ACTION_ALIASES.items():
            for alias in defaults:
                if self._contains_action_alias(normalized, action, alias):
                    matches.append(action)
                    break
        for action, entry in self.alias_manager.data.get("actions", {}).items():
            for alias in entry.get("aliases", []):
                if self._contains_action_alias(normalized, action, alias):
                    matches.append(action)
                    break
        unique_actions = set(matches)
        if len(unique_actions) > 1:
            logger.info("compound_command detected actions=%s text=%r", sorted(unique_actions), text)
            return True
        return False

    def is_async_system_command(self, text: str) -> bool:
        """Определяет команды, которые выполняют системные/дисковые/сетевые операции и должны запускаться в фоне."""
        normalized = self._normalize_command_text(text)
        lower = normalized.casefold()

        if lower in {item.casefold() for item in self._definition_display("system_telemetry")}:
            return True

        for cmd_id in self.ASYNC_SYSTEM_COMMANDS:
            if self._match_definition(cmd_id, normalized):
                return True

        action = self._resolve_action(normalized)
        if action and action[0] == "launch":
            if getattr(self, "website_manager", None) and self.website_manager.resolve_url(action[1]):
                return True
            if getattr(self, "steam_manager", None) and self.steam_manager.resolve_game(action[1]):
                return True
            if getattr(self, "app_indexer", None) and self.app_indexer.resolve_app(action[1]):
                return True

        return False

    def _resolve_action(self, text: str):
        action = self.alias_manager.resolve_action(text)
        if not action:
            return None
        action_name, target = action
        if action_name == "search":
            for alias in self._CONTEXTUAL_SEARCH_ALIASES:
                if re.match(rf"^{re.escape(alias)}(?:,)?\s+", text, flags=re.IGNORECASE):
                    if not self._is_contextual_file_search(alias, target):
                        logger.info("contextual_search_rejected target=%r text=%r", target, text)
                        return None
                    break
        return action

    @staticmethod
    def _reply(result: dict, include_path: bool = True) -> str:
        if result.get("pending_confirmation"):
            tool_name = result.get("confirmation_tool", "действие")
            labels = {
                "delete_file": "удаление файла",
                "write_file": "перезапись файла",
                "rename_file": "переименование файла",
                "copy_file": "копирование файла",
                "move_file": "перемещение файла",
                "close_application": "закрытие приложения",
            }
            return f"[Подтверждение] Подтвердить {labels.get(tool_name, tool_name)}? Ответь «да» или «нет»."
        if not result.get("success"):
            matches = result.get("matches") or []
            if result.get("ambiguous") and matches:
                return result.get("error") or "Неоднозначный запрос."
            return f"Не выполнено: {result.get('error', 'неизвестная ошибка')}"
        if result.get("content") is not None:
            content_str = str(result["content"])
            if result.get("system_telemetry") or result.get("media_control") or "Скриншот" in content_str:
                return content_str
            if include_path:
                path = result.get("path")
                if path:
                    file_name = PurePath(str(path).replace("\\", "/")).name
                    prefix = f"Содержимое {file_name}:\n"
                else:
                    prefix = "Содержимое файла:\n"
            else:
                prefix = "Содержимое файла:\n"
            return prefix + content_str
        if result.get("matches") is not None:
            matches = result.get("matches") or []
            if not matches:
                return "Ничего не найдено."
            return "Найдено:\n" + "\n".join(matches[:20])
        if result.get("running") is not None:
            return "Приложение запущено." if result["running"] else "Приложение не запущено."
        if result.get("path"):
            file_name = PurePath(str(result["path"]).replace("\\", "/")).name
            return f"Готово: {file_name}" if file_name else f"Готово: {result['path']}"
        return "Готово."

    @classmethod
    def _close_reply(cls, target: str, result: dict) -> str:
        if result.get("pending_confirmation"):
            return cls._reply(result)
        if not result.get("success"):
            matches = result.get("matches") or []
            if result.get("ambiguous") and matches:
                return result.get("error") or "Неоднозначный запрос."
            return f"Не удалось закрыть {target}: {result.get('error', 'неизвестная ошибка')}"
        if result.get("already_closed") or result.get("running") is False:
            return f"{target} уже закрыт."
        return f"{target} закрыт."

    def _resolve_target(self, query, categories, alias_confirmation_callback=None, *, use_workspace_index=False):
        """Разрешает цель даже если она является частью естественной фразы."""
        return self.target_resolver.resolve(
            query,
            categories,
            alias_confirmation_callback=alias_confirmation_callback,
            use_workspace_index=use_workspace_index,
        )

    def execute_confirmed(self, tool_name: str, arguments: dict) -> str:
        """Исполняет ранее подтверждённое действие без повторной маршрутизации."""
        result = self._executor().execute(
            tool_name,
            dict(arguments),
            confirmation_callback=lambda *_args: True,
        )
        if tool_name == "close_application":
            target = str(arguments.get("name") or arguments.get("target") or "приложение")
            return self._close_reply(target, result)
        return self._reply(result)

    def _direct_tool(self, tool_name: str, arguments: dict, confirmation_callback=None) -> str:
        result = self._executor().execute(
            tool_name,
            arguments,
            confirmation_callback=confirmation_callback,
        )
        return self._reply(result)

    def _route_extended_tools(self, text: str, confirmation_callback=None, alias_confirmation_callback=None) -> str | None:
        """Прямые маршруты для всех инструментов, которые иначе доступны LLM."""
        executor = self._executor()

        # 1. Фирменные и пользовательские протоколы JARVIS
        res = dispatch_protocol_command(text, self.protocols_manager, self.config)
        if res is not None:
            return res

        # 2. Системные команды ПК (мышь, vpn, zapret, чат, скриншот, блокировка, дата/время, папки, корзина)
        res = dispatch_system_command(text, executor, self._reply, self.ui_actions)
        if res is not None:
            return res

        # 3. Веб-поиск и URL
        res = dispatch_site_command(text, executor, self._reply, self._direct_tool, confirmation_callback)
        if res is not None:
            return res

        # 4. Файловые команды прямого действия (create_file, write_file, rename_file, copy_file, move_file, file_info)
        res = dispatch_file_command(text, executor, self._direct_tool, confirmation_callback)
        if res is not None:
            return res

        # 5. Управление звуком и медиаплеером
        res = dispatch_media_command(text, executor, self._reply)
        if res is not None:
            return res

        # 6. Специальные команды Jarvis / окна (раньше app_management, чтобы "сверни окно" не уходило в поиск приложения)
        assistant_name = str(self.config.get("assistant_name", "Kirieshcka")) if hasattr(self.config, "get") else "Kirieshcka"
        res = dispatch_jarvis_window_command(text, self.ui_actions, assistant_name)
        if res is not None:
            return res

        # 7. Поиск и сворачивание приложений
        res = dispatch_app_management_command(
            text,
            executor,
            self._direct_tool,
            self._resolve_action,
            self._resolve_target,
            confirmation_callback,
            alias_confirmation_callback,
        )
        if res is not None:
            return res

        # 8. Управление Ollama и моделью
        model = str(self.config.get("model", "")).strip() if hasattr(self.config, "get") else ""
        res = dispatch_ollama_control_command(text, self.ollama_manager, model)
        if res is not None:
            return res

        return None

    def command_catalog(self) -> list[dict[str, object]]:
        """Справочник из единого набора определений Router."""
        catalog = []
        for action, aliases in DEFAULT_ACTION_ALIASES.items():
            meta = ACTION_META.get(action)
            if not meta:
                continue
            commands = list(aliases)
            custom = self.alias_manager.data.get("actions", {}).get(action, {})
            for alias in custom.get("aliases", []):
                if alias not in commands:
                    commands.append(alias)
            catalog.append({
                "id": f"action_{action}",
                "name": meta["name"],
                "category": meta["category"],
                "description": meta["description"],
                "example": meta["example"],
                "commands": commands,
            })
        for cmd_id, definition in self.ROUTER_COMMANDS.items():
            if definition.get("display"):
                catalog.append({
                    "id": cmd_id,
                    "name": definition["name"],
                    "category": definition.get("category", "system"),
                    "description": definition.get("description", ""),
                    "example": definition.get("example", (definition.get("display") or [""])[0]),
                    "commands": list(definition["display"]),
                })
        return catalog

    def tools_for_message(self, text: str) -> set[str]:
        """Определяет набор LLM-инструментов для текущего сообщения."""
        lower = self._normalize_command_text(text).casefold()
        action = self._resolve_action(lower)
        executor = self._executor()
        enabled = {name for name in TOOLS if executor._is_enabled(name)}

        action_tools = {
            "launch": {"launch_application", "get_process_status"},
            "close": {"close_application", "get_process_status"},
            "minimize": {"minimize_application", "get_process_status"},
            "status": {"get_process_status"},
            "search": {"search_files"},
            "read": {"read_file"},
            "delete": {"delete_file", "search_files"},
        }

        detected_actions: set[str] = set()
        for action_name, aliases in DEFAULT_ACTION_ALIASES.items():
            if any(self._contains_action_alias(lower, action_name, alias) for alias in aliases):
                detected_actions.add(action_name)

        if len(detected_actions) > 1:
            selected = set()
            for action_name in detected_actions:
                selected.update(action_tools.get(action_name, set()))
            result = selected & enabled
            logger.info("router_tool_scope text=%r tools=%s reason=compound_actions actions=%s", text, sorted(result), sorted(detected_actions))
            return result

        if action:
            selected = action_tools.get(action[0])
            if selected:
                result = selected & enabled
                logger.info("router_tool_scope text=%r tools=%s reason=action", text, sorted(result))
                return result

        selected = set()
        for keyword, names in KEYWORD_TOOLS.items():
            if keyword in lower:
                selected.update(names)

        result = selected & enabled
        logger.info("router_tool_scope text=%r tools=%s reason=keywords_or_chat", text, sorted(result))
        return result

    def _normalize_command_text(self, text: str) -> str:
        return self.alias_manager.normalize_command_text(text)

    def route(self, text: str, confirmation_callback=None, alias_confirmation_callback=None) -> str | None:
        started = time.perf_counter()
        normalized = self._normalize_command_text(text)
        lower = normalized.casefold()
        logger.info("route_start text=%r normalized=%r", text, normalized)

        for pattern, reply in self._EXACT_AUTO_REPLIES:
            if pattern.fullmatch(lower):
                return reply

        executor = self._executor()

        if applications.has_pending_launch_choices() and re.fullmatch(r"(?:\d+|перв(?:ый|ая)|втор(?:ой|ая)|трет(?:ий|ья)|четверт(?:ый|ая)|четвёрт(?:ый|ая)|пят(?:ый|ая))\.?", lower):
            return self._reply(executor.execute("launch_application", {"target": normalized}, confirmation_callback=confirmation_callback))

        if lower in {item.casefold() for item in self._definition_display("ollama_status")}:
            return f"Ollama Server: {self.ollama_manager.server_status()}. Загружено моделей: {len(self.ollama_manager.get_loaded_models())}."

        if lower in {item.casefold() for item in self._definition_display("ollama_start")}:
            try:
                self.ollama_manager.start()
                return "Ollama Server запущен."
            except Exception as exc:
                logger.exception("route_ollama_start_failed")
                return f"Не удалось запустить Ollama: {exc}"

        if lower in {item.casefold() for item in self._definition_display("ollama_stop")}:
            result = self.ollama_manager.stop_server()
            return "Ollama Server остановлен." if result.get("success") else f"Не удалось остановить Ollama: {result.get('error')}"

        if lower in {item.casefold() for item in self._definition_display("system_telemetry")}:
            return self._reply(executor.execute("get_system_telemetry", {}))

        extended = self._route_extended_tools(normalized, confirmation_callback, alias_confirmation_callback)
        if extended is not None:
            return extended

        if self._has_multiple_actions(normalized):
            return None

        action = self._resolve_action(normalized)
        if not action:
            return None
        action_name, target = action

        if action_name == "search" and executor._is_enabled("search_files"):
            target = re.sub(r"^(?:файл|файлы)\s+", "", target, flags=re.IGNORECASE)
            return self._reply(executor.execute("search_files", {"name": target}, confirmation_callback=confirmation_callback))

        if action_name == "read" and executor._is_enabled("read_file"):
            target = re.sub(r"^(?:файл|файлы)\s+", "", target, flags=re.IGNORECASE)
            result = executor.execute("read_file", {"path": target}, confirmation_callback=confirmation_callback)
            return self._reply(result, include_path=False)

        if action_name == "delete" and executor._is_enabled("delete_file"):
            target = re.sub(r"^(?:файл|файлы)\s+", "", target, flags=re.IGNORECASE)
            resolved, error = self._resolve_target(target, ("files",), alias_confirmation_callback, use_workspace_index=True)
            if error:
                return f"Не выполнено: {error}"
            return self._reply(executor.execute("delete_file", {"path": resolved}, confirmation_callback=confirmation_callback))

        if action_name == "status" and executor._is_enabled("get_process_status"):
            resolved, error = self._resolve_target(target, ("applications",), alias_confirmation_callback)
            if error:
                return f"Не выполнено: {error}"
            return self._reply(executor.execute("get_process_status", {"name": resolved}, confirmation_callback=confirmation_callback))

        if action_name == "launch":
            # 1. Проверяем, не является ли цель известным сайтом (ютуб, вк, гитхаб и т.д.)
            if getattr(self, "website_manager", None):
                resolved_site = self.website_manager.resolve_url(target)
                if resolved_site:
                    import webbrowser
                    webbrowser.open(resolved_site[1])
                    return f"Открываю {resolved_site[0].get('name') or target}."

            # 2. Проверяем, не является ли цель установленной игрой Steam (CS2, Dota 2, Cyberpunk и т.д.)
            if getattr(self, "steam_manager", None):
                steam_game = self.steam_manager.resolve_game(target)
                if steam_game:
                    if self.steam_manager.is_game_running(steam_game):
                        return f"Игра «{steam_game.get('name')}» уже запущена, сэр."
                    launch_res = self.steam_manager.launch_game(steam_game)
                    if launch_res.get("success"):
                        return f"Запускаю «{steam_game.get('name')}» через Steam."
                    return f"Не удалось запустить {steam_game.get('name')}: {launch_res.get('error')}"

            # 2.5. Проверяем, не является ли цель установленным софтом Windows (Discord, Telegram, OBS, VS Code и т.д.)
            if getattr(self, "app_indexer", None) and executor._is_enabled("launch_application"):
                app_match = self.app_indexer.resolve_app(target)
                if app_match:
                    app_name = app_match.get("name") or target
                    status = executor.execute("get_process_status", {"name": app_name}, confirmation_callback=confirmation_callback) if executor._is_enabled("get_process_status") else {"running": False}
                    if status.get("success") and status.get("running"):
                        return f"{app_name} уже запущен."
                    launch_res = self.app_indexer.launch_app(app_match)
                    if launch_res.get("success"):
                        return f"Запускаю «{app_name}»."
                    return f"Не удалось запустить {app_name}: {launch_res.get('error')}"

            # 3. Иначе запускаем локальное приложение / файл / папку
            if executor._is_enabled("launch_application"):
                resolved, error = self._resolve_target(
                    target,
                    ("applications", "files", "folders"),
                    alias_confirmation_callback,
                    use_workspace_index=True,
                )
                if not error:
                    status = executor.execute("get_process_status", {"name": resolved}, confirmation_callback=confirmation_callback) if executor._is_enabled("get_process_status") else {"running": False}
                    if status.get("success") and status.get("running"):
                        return f"{target} уже запущен."
                    result = executor.execute("launch_application", {"target": resolved}, confirmation_callback=confirmation_callback)
                    if not result.get("success") and getattr(self, "website_manager", None):
                        resolved_site = self.website_manager.resolve_url(target)
                        if resolved_site:
                            import webbrowser
                            webbrowser.open(resolved_site[1])
                            return f"Открываю {resolved_site[0].get('name') or target}."
                    return self._reply(result)

            if executor._is_enabled("launch_application"):
                return f"Не выполнено: {error}"

        if action_name == "close" and executor._is_enabled("close_application"):
            if target.strip().casefold() in self._GENERIC_APPLICATION_TARGETS:
                return "Какое приложение закрыть?"
            resolved, error = self._resolve_target(target, ("applications",), alias_confirmation_callback)
            if error:
                return f"Не выполнено: {error}"
            result = executor.execute("close_application", {"name": resolved}, confirmation_callback=confirmation_callback)
            return self._close_reply(resolved, result)

        return None

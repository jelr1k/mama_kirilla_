from __future__ import annotations

import logging
import random
import re
from pathlib import PurePath

from services.rofl_phrases import DEMON_LINES, FUTURE_LINES, NORMAL_LINES, ROUTER_LINES


logger = logging.getLogger("jarvis.rofl")


class RoflService:
    """Шуточные и характерные реплики Jarvis (Kirieshka v2)."""

    DEFAULT_ROFL_CHANCE = 0.12
    DEFAULT_DEMON_CHANCE = 0.15

    NORMAL_LINES = NORMAL_LINES
    DEMON_LINES = DEMON_LINES
    FUTURE_LINES = FUTURE_LINES
    ROUTER_LINES = ROUTER_LINES

    def __init__(self, event_bus, config=None):
        self.events = event_bus
        rofl_config = config.get("rofl", {}) if config is not None else {}
        self.rofl_chance = self._clamp_chance(
            rofl_config.get("chance", self.DEFAULT_ROFL_CHANCE),
            self.DEFAULT_ROFL_CHANCE,
        )
        self.demon_chance = self._clamp_chance(
            rofl_config.get("demon_chance", self.DEFAULT_DEMON_CHANCE),
            self.DEFAULT_DEMON_CHANCE,
        )
        event_bus.subscribe("tool.executed", self._on_tool_executed)
        event_bus.subscribe("router.rofl_candidate", self._on_router_rofl_candidate)
        event_bus.subscribe("rofl.settings_changed", self._on_settings_changed)
        logger.debug(
            "rofl_service_created chance=%.2f demon_chance=%.2f",
            self.rofl_chance,
            self.demon_chance,
        )

    def _emit_rofl_response(self, text: str) -> None:
        """Send the same joke to the UI and the reusable speech service."""
        self.events.emit("chat.rofl_response", text)
        self.events.emit("speech.requested", text, "rofl")

    @staticmethod
    def _clamp_chance(value, default):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return default

    def _on_settings_changed(self, settings: dict):
        self.rofl_chance = self._clamp_chance(
            settings.get("chance", self.DEFAULT_ROFL_CHANCE),
            self.DEFAULT_ROFL_CHANCE,
        )
        self.demon_chance = self._clamp_chance(
            settings.get("demon_chance", self.DEFAULT_DEMON_CHANCE),
            self.DEFAULT_DEMON_CHANCE,
        )
        logger.info(
            "rofl_settings_applied chance=%.2f demon_chance=%.2f",
            self.rofl_chance,
            self.demon_chance,
        )

    @staticmethod
    def _display_target(arguments: dict, result: dict) -> str:
        target = str(arguments.get("target") or result.get("path") or "объект").strip().strip("\"'")
        if not target:
            return "объект"
        if "/" in target or "\\" in target:
            name = PurePath(target.replace("\\", "/")).name
            if name:
                return name
        return target

    @staticmethod
    def _is_failed_response(response: str) -> bool:
        text = str(response).casefold()
        return (
            text.startswith("не выполнено:")
            or text.startswith("не удалось")
            or text.startswith("не найдено")
            or text.startswith("неоднозначный")
            or "отменено" in text
            or "требуется подтверждение" in text
        )

    @staticmethod
    def _router_action(command_text: str, router=None) -> str | None:
        text = " ".join(str(command_text).casefold().split())

        # Расширенные команды проверяем первыми: например, «найди приложение»
        # иначе общий алиас «найди» ошибочно классифицируется как поиск файла.
        extended = (
            ("media_volume_up", r"^(?:(?:сделай|сделать)?\s*(?:по)?громче|прибавь\s+(?:звук|громкость))"),
            ("media_volume_down", r"^(?:(?:сделай|сделать)?\s*(?:по)?тише|убавь\s+(?:звук|громкость))"),
            ("media_sound_off", r"^(?:(?:выключи|заглуши|выруби|замуть)\s+(?:звук|громкость)|мут|без\s+звука)$"),
            ("media_sound_on", r"^(?:(?:включи|разглуши|вруби|верни|размуть)\s+(?:звук|громкость)|размут)$"),
            ("media_mute_toggle", r"^(?:переключи\s+(?:звук|громкость))$"),
            ("media_mute", r"^(?:(?:выключи|включи|переключи|заглуши|замуть|размуть)\s+(?:звук|громкость)|мут)$"),
            ("media_stop", r"^(?:стоп|stop|(?:стоп|останови(?:ть)?|выключи(?:ть)?)\s+(?:музыку|трек|песню)|музыка\s+стоп)$"),
            ("media_play_pause", r"^(?:(?:пауза|плей|возобнови|останови)\s*(?:музыку|трек|видео)?|play|pause|включи\s+музыку)$"),
            ("media_next", r"^(?:впер[её]д|дальше|скип|скипни|(?:следующий|включи\s+следующий|пропусти|скипни)\s+(?:трек|песню)|следующий\s+трек|музыка\s+впер[её]д)$"),
            ("media_prev", r"^(?:назад|(?:предыдущий|верни)\s+(?:трек|песню)|предыдущий\s+трек|музыка\s+назад)$"),
            ("system_telemetry", r"^(?:(?:телеметри[яи]|нагрузк[аеу]|состояни[ея]|статус|ресурсы|параметры)\s+(?:пк|системы|процессора)|телеметри[яи]|че\s+по\s+нагрузке|сколько\s+(?:памяти|оперативы)|аптайм|время\s+работы(?:\s+(?:пк|системы|компьютера))?|сколько\s+работает(?:\s+(?:пк|комп|система))?)$"),
            ("ollama_start", r"^(?:(?:запусти|запустить|включи|включить|подними|поднять|стартуй|стартовать)\s+(?:сервер\s+)?(?:оллам[ауы]|ollama)|(?:сервер\s+)?(?:оллам[ауы]|ollama)\s+(?:старт|запуск))"),
            ("ollama_stop", r"^(?:(?:останови|остановить|закрой|закрыть|выключи|выключить|заверши|завершить|потуши|потушить)\s+(?:сервер\s+)?(?:оллам[ауы]|ollama)|(?:сервер\s+)?(?:оллам[ауы]|ollama)\s+(?:стоп|остановка))"),
            ("ollama_status", r"^(?:статус\s+(?:оллам[ауы]|ollama)|(?:оллам[ауы]|ollama)\s+статус)$"),
            ("model_unload", r"^(?:выгрузи|выгрузить|освободи|освободить)\s+(?:текущую\s+)?(?:модель|квен[ау]?|квэн[ау]?|qwen|ллм[ку]?)"),
            ("zapret_start", r"^(?:(?:запусти|запустить|включи|включить|стартуй|стартовать)\s+(?:запрет|zapret)|запрет|zapret)$"),
            ("vpn_status", r"^(?:(?:статус|состояние|проверь)\s+(?:vpn|запрет[ау]?|сети)|(?:vpn|запрет)\s+статус)$"),
            ("vpn_connect", r"^(?:(?:включи|включить|подключи|подключить|запусти|запустить)\s+vpn|vpn\s+(?:вкл|старт|подключи)|подключись\s+к\s+vpn)$"),
            ("apply_mouse_settings", r"^(?:(?:настройки|софт|программа)\s+мыши?|(?:примени|нажми\s+применить|активируй)\s+(?:мышь|zet|fury)|мышь|мыш|мышка)$"),
            ("fibonacci_calculator", r"^(?:(?:запусти(?:ть)?\s+)?калькулятор\s+фибоначчи|(?:расчет|числа|ряд)\s+фибоначчи|фибоначчи)$"),
            ("clear_chat", r"^(?:очисти|очистить|сотри)\s+(?:чат|историю|сообщения)$"),
            ("take_screenshot", r"^(?:сделай|сделать)?\s*(?:скриншот|скрин|снимок\s+экрана)$"),
            ("lock_pc", r"^(?:заблокируй|заблочь)\s+(?:пк|комп|компьютер|экран|систему)$"),
            ("date_time", r"^(?:сколько\s+времени|который\s+час|какое\s+сегодня\s+число|какая\s+дата|какой\s+сегодня\s+день(?: недели)?|время|дата)$"),
            ("open_system_folder", r"^(?:открой|открыть)\s+(?:папку\s+)?(загрузки|рабочий\s+стол|документы|видео|музыку|картинки|изображения|проводник|корзину|скриншоты)$"),
            ("empty_recycle_bin", r"^(?:(?:очисти|почисти|очистить|вынеси)\s+(?:корзину|мусор|мусорку)|вынеси\s+мусор)$"),
            ("open_url", r"^(?:открой|открыть)\s+(https?://\S+)"),
            ("open_website", r"^(?:зайди\s+на|открой\s+сайт)\s+(?:[a-zA-Zа-яА-ЯёЁ0-9_\s-]+)"),
            ("create_file", r"^(?:создай|создать)\s+(?:новый\s+)?файл\s+"),
            ("create_folder", r"^(?:создай|создать)\s+(?:новую\s+)?папку\s+"),
            ("write_file", r"^(?:запиши|записать|перезапиши|перезаписать)\s+"),
            ("rename_file", r"^(?:переименуй|переименовать)\s+(?:файл\s+)?"),
            ("copy_file", r"^(?:скопируй|скопировать)\s+(?:файл\s+)?"),
            ("move_file", r"^(?:перемести|переместить)\s+(?:файл\s+)?"),
            ("file_info", r"^(?:информация|сведения|свойства)\s+"),
            ("find_application", r"^(?:найди|найти)\s+(?:приложение|приложения|программу|программа)\s+"),
            ("search_youtube", r"^(?:найди|поищи)\s+(?:на|в)\s+ютуб[еа]?\s+"),
            ("search_yandex", r"^(?:найди|поищи)\s+в\s+яндекс[еа]?\s+"),
            ("search_google", r"^(?:найди|поищи|загугли|гугли|прогугли)\s+(?:в\s+гугл[еа]?\s+)?"),
            ("protocol_stark", r"^(?:(?:(?:джарвис|кириешка|kirieshcka)\s+)?(?:протокол|режим)\s+(?:доброе\s+утро|защита|блокировка|кино|игра|чистый\s+стол|работа|дефолт)|доброе\s+утро|время\s+кино|время\s+играть|чистый\s+стол|к\s+работе)$"),
            ("jarvis_window", r"^(?:свернись|сверни\s+окно|развернись|разверни\s+окно|на\s+весь\s+экран|восстанови\s+окно|верни\s+окно)$"),
            ("open_url", r"^(?:открой|открыть)\s+https?://"),
        )
        for action, pattern in extended:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return action

        if router is not None:
            action = router._resolve_action(command_text)
            if action:
                if action[0] == "launch":
                    target_str = str(action[1]).strip()
                    if getattr(router, "steam_manager", None) and router.steam_manager.resolve_game(action[1]):
                        return "steam_game"
                    if getattr(router, "website_manager", None) and router.website_manager.resolve_url(action[1]):
                        return "open_website"
                    if target_str.startswith(("http://", "https://")):
                        return "open_url"
                return action[0]

        if re.match(r"^(?:открой|открыть|запусти|запустить|включи|включить|стартуй|стартовать|запускай|вруби|врубить)\s+", text):
            return "launch"
        if re.match(r"^(?:закрой|закрыть|останови|остановить|выключи|выключить|заверши|завершить|выруби|вырубить)\s+", text):
            return "close"
        if re.match(r"^(?:найди|найти|поищи|поискать|отыщи|отыскать|разыщи|разыскать|покажи|показать)\s+", text):
            return "search"
        if re.match(r"^(?:прочитай|прочесть|прочитать|прочти|зачитай|зачитать|озвучь|озвучить)\s+", text):
            return "read"
        if re.match(r"^(?:удали|удалить|стереть|сотри|убери|убрать)\s+", text):
            return "delete"
        if re.match(r"^(?:проверь|проверить)\s+", text):
            return "status"
        if re.match(r"^(?:сверни|свернуть|сворачивай)\s+", text):
            return "minimize"
        return None

    @classmethod
    def merge_response(
        cls,
        command_text: str,
        base_response: str,
        router=None,
        action: str | None = None,
        config: dict | None = None,
    ) -> str:
        """Сливает рофлы с базовым ответом, формируя цельную реплику Кириешки."""
        if not base_response or cls._is_failed_response(base_response) or base_response.startswith("[Подтверждение]"):
            return base_response

        action = action or cls._router_action(command_text, router)
        if not action:
            return base_response

        demon_chance = cls.DEFAULT_DEMON_CHANCE
        if config is not None:
            rofl_cfg = config.get("rofl", {}) if isinstance(config, dict) else {}
            demon_chance = cls._clamp_chance(rofl_cfg.get("demon_chance", demon_chance), demon_chance)

        if action == "launch":
            use_demon = random.random() < demon_chance
            if use_demon and cls.DEMON_LINES:
                return random.choice(cls.DEMON_LINES)
            if cls.NORMAL_LINES:
                target_match = re.match(
                    r"^(?:открой|открыть|запусти|запустить|включи|включить|стартуй|стартовать|запускай|вруби|врубить)\s+(.+)",
                    command_text,
                    flags=re.IGNORECASE,
                )
                target = target_match.group(1).strip() if target_match else "приложение"
                template = random.choice(cls.NORMAL_LINES)
                try:
                    return template.format(target=target)
                except Exception:
                    return template.replace("{target}", target)
            return base_response

        if action not in cls.ROUTER_LINES:
            return base_response

        normal_lines, latin_lines = cls.ROUTER_LINES[action]
        use_demon = random.random() < demon_chance and bool(latin_lines)
        rofl = random.choice(latin_lines) if use_demon else random.choice(normal_lines)

        # Информационные команды: выводим рофл в качестве вступления к блоку данных
        if action in ("system_telemetry", "vpn_status", "ollama_status", "file_info", "find_application", "search", "read"):
            return f"{rofl}\n\n{base_response}"
        if action == "date_time":
            if use_demon:
                return f"{base_response}\n\n{rofl}"
            return f"{base_response} {rofl}"

        # Команды закрытия: сохраняем указание на закрытый процесс и добавляем реплику
        if action == "close":
            return f"{base_response} {rofl}"

        # Команды-действия: рофл заменяет сухую базу
        return rofl

    def maybe_router_response(self, command_text: str, response: str, router=None, action: str | None = None):
        """Иногда добавляет рофл к успешному прямому ответу CommandRouter."""
        if not response or self._is_failed_response(response):
            return
        action = action or self._router_action(command_text, router)
        if not action or action not in self.ROUTER_LINES:
            return
        if random.random() >= self.rofl_chance:
            return

        normal_lines, latin_lines = self.ROUTER_LINES[action]
        lines = latin_lines if random.random() < self.demon_chance else normal_lines
        text = random.choice(lines)
        logger.info("router_rofl_response action=%s text=%r command=%r", action, text, command_text)
        self._emit_rofl_response(text)

    def _on_router_rofl_candidate(self, command_text: str, response: str, action: str | None = None):
        self.maybe_router_response(command_text, response, action=action)

    def _on_tool_executed(self, tool_name: str, arguments: dict, result: dict):
        if tool_name != "launch_application" or not result.get("success"):
            return
        if random.random() >= self.rofl_chance:
            return

        if random.random() < self.demon_chance:
            text = random.choice(self.DEMON_LINES)
            category = "demon"
        else:
            text = random.choice(self.NORMAL_LINES).format(
                target=self._display_target(arguments, result)
            )
            category = "normal"

        logger.info(
            "rofl_response category=%s text=%r target=%r",
            category,
            text,
            arguments.get("target"),
        )
        self._emit_rofl_response(text)

    def close(self):
        self.events.unsubscribe("tool.executed", self._on_tool_executed)
        self.events.unsubscribe("router.rofl_candidate", self._on_router_rofl_candidate)
        self.events.unsubscribe("rofl.settings_changed", self._on_settings_changed)

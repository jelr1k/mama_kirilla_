from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.app_paths import WORKSPACE_DIR
from core.version import APP_VERSION
from services.model_service import ModelService
from tools.system_info import get_system_telemetry


logger = logging.getLogger("jarvis.gateway")

RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_APP_NAME = "KirieshckaV2"


def _is_autostart_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, AUTOSTART_APP_NAME)
            return True
    except Exception:
        return False


def _set_autostart(enabled: bool) -> bool:
    try:
        import winreg
        from pathlib import Path
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                launcher = Path(__file__).resolve().parent.parent / "start.bat"
                if not launcher.is_file():
                    launcher = Path(__file__).resolve().parent.parent.parent / "start.bat"
                winreg.SetValueEx(key, AUTOSTART_APP_NAME, 0, winreg.REG_SZ, f'"{launcher}"')
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_APP_NAME)
                except FileNotFoundError:
                    pass
            return True
    except Exception as exc:
        logger.exception("set_autostart_failed: %s", exc)
        return False


class WebSocketHub:
    """Thread-safe WebSocket manager broadcasting events to connected UI clients."""

    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._disconnect_timer: threading.Timer | None = None
        self.on_all_disconnected: Any = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            if self._disconnect_timer:
                self._disconnect_timer.cancel()
                self._disconnect_timer = None
            self._connections.add(websocket)
        logger.info("ui_client_connected clients=%d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.discard(websocket)
            has_remaining = bool(self._connections)
            if not has_remaining and self.on_all_disconnected:
                if self._disconnect_timer:
                    self._disconnect_timer.cancel()
                self._disconnect_timer = threading.Timer(4.0, self.on_all_disconnected)
                self._disconnect_timer.daemon = True
                self._disconnect_timer.start()
        logger.info("ui_client_disconnected clients=%d", len(self._connections))

    @property
    def has_clients(self) -> bool:
        with self._lock:
            return bool(self._connections)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """Thread-safe broadcast called from any worker thread."""
        if not self._connections or self._loop is None or self._loop.is_closed():
            return

        message = json.dumps(payload, ensure_ascii=False)

        async def _send_all():
            with self._lock:
                targets = list(self._connections)
            dead = []
            for ws in targets:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            if dead:
                with self._lock:
                    for d in dead:
                        self._connections.discard(d)

        try:
            asyncio.run_coroutine_threadsafe(_send_all(), self._loop)
        except Exception as exc:
            logger.debug("broadcast_enqueue_failed error=%s", exc)


class GatewayService:
    """FastAPI & WebSocket gateway bridging Jarvis core to modern web / Tauri UIs."""

    def __init__(self, app_context: Any, host: str = "127.0.0.1", port: int = 8765):
        self.app_context = app_context
        self.host = host
        self.port = port
        self.hub = WebSocketHub()

        def _handle_auto_shutdown():
            logger.info("all_ui_clients_disconnected_shutting_down_backend")
            try:
                if hasattr(self.app_context, "shutdown"):
                    self.app_context.shutdown()
            finally:
                os._exit(0)

        self.hub.on_all_disconnected = _handle_auto_shutdown
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._telemetry_thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()

        self.fastapi_app = FastAPI(title="Kirieshcka v2 Gateway", version=APP_VERSION)

        # Standalone Updater components
        from services.update_downloader import UpdateDownloader
        from services.update_validator import UpdateValidator
        from services.update_backup import UpdateBackupService
        from services.update_relauncher import UpdateRelauncher

        self._update_downloader = UpdateDownloader()
        self._update_validator = UpdateValidator()
        self._update_backup = UpdateBackupService()
        self._update_relauncher = UpdateRelauncher()
        self._current_update_plan = None
        self._update_state = {
            "status": "idle",
            "progress_percent": 0,
            "download_speed_mb": 0.0,
            "error": None,
        }
        self._model_download_states: dict[str, str] = {}
        self._model_download_errors: dict[str, str] = {}

        self._setup_middleware()
        self._setup_routes()
        self._setup_event_subscriptions()

    def _setup_middleware(self) -> None:
        self.fastapi_app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https?://tauri\.localhost$|^tauri://localhost$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self) -> None:
        @self.fastapi_app.get("/health")
        def health_check():
            return {
                "status": "ok",
                "app": "Kirieshcka v2",
                "version": APP_VERSION,
                "timestamp": time.time(),
            }

        @self.fastapi_app.get("/api/status")
        def assistant_status():
            cfg = getattr(self.app_context, "config", None)
            model = cfg.get("model", "unknown") if cfg else "unknown"
            name = cfg.get("assistant_name", "Kirieshcka") if cfg else "Kirieshcka"
            voice_cfg = cfg.get("voice", {}) if cfg else {}

            voice_service = getattr(self.app_context, "voice_service", None)
            is_recording = voice_service.is_recording if voice_service else False
            is_transcribing = voice_service.transcribing() if voice_service else False

            wake_word_detector = getattr(self.app_context, "wake_word_detector", None)
            wake_word_running = wake_word_detector.is_running() if wake_word_detector else False

            return {
                "assistant_name": name,
                "model": model,
                "wake_word_enabled": voice_cfg.get("wake_word_enabled", True),
                "wake_word_running": wake_word_running,
                "is_recording": is_recording,
                "is_transcribing": is_transcribing,
            }

        @self.fastapi_app.get("/api/telemetry")
        def telemetry():
            return get_system_telemetry()

        @self.fastapi_app.get("/api/commands")
        def commands_catalog():
            chat_service = getattr(self.app_context, "chat_service", None)
            if chat_service and hasattr(chat_service, "router"):
                return {"commands": chat_service.router.command_catalog()}
            return {"commands": []}

        @self.fastapi_app.get("/api/settings")
        def get_settings():
            cfg = getattr(self.app_context, "config", None)
            return {"settings": cfg.data if cfg and hasattr(cfg, "data") else {}}

        @self.fastapi_app.post("/api/settings")
        def update_settings(payload: dict[str, Any]):
            cfg = getattr(self.app_context, "config", None)
            if not cfg:
                return {"success": False, "error": "ConfigManager unavailable"}
            for k, v in payload.items():
                cfg.set(k, v)
            cfg.save()
            if hasattr(self.app_context, "apply_settings"):
                self.app_context.apply_settings()
            name = cfg.get("assistant_name", "Kirieshcka")
            model = cfg.get("model", "")
            app_title = cfg.get("app_title", "Kirieshcka v2")
            self.hub.broadcast({
                "type": "state",
                "assistant_name": name,
                "model": model,
                "app_title": app_title,
            })
            return {"success": True}

        @self.fastapi_app.post("/api/chat")
        def send_chat(payload: dict[str, Any]):
            text = payload.get("text", "").strip()
            if not text:
                return {"success": False, "error": "Empty message"}
            chat_service = getattr(self.app_context, "chat_service", None)
            if not chat_service:
                return {"success": False, "error": "ChatService unavailable"}
            chat_service.send(text)
            return {"success": True}

        @self.fastapi_app.post("/api/shutdown")
        def shutdown_app():
            logger.info("api_shutdown_requested")
            def _delayed_exit():
                time.sleep(0.3)
                try:
                    if hasattr(self.app_context, "shutdown"):
                        self.app_context.shutdown()
                finally:
                    os._exit(0)
            threading.Thread(target=_delayed_exit, daemon=True).start()
            return {"success": True, "message": "Shutting down"}

        @self.fastapi_app.get("/api/autostart")
        def get_autostart():
            return {"enabled": _is_autostart_enabled()}

        @self.fastapi_app.post("/api/autostart")
        def set_autostart_route(payload: dict[str, Any]):
            enabled = bool(payload.get("enabled", False))
            success = _set_autostart(enabled)
            return {"success": success, "enabled": enabled}

        @self.fastapi_app.get("/api/updates")
        def check_updates():
            checker = getattr(self.app_context, "update_checker", None)
            service = getattr(self.app_context, "update_service", None)
            current_ver = APP_VERSION
            latest_ver = APP_VERSION
            has_update = False
            html_url = "https://github.com/jelr1k/mama_kirilla_/releases"
            archive_name = ""
            archive_size = 0

            if checker:
                try:
                    info = checker.check()
                    current_ver = getattr(info, "current_version", APP_VERSION)
                    latest_ver = getattr(info, "latest_version", current_ver)
                    has_update = bool(getattr(info, "update_available", False))
                    html_url = getattr(info, "release_url", html_url)
                    if has_update and service:
                        try:
                            plan = service.prepare(info)
                            self._current_update_plan = plan
                            archive_name = getattr(plan, "asset_name", "")
                            archive_size = getattr(plan, "asset_size", 0)
                        except Exception as exc:
                            logger.warning("prepare_update_plan_failed: %s", exc)
                except Exception as exc:
                    logger.warning("check_update_failed: %s", exc)

            return {
                "has_update": has_update,
                "current_version": current_ver,
                "latest_version": latest_ver,
                "html_url": html_url,
                "plan_available": bool(self._current_update_plan),
                "archive_name": archive_name,
                "archive_size": archive_size,
                "status": self._update_state["status"],
                "progress_percent": self._update_state["progress_percent"],
                "download_speed_mb": self._update_state["download_speed_mb"],
                "error": self._update_state["error"],
            }

        @self.fastapi_app.post("/api/updates/check")
        def force_check_updates():
            return check_updates()

        @self.fastapi_app.post("/api/updates/apply")
        def apply_update():
            if not self._current_update_plan:
                checker = getattr(self.app_context, "update_checker", None)
                service = getattr(self.app_context, "update_service", None)
                if checker and service:
                    try:
                        info = checker.check()
                        if getattr(info, "update_available", False):
                            self._current_update_plan = service.prepare(info)
                    except Exception as e:
                        return {"success": False, "error": f"Не удалось подготовить обновление: {e}"}

            if not self._current_update_plan:
                return {"success": False, "error": "Нет доступного плана обновления для установки"}

            if self._update_state["status"] in ("downloading", "validating", "backing_up", "relaunching"):
                return {"success": False, "error": f"Обновление уже выполняется (статус: {self._update_state['status']})"}

            threading.Thread(target=self._apply_update_worker, daemon=True).start()
            return {"success": True, "message": "Процесс обновления запущен в фоне"}

        @self.fastapi_app.post("/api/ollama/restart")
        def restart_ollama():
            ollama_mgr = getattr(self.app_context, "ollama_manager", None)
            if ollama_mgr:
                try:
                    res = ollama_mgr.start()
                    return {"success": True, "result": res}
                except Exception as exc:
                    return {"success": False, "error": str(exc)}
            return {"success": False, "error": "OllamaManager unavailable"}

        @self.fastapi_app.post("/api/ollama/unload")
        def unload_ollama():
            ollama_mgr = getattr(self.app_context, "ollama_manager", None)
            cfg = getattr(self.app_context, "config", None)
            target_model = cfg.get("model", "") if cfg else ""
            unloaded = []
            if ollama_mgr:
                try:
                    # 1. Unload from tracked models
                    res = ollama_mgr.unload_models()
                    for r in res:
                        if isinstance(r, dict) and r.get("model"):
                            unloaded.append(r["model"])

                    # 2. Query /api/ps to make sure any active model is purged
                    loaded = ollama_mgr.get_loaded_models()
                    for item in loaded:
                        name = item.get("name") or item.get("model")
                        if name and name not in unloaded:
                            ollama_mgr.unload_model(name)
                            unloaded.append(name)

                    # 3. Explicitly unload target model if present
                    if target_model and target_model not in unloaded:
                        ollama_mgr.unload_model(target_model)
                        unloaded.append(target_model)

                    return {
                        "success": True,
                        "unloaded": unloaded,
                        "message": f"Модель {', '.join(unloaded)} выгружена из памяти видеокарты" if unloaded else "Все модели выгружены из памяти"
                    }
                except Exception as exc:
                    return {"success": False, "error": str(exc)}
            return {"success": False, "error": "OllamaManager недоступен"}

        @self.fastapi_app.post("/api/tts/test")
        def test_tts(payload: dict[str, Any]):
            tts = getattr(self.app_context, "tts_service", None)
            text = payload.get("text", "Тест синтеза речи Кириешка")
            if tts:
                try:
                    tts.speak(text)
                    return {"success": True}
                except Exception as exc:
                    return {"success": False, "error": str(exc)}
            return {"success": False, "error": "TTSService unavailable"}

        @self.fastapi_app.post("/api/microphones/test")
        def test_mic(payload: dict[str, Any]):
            voice = getattr(self.app_context, "voice_service", None)
            device = payload.get("device")
            if voice and hasattr(voice, "test_microphone"):
                try:
                    return voice.test_microphone(device)
                except Exception as exc:
                    return {"success": False, "error": str(exc)}
            return {"success": False, "error": "VoiceService unavailable"}

        @self.fastapi_app.get("/api/microphones")
        def get_microphones():
            voice_service = getattr(self.app_context, "voice_service", None)
            if voice_service and hasattr(voice_service, "list_microphones"):
                return voice_service.list_microphones()
            return {"success": False, "devices": []}

        @self.fastapi_app.get("/api/models")
        def get_models():
            model_service = ModelService(getattr(self.app_context, "provider", None)) if hasattr(self.app_context, "provider") else None
            ollama_models = []
            if model_service:
                try:
                    res = model_service.get_available_models()
                    ollama_models = res.get("models", [])
                except Exception:
                    pass
            cfg = getattr(self.app_context, "config", None)
            current_model = cfg.get("model", "") if cfg else ""
            if not current_model and ollama_models:
                current_model = ollama_models[0]
            elif not current_model:
                current_model = "qwen3:1.7b"

            ollama_mgr = getattr(self.app_context, "ollama_manager", None)
            loaded_models = []
            if ollama_mgr:
                try:
                    loaded = ollama_mgr.get_loaded_models()
                    loaded_models = [m.get("name") or m.get("model") for m in loaded if isinstance(m, dict)]
                except Exception:
                    pass

            return {
                "current_model": current_model,
                "loaded_models": loaded_models,
                "ollama_models": ollama_models,
                "whisper_models": ["small", "medium", "large-v3", "custom"],
                "tts_voices": [
                    {"id": "ru_RU-dmitri-medium", "name": "Дмитрий (medium)"},
                    {"id": "ru_RU-irina-medium", "name": "Ирина (medium)"},
                    {"id": "ru_RU-ruslan-medium", "name": "Руслан (medium)"},
                ],
            }

        @self.fastapi_app.get("/api/whisper/status")
        def whisper_models_status():
            dep = getattr(self.app_context, "dependency_manager", None)
            models = ["small", "medium", "large-v3"]
            statuses = {}
            errors = {}
            for m in models:
                key = f"whisper:{m}"
                state = self._model_download_states.get(key)
                if state:
                    statuses[m] = state
                elif dep:
                    statuses[m] = dep.whisper_status(m)
                else:
                    statuses[m] = "unknown"
                if key in self._model_download_errors:
                    errors[m] = self._model_download_errors[key]
            return {"statuses": statuses, "errors": errors}

        @self.fastapi_app.post("/api/whisper/download")
        def download_whisper_model(payload: dict[str, Any]):
            model = payload.get("model", "").strip()
            dep = getattr(self.app_context, "dependency_manager", None)
            if not dep:
                return {"success": False, "error": "DependencyManager unavailable"}
            key = f"whisper:{model}"
            self._model_download_states[key] = "downloading"
            self._model_download_errors.pop(key, None)
            def _dl():
                try:
                    dep.ensure_whisper_model(model)
                    self._model_download_states[key] = "installed"
                except Exception as exc:
                    logger.exception("whisper_download_failed model=%s", model)
                    self._model_download_states[key] = "failed"
                    self._model_download_errors[key] = str(exc)
            threading.Thread(target=_dl, daemon=True).start()
            return {"success": True, "message": f"Downloading {model} started in background"}

        @self.fastapi_app.get("/api/tts/status")
        def tts_voices_status():
            tts = getattr(self.app_context, "tts_service", None)
            voices = ["ru_RU-dmitri-medium", "ru_RU-irina-medium", "ru_RU-ruslan-medium"]
            statuses = {}
            errors = {}
            for v in voices:
                key = f"tts:{v}"
                state = self._model_download_states.get(key)
                if state:
                    statuses[v] = state
                elif tts:
                    statuses[v] = tts.voice_status(v)
                else:
                    statuses[v] = "missing"
                if key in self._model_download_errors:
                    errors[v] = self._model_download_errors[key]
            return {"statuses": statuses, "errors": errors}

        @self.fastapi_app.post("/api/tts/download")
        def download_tts_voice(payload: dict[str, Any]):
            voice_id = payload.get("voice", "").strip()
            tts = getattr(self.app_context, "tts_service", None)
            if not tts:
                return {"success": False, "error": "TTSService unavailable"}
            key = f"tts:{voice_id}"
            self._model_download_states[key] = "downloading"
            self._model_download_errors.pop(key, None)
            def _dl():
                try:
                    tts.ensure_voice(voice_id)
                    self._model_download_states[key] = "installed"
                except Exception as exc:
                    logger.exception("tts_voice_download_failed voice=%s", voice_id)
                    self._model_download_states[key] = "failed"
                    self._model_download_errors[key] = str(exc)
            threading.Thread(target=_dl, daemon=True).start()
            return {"success": True, "message": f"Downloading voice {voice_id} started in background"}

        @self.fastapi_app.get("/api/aliases")
        def get_aliases(category: str | None = None):
            alias_mgr = getattr(self.app_context, "alias_manager", None)
            if not alias_mgr:
                return {"aliases": []}
            return {"aliases": alias_mgr.list_objects(category)}

        @self.fastapi_app.post("/api/aliases")
        def save_aliases(payload: dict[str, Any]):
            alias_mgr = getattr(self.app_context, "alias_manager", None)
            if not alias_mgr:
                return {"success": False, "error": "AliasManager unavailable"}
            category = payload.get("category", "applications")
            target = payload.get("target", "").strip()
            aliases = payload.get("aliases", [])
            if not target:
                return {"success": False, "error": "Target is required"}
            alias_mgr.set_aliases(category, target, aliases)
            alias_mgr.save()
            return {"success": True}

        @self.fastapi_app.delete("/api/aliases")
        def delete_alias(payload: dict[str, Any]):
            alias_mgr = getattr(self.app_context, "alias_manager", None)
            if not alias_mgr:
                return {"success": False, "error": "AliasManager unavailable"}
            category = payload.get("category", "applications")
            target = payload.get("target", "").strip()
            alias_mgr.remove_object(category, target)
            alias_mgr.save()
            return {"success": True}

        @self.fastapi_app.get("/api/workspace")
        def get_workspace():
            from core.workspace_view_model import WorkspaceViewModel
            alias_mgr = getattr(self.app_context, "alias_manager", None)
            vm = WorkspaceViewModel(WORKSPACE_DIR, alias_mgr)
            items = []
            try:
                for obj in vm.refresh():
                    items.append({
                        "name": obj.entry.name,
                        "path": obj.entry.relative_path,
                        "category": obj.entry.category,
                        "exists": obj.entry.path.exists(),
                        "is_dir": obj.entry.is_dir,
                        "user_aliases": list(obj.user_aliases),
                        "automatic_aliases": list(obj.automatic_aliases),
                    })
            except Exception as exc:
                logger.debug("workspace_refresh_failed: %s", exc)
            return {"workspace_dir": str(WORKSPACE_DIR), "items": items}

        @self.fastapi_app.post("/api/workspace/open")
        def open_workspace():
            try:
                os.startfile(WORKSPACE_DIR)
                return {"success": True}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        @self.fastapi_app.post("/api/commands/execute")
        def execute_command(payload: dict[str, Any]):
            cmd = payload.get("command", "").strip()
            if not cmd:
                return {"success": False, "error": "Empty command"}
            chat_service = getattr(self.app_context, "chat_service", None)
            if chat_service:
                chat_service.send(cmd)
                return {"success": True}
            return {"success": False, "error": "ChatService unavailable"}

        # Websites management
        @self.fastapi_app.get("/api/websites")
        def list_websites():
            mgr = getattr(self.app_context, "website_manager", None)
            if not mgr:
                return {"websites": []}
            return {"websites": mgr.get_websites()}

        @self.fastapi_app.post("/api/websites")
        def create_website(payload: dict[str, Any]):
            mgr = getattr(self.app_context, "website_manager", None)
            if not mgr:
                return {"success": False, "error": "WebsiteManager not available"}
            name = payload.get("name", "").strip()
            url = payload.get("url", "").strip()
            aliases = payload.get("aliases", [])
            auto_aliases = bool(payload.get("auto_aliases", True))
            if not name or not url:
                return {"success": False, "error": "Name and URL are required"}
            try:
                entry = mgr.add_website(name, url, aliases=aliases, auto_aliases=auto_aliases)
                return {"success": True, "website": entry}
            except Exception as exc:
                logger.exception("create_website_failed")
                return {"success": False, "error": str(exc)}

        @self.fastapi_app.put("/api/websites/{site_id}")
        def update_website(site_id: str, payload: dict[str, Any]):
            mgr = getattr(self.app_context, "website_manager", None)
            if not mgr:
                return {"success": False, "error": "WebsiteManager not available"}
            name = payload.get("name", "").strip()
            url = payload.get("url", "").strip()
            aliases = payload.get("aliases", [])
            success = mgr.update_website(site_id, name, url, aliases)
            return {"success": success}

        @self.fastapi_app.delete("/api/websites/{site_id}")
        def delete_website(site_id: str):
            mgr = getattr(self.app_context, "website_manager", None)
            if not mgr:
                return {"success": False, "error": "WebsiteManager not available"}
            success = mgr.delete_website(site_id)
            return {"success": success}

        @self.fastapi_app.post("/api/websites/open")
        def open_website(payload: dict[str, Any]):
            import webbrowser
            url = payload.get("url", "").strip()
            site_id = payload.get("site_id", "").strip()
            mgr = getattr(self.app_context, "website_manager", None)
            if site_id and mgr:
                for s in mgr.get_websites():
                    if s.get("id") == site_id:
                        url = s.get("url", "")
                        break
            if not url:
                return {"success": False, "error": "URL or site_id is required"}
            try:
                webbrowser.open(url)
                return {"success": True}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        @self.fastapi_app.post("/api/websites/reset")
        def reset_websites():
            mgr = getattr(self.app_context, "website_manager", None)
            if mgr:
                mgr.reset_to_defaults()
                return {"success": True, "websites": mgr.get_websites()}
            return {"success": False}

        # Tools & Permissions
        @self.fastapi_app.get("/api/tools")
        def list_tools():
            from tools.registry import TOOLS
            perm = getattr(self.app_context, "permission_manager", None)
            tool_names = {
                "search_files": "Поиск файлов",
                "read_file": "Чтение файла",
                "create_file": "Создание файла",
                "write_file": "Запись файла",
                "delete_file": "Удаление файла",
                "rename_file": "Переименование файла",
                "copy_file": "Копирование файла",
                "move_file": "Перемещение файла",
                "create_folder": "Создание папки",
                "file_info": "Информация о файле",
                "find_application": "Поиск приложения",
                "get_process_status": "Проверка состояния процесса",
                "launch_application": "Запуск приложения",
                "minimize_application": "Сворачивание приложения",
                "close_application": "Закрытие приложения",
                "open_url": "Открытие ссылки",
                "get_system_telemetry": "Системная телеметрия",
                "control_media": "Управление медиа и звуком",
                "empty_recycle_bin": "Очистка корзины",
                "get_current_time_date": "Текущее время и дата",
                "lock_pc": "Блокировка ПК",
                "open_system_folder": "Открытие системных папок",
                "take_screenshot": "Снимок экрана",
            }
            items = []
            for name, tool in TOOLS.items():
                enabled = perm.is_enabled(name) if perm else True
                items.append({
                    "name": name,
                    "title": tool_names.get(name, name),
                    "description": tool.get("description", ""),
                    "enabled": enabled,
                    "requires_confirmation": bool(tool.get("requires_confirmation", False)),
                })
            return {"tools": items}

        @self.fastapi_app.post("/api/tools/permission")
        def set_tool_permission(payload: dict[str, Any]):
            tool_name = payload.get("tool", "").strip()
            enabled = bool(payload.get("enabled", True))
            perm = getattr(self.app_context, "permission_manager", None)
            if not perm:
                return {"success": False, "error": "PermissionManager not available"}
            try:
                perm.update(tool_name, enabled)
                return {"success": True, "tool": tool_name, "enabled": enabled}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        # Statistics & Real Measurements
        @self.fastapi_app.get("/api/statistics")
        def get_statistics():
            stats_svc = getattr(self.app_context, "statistics_service", None)
            latest_llm = None
            latest_whisper = None
            history = []
            if stats_svc:
                if stats_svc.latest:
                    s = stats_svc.latest
                    latest_llm = {
                        "model": getattr(s, "model", ""),
                        "input_tokens": getattr(s, "input_tokens", 0),
                        "output_tokens": getattr(s, "output_tokens", 0),
                        "total_tokens": getattr(s, "total_tokens", 0),
                        "generation_time_s": getattr(s, "generation_time_s", 0.0),
                        "generation_speed_tps": getattr(s, "generation_speed_tps", 0.0),
                        "total_time_s": getattr(s, "total_time_s", 0.0),
                        "load_time_s": getattr(s, "load_time_s", 0.0),
                        "prompt_eval_time_s": getattr(s, "prompt_eval_time_s", 0.0),
                        "ttft_s": getattr(s, "ttft_s", 0.0),
                        "thinking": getattr(s, "thinking", False),
                    }
                if stats_svc.latest_whisper:
                    w = stats_svc.latest_whisper
                    latest_whisper = {
                        "model": getattr(w, "model", ""),
                        "beam_size": getattr(w, "beam_size", 0),
                        "model_load_time_s": getattr(w, "model_load_time_s", 0.0),
                        "audio_duration_s": getattr(w, "audio_duration_s", 0.0),
                        "transcription_time_s": getattr(w, "transcription_time_s", 0.0),
                        "total_time_s": getattr(w, "total_time_s", 0.0),
                        "real_time_factor": getattr(w, "real_time_factor", 0.0),
                        "cpu_threads": getattr(w, "cpu_threads", 0),
                        "device": getattr(w, "device", ""),
                    }
                for item in reversed(stats_svc.history[-25:]):
                    history.append({
                        "model": getattr(item, "model", ""),
                        "total_tokens": getattr(item, "total_tokens", 0),
                        "generation_speed_tps": round(getattr(item, "generation_speed_tps", 0.0), 2),
                        "total_time_s": round(getattr(item, "total_time_s", 0.0), 3),
                        "generation_time_s": round(getattr(item, "generation_time_s", 0.0), 3),
                    })

            telemetry = {}
            try:
                telemetry = get_system_telemetry()
            except Exception:
                pass

            return {
                "latest_llm": latest_llm,
                "latest_whisper": latest_whisper,
                "telemetry": telemetry,
                "history": history,
            }

        # ROFL Settings with secret word
        @self.fastapi_app.get("/api/rofl")
        def get_rofl_settings():
            cfg = getattr(self.app_context, "config", None)
            rofl_cfg = cfg.get("rofl", {}) if cfg else {}
            return {
                "chance": float(rofl_cfg.get("chance", 0.12)),
                "demon_chance": float(rofl_cfg.get("demon_chance", 0.15)),
            }

        @self.fastapi_app.post("/api/rofl/verify")
        def verify_rofl_secret(payload: dict[str, Any]):
            secret = str(payload.get("secret", "")).strip().casefold()
            if secret == "джарвис":
                cfg = getattr(self.app_context, "config", None)
                rofl_cfg = cfg.get("rofl", {}) if cfg else {}
                return {
                    "success": True,
                    "unlocked": True,
                    "chance": float(rofl_cfg.get("chance", 0.12)),
                    "demon_chance": float(rofl_cfg.get("demon_chance", 0.15)),
                }
            return {"success": False, "unlocked": False, "error": "Неверное служебное слово"}

        @self.fastapi_app.post("/api/rofl")
        def update_rofl_settings(payload: dict[str, Any]):
            secret = str(payload.get("secret", "")).strip().casefold()
            if secret != "джарвис":
                return {"success": False, "error": "Неверное служебное слово"}
            chance = max(0.0, min(1.0, float(payload.get("chance", 0.12))))
            demon_chance = max(0.0, min(1.0, float(payload.get("demon_chance", 0.15))))
            cfg = getattr(self.app_context, "config", None)
            if cfg:
                rofl_dict = cfg.data.setdefault("rofl", {})
                rofl_dict["chance"] = chance
                rofl_dict["demon_chance"] = demon_chance
                cfg.save()
            events = getattr(self.app_context, "events", None)
            if events:
                events.emit("rofl.settings_changed", {"chance": chance, "demon_chance": demon_chance})
            return {
                "success": True,
                "chance": chance,
                "demon_chance": demon_chance,
            }

        @self.fastapi_app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.hub.connect(websocket)
            try:
                # Send initial state snapshot on connect
                await websocket.send_text(
                    json.dumps({
                        "type": "state",
                        "assistant_name": getattr(self.app_context, "config", {}).get("assistant_name", "Kirieshcka"),
                        "app_title": getattr(self.app_context, "config", {}).get("app_title", "Kirieshcka v2"),
                        "model": getattr(self.app_context, "config", {}).get("model", ""),
                        "telemetry": get_system_telemetry(),
                    }, ensure_ascii=False)
                )

                while True:
                    data_str = await websocket.receive_text()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    action = data.get("action") or data.get("type")
                    self._handle_client_action(action, data)
            except WebSocketDisconnect:
                self.hub.disconnect(websocket)
            except Exception as exc:
                logger.debug("websocket_exception error=%s", exc)
                self.hub.disconnect(websocket)

        # Mount pre-built React UI if available
        from pathlib import Path
        candidate_dist = Path(__file__).resolve().parent.parent / "ui" / "dist"
        if candidate_dist.is_dir() and (candidate_dist / "index.html").is_file():
            try:
                from fastapi.staticfiles import StaticFiles
                self.fastapi_app.mount("/", StaticFiles(directory=str(candidate_dist), html=True), name="static_ui")
                logger.info("mounted_static_ui dist=%s", candidate_dist)
            except Exception as exc:
                logger.warning("failed_to_mount_static_ui error=%s", exc)

    def _apply_update_worker(self) -> None:
        """Run download -> validate -> backup -> relaunch pipeline in background."""
        from core.app_paths import APP_ROOT, APP_DATA_DIR
        plan = self._current_update_plan
        if not plan:
            self._update_state["status"] = "error"
            self._update_state["error"] = "План обновления не подготовлен"
            self.hub.broadcast({"type": "update_status", **self._update_state})
            return

        self._update_state["status"] = "downloading"
        self._update_state["progress_percent"] = 0
        self._update_state["error"] = None
        self.hub.broadcast({"type": "update_status", **self._update_state})

        def progress(current, total, speed):
            pct = int((current / total) * 100) if total > 0 else 0
            self._update_state["progress_percent"] = pct
            self._update_state["download_speed_mb"] = round(speed / (1024 * 1024), 2)
            self.hub.broadcast({
                "type": "update_progress",
                "progress_percent": pct,
                "download_speed_mb": self._update_state["download_speed_mb"],
                "current_bytes": current,
                "total_bytes": total,
            })

        download_result = None
        try:
            download_result = self._update_downloader.download(plan, progress_callback=progress)
            self._update_state["status"] = "validating"
            self.hub.broadcast({"type": "update_status", **self._update_state})

            self._update_validator.validate(
                download_result.archive_path,
                download_result.expected_size,
            )

            self._update_state["status"] = "backing_up"
            self.hub.broadcast({"type": "update_status", **self._update_state})

            backup_result = self._update_backup.create_backup(
                APP_ROOT,
                preserve_paths=(APP_DATA_DIR,),
            )

            self._update_state["status"] = "relaunching"
            self.hub.broadcast({"type": "update_status", **self._update_state})

            relaunch_plan = self._update_relauncher.prepare(
                APP_ROOT,
                download_result.archive_path,
                download_result.expected_size,
                backup_application=backup_result.application_backup,
                expected_version=getattr(plan, "target_version", ""),
            )
            self._update_relauncher.launch(relaunch_plan)

            logger.info("updater_process_launched_shutting_down_jarvis")
            def _exit():
                time.sleep(1.2)
                try:
                    if hasattr(self.app_context, "shutdown"):
                        self.app_context.shutdown()
                except Exception:
                    pass
                os._exit(0)

            threading.Thread(target=_exit, daemon=True).start()

        except Exception as exc:
            logger.exception("apply_update_failed: %s", exc)
            if download_result is not None:
                try:
                    self._update_downloader.cleanup(download_result)
                except Exception:
                    pass
            self._update_state["status"] = "error"
            self._update_state["error"] = str(exc)
            self.hub.broadcast({"type": "update_status", **self._update_state})

    def _handle_client_action(self, action: str | None, data: dict[str, Any]) -> None:
        """Handle incoming actions from the frontend UI."""
        if not action:
            return

        if action == "chat.send":
            text = str(data.get("text", "")).strip()
            thinking = bool(data.get("thinking", False))
            chat_service = getattr(self.app_context, "chat_service", None)
            if text and chat_service:
                try:
                    chat_service.send(text, thinking)
                except TypeError:
                    chat_service.send(text)

        elif action == "voice.start":
            voice = getattr(self.app_context, "voice_service", None)
            if voice:
                wake_word = getattr(self.app_context, "wake_word_detector", None)
                if wake_word and wake_word.is_running():
                    wake_word.stop()
                voice.start()

        elif action == "voice.stop":
            voice = getattr(self.app_context, "voice_service", None)
            if voice:
                voice.stop()

        elif action == "tts.stop":
            tts = getattr(self.app_context, "tts_service", None)
            if tts:
                tts.stop()

        elif action == "wake_word.toggle":
            enabled = bool(data.get("enabled", True))
            wake_word = getattr(self.app_context, "wake_word_detector", None)
            if wake_word:
                if enabled:
                    wake_word.start()
                else:
                    wake_word.stop()

        elif action == "telemetry.get":
            self.hub.broadcast({"type": "telemetry", "data": get_system_telemetry()})

        elif action == "app.quit":
            logger.info("action_app_quit_received")
            def _delayed_exit():
                time.sleep(0.3)
                try:
                    if hasattr(self.app_context, "shutdown"):
                        self.app_context.shutdown()
                finally:
                    os._exit(0)
            threading.Thread(target=_delayed_exit, daemon=True).start()

    def _setup_event_subscriptions(self) -> None:
        events = getattr(self.app_context, "events", None)
        if not events:
            return

        events.subscribe("wake_word.detected", self._on_wake_word_detected)
        events.subscribe("wake_word.recognized", lambda p: self.hub.broadcast({"type": "wake_word.recognized", "text": p}))
        events.subscribe("wake_word.status", lambda s: self.hub.broadcast({"type": "wake_word.status", "status": s}))
        events.subscribe("wake_word.listening_changed", lambda a: self.hub.broadcast({"type": "wake_word.listening", "active": a}))

        def _on_whisper_stats(s):
            from dataclasses import is_dataclass, asdict
            s_dict = asdict(s) if is_dataclass(s) else (s if isinstance(s, dict) else {})
            self.hub.broadcast({"type": "voice.whisper_stats", "stats": s_dict})

        def _on_chat_chunk(chunk):
            chunk_text = getattr(chunk, "text", str(chunk))
            thinking = getattr(chunk, "thinking", "")
            self.hub.broadcast({
                "type": "chat.chunk",
                "chunk": chunk_text,
                "text": chunk_text,
                "thinking": thinking,
            })

        def _on_gen_finished(stats):
            from dataclasses import is_dataclass, asdict
            stats_dict = asdict(stats) if is_dataclass(stats) else (stats if isinstance(stats, dict) else {})
            self.hub.broadcast({"type": "chat.status", "status": "idle", "stats": stats_dict})

        events.subscribe("voice.listening_changed", lambda a: self.hub.broadcast({"type": "voice.listening", "active": a}))
        events.subscribe("voice.transcribing_changed", lambda a: self.hub.broadcast({"type": "voice.transcribing", "active": a}))
        events.subscribe("voice.transcript_ready", self._on_voice_transcription_finished)
        events.subscribe("voice.whisper_stats", _on_whisper_stats)
        events.subscribe("voice.error", lambda err: self.hub.broadcast({"type": "voice.error", "error": str(err)}))

        events.subscribe("chat.generation_started", lambda req: self.hub.broadcast({"type": "chat.status", "status": "thinking"}))
        events.subscribe("chat.chunk", _on_chat_chunk)
        events.subscribe("chat.direct_response", lambda text: self.hub.broadcast({"type": "chat.response", "text": text}))
        events.subscribe("chat.rofl_response", lambda text: self.hub.broadcast({"type": "chat.response", "text": text, "is_rofl": True}))
        events.subscribe("chat.generation_finished", _on_gen_finished)
        events.subscribe("chat.error", lambda err: self.hub.broadcast({"type": "chat.error", "error": str(err)}))

        events.subscribe("tts.state_changed", lambda state, msg: self.hub.broadcast({"type": "tts.state", "state": state, "message": msg}))

    def _on_wake_word_detected(self, wake_word: str) -> None:
        logger.info("gateway_wake_word_detected wake_word=%s", wake_word)
        self.hub.broadcast({"type": "wake_word.detected", "word": wake_word})
        # Automatically stop wake word and activate voice recording
        wake_word_detector = getattr(self.app_context, "wake_word_detector", None)
        voice_service = getattr(self.app_context, "voice_service", None)
        if wake_word_detector:
            wake_word_detector.stop()
        if voice_service:
            # Short delay to avoid picking up the tail of the wake word utterance
            threading.Timer(0.12, voice_service.start).start()

    def _on_voice_transcription_finished(self, text: str) -> None:
        self.hub.broadcast({"type": "voice.transcription", "text": text})
        # Automatically send transcribed command to chat service
        chat_service = getattr(self.app_context, "chat_service", None)
        if text and chat_service:
            chat_service.send(text)

        # Resume wake word detector if enabled
        wake_word_detector = getattr(self.app_context, "wake_word_detector", None)
        cfg = getattr(self.app_context, "config", None)
        wake_word_enabled = cfg.get("voice", {}).get("wake_word_enabled", True) if cfg else True
        if wake_word_detector and wake_word_enabled:
            threading.Timer(0.3, wake_word_detector.start).start()

    def start(self) -> None:
        """Launch uvicorn server and telemetry ticker in background threads."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()

        import sys
        if sys.stdout is None:
            class _NullStream:
                def write(self, *a, **k): pass
                def flush(self): pass
                def isatty(self): return False
            sys.stdout = _NullStream()
        if sys.stderr is None:
            sys.stderr = sys.stdout

        config = uvicorn.Config(
            app=self.fastapi_app,
            host=self.host,
            port=self.port,
            log_config=None,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.hub.set_loop(loop)
            loop.run_until_complete(self._server.serve())

        self._server_thread = threading.Thread(target=_run_server, name="GatewayUvicornThread", daemon=True)
        self._server_thread.start()

        def _telemetry_ticker():
            while not self._stop_event.is_set():
                if self.hub.has_clients:
                    try:
                        data = get_system_telemetry()
                        self.hub.broadcast({"type": "telemetry", "data": data})
                    except Exception:
                        pass
                self._stop_event.wait(2.5)

        self._telemetry_thread = threading.Thread(target=_telemetry_ticker, name="GatewayTelemetryThread", daemon=True)
        self._telemetry_thread.start()
        logger.info("gateway_service_started on http://%s:%d", self.host, self.port)

    def shutdown(self) -> None:
        """Stop background gateway server cleanly."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._server:
            self._server.should_exit = True
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
        logger.info("gateway_service_stopped")

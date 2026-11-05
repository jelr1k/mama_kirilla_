from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.version import APP_VERSION
from services.gateway.hub import WebSocketHub, _is_allowed_ws_origin, is_allowed_ws_origin
from services.gateway.routers import (
    chat_router,
    integrations_router,
    settings_router,
    system_router,
    voice_router,
)
from services.gateway.routers.system import (
    AUTOSTART_APP_NAME,
    RUN_REG_KEY,
    _is_autostart_enabled,
    _set_autostart,
    is_autostart_enabled,
    set_autostart,
)
from tools.system_info import get_system_telemetry

logger = logging.getLogger("jarvis.gateway")

__all__ = [
    "AUTOSTART_APP_NAME",
    "GatewayService",
    "RUN_REG_KEY",
    "WebSocketHub",
    "_is_allowed_ws_origin",
    "_is_autostart_enabled",
    "_set_autostart",
    "is_allowed_ws_origin",
    "is_autostart_enabled",
    "set_autostart",
]


class GatewayService:
    """FastAPI & WebSocket gateway bridging Jarvis core to modern web / Tauri UIs."""

    def __init__(self, app_context: Any, host: str = "127.0.0.1", port: int = 8765):
        self.app_context = app_context
        self.host = host
        self.port = port
        self.hub = WebSocketHub()

        def _handle_auto_disconnect():
            logger.info("all_ui_clients_disconnected_staying_alive_in_tray")

        self.hub.on_all_disconnected = _handle_auto_disconnect
        self._server: uvicorn.Server | None = None
        self._server_thread: threading.Thread | None = None
        self._telemetry_thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()

        self.fastapi_app = FastAPI(title="Kirieshcka v2 Gateway", version=APP_VERSION)
        self.fastapi_app.state.gateway = self

        # Standalone Updater components
        from services.update_backup import UpdateBackupService
        from services.update_downloader import UpdateDownloader
        from services.update_relauncher import UpdateRelauncher
        from services.update_validator import UpdateValidator

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
        self.fastapi_app.include_router(chat_router)
        self.fastapi_app.include_router(settings_router)
        self.fastapi_app.include_router(system_router)
        self.fastapi_app.include_router(voice_router)
        self.fastapi_app.include_router(integrations_router)

        @self.fastapi_app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            origin = websocket.headers.get("origin")
            if not is_allowed_ws_origin(origin):
                logger.warning("websocket_rejected_untrusted_origin origin=%s", origin)
                await websocket.close(code=1008)
                return
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
        from core.app_paths import APP_DATA_DIR, APP_ROOT
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

        elif action == "protocols.get":
            pm = getattr(self.app_context, "protocols_manager", None)
            if pm:
                self.hub.broadcast({
                    "type": "protocols",
                    "data": {
                        "active_profile": pm.get_active_profile(),
                        "profiles": pm.list_profiles(),
                        "protocols": pm.get_protocols(),
                    },
                })
        elif action == "protocols.execute":
            proto_id = str(data.get("protocol_id", "")).strip()
            pm = getattr(self.app_context, "protocols_manager", None)
            from services.stark_protocols import StarkProtocols

            cfg = getattr(self.app_context, "config", None)
            ollama_url = getattr(cfg, "ollama_url", None)
            model = cfg.get("model") if hasattr(cfg, "get") else None
            proto = pm.get_protocol_by_id(proto_id) if pm else None
            resp = StarkProtocols.execute_protocol(proto or proto_id, ollama_url=ollama_url, model=model)
            self.hub.broadcast({"type": "protocol.executed", "protocol_id": proto_id, "result": resp})
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
        events.subscribe("protocols.changed", lambda data: self.hub.broadcast({"type": "protocols.changed", "data": data}))
        events.subscribe("steam.game_launched", lambda data: self.hub.broadcast({"type": "steam.game_launched", "data": data}))
        events.subscribe("wake_word.recognized", lambda p: self.hub.broadcast({"type": "wake_word.recognized", "text": p}))
        events.subscribe("wake_word.status", lambda s: self.hub.broadcast({"type": "wake_word.status", "status": s}))
        events.subscribe("wake_word.listening_changed", lambda a: self.hub.broadcast({"type": "wake_word.listening", "active": a}))

        def _on_whisper_stats(s):
            from dataclasses import asdict, is_dataclass
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
            from dataclasses import asdict, is_dataclass
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

        # Start optional Telegram bot if enabled
        try:
            from modules.telegram_bot import get_telegram_bot

            t_bot = get_telegram_bot(
                config_manager=getattr(self.app_context, "config", None),
                app_context=self.app_context,
            )
            if t_bot.is_enabled and t_bot.bot_token:
                t_bot.start()
        except Exception as t_err:
            logger.warning("telegram_bot_autostart_failed: %s", t_err)

        logger.info("gateway_service_started on http://%s:%d", self.host, self.port)

    def shutdown(self) -> None:
        """Stop background gateway server cleanly."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()

        try:
            from modules.telegram_bot import get_telegram_bot

            bot = get_telegram_bot()
            bot.notify_shutdown()
            bot.stop()
        except Exception:
            pass

        if self._server:
            self._server.should_exit = True
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
        logger.info("gateway_service_stopped")

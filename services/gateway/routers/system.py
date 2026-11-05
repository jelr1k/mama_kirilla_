from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from core.version import APP_VERSION
from services.gateway.deps import get_gateway
from tools.system_info import get_system_telemetry

logger = logging.getLogger("jarvis.gateway.system")

router = APIRouter(tags=["system"])

RUN_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_APP_NAME = "KirieshckaV2"


def is_autostart_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, AUTOSTART_APP_NAME)
            return True
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                launcher = Path(__file__).resolve().parent.parent.parent / "start.bat"
                if not launcher.is_file():
                    launcher = Path(__file__).resolve().parent.parent.parent.parent / "start.bat"
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


_is_autostart_enabled = is_autostart_enabled
_set_autostart = set_autostart


@router.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "Kirieshcka v2",
        "version": APP_VERSION,
        "timestamp": time.time(),
    }


@router.get("/api/status")
def assistant_status(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    app_context = gateway.app_context
    cfg = getattr(app_context, "config", None)
    model = cfg.get("model", "unknown") if cfg else "unknown"
    name = cfg.get("assistant_name", "Kirieshcka") if cfg else "Kirieshcka"
    voice_cfg = cfg.get("voice", {}) if cfg else {}

    voice_service = getattr(app_context, "voice_service", None)
    is_recording = voice_service.is_recording if voice_service else False
    is_transcribing = voice_service.transcribing() if voice_service else False

    wake_word_detector = getattr(app_context, "wake_word_detector", None)
    wake_word_running = wake_word_detector.is_running() if wake_word_detector else False

    return {
        "assistant_name": name,
        "model": model,
        "wake_word_enabled": voice_cfg.get("wake_word_enabled", True),
        "wake_word_running": wake_word_running,
        "is_recording": is_recording,
        "is_transcribing": is_transcribing,
    }


@router.get("/api/telemetry")
def telemetry() -> dict[str, Any]:
    return get_system_telemetry()


@router.post("/api/shutdown")
def shutdown_app(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    logger.info("api_shutdown_requested")
    app_context = gateway.app_context

    def _delayed_exit():
        time.sleep(0.3)
        try:
            if hasattr(app_context, "shutdown"):
                app_context.shutdown()
        finally:
            os._exit(0)

    threading.Thread(target=_delayed_exit, daemon=True).start()
    return {"success": True, "message": "Shutting down"}


@router.get("/api/autostart")
def get_autostart() -> dict[str, Any]:
    return {"enabled": is_autostart_enabled()}


@router.post("/api/autostart")
def set_autostart_route(payload: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(payload.get("enabled", False))
    success = set_autostart(enabled)
    return {"success": success, "enabled": enabled}


@router.get("/api/updates")
def check_updates(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    app_context = gateway.app_context
    checker = getattr(app_context, "update_checker", None)
    service = getattr(app_context, "update_service", None)
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
                    gateway._current_update_plan = plan
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
        "plan_available": bool(gateway._current_update_plan),
        "archive_name": archive_name,
        "archive_size": archive_size,
        "status": gateway._update_state["status"],
        "progress_percent": gateway._update_state["progress_percent"],
        "download_speed_mb": gateway._update_state["download_speed_mb"],
        "error": gateway._update_state["error"],
    }


@router.post("/api/updates/check")
def force_check_updates(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    return check_updates(gateway=gateway)


@router.post("/api/updates/apply")
def apply_update(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    if not gateway._current_update_plan:
        checker = getattr(gateway.app_context, "update_checker", None)
        service = getattr(gateway.app_context, "update_service", None)
        if checker and service:
            try:
                info = checker.check()
                if getattr(info, "update_available", False):
                    gateway._current_update_plan = service.prepare(info)
            except Exception as e:
                return {"success": False, "error": f"Не удалось подготовить обновление: {e}"}

    if not gateway._current_update_plan:
        return {"success": False, "error": "Нет доступного плана обновления для установки"}

    if gateway._update_state["status"] in ("downloading", "validating", "backing_up", "relaunching"):
        return {"success": False, "error": f"Обновление уже выполняется (статус: {gateway._update_state['status']})"}

    threading.Thread(target=gateway._apply_update_worker, daemon=True).start()
    return {"success": True, "message": "Процесс обновления запущен в фоне"}


@router.get("/api/statistics")
def get_statistics(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    stats_svc = getattr(gateway.app_context, "statistics_service", None)
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

    telemetry_data = {}
    try:
        telemetry_data = get_system_telemetry()
    except Exception:
        pass

    return {
        "latest_llm": latest_llm,
        "latest_whisper": latest_whisper,
        "telemetry": telemetry_data,
        "history": history,
    }


@router.get("/api/network/services")
async def get_network_services(force: bool = False) -> dict[str, Any]:
    from modules.network_checker import get_network_checker

    return await get_network_checker().check_all(force=force)

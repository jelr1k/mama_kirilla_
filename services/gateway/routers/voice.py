from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter, Depends

from services.gateway.deps import get_gateway
from services.model_service import ModelService

logger = logging.getLogger("jarvis.gateway.voice")

router = APIRouter(tags=["voice"])


@router.post("/api/tts/test")
def test_tts(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    tts = getattr(gateway.app_context, "tts_service", None)
    text = payload.get("text", "Тест синтеза речи Кириешка")
    if tts:
        try:
            tts.speak(text)
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    return {"success": False, "error": "TTSService unavailable"}


@router.post("/api/microphones/test")
def test_mic(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    voice = getattr(gateway.app_context, "voice_service", None)
    raw_device = payload.get("device")
    device = int(raw_device.strip()) if isinstance(raw_device, str) and raw_device.strip().isdigit() else (None if raw_device == "default" else raw_device)
    if voice and hasattr(voice, "test_microphone"):
        try:
            return voice.test_microphone(device)
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    return {"success": False, "error": "VoiceService unavailable"}


@router.post("/api/voice/test_recognition")
def test_voice_recognition(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    voice = getattr(gateway.app_context, "voice_service", None)
    raw_device = payload.get("device")
    device = int(raw_device.strip()) if isinstance(raw_device, str) and raw_device.strip().isdigit() else (None if raw_device == "default" else raw_device)
    model = payload.get("model")
    duration = float(payload.get("duration", 3.5))
    if voice and hasattr(voice, "test_recognition"):
        try:
            return voice.test_recognition(device=device, model=model, duration=duration)
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    return {"success": False, "error": "VoiceService unavailable"}


@router.get("/api/microphones")
def get_microphones(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    voice_service = getattr(gateway.app_context, "voice_service", None)
    if voice_service and hasattr(voice_service, "list_microphones"):
        return voice_service.list_microphones()
    return {"success": False, "devices": []}


@router.get("/api/models")
def get_models(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    app_context = gateway.app_context
    model_service = ModelService(getattr(app_context, "provider", None)) if hasattr(app_context, "provider") else None
    ollama_models = []
    if model_service:
        try:
            res = model_service.get_available_models()
            ollama_models = res.get("models", [])
        except Exception:
            pass
    cfg = getattr(app_context, "config", None)
    current_model = cfg.get("model", "") if cfg else ""
    if not current_model and ollama_models:
        current_model = ollama_models[0]
    elif not current_model:
        current_model = "qwen3:1.7b"

    ollama_mgr = getattr(app_context, "ollama_manager", None)
    loaded_models = []
    if ollama_mgr:
        try:
            loaded = ollama_mgr.get_loaded_models()
            loaded_models = [m.get("name") or m.get("model") for m in loaded if isinstance(m, dict)]
        except Exception:
            pass

    from voice.tts.engines import list_tts_voices

    return {
        "current_model": current_model,
        "loaded_models": loaded_models,
        "ollama_models": ollama_models,
        "whisper_models": ["base", "small", "medium", "large-v3", "custom"],
        "tts_voices": list_tts_voices(),
    }


@router.get("/api/whisper/status")
def whisper_models_status(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    dep = getattr(gateway.app_context, "dependency_manager", None)
    models = ["base", "small", "medium", "large-v3"]
    statuses = {}
    errors = {}
    for m in models:
        key = f"whisper:{m}"
        state = gateway._model_download_states.get(key)
        if state:
            statuses[m] = state
        elif dep:
            statuses[m] = dep.whisper_status(m)
        else:
            statuses[m] = "unknown"
        if key in gateway._model_download_errors:
            errors[m] = gateway._model_download_errors[key]
    return {"statuses": statuses, "errors": errors}


@router.post("/api/whisper/download")
def download_whisper_model(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    model = payload.get("model", "").strip()
    dep = getattr(gateway.app_context, "dependency_manager", None)
    if not dep:
        return {"success": False, "error": "DependencyManager unavailable"}
    key = f"whisper:{model}"
    gateway._model_download_states[key] = "downloading"
    gateway._model_download_errors.pop(key, None)

    def _dl():
        try:
            dep.ensure_whisper_model(model)
            gateway._model_download_states[key] = "installed"
        except Exception as exc:
            logger.exception("whisper_download_failed model=%s", model)
            gateway._model_download_states[key] = "failed"
            gateway._model_download_errors[key] = str(exc)

    threading.Thread(target=_dl, daemon=True).start()
    return {"success": True, "message": f"Downloading {model} started in background"}


@router.get("/api/tts/status")
def tts_voices_status(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    from voice.tts.engines import list_tts_voices

    tts = getattr(gateway.app_context, "tts_service", None)
    voices = [v["id"] for v in list_tts_voices()]
    statuses = {}
    errors = {}
    progress = {}
    progress_map = getattr(gateway, "_model_download_progress", {})
    for v in voices:
        key = f"tts:{v}"
        state = gateway._model_download_states.get(key)
        if state:
            statuses[v] = state
        elif tts:
            statuses[v] = tts.voice_status(v)
        else:
            statuses[v] = "missing"
        if key in gateway._model_download_errors:
            errors[v] = gateway._model_download_errors[key]
        if key in progress_map:
            progress[v] = progress_map[key]
    return {"statuses": statuses, "errors": errors, "progress": progress}


@router.post("/api/tts/download")
def download_tts_voice(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    voice_id = payload.get("voice", "").strip()
    tts = getattr(gateway.app_context, "tts_service", None)
    if not tts:
        return {"success": False, "error": "TTSService unavailable"}
    key = f"tts:{voice_id}"
    gateway._model_download_states[key] = "downloading"
    gateway._model_download_errors.pop(key, None)
    progress_map = getattr(gateway, "_model_download_progress", None)
    if progress_map is None:
        progress_map = {}
        gateway._model_download_progress = progress_map
    progress_map[key] = {
        "downloaded_bytes": 0,
        "total_bytes": None,
        "percent": 0.0,
        "current_file": "",
    }

    def _on_progress(downloaded_bytes: int, total_bytes: int | None, current_file: str = "") -> None:
        percent = None
        if total_bytes and total_bytes > 0:
            percent = round(min(100.0, (downloaded_bytes / total_bytes) * 100.0), 1)
        progress_map[key] = {
            "downloaded_bytes": int(downloaded_bytes),
            "total_bytes": int(total_bytes) if total_bytes else None,
            "percent": percent,
            "current_file": current_file,
        }

    def _dl():
        try:
            tts.ensure_voice(voice_id, progress_callback=_on_progress)
            gateway._model_download_states[key] = "installed"
            prev = progress_map.get(key) or {}
            total = prev.get("total_bytes") or prev.get("downloaded_bytes") or 0
            progress_map[key] = {
                "downloaded_bytes": total,
                "total_bytes": total or None,
                "percent": 100.0,
                "current_file": "",
            }
        except Exception as exc:
            logger.exception("tts_voice_download_failed voice=%s", voice_id)
            gateway._model_download_states[key] = "failed"
            gateway._model_download_errors[key] = str(exc)

    threading.Thread(target=_dl, daemon=True).start()
    return {"success": True, "message": f"Downloading voice {voice_id} started in background"}


@router.post("/api/ollama/restart")
def restart_ollama(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    ollama_mgr = getattr(gateway.app_context, "ollama_manager", None)
    if ollama_mgr:
        try:
            res = ollama_mgr.start()
            return {"success": True, "result": res}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    return {"success": False, "error": "OllamaManager unavailable"}


@router.post("/api/ollama/unload")
def unload_ollama(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    ollama_mgr = getattr(gateway.app_context, "ollama_manager", None)
    cfg = getattr(gateway.app_context, "config", None)
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
                "message": f"Модель {', '.join(unloaded)} выгружена из памяти видеокарты" if unloaded else "Все модели выгружены из памяти",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
    return {"success": False, "error": "OllamaManager недоступен"}

"""Registry and factory for independent TTS backend adapters."""
from __future__ import annotations

from typing import Any

from ..engine import TTSBackend
from .piper import (
    DEFAULT_TTS_SPEED,
    DEFAULT_TTS_VOICE,
    DEFAULT_TTS_VOLUME,
    MAX_VOICE_FILE_BYTES,
    SUPPORTED_TTS_VOICES,
    PiperTTSBackend,
)
from .silero import SUPPORTED_SILERO_VOICES, SileroTTSBackend
from .supertonic import SUPPORTED_SUPERTONIC_VOICES, SupertonicTTSBackend
from .teratts import SUPPORTED_TERATTS_VOICES, TeraTTSBackend
from .tiny_voca import SUPPORTED_TINY_VOCA_VOICES, TinyVocaTTSBackend

TTS_ENGINES: dict[str, type[Any]] = {
    "piper": PiperTTSBackend,
    "tiny_voca": TinyVocaTTSBackend,
    "silero": SileroTTSBackend,
    "teratts": TeraTTSBackend,
    "supertonic": SupertonicTTSBackend,
}

_DEFAULT_VOICE_BY_ENGINE: dict[str, str] = {
    "piper": DEFAULT_TTS_VOICE,
    "tiny_voca": "tiny-voca:F2",
    "silero": "silero:baya",
    "teratts": "teratts:ru_f1",
    "supertonic": "supertonic:F4",
}


def register_tts_engine(engine_id: str, backend_cls: type[Any]) -> None:
    """Register a custom TTS backend adapter by engine_id."""
    TTS_ENGINES[str(engine_id).strip()] = backend_cls


def resolve_engine_for_voice(voice_name: str | None) -> str:
    """Infer engine_id from a voice identifier, defaulting to 'piper'."""
    name = str(voice_name or "").strip()
    if name in SUPPORTED_TINY_VOCA_VOICES or name.startswith("tiny-voca:"):
        return "tiny_voca"
    if name in SUPPORTED_SILERO_VOICES or name.startswith("silero:"):
        return "silero"
    if name in SUPPORTED_TERATTS_VOICES or name.startswith("teratts:"):
        return "teratts"
    if name in SUPPORTED_SUPERTONIC_VOICES or name.startswith("supertonic:"):
        return "supertonic"
    return "piper"


def create_tts_backend(
    engine_id: str = "auto",
    *,
    voice_name: str | None = None,
    speed: float = DEFAULT_TTS_SPEED,
    volume: float = DEFAULT_TTS_VOLUME,
) -> TTSBackend:
    """Instantiate a TTS backend by engine_id ('auto' infers from voice_name)."""
    selected_engine = str(engine_id or "auto").strip().lower()
    if selected_engine in ("", "auto"):
        selected_engine = resolve_engine_for_voice(voice_name)

    backend_cls = TTS_ENGINES.get(selected_engine)
    if backend_cls is None:
        backend_cls = PiperTTSBackend
        selected_engine = "piper"

    default_voice = _DEFAULT_VOICE_BY_ENGINE.get(selected_engine, DEFAULT_TTS_VOICE)
    return backend_cls(
        voice_name=voice_name or default_voice,
        speed=speed,
        volume=volume,
    )


def list_tts_voices() -> list[dict[str, Any]]:
    """Return unified list of available voices across all registered engines."""
    voices: list[dict[str, Any]] = []
    for vid, (_remote_dir, _stem, label) in SUPPORTED_TTS_VOICES.items():
        voices.append({
            "id": vid,
            "name": label,
            "engine": "piper",
            "language": "ru",
            "size_mb": 63,
        })
    for vid, (_speaker, label) in SUPPORTED_SILERO_VOICES.items():
        voices.append({
            "id": vid,
            "name": label,
            "engine": "silero",
            "language": "ru",
            "size_mb": 141,
        })
    for vid, (_speaker, label) in SUPPORTED_TERATTS_VOICES.items():
        voices.append({
            "id": vid,
            "name": label,
            "engine": "teratts",
            "language": "ru",
            "size_mb": 260,
        })
    for vid, (_speaker, label) in SUPPORTED_SUPERTONIC_VOICES.items():
        voices.append({
            "id": vid,
            "name": label,
            "engine": "supertonic",
            "language": "ru",
            "size_mb": 400,
        })
    for vid, (_speaker, label) in SUPPORTED_TINY_VOCA_VOICES.items():
        voices.append({
            "id": vid,
            "name": label,
            "engine": "tiny_voca",
            "language": "en",
            "size_mb": 45,
        })
    return voices


__all__ = [
    "DEFAULT_TTS_SPEED",
    "DEFAULT_TTS_VOLUME",
    "DEFAULT_TTS_VOICE",
    "MAX_VOICE_FILE_BYTES",
    "SUPPORTED_SILERO_VOICES",
    "SUPPORTED_SUPERTONIC_VOICES",
    "SUPPORTED_TERATTS_VOICES",
    "SUPPORTED_TTS_VOICES",
    "SUPPORTED_TINY_VOCA_VOICES",
    "TTS_ENGINES",
    "PiperTTSBackend",
    "SileroTTSBackend",
    "SupertonicTTSBackend",
    "TeraTTSBackend",
    "TinyVocaTTSBackend",
    "create_tts_backend",
    "list_tts_voices",
    "register_tts_engine",
    "resolve_engine_for_voice",
]

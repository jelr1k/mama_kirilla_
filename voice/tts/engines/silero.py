"""Silero TTS v5 Russian backend adapter (48 kHz CPU PyTorch package)."""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from core.app_paths import MODELS_DIR
from ..download import ProgressCallback, download_file
from ..errors import TTSConfigurationError, TTSError, TTSVoiceNotInstalledError
from ..text import prepare_speech_text

logger = logging.getLogger("jarvis.tts.silero")

SILERO_V5_RU_URL = "https://models.silero.ai/models/tts/ru/v5_6_ru.pt"
SILERO_SAMPLE_RATE = 48000
MAX_SILERO_FILE_BYTES = 300 * 1024 * 1024

SUPPORTED_SILERO_VOICES: dict[str, tuple[str, str]] = {
    "silero:baya": ("baya", "Silero v5 Бая (Русский, Женский)"),
    "silero:kseniya": ("kseniya", "Silero v5 Ксения (Русский, Женский)"),
    "silero:xenia": ("xenia", "Silero v5 Ксеня (Русский, Женский)"),
}


def _resample_linear(audio: np.ndarray, speed: float) -> np.ndarray:
    """Adjust speech speed cleanly without extra audio dependencies."""
    if abs(speed - 1.0) < 1e-3 or audio.size < 2:
        return audio
    new_len = max(1, int(round(audio.size / speed)))
    old_idx = np.linspace(0.0, float(audio.size - 1), num=new_len, dtype=np.float64)
    return np.interp(old_idx, np.arange(audio.size, dtype=np.float64), audio).astype(np.float32)


class SileroTTSBackend:
    """Local Silero TTS v5 backend (v5_6_ru, 48 kHz mono)."""

    engine_id = "silero"

    def __init__(
        self,
        model_dir: str | Path | None = None,
        voice_name: str = "silero:baya",
        speed: float = 1.0,
        volume: float = 0.85,
    ):
        self.model_dir = Path(model_dir) if model_dir is not None else (MODELS_DIR / "tts" / "silero")
        self.voice_name = "silero:baya"
        self.speed = 1.0
        self.volume = 0.85
        self._model = None
        self._lock = threading.RLock()
        self.configure(voice_name=voice_name, speed=speed, volume=volume)

    @staticmethod
    def _voice_info(voice_name: str) -> tuple[str, str]:
        voice_name = str(voice_name or "").strip()
        info = SUPPORTED_SILERO_VOICES.get(voice_name)
        if info is None:
            raise TTSConfigurationError(f"Неподдерживаемый голос Silero: {voice_name or '(пусто)'}")
        return info

    def configure(self, voice_name: str, speed: float = 1.0, volume: float = 0.85) -> None:
        voice_name = str(voice_name or "silero:baya").strip()
        self._voice_info(voice_name)
        try:
            speed = float(speed)
            volume = float(volume)
        except (TypeError, ValueError) as exc:
            raise TTSConfigurationError("Скорость и громкость TTS должны быть числами.") from exc
        if not 0.5 <= speed <= 2.0:
            raise TTSConfigurationError("Скорость TTS должна находиться в диапазоне 0.5–2.0.")
        if not 0.0 <= volume <= 1.0:
            raise TTSConfigurationError("Громкость TTS должна находиться в диапазоне 0–1.")

        with self._lock:
            self.voice_name = voice_name
            self.speed = speed
            self.volume = volume

    def model_path(self) -> Path:
        return self.model_dir / "v5_6_ru.pt"

    def voice_status(self, voice_name: str | None = None) -> str:
        try:
            self._voice_info(voice_name or self.voice_name)
        except TTSConfigurationError:
            return "unsupported"
        path = self.model_path()
        try:
            if path.is_file() and path.stat().st_size >= 1024 * 1024:
                return "installed"
        except OSError:
            pass
        return "missing"

    def ensure_voice(
        self,
        voice_name: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        selected = voice_name or self.voice_name
        self._voice_info(selected)
        path = self.model_path()
        with self._lock:
            if self.voice_status(selected) != "installed":
                download_file(
                    SILERO_V5_RU_URL,
                    path,
                    max_bytes=MAX_SILERO_FILE_BYTES,
                    progress_callback=progress_callback,
                    label="v5_6_ru.pt",
                )
            if self.voice_status(selected) != "installed":
                raise TTSError("Скачанный файл Silero v5_6_ru.pt не прошел проверку.")
        logger.info("silero_installed voice=%s path=%s", selected, path)
        return path

    def _get_model(self):
        with self._lock:
            if self._model is not None:
                return self._model
            if self.voice_status(self.voice_name) != "installed":
                raise TTSVoiceNotInstalledError(
                    f"Модель Silero для голоса «{self.voice_name}» не установлена."
                )
            try:
                import torch
            except ImportError as exc:
                raise TTSError(
                    "Для Silero TTS требуется пакет torch (CPU). Установите его в .venv."
                ) from exc
            try:
                torch.set_num_threads(4)
                importer = torch.package.PackageImporter(str(self.model_path()))
                model = importer.load_pickle("tts_models", "model")
                model.to(torch.device("cpu"))
                self._model = model
                return self._model
            except Exception as exc:
                raise TTSError(f"Не удалось загрузить Silero v5_6_ru.pt: {exc}") from exc

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        cleaned = prepare_speech_text(text)
        if not cleaned:
            return np.zeros(0, dtype=np.float32), SILERO_SAMPLE_RATE
        speaker_id, _label = self._voice_info(self.voice_name)
        model = self._get_model()
        try:
            with self._lock:
                audio = model.apply_tts(
                    text=cleaned,
                    speaker=speaker_id,
                    sample_rate=SILERO_SAMPLE_RATE,
                    put_accent=True,
                    put_yo=True,
                )
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            arr = np.asarray(audio, dtype=np.float32).reshape(-1)
            arr = _resample_linear(arr, self.speed)
            if self.volume != 1.0:
                arr = np.clip(arr * float(self.volume), -1.0, 1.0).astype(np.float32)
            return arr, SILERO_SAMPLE_RATE
        except TTSError:
            raise
        except Exception as exc:
            raise TTSError(f"Ошибка синтеза Silero: {exc}") from exc

"""Supertonic 3 ONNX backend adapter (multilingual fast CPU TTS with Russian support)."""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from core.app_paths import MODELS_DIR
from ..download import ProgressCallback, download_hf_assets
from ..errors import TTSConfigurationError, TTSError, TTSVoiceNotInstalledError
from ..text import prepare_speech_text

logger = logging.getLogger("jarvis.tts.supertonic")

SUPERTONIC_REPO_ID = "Supertone/supertonic-3"

SUPPORTED_SUPERTONIC_VOICES: dict[str, tuple[str, str]] = {
    "supertonic:F4": ("F4", "Supertonic 3 Женский 4 (Русский)"),
    "supertonic:F1": ("F1", "Supertonic 3 Женский 1 (Русский)"),
    "supertonic:F2": ("F2", "Supertonic 3 Женский 2 (Русский)"),
    "supertonic:F3": ("F3", "Supertonic 3 Женский 3 (Русский)"),
    "supertonic:F5": ("F5", "Supertonic 3 Женский 5 (Русский)"),
}

_REQUIRED_ONNX_ASSETS = (
    "onnx/tts.json",
    "onnx/duration_predictor.onnx",
    "onnx/text_encoder.onnx",
    "onnx/vector_estimator.onnx",
    "onnx/vocoder.onnx",
    "onnx/unicode_indexer.json",
)


class SupertonicTTSBackend:
    """Local Supertonic 3 ONNX backend (Russian female styles F1-F5)."""

    engine_id = "supertonic"

    def __init__(
        self,
        model_dir: str | Path | None = None,
        voice_name: str = "supertonic:F4",
        speed: float = 1.0,
        volume: float = 0.85,
        total_steps: int = 5,
    ):
        self.model_dir = Path(model_dir) if model_dir is not None else (MODELS_DIR / "tts" / "supertonic-3")
        self.voice_name = "supertonic:F4"
        self.speed = 1.0
        self.volume = 0.85
        self.total_steps = max(2, int(total_steps))
        self._tts = None
        self._styles: dict[str, object] = {}
        self._lock = threading.RLock()
        self.configure(voice_name=voice_name, speed=speed, volume=volume)

    @staticmethod
    def _voice_info(voice_name: str) -> tuple[str, str]:
        voice_name = str(voice_name or "").strip()
        info = SUPPORTED_SUPERTONIC_VOICES.get(voice_name)
        if info is None:
            raise TTSConfigurationError(f"Неподдерживаемый голос Supertonic: {voice_name or '(пусто)'}")
        return info

    def configure(self, voice_name: str, speed: float = 1.0, volume: float = 0.85) -> None:
        voice_name = str(voice_name or "supertonic:F4").strip()
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

    def _required_files(self, voice_name: str | None = None) -> tuple[str, ...]:
        speaker_id, _ = self._voice_info(voice_name or self.voice_name)
        return _REQUIRED_ONNX_ASSETS + (f"voice_styles/{speaker_id}.json",)

    def voice_status(self, voice_name: str | None = None) -> str:
        try:
            files = self._required_files(voice_name)
        except TTSConfigurationError:
            return "unsupported"
        for rel in files:
            path = self.model_dir / rel
            if not path.is_file():
                return "missing"
            try:
                if path.stat().st_size < 16:
                    return "missing"
            except OSError:
                return "missing"
        return "installed"

    def ensure_voice(
        self,
        voice_name: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        selected = voice_name or self.voice_name
        files = self._required_files(selected)
        with self._lock:
            download_hf_assets(
                SUPERTONIC_REPO_ID,
                files,
                self.model_dir,
                max_file_bytes=512 * 1024 * 1024,
                progress_callback=progress_callback,
            )
            if self.voice_status(selected) != "installed":
                raise TTSError("Скачанные файлы Supertonic 3 не прошли проверку.")
        logger.info("supertonic_installed voice=%s path=%s", selected, self.model_dir)
        return self.model_dir

    def _get_tts(self):
        with self._lock:
            if self._tts is not None:
                return self._tts
            if self.voice_status(self.voice_name) != "installed":
                raise TTSVoiceNotInstalledError(
                    f"Модель Supertonic 3 для голоса «{self.voice_name}» не установлена."
                )
            try:
                from supertonic import TTS
            except ImportError as exc:
                raise TTSError(
                    "Для Supertonic TTS требуется пакет supertonic. Установите его в .venv."
                ) from exc
            try:
                self._tts = TTS(
                    model="supertonic-3",
                    model_dir=self.model_dir,
                    auto_download=False,
                    intra_op_num_threads=4,
                    inter_op_num_threads=1,
                )
                return self._tts
            except Exception as exc:
                raise TTSError(f"Не удалось инициализировать Supertonic 3: {exc}") from exc

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        cleaned = prepare_speech_text(text)
        if not cleaned:
            return np.zeros(0, dtype=np.float32), 44100
        speaker_id, _ = self._voice_info(self.voice_name)
        tts = self._get_tts()
        try:
            with self._lock:
                style = self._styles.get(speaker_id)
                if style is None:
                    style = tts.get_voice_style(voice_name=speaker_id)
                    self._styles[speaker_id] = style
                wav, _duration = tts.synthesize(
                    text=cleaned,
                    voice_style=style,
                    total_steps=self.total_steps,
                    speed=float(self.speed),
                    lang="ru",
                )
            sample_rate = int(getattr(tts, "sample_rate", 44100))
            arr = np.asarray(wav, dtype=np.float32).reshape(-1)
            if self.volume != 1.0:
                arr = np.clip(arr * float(self.volume), -1.0, 1.0).astype(np.float32)
            return arr, sample_rate
        except TTSError:
            raise
        except Exception as exc:
            raise TTSError(f"Ошибка синтеза Supertonic 3: {exc}") from exc

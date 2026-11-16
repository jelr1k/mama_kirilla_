"""TeraTTS v2 ONNX backend adapter (native Russian stress + ONNX Runtime)."""
from __future__ import annotations

import importlib.util
import logging
import sys
import threading
from pathlib import Path

import numpy as np

from core.app_paths import MODELS_DIR
from ..download import ProgressCallback, download_hf_assets
from ..errors import TTSConfigurationError, TTSError, TTSVoiceNotInstalledError
from ..text import prepare_speech_text

logger = logging.getLogger("jarvis.tts.teratts")

TERATTS_REPO_ID = "TeraSpace/TeraTTSv2"
TERATTS_SAMPLE_RATE = 44100

SUPPORTED_TERATTS_VOICES: dict[str, tuple[str, str]] = {
    "teratts:ru_f1": ("ru_f1", "TeraTTS v2 F1 (Русский, Женский)"),
    "teratts:ru_f2": ("ru_f2", "TeraTTS v2 F2 (Русский, Женский)"),
}

_CORE_ASSETS = (
    "config.json",
    "teratts.py",
    "teratts_ruaccent.py",
    "unicode_indexer.json",
    "models/duration_predictor.onnx",
    "models/sampler_distilled_cfg3_8step.onnx",
    "models/text_encoder.onnx",
    "models/vocoder.onnx",
)


def _list_teratts_assets(voice_id: str) -> list[str]:
    """Build the minimal asset list for TeraTTSv2 (skipping unused teacher/other-speaker files)."""
    assets = list(_CORE_ASSETS)
    assets.extend((f"styles/{voice_id}/style_dp.npy", f"styles/{voice_id}/style_ttl.npy"))
    try:
        from huggingface_hub import HfApi

        for item in HfApi().list_repo_tree(repo_id=TERATTS_REPO_ID, recursive=True):
            path = getattr(item, "path", None)
            item_type = getattr(item, "type", None)
            if not path or item_type == "directory":
                continue
            if path.startswith("ruaccent/"):
                assets.append(path)
    except Exception as exc:
        raise TTSError(f"Не удалось получить список файлов TeraTTSv2 с Hugging Face: {exc}") from exc
    return assets


class TeraTTSBackend:
    """Local TeraTTS v2 ONNX backend (44.1 kHz mono, Russian female styles)."""

    engine_id = "teratts"

    def __init__(
        self,
        model_dir: str | Path | None = None,
        voice_name: str = "teratts:ru_f1",
        speed: float = 1.0,
        volume: float = 0.85,
    ):
        self.model_dir = Path(model_dir) if model_dir is not None else (MODELS_DIR / "tts" / "teratts-v2")
        self.voice_name = "teratts:ru_f1"
        self.speed = 1.0
        self.volume = 0.85
        self._module = None
        self._runtime = None
        self._lock = threading.RLock()
        self.configure(voice_name=voice_name, speed=speed, volume=volume)

    @staticmethod
    def _voice_info(voice_name: str) -> tuple[str, str]:
        voice_name = str(voice_name or "").strip()
        info = SUPPORTED_TERATTS_VOICES.get(voice_name)
        if info is None:
            raise TTSConfigurationError(f"Неподдерживаемый голос TeraTTS: {voice_name or '(пусто)'}")
        return info

    def configure(self, voice_name: str, speed: float = 1.0, volume: float = 0.85) -> None:
        voice_name = str(voice_name or "teratts:ru_f1").strip()
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

    def voice_status(self, voice_name: str | None = None) -> str:
        try:
            speaker_id, _ = self._voice_info(voice_name or self.voice_name)
        except TTSConfigurationError:
            return "unsupported"
        required = list(_CORE_ASSETS) + [
            f"styles/{speaker_id}/style_dp.npy",
            f"styles/{speaker_id}/style_ttl.npy",
            "ruaccent/nn/nn_accent/model.onnx",
        ]
        for rel in required:
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
        speaker_id, _ = self._voice_info(selected)
        with self._lock:
            assets = _list_teratts_assets(speaker_id)
            download_hf_assets(
                TERATTS_REPO_ID,
                assets,
                self.model_dir,
                max_file_bytes=512 * 1024 * 1024,
                progress_callback=progress_callback,
            )
            if self.voice_status(selected) != "installed":
                raise TTSError("Скачанные файлы TeraTTSv2 не прошли проверку.")
        logger.info("teratts_installed voice=%s path=%s", selected, self.model_dir)
        return self.model_dir

    def _get_runtime(self):
        with self._lock:
            if self._runtime is not None and self._module is not None:
                return self._module, self._runtime
            if self.voice_status(self.voice_name) != "installed":
                raise TTSVoiceNotInstalledError(
                    f"Модель TeraTTSv2 для голоса «{self.voice_name}» не установлена."
                )
            try:
                mod_path = self.model_dir / "teratts.py"
                model_dir_str = str(self.model_dir)
                if model_dir_str not in sys.path:
                    sys.path.insert(0, model_dir_str)
                spec = importlib.util.spec_from_file_location("_teratts_runtime_mod", str(mod_path))
                if spec is None or spec.loader is None:
                    raise TTSError("Не удалось загрузить модуль teratts.py.")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                runtime = module.load_model(
                    self.model_dir,
                    provider="CPUExecutionProvider",
                    threads=6,
                    russian_stress=True,
                )
                self._module = module
                self._runtime = runtime
                return self._module, self._runtime
            except TTSError:
                raise
            except Exception as exc:
                raise TTSError(f"Не удалось загрузить TeraTTSv2: {exc}") from exc

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        cleaned = prepare_speech_text(text)
        if not cleaned:
            return np.zeros(0, dtype=np.float32), TERATTS_SAMPLE_RATE
        speaker_id, _ = self._voice_info(self.voice_name)
        module, runtime = self._get_runtime()
        tagged = cleaned if ("<ru>" in cleaned or "<en>" in cleaned) else f"<ru>{cleaned}</ru>"
        duration_scale = max(0.5, min(2.0, 1.0 / float(self.speed)))
        try:
            with self._lock:
                wav = module.generate_speech(
                    runtime,
                    text=tagged,
                    voice=speaker_id,
                    duration_scale=duration_scale,
                )
            arr = np.asarray(wav, dtype=np.float32).reshape(-1)
            if self.volume != 1.0:
                arr = np.clip(arr * float(self.volume), -1.0, 1.0).astype(np.float32)
            sample_rate = int(getattr(module, "SAMPLE_RATE", TERATTS_SAMPLE_RATE))
            return arr, sample_rate
        except TTSError:
            raise
        except Exception as exc:
            raise TTSError(f"Ошибка синтеза TeraTTSv2: {exc}") from exc

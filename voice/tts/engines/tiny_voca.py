"""ONNX backend adapter for n4ze3m/tiny-voca (lightweight English TTS)."""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path

import numpy as np
import requests

from core.app_paths import MODELS_DIR
from ..download import ProgressCallback, download_file
from ..errors import TTSConfigurationError, TTSError, TTSVoiceNotInstalledError
from ..text import prepare_speech_text

logger = logging.getLogger("jarvis.tts.tiny_voca")

TINY_VOCA_BASE_URL = "https://huggingface.co/n4ze3m/tiny-voca/resolve/main"
MAX_TINY_VOCA_FILE_BYTES = 64 * 1024 * 1024

SUPPORTED_TINY_VOCA_VOICES: dict[str, tuple[str, str]] = {
    "tiny-voca:F2": ("F2", "Tiny Voca F2 (English, Female)"),
    "tiny-voca:M2": ("M2", "Tiny Voca M2 (English, Male)"),
}

_PUNCT_TOKENS = set(',.?!;:"\'()—…')
_TOKEN_SPLIT_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+|[,.?!;:\"'()—…]")

# Simple letter-to-IPA fallback for out-of-lexicon English words when dizione is not installed
_FALLBACK_GRAPHEME_MAP = {
    "a": "æ", "b": "b", "c": "k", "d": "d", "e": "ɛ", "f": "f", "g": "ɡ",
    "h": "h", "i": "ɪ", "j": "dʒ", "k": "k", "l": "l", "m": "m", "n": "n",
    "o": "ɑː", "p": "p", "q": "k", "r": "ɹ", "s": "s", "t": "t", "u": "ʌ",
    "v": "v", "w": "w", "x": "k s", "y": "j", "z": "z",
}


class TinyVocaTTSBackend:
    """Local ONNX backend for n4ze3m/tiny-voca (24 kHz mono, voices F2 / M2)."""

    engine_id = "tiny_voca"

    def __init__(
        self,
        model_dir: str | Path | None = None,
        voice_name: str = "tiny-voca:F2",
        speed: float = 1.0,
        volume: float = 0.85,
    ):
        self.model_dir = Path(model_dir) if model_dir is not None else (MODELS_DIR / "tts" / "tiny-voca")
        self.voice_name = "tiny-voca:F2"
        self.speed = 1.0
        self.volume = 0.85
        self._session = None
        self._config: dict | None = None
        self._lexicon: dict[str, str] | None = None
        self._lock = threading.RLock()
        self.configure(voice_name=voice_name, speed=speed, volume=volume)

    @staticmethod
    def _voice_info(voice_name: str) -> tuple[str, str]:
        voice_name = str(voice_name or "").strip()
        info = SUPPORTED_TINY_VOCA_VOICES.get(voice_name)
        if info is None:
            raise TTSConfigurationError(f"Неподдерживаемый голос Tiny Voca: {voice_name or '(пусто)'}")
        return info

    def configure(self, voice_name: str, speed: float = 1.0, volume: float = 0.85) -> None:
        voice_name = str(voice_name or "tiny-voca:F2").strip()
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

    def paths_for(self, _voice_name: str | None = None) -> tuple[Path, Path, Path]:
        return (
            self.model_dir / "onnx" / "model.onnx",
            self.model_dir / "config.json",
            self.model_dir / "phonemizer" / "lexicon.json",
        )

    def voice_status(self, voice_name: str | None = None) -> str:
        try:
            self._voice_info(voice_name or self.voice_name)
        except TTSConfigurationError:
            return "unsupported"
        model_path, config_path, lexicon_path = self.paths_for(voice_name)
        if not (model_path.is_file() and config_path.is_file() and lexicon_path.is_file()):
            return "missing"
        try:
            if model_path.stat().st_size < 1024 or config_path.stat().st_size < 100:
                return "missing"
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(cfg, dict) or not isinstance(cfg.get("vocab"), dict):
                return "missing"
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return "missing"
        return "installed"

    def ensure_voice(
        self,
        voice_name: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> Path:
        selected = voice_name or self.voice_name
        self._voice_info(selected)
        model_path, config_path, lexicon_path = self.paths_for(selected)
        assets = (
            (f"{TINY_VOCA_BASE_URL}/onnx/model.onnx?download=true", model_path, MAX_TINY_VOCA_FILE_BYTES),
            (f"{TINY_VOCA_BASE_URL}/config.json?download=true", config_path, 2 * 1024 * 1024),
            (f"{TINY_VOCA_BASE_URL}/phonemizer/lexicon.json?download=true", lexicon_path, 32 * 1024 * 1024),
        )
        with self._lock:
            downloaded = 0
            for url, target, max_bytes in assets:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.is_file() or target.stat().st_size < 16:
                    downloaded += download_file(
                        url,
                        target,
                        max_bytes=max_bytes,
                        progress_callback=progress_callback,
                        base_downloaded=downloaded,
                        label=target.name,
                    )
                else:
                    downloaded += target.stat().st_size
            if self.voice_status(selected) != "installed":
                raise TTSError("Скачанные файлы Tiny Voca не прошли проверку.")
        logger.info("tiny_voca_installed voice=%s path=%s", selected, model_path)
        return model_path

    def _load_runtime(self) -> None:
        model_path, config_path, lexicon_path = self.paths_for()
        if self._config is None:
            self._config = json.loads(config_path.read_text(encoding="utf-8"))
        if self._lexicon is None:
            raw_lex = json.loads(lexicon_path.read_text(encoding="utf-8"))
            self._lexicon = raw_lex if isinstance(raw_lex, dict) else {}
        if self._session is None:
            try:
                import onnxruntime as ort
            except Exception as exc:
                raise TTSError(f"onnxruntime не установлен для Tiny Voca: {exc}") from exc
            self._session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])

    def _word_to_phonemes(self, word: str) -> str:
        lower = word.lower()
        if self._lexicon and lower in self._lexicon:
            val = self._lexicon[lower]
            if isinstance(val, list) and val:
                return str(val[0])
            return str(val)
        return " ".join(_FALLBACK_GRAPHEME_MAP.get(ch, "") for ch in lower if ch in _FALLBACK_GRAPHEME_MAP)

    def _encode_text(self, text: str) -> tuple[np.ndarray, np.ndarray]:
        assert self._config is not None
        vocab: dict[str, int] = self._config["vocab"]
        bos_id = int(vocab.get("<bos>", 1))
        eos_id = int(vocab.get("<eos>", 2))
        sp_id = int(vocab.get("<sp>", 3))
        unk_id = int(vocab.get("<unk>", 4))

        token_ids: list[int] = [bos_id]
        stress_ids: list[int] = [0]

        chunks = _TOKEN_SPLIT_RE.findall(text)
        for idx, chunk in enumerate(chunks):
            if chunk in _PUNCT_TOKENS:
                token_ids.append(int(vocab.get(chunk, unk_id)))
                stress_ids.append(0)
                continue

            if idx > 0 and chunks[idx - 1] not in _PUNCT_TOKENS:
                token_ids.append(sp_id)
                stress_ids.append(0)

            phoneme_str = self._word_to_phonemes(chunk)
            for sym in phoneme_str.split():
                stress = 0
                if sym.startswith("ˈ"):
                    stress = 1
                    sym = sym[1:]
                elif sym.startswith("ˌ"):
                    stress = 2
                    sym = sym[1:]
                if not sym:
                    continue
                token_ids.append(int(vocab.get(sym, unk_id)))
                stress_ids.append(stress)

        token_ids.append(eos_id)
        stress_ids.append(0)

        max_tokens = int(self._config.get("model", {}).get("max_tokens", 512))
        if len(token_ids) > max_tokens:
            token_ids = token_ids[: max_tokens - 1] + [eos_id]
            stress_ids = stress_ids[: max_tokens - 1] + [0]

        return (
            np.asarray([token_ids], dtype=np.int64),
            np.asarray([stress_ids], dtype=np.int64),
        )

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        text = prepare_speech_text(text)
        if not text:
            raise TTSError("Нет текста для озвучивания.")
        with self._lock:
            if self.voice_status(self.voice_name) != "installed":
                raise TTSVoiceNotInstalledError(
                    "Модель Tiny Voca не скачана. Открой настройки и скачай её."
                )
            self._load_runtime()
            assert self._session is not None and self._config is not None

            speaker_code, _label = self._voice_info(self.voice_name)
            voices_list = list(self._config.get("voices") or ["F2", "M2"])
            voice_idx = voices_list.index(speaker_code) if speaker_code in voices_list else 0
            sample_rate = int(self._config.get("sample_rate", 24000))

            tokens, stress = self._encode_text(text)
            inputs = {
                "tokens": tokens,
                "stress": stress,
                "voice": np.asarray([voice_idx], dtype=np.int64),
                "speed": np.asarray([self.speed], dtype=np.float32),
                "pitch_shift": np.asarray([0.0], dtype=np.float32),
                "pitch_range": np.asarray([1.0], dtype=np.float32),
            }
            try:
                outputs = self._session.run(None, inputs)
                audio = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
                if self.volume < 1.0:
                    audio = audio * np.float32(self.volume)
                audio = np.clip(audio, -1.0, 1.0)
                if audio.size == 0:
                    raise TTSError("Tiny Voca вернула пустой аудиофрагмент.")
                return audio, sample_rate
            except TTSError:
                raise
            except Exception as exc:
                logger.exception("tiny_voca_synthesis_failed voice=%s", self.voice_name)
                raise TTSError(f"Ошибка синтеза речи Tiny Voca: {exc}") from exc

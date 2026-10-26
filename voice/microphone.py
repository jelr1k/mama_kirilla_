from __future__ import annotations

import logging
import time
from threading import Lock

import numpy as np
import sounddevice as sd

from voice.devices import resolve_shared_input_device, get_shared_input_extra_settings


logger = logging.getLogger("jarvis.voice.microphone")


class MicrophoneRecorder:
    """Small push-to-talk recorder backed by the system microphone."""

    _SILENCE_RMS_THRESHOLD = 0.01

    def __init__(self, sample_rate: int = 16000, channels: int = 1, device=None):
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.device = device
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._lock = Lock()
        self._last_voice_at = 0.0
        self._has_voice = False

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    @property
    def has_voice(self) -> bool:
        with self._lock:
            return self._has_voice

    @property
    def silence_duration(self) -> float:
        with self._lock:
            if not self._has_voice or self._last_voice_at <= 0:
                return 0.0
            return max(0.0, time.monotonic() - self._last_voice_at)

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._chunks = []
            self._last_voice_at = 0.0
            self._has_voice = False

        try:
            target_dev = self.device
            if target_dev is None:
                try:
                    def_idx = sd.default.device[0]
                    if def_idx is not None and def_idx >= 0:
                        target_dev = def_idx
                except Exception:
                    pass
            shared_device = resolve_shared_input_device(target_dev)
            extra_settings = get_shared_input_extra_settings(shared_device)
            stream_device = shared_device if shared_device is not None else self.device
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=stream_device,
                extra_settings=extra_settings,
                callback=self._callback,
            )
            self._stream.start()
            logger.info(
                "microphone_recording_started sample_rate=%s channels=%s device=%r (stream_device=%r, shared=%s)",
                self.sample_rate,
                self.channels,
                self.device,
                stream_device,
                extra_settings is not None,
            )
        except Exception:
            self._stream = None
            logger.exception("microphone_recording_start_failed")
            raise

    def stop(self) -> np.ndarray:
        stream = self._stream
        self._stream = None
        if stream is None:
            return np.empty(0, dtype=np.float32)

        try:
            stream.stop()
            stream.close()
        finally:
            with self._lock:
                chunks = self._chunks
                self._chunks = []
                self._last_voice_at = 0.0
                self._has_voice = False

        if not chunks:
            return np.empty(0, dtype=np.float32)

        audio = np.concatenate(chunks, axis=0)
        if self.channels > 1:
            audio = np.mean(audio, axis=1)
        else:
            audio = audio[:, 0]

        audio = np.asarray(audio, dtype=np.float32)
        logger.info(
            "microphone_recording_stopped samples=%d duration=%.2fs",
            len(audio),
            len(audio) / self.sample_rate,
        )
        return audio

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("microphone_stream_status=%s", status)

        chunk = indata.copy()
        rms = float(np.sqrt(np.mean(np.square(chunk)))) if chunk.size else 0.0
        now = time.monotonic()

        with self._lock:
            self._chunks.append(chunk)
            if rms >= self._SILENCE_RMS_THRESHOLD:
                self._has_voice = True
                self._last_voice_at = now

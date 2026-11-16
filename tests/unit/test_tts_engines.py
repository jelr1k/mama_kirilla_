from __future__ import annotations

import json
from unittest.mock import Mock

import numpy as np
import pytest

from core.events import EventBus
from voice.tts.engines import (
    TTS_ENGINES,
    PiperTTSBackend,
    SileroTTSBackend,
    SupertonicTTSBackend,
    TeraTTSBackend,
    TinyVocaTTSBackend,
    create_tts_backend,
    list_tts_voices,
    resolve_engine_for_voice,
)
from voice.tts.service import TTSService


def test_tts_registry_resolves_engines_and_lists_voices():
    assert "piper" in TTS_ENGINES
    assert "tiny_voca" in TTS_ENGINES
    assert resolve_engine_for_voice("ru_RU-dmitri-medium") == "piper"
    assert resolve_engine_for_voice("tiny-voca:F2") == "tiny_voca"
    assert resolve_engine_for_voice("tiny-voca:M2") == "tiny_voca"

    voices = list_tts_voices()
    ids = {v["id"] for v in voices}
    assert "ru_RU-dmitri-medium" in ids
    assert "tiny-voca:F2" in ids
    assert "tiny-voca:M2" in ids


def test_create_tts_backend_auto_selects_tiny_voca():
    backend = create_tts_backend("auto", voice_name="tiny-voca:M2", speed=1.1, volume=0.7)
    assert isinstance(backend, TinyVocaTTSBackend)
    assert backend.voice_name == "tiny-voca:M2"
    assert backend.speed == pytest.approx(1.1)
    assert backend.volume == pytest.approx(0.7)

    piper = create_tts_backend("auto", voice_name="ru_RU-irina-medium")
    assert isinstance(piper, PiperTTSBackend)


def test_tiny_voca_encode_and_synthesize_with_mocked_session(tmp_path):
    (tmp_path / "onnx").mkdir(parents=True)
    (tmp_path / "phonemizer").mkdir(parents=True)
    (tmp_path / "onnx" / "model.onnx").write_bytes(b"0" * 2048)

    config_data = {
        "sample_rate": 24000,
        "voices": ["F2", "M2"],
        "model": {"max_tokens": 512},
        "vocab": {
            "<pad>": 0, "<bos>": 1, "<eos>": 2, "<sp>": 3, "<unk>": 4,
            "!": 8, "h": 31, "ə": 43, "l": 35, "oʊ": 62,
        },
    }
    (tmp_path / "config.json").write_text(json.dumps(config_data), encoding="utf-8")
    (tmp_path / "phonemizer" / "lexicon.json").write_text(
        json.dumps({"hello": "h ə l ˈoʊ"}),
        encoding="utf-8",
    )

    backend = TinyVocaTTSBackend(model_dir=tmp_path, voice_name="tiny-voca:F2", speed=1.0, volume=0.5)
    assert backend.voice_status() == "installed"

    fake_session = Mock()
    fake_session.run.return_value = [np.ones((1, 240), dtype=np.float32)]
    backend._session = fake_session

    audio, sr = backend.synthesize("Hello!")
    assert sr == 24000
    assert audio.shape == (240,)
    assert np.allclose(audio, 0.5)

    feed = fake_session.run.call_args[0][1]
    assert feed["tokens"][0, 0] == 1  # <bos>
    assert feed["tokens"][0, -1] == 2  # <eos>
    assert feed["voice"].tolist() == [0]  # F2


def test_tts_service_hot_switches_engine_on_apply_config():
    events = EventBus()
    service = TTSService(events, {"tts": {"enabled": False, "voice": "ru_RU-dmitri-medium"}}, player=Mock())
    try:
        assert isinstance(service._backend, PiperTTSBackend)

        service.apply_config({
            "tts": {
                "enabled": False,
                "engine": "auto",
                "voice": "tiny-voca:F2",
                "speed": 1.0,
                "volume": 0.8,
            }
        })
        assert isinstance(service._backend, TinyVocaTTSBackend)
        assert service._backend.voice_name == "tiny-voca:F2"

        service.apply_config({
            "tts": {
                "enabled": False,
                "voice": "ru_RU-irina-medium",
            }
        })
        assert isinstance(service._backend, PiperTTSBackend)
        assert service._backend.voice_name == "ru_RU-irina-medium"
    finally:
        service.close()


def test_new_russian_engines_registered_and_resolved(tmp_path):
    for eid in ("silero", "teratts", "supertonic"):
        assert eid in TTS_ENGINES

    assert resolve_engine_for_voice("silero:baya") == "silero"
    assert resolve_engine_for_voice("teratts:ru_f1") == "teratts"
    assert resolve_engine_for_voice("supertonic:F4") == "supertonic"

    voices = list_tts_voices()
    by_id = {v["id"]: v for v in voices}
    for vid in ("silero:baya", "silero:kseniya", "teratts:ru_f1", "supertonic:F4"):
        assert vid in by_id
        assert by_id[vid]["language"] == "ru"
        assert isinstance(by_id[vid]["size_mb"], int)

    assert isinstance(create_tts_backend("auto", voice_name="silero:kseniya"), SileroTTSBackend)
    assert isinstance(create_tts_backend("auto", voice_name="teratts:ru_f1"), TeraTTSBackend)
    assert isinstance(create_tts_backend("auto", voice_name="supertonic:F4"), SupertonicTTSBackend)

    silero = SileroTTSBackend(model_dir=tmp_path / "silero", voice_name="silero:baya")
    assert silero.voice_status() == "missing"
    (tmp_path / "silero").mkdir(parents=True)
    (tmp_path / "silero" / "v5_6_ru.pt").write_bytes(b"x" * (1024 * 1024 + 16))
    assert silero.voice_status() == "installed"

    tera = TeraTTSBackend(model_dir=tmp_path / "tera", voice_name="teratts:ru_f1")
    assert tera.voice_status() == "missing"

    sup = SupertonicTTSBackend(model_dir=tmp_path / "sup", voice_name="supertonic:F4")
    assert sup.voice_status() == "missing"


def test_tts_status_includes_download_progress_and_errors():
    from types import SimpleNamespace
    from services.gateway.routers.voice import tts_voices_status

    fake_tts = Mock()
    fake_tts.voice_status.return_value = "missing"
    gateway = SimpleNamespace(
        app_context=SimpleNamespace(tts_service=fake_tts),
        _model_download_states={"tts:silero:baya": "downloading", "tts:teratts:ru_f1": "failed"},
        _model_download_errors={"tts:teratts:ru_f1": "network timeout"},
        _model_download_progress={
            "tts:silero:baya": {
                "downloaded_bytes": 50_000_000,
                "total_bytes": 141_000_000,
                "percent": 35.5,
                "current_file": "v5_6_ru.pt",
            }
        },
    )

    res = tts_voices_status(gateway=gateway)
    assert res["statuses"]["silero:baya"] == "downloading"
    assert res["progress"]["silero:baya"]["percent"] == 35.5
    assert res["statuses"]["teratts:ru_f1"] == "failed"
    assert res["errors"]["teratts:ru_f1"] == "network timeout"

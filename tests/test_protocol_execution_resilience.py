from __future__ import annotations

from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest

from services.stark_protocols import StarkProtocols


def test_launch_if_not_running_missing_app_handles_cleanly():
    # If app path cannot be resolved and startfile fails, function should return False without crashing
    with patch.object(StarkProtocols, "is_app_running", return_value=False), \
         patch.object(StarkProtocols, "_resolve_app_path", return_value=None), \
         patch("os.startfile", side_effect=FileNotFoundError("Executable not found")):

        ok, msg = StarkProtocols.launch_if_not_running("non_existent_custom_tool")
        assert ok is False
        assert msg == "путь не найден"


def test_weather_info_network_error_graceful_fallback():
    # When Open-Meteo times out or throws URLError, get_weather_info should return empty string
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        weather = StarkProtocols.get_weather_info()
        assert weather == ""


def test_dynamic_protocol_briefing_survives_weather_failure():
    proto = {
        "id": "morning",
        "name": "Доброе утро",
        "briefing": True,
        "response_text": "Системы в строю.",
    }
    with patch.object(StarkProtocols, "get_weather_info", return_value=""):
        res = StarkProtocols.execute_protocol(proto)
        assert "Доброе утро, сэр. Время" in res
        assert "Системы в строю." in res


def test_dynamic_protocol_llm_failure_falls_back_to_stark():
    proto = {
        "id": "cinema",
        "name": "Кино",
        "close_mode": "cinema",
        "open_apps": [],
        "response_text": "",
    }
    with patch.object(StarkProtocols, "_try_generate_llm_response", return_value=None), \
         patch.object(StarkProtocols, "close_apps_for_cinema"):

        res = StarkProtocols.execute_protocol(proto)
        assert isinstance(res, str)
        assert bool(res)
        # Should contain one of the cinema fallback phrases
        assert any(word in res for word in ("Кино", "просмотра", "сеансу", "Звук", "сэр"))


def test_clean_desk_recycle_bin_error():
    with patch("services.stark_protocols.empty_recycle_bin", return_value={"success": False, "error": "Корзина заблокирована"}):
        res = StarkProtocols.execute_protocol("clean_desk")
        assert "Не удалось очистить корзину" in res
        assert "Корзина заблокирована" in res

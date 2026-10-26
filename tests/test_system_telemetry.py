from __future__ import annotations

from unittest.mock import Mock

from core.alias_manager import AliasManager
from services.command_router import CommandRouter
from services.rofl_service import RoflService
from tools.system_info import get_system_telemetry


def test_get_system_telemetry_returns_hardware_stats():
    res = get_system_telemetry()
    assert res["success"] is True
    assert res["system_telemetry"] is True
    assert "Состояние системы:" in res["content"]
    assert "Процессор:" in res["content"]
    assert "Оперативная память:" in res["content"]
    assert isinstance(res["cpu_percent"], (int, float))
    assert isinstance(res["ram_percent"], (int, float))
    assert res["ram_total_gb"] > 0


def test_command_router_routes_telemetry_queries():
    config = {
        "tools": {"get_system_telemetry": True},
        "model": "qwen",
        "temperature": 0.7,
        "context_length": 4096,
        "max_tokens": 128,
    }
    router = CommandRouter(config, Mock(), AliasManager())

    reply = router.route("телеметрия пк")
    assert reply is not None
    assert "Состояние системы:" in reply
    assert "Оперативная память:" in reply

    reply2 = router.route("че по нагрузке")
    assert reply2 is not None
    assert "Состояние системы:" in reply2


def test_rofl_service_recognizes_telemetry_action(monkeypatch):
    assert RoflService._router_action("телеметрия пк") == "system_telemetry"
    assert RoflService._router_action("нагрузка процессора") == "system_telemetry"
    assert RoflService._router_action("че по нагрузке") == "system_telemetry"

    bus = Mock()
    emitted = []
    bus.emit = lambda event, *args: emitted.append((event, args))
    service = RoflService(bus)

    monkeypatch.setattr("services.rofl_service.random.random", lambda: 0.0)
    monkeypatch.setattr("services.rofl_service.random.choice", lambda seq: seq[0])

    service.maybe_router_response("телеметрия пк", "Состояние системы:\nOK")
    assert any(event == "chat.rofl_response" for event, _ in emitted)


def test_hardware_detection_fallback_no_hardcoded_strings(monkeypatch):
    from tools.system_info import _get_cpu_name, _get_gpu_name

    # При отказе реестра функции не должны возвращать чужое железо (6500 XT / Ryzen)
    monkeypatch.setattr("tools.system_info.winreg", None)
    monkeypatch.setattr("platform.processor", lambda: "")

    cpu = _get_cpu_name()
    gpu = _get_gpu_name()

    assert cpu == "Не удалось определить"
    assert gpu == "Не удалось определить"
    assert "6500" not in gpu
    assert "Ryzen" not in cpu

from unittest.mock import Mock
from services.rofl_service import RoflService


class FakeEventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    def unsubscribe(self, event, handler):
        self.handlers[event].remove(handler)

    def emit(self, event, *args):
        for handler in list(self.handlers.get(event, [])):
            handler(*args)


def test_rofl_ignores_failed_and_other_tools():
    bus = FakeEventBus()
    RoflService(bus)
    emitted = []
    bus.subscribe("chat.rofl_response", emitted.append)

    bus.emit("tool.executed", "open_url", {"url": "https://example.com"}, {"success": True})
    bus.emit("tool.executed", "launch_application", {"target": "test"}, {"success": False})

    assert emitted == []


def test_rofl_emits_normal_response(monkeypatch):
    bus = FakeEventBus()
    RoflService(bus)
    emitted = []
    spoken = []
    bus.subscribe("chat.rofl_response", emitted.append)
    bus.subscribe("speech.requested", lambda text, source: spoken.append((text, source)))

    values = iter([0.0, 1.0])
    monkeypatch.setattr("services.rofl_service.random.random", lambda: next(values))
    monkeypatch.setattr("services.rofl_service.random.choice", lambda seq: seq[0])

    bus.emit(
        "tool.executed",
        "launch_application",
        {"target": "C:\\Apps\\Kirill.exe"},
        {"success": True, "path": "C:\\Apps\\Kirill.exe"},
    )

    assert emitted == ["Готово, Kirill.exe открыта."]
    assert spoken == [("Готово, Kirill.exe открыта.", "rofl")]


def test_rofl_emits_demon_response(monkeypatch):
    bus = FakeEventBus()
    RoflService(bus)
    emitted = []
    bus.subscribe("chat.rofl_response", emitted.append)

    values = iter([0.0, 0.0])
    monkeypatch.setattr("services.rofl_service.random.random", lambda: next(values))
    monkeypatch.setattr("services.rofl_service.random.choice", lambda seq: seq[0])

    bus.emit("tool.executed", "launch_application", {"target": "Discord"}, {"success": True})

    assert emitted == ["Ритуал завершён. Он уже здесь."]


def test_router_rofl_uses_latin_response(monkeypatch):
    bus = FakeEventBus()
    service = RoflService(bus)
    emitted = []
    bus.subscribe("chat.rofl_response", emitted.append)

    values = iter([0.0, 0.0])
    monkeypatch.setattr("services.rofl_service.random.random", lambda: next(values))
    monkeypatch.setattr("services.rofl_service.random.choice", lambda seq: seq[0])

    service.maybe_router_response("удали файл test.txt", "Готово.", action="delete")

    assert emitted == ["Deletio perfecta est. Iam non est."]


def test_router_rofl_ignores_failed_response(monkeypatch):
    bus = FakeEventBus()
    service = RoflService(bus)
    emitted = []
    bus.subscribe("chat.rofl_response", emitted.append)

    monkeypatch.setattr("services.rofl_service.random.random", lambda: 0.0)

    service.maybe_router_response(
        "закрой Discord",
        "Не удалось закрыть Discord: процесс не найден.",
        action="close",
    )

    assert emitted == []


def test_rofl_settings_are_applied():
    bus = FakeEventBus()
    config = {"rofl": {"chance": 0.42, "demon_chance": 0.33}}
    service = RoflService(bus, config)

    assert service.rofl_chance == 0.42
    assert service.demon_chance == 0.33

    bus.emit("rofl.settings_changed", {"chance": 0.75, "demon_chance": 0.2})

    assert service.rofl_chance == 0.75
    assert service.demon_chance == 0.2


def test_router_action_prefers_extended_command():
    assert RoflService._router_action("найди приложение Discord") == "find_application"
    assert RoflService._router_action("открой https://example.com") == "open_url"


def test_router_action_recognizes_ollama_and_model_commands():
    assert RoflService._router_action("запусти олламу") == "ollama_start"
    assert RoflService._router_action("включи сервер ollama") == "ollama_start"
    assert RoflService._router_action("останови олламу") == "ollama_stop"
    assert RoflService._router_action("потуши сервер ollama") == "ollama_stop"
    assert RoflService._router_action("выгрузи модель") == "model_unload"
    assert RoflService._router_action("освободи квена") == "model_unload"


def test_router_action_recognizes_new_extended_commands():
    assert RoflService._router_action("найди на ютубе котики") == "search_youtube"
    assert RoflService._router_action("найди в яндексе погода") == "search_yandex"
    assert RoflService._router_action("найди в гугле питон") == "search_google"
    assert RoflService._router_action("протокол кино") == "protocol_stark"
    assert RoflService._router_action("кириешка протокол кино") == "protocol_stark"
    assert RoflService._router_action("свернись") == "jarvis_window"
    assert RoflService._router_action("на весь экран") == "jarvis_window"
    assert RoflService._router_action("зайди на хабр") == "open_website"
    assert RoflService._router_action("открой сайт github") == "open_website"

    # Проверка, что обычный запуск не превращается в сайт
    assert RoflService._router_action("запусти калькулятор") == "launch"

    # Проверка запуска игры через роутер со SteamManager
    mock_router = Mock()
    mock_router._resolve_action.return_value = ("launch", "dota 2")
    mock_router.steam_manager.resolve_game.return_value = {"name": "Dota 2"}
    assert RoflService._router_action("запусти доту", router=mock_router) == "steam_game"


def test_router_rofl_emits_ollama_response(monkeypatch):
    bus = FakeEventBus()
    service = RoflService(bus)
    emitted = []
    bus.subscribe("chat.rofl_response", emitted.append)

    monkeypatch.setattr("services.rofl_service.random.random", lambda: 0.0)
    monkeypatch.setattr("services.rofl_service.random.choice", lambda seq: seq[0])

    service.maybe_router_response("запусти олламу", "Ollama Server запущен.")
    assert len(emitted) == 1
    assert any(needle in emitted[0] for needle in ["Ollama experrecta est", "Оллама проснулась"])

def test_router_action_recognizes_blind_zones():
    assert RoflService._router_action("запусти запрет") == "zapret_start"
    assert RoflService._router_action("включи vpn") == "vpn_connect"
    assert RoflService._router_action("статус vpn") == "vpn_status"
    assert RoflService._router_action("примени мышь") == "apply_mouse_settings"
    assert RoflService._router_action("числа фибоначчи") == "fibonacci_calculator"
    assert RoflService._router_action("статус оллама") == "ollama_status"
    assert RoflService._router_action("чистый стол") == "protocol_stark"


def test_router_action_distinguishes_uptime_and_datetime():
    assert RoflService._router_action("аптайм") == "system_telemetry"
    assert RoflService._router_action("время работы пк") == "system_telemetry"
    assert RoflService._router_action("сколько работает пк") == "system_telemetry"
    assert RoflService._router_action("сколько времени") == "date_time"
    assert RoflService._router_action("который час") == "date_time"


def test_rofl_merge_response_for_action_and_info():
    merged_bin = RoflService.merge_response("очисти корзину", "Корзина очищена.")
    normal_lines, latin_lines = RoflService.ROUTER_LINES["empty_recycle_bin"]
    assert merged_bin in normal_lines + latin_lines

    raw_telemetry = "Состояние системы:\n• Процессор: AMD Ryzen 5 3600 (загрузка: 12%)\n• Видеокарта: RX 6500 XT"
    merged_telemetry = RoflService.merge_response("телеметрия", raw_telemetry)
    assert "AMD Ryzen 5 3600" in merged_telemetry
    assert "Состояние системы:" in merged_telemetry
    assert len(merged_telemetry.splitlines()) > len(raw_telemetry.splitlines())

    raw_time = "Сейчас 12:30, суббота, 8 ноября 2026 г."
    merged_time = RoflService.merge_response("сколько времени", raw_time)
    assert "12:30" in merged_time
    assert len(merged_time) > len(raw_time)


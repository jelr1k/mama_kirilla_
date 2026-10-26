from __future__ import annotations

from unittest.mock import Mock, patch
import pytest

from core.website_manager import WebsiteManager
from tools.system_actions import empty_recycle_bin
from tools.files import create_file, create_folder, delete_file, copy_file, move_file
from services.command_router import CommandRouter


@pytest.fixture
def temp_website_manager(tmp_path):
    json_path = tmp_path / "websites.json"
    return WebsiteManager(file_path=json_path)


def test_website_manager_defaults(temp_website_manager):
    sites = temp_website_manager.get_websites()
    assert len(sites) >= 7
    res = temp_website_manager.resolve_url("ютуб")
    assert res is not None
    assert "youtube.com" in res[1]


def test_website_manager_auto_aliases(temp_website_manager):
    auto = temp_website_manager.generate_auto_aliases("https://mysite.com/blog", "Мой Сайт")
    assert "мой сайт" in auto
    assert "mysite" in auto
    assert any("маи" in a or "мисит" in a or "мисите" in a for a in auto)


def test_website_manager_crud(temp_website_manager):
    item = temp_website_manager.add_website("Habr", "https://habr.com", ["хабр", "habr"])
    assert item["name"] == "Habr"
    res = temp_website_manager.resolve_url("хабр")
    assert res is not None
    assert res[1] == "https://habr.com"

    # Update
    temp_website_manager.update_website(item["id"], "Habr Media", "https://habr.com/ru/all", ["хабрик"])
    res2 = temp_website_manager.resolve_url("хабрик")
    assert res2 is not None
    assert res2[1] == "https://habr.com/ru/all"

    # Delete
    deleted = temp_website_manager.delete_website(item["id"])
    assert deleted is True
    assert temp_website_manager.resolve_url("хабрик") is None


def test_empty_recycle_bin_tool(monkeypatch):
    monkeypatch.setattr("ctypes.windll.shell32.SHEmptyRecycleBinW", lambda *args: 0)
    res = empty_recycle_bin()
    assert res["success"] is True
    assert "Корзина очищена" in res["content"]


def test_command_router_empty_recycle_bin(tmp_path, monkeypatch):
    cfg = {"tools": {"empty_recycle_bin": True}}
    router = CommandRouter(config=cfg, ollama_manager=Mock())
    monkeypatch.setattr("ctypes.windll.shell32.SHEmptyRecycleBinW", lambda *args: 0)
    for phrase in ["очисти корзину", "почисти мусор", "вынеси мусор", "очистить корзину"]:
        reply = router.route(phrase)
        assert reply is not None
        assert "Корзина очищена" in reply


def test_command_router_web_search(tmp_path, monkeypatch):
    router = CommandRouter(config={}, ollama_manager=Mock())
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda u: opened_urls.append(u))

    reply_google = router.route("загугли как играть в rimworld")
    assert reply_google is not None
    assert "Google" in reply_google
    assert any("google.com" in u and "rimworld" in u for u in opened_urls)

    opened_urls.clear()
    reply_yt = router.route("найди на ютубе rimworld гайд")
    assert reply_yt is not None
    assert "YouTube" in reply_yt
    assert any("youtube.com" in u and "rimworld" in u for u in opened_urls)


def test_command_router_open_website(tmp_path, monkeypatch):
    wm = WebsiteManager(file_path=tmp_path / "websites.json")
    router = CommandRouter(config={}, ollama_manager=Mock(), website_manager=wm)
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda u: opened_urls.append(u))

    reply = router.route("открой ютуб")
    assert reply is not None
    assert "YouTube" in reply
    assert any("youtube.com" in u for u in opened_urls)


def test_files_prevent_overwrite(tmp_path):
    with patch("tools.paths.TOOL_WORKSPACE", tmp_path), patch("security.sandbox.WORKSPACE_DIR", tmp_path):
        create_file("source.txt", "content 1")
        create_file("dest.txt", "content 2")

        res_copy = copy_file("source.txt", "dest.txt")
        assert res_copy["success"] is False
        assert "уже существует" in res_copy["error"]

        res_move = move_file("source.txt", "dest.txt")
        assert res_move["success"] is False
        assert "уже существует" in res_move["error"]


def test_delete_folder_directory(tmp_path):
    with patch("tools.paths.TOOL_WORKSPACE", tmp_path), patch("security.sandbox.WORKSPACE_DIR", tmp_path):
        create_folder("test_dir")
        create_file("test_dir/nested.txt", "hello")
        res = delete_file("test_dir")
        assert res["success"] is True
        assert not (tmp_path / "test_dir").exists()


def test_chat_service_async_empty_recycle_bin(tmp_path, monkeypatch):
    from services.chat_service import ChatService
    from core.events import EventBus
    from concurrent.futures import Future

    events = EventBus()
    responses = []
    events.subscribe("chat.direct_response", lambda text: responses.append(text))

    class ImmediateRunner:
        def __init__(self):
            self.submitted = []

        def submit(self, fn, *args, **kwargs):
            fut = Future()
            fut.set_result(fn(*args, **kwargs))
            self.submitted.append(fut)
            return fut

    monkeypatch.setattr("ctypes.windll.shell32.SHEmptyRecycleBinW", lambda *args: 0)

    service = ChatService(
        Mock(),
        {"tools": {"empty_recycle_bin": True}, "model": "qwen", "temperature": 0.7, "context_length": 4096, "max_tokens": 128},
        event_bus=events,
        task_runner=ImmediateRunner(),
    )

    service.send("очисти корзину")

    assert any("Корзина очищена" in r for r in responses)
    assert any("Корзина очищена" in m.content for m in service.conversation.messages if m.role == "assistant")


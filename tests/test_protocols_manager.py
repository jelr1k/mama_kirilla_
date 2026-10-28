from __future__ import annotations

import json
from unittest.mock import Mock
import pytest

from core.protocols_manager import ProtocolsManager, DEFAULT_PROTOCOLS
from presentation.protocols_controller import ProtocolsController


@pytest.fixture
def temp_protocols_file(tmp_path):
    return tmp_path / "protocols.json"


@pytest.fixture
def protocols_mgr(temp_protocols_file):
    return ProtocolsManager(file_path=temp_protocols_file)


def test_protocols_manager_defaults(protocols_mgr, temp_protocols_file):
    profiles = protocols_mgr.list_profiles()
    assert "default" in profiles
    assert profiles["default"] == "\u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 (\u0422\u043e\u043d\u0438)"

    active = protocols_mgr.get_active_profile()
    assert active == "default"

    protocols = protocols_mgr.get_protocols()
    assert len(protocols) == len(DEFAULT_PROTOCOLS)

    proto_ids = {p["id"] for p in protocols}
    assert "morning" in proto_ids
    assert "lockdown" in proto_ids
    assert "cinema" in proto_ids
    assert "game" in proto_ids
    assert "clean_desk" in proto_ids
    assert "work" in proto_ids
    assert "default" in proto_ids

    assert temp_protocols_file.exists()


def test_protocols_manager_profile_management(protocols_mgr):
    guest_id = protocols_mgr.add_profile("\u0413\u043e\u0441\u0442\u044c")
    assert bool(guest_id)

    profiles = protocols_mgr.list_profiles()
    assert guest_id in profiles
    assert profiles[guest_id] == "\u0413\u043e\u0441\u0442\u044c"
    assert protocols_mgr.get_active_profile() == guest_id

    guest_protos = protocols_mgr.get_protocols()
    assert len(guest_protos) == len(DEFAULT_PROTOCOLS)

    morning = protocols_mgr.get_protocol_by_id("morning")
    assert morning is not None
    morning["open_apps"] = ["notepad"]
    protocols_mgr.save_protocol(morning)

    assert protocols_mgr.get_protocol_by_id("morning")["open_apps"] == ["notepad"]

    protocols_mgr.set_active_profile("default")
    assert protocols_mgr.get_active_profile() == "default"
    assert protocols_mgr.get_protocol_by_id("morning")["open_apps"] == ["opera", "discord", "steam"]

    deleted = protocols_mgr.delete_profile(guest_id)
    assert deleted is True
    assert guest_id not in protocols_mgr.list_profiles()

    assert protocols_mgr.delete_profile("default") is False


def test_protocols_manager_crud(protocols_mgr):
    new_proto = {
        "name": "\u0421\u0442\u0440\u0438\u043c",
        "description": "\u0417\u0430\u043f\u0443\u0441\u043a OBS \u0438 Twitch",
        "phrases": [
            "\u043f\u043e\u0433\u043d\u0430\u043b\u0438 \u0441\u0442\u0440\u0438\u043c\u0438\u0442\u044c",
            "\u043f\u0440\u043e\u0442\u043e\u043a\u043e\u043b \u0441\u0442\u0440\u0438\u043c",
        ],
        "open_apps": ["obs64", "opera"],
        "close_mode": "none",
        "close_apps": [],
        "volume_mode": "max",
        "pause_media": False,
        "lock_screen": False,
        "clean_recycle_bin": False,
        "briefing": False,
        "response_text": "\u0421\u0442\u0440\u0438\u043c-\u0440\u0435\u0436\u0438\u043c \u0433\u043e\u0442\u043e\u0432 \u043a \u044d\u0444\u0438\u0440\u0443.",
    }
    pid = protocols_mgr.save_protocol(new_proto)
    assert bool(pid)

    saved = protocols_mgr.get_protocol_by_id(pid)
    assert saved is not None
    assert saved["name"] == "\u0421\u0442\u0440\u0438\u043c"

    matched = protocols_mgr.find_protocol_by_phrase("\u041f\u043e\u0433\u043d\u0430\u043b\u0438 \u0441\u0442\u0440\u0438\u043c\u0438\u0442\u044c!")
    assert matched is not None
    assert matched["id"] == pid

    saved["name"] = "\u0421\u0442\u0440\u0438\u043c 2.0"
    protocols_mgr.save_protocol(saved)
    assert protocols_mgr.get_protocol_by_id(pid)["name"] == "\u0421\u0442\u0440\u0438\u043c 2.0"

    assert protocols_mgr.delete_protocol(pid) is True
    assert protocols_mgr.get_protocol_by_id(pid) is None
    assert protocols_mgr.find_protocol_by_phrase("\u043f\u043e\u0433\u043d\u0430\u043b\u0438 \u0441\u0442\u0440\u0438\u043c\u0438\u0442\u044c") is None


def test_protocols_controller_signals(protocols_mgr):
    controller = ProtocolsController(protocols_mgr)

    changed_mock = Mock()
    profile_changed_mock = Mock()
    controller.changed.connect(changed_mock)
    controller.profile_changed.connect(profile_changed_mock)

    pid = controller.add_profile("\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c")
    assert changed_mock.called
    profile_changed_mock.assert_called_with(pid)

    changed_mock.reset_mock()
    controller.save_protocol({
        "name": "\u041d\u043e\u0432\u044b\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439",
        "phrases": ["\u0442\u0435\u0441\u0442 \u0444\u0440\u0430\u0437\u0430"],
    })
    assert changed_mock.called

from unittest.mock import patch

from voice.devices import list_input_devices, resolve_shared_input_device


_HOSTAPIS = [
    {"name": "MME", "default_input_device": 0},
    {"name": "Windows WASAPI", "default_input_device": 1},
    {"name": "Windows WDM-KS", "default_input_device": 2},
]
_DEVICES = [
    {"name": "Микрофон (USB Audio Device)", "max_input_channels": 1, "hostapi": 0},
    {"name": "Микрофон (USB Audio Device)", "max_input_channels": 1, "hostapi": 1},
    {"name": "Микрофон (MicIn)", "max_input_channels": 1, "hostapi": 2},
]


def test_wdmks_devices_are_hidden_from_list():
    result = list_input_devices(_DEVICES, _HOSTAPIS)
    assert [item["index"] for item in result] == [1]


def test_wdmks_device_falls_back_to_wasapi_default():
    with patch("voice.devices.sd.query_devices", return_value=_DEVICES), patch("voice.devices.sd.query_hostapis", return_value=_HOSTAPIS):
        assert resolve_shared_input_device(2) == 1

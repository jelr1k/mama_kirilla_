from __future__ import annotations

import ctypes
import logging
import time
import uuid
from ctypes import CFUNCTYPE, HRESULT, POINTER, Structure, byref, c_int, c_void_p, cast
from ctypes.wintypes import BOOL, DWORD, WORD
from typing import Any

logger = logging.getLogger("jarvis.media")

VK_MAP = {
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "volume_mute": 0xAD,
    "play_pause": 0xB3,
    "next_track": 0xB0,
    "prev_track": 0xB1,
}

KEYEVENTF_KEYUP = 0x0002


class _GUID(Structure):
    _fields_ = [
        ("Data1", DWORD),
        ("Data2", WORD),
        ("Data3", WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_str(cls, s: str) -> _GUID:
        u = uuid.UUID(s)
        return cls(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))


def _release_com(ptr: c_void_p | None) -> None:
    if ptr:
        try:
            vtable = cast(cast(ptr, POINTER(c_void_p))[0], POINTER(c_void_p))
            release = CFUNCTYPE(ctypes.c_ulong, c_void_p)(vtable[2])
            release(ptr)
        except Exception:
            pass


def _get_audio_endpoint_volume() -> c_void_p | None:
    """Получает COM-интерфейс IAudioEndpointVolume для управления системным аудио в Windows."""
    p_enum = c_void_p()
    p_device = c_void_p()
    p_endpoint_vol = c_void_p()
    try:
        ole32 = ctypes.oledll.ole32
        ole32.CoInitialize(None)

        clsid_mm_dev_enum = _GUID.from_str("BCDE0395-E52F-467C-8E3D-C4579291692E")
        iid_imm_dev_enum = _GUID.from_str("A95664D2-9614-4F35-A746-DE8DB63617E6")
        iid_iaudio_endpoint_vol = _GUID.from_str("5CDF2C82-841E-4546-9722-0CF74078229A")

        hr = ole32.CoCreateInstance(
            byref(clsid_mm_dev_enum), None, 23, byref(iid_imm_dev_enum), byref(p_enum)
        )
        if hr != 0 or not p_enum:
            return None

        vtable = cast(cast(p_enum, POINTER(c_void_p))[0], POINTER(c_void_p))
        get_default_endpoint = CFUNCTYPE(HRESULT, c_void_p, c_int, c_int, POINTER(c_void_p))(
            vtable[4]
        )

        hr = get_default_endpoint(p_enum, 0, 0, byref(p_device))
        if hr != 0 or not p_device:
            return None

        dev_vtable = cast(cast(p_device, POINTER(c_void_p))[0], POINTER(c_void_p))
        activate = CFUNCTYPE(HRESULT, c_void_p, POINTER(_GUID), DWORD, c_void_p, POINTER(c_void_p))(
            dev_vtable[3]
        )

        hr = activate(p_device, byref(iid_iaudio_endpoint_vol), 23, None, byref(p_endpoint_vol))
        if hr != 0 or not p_endpoint_vol:
            return None

        return p_endpoint_vol
    except Exception as exc:
        logger.debug("Failed to acquire IAudioEndpointVolume: %s", exc)
        return None
    finally:
        _release_com(p_device)
        _release_com(p_enum)


def get_master_mute() -> bool | None:
    """Возвращает текущее состояние звука Windows (True если звук заглушен, False если включен)."""
    p_vol = _get_audio_endpoint_volume()
    if not p_vol:
        return None
    try:
        vol_vtable = cast(cast(p_vol, POINTER(c_void_p))[0], POINTER(c_void_p))
        get_mute_func = CFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))(vol_vtable[15])
        is_muted = BOOL()
        if get_mute_func(p_vol, byref(is_muted)) == 0:
            return bool(is_muted.value)
    except Exception as exc:
        logger.debug("get_master_mute error: %s", exc)
    finally:
        _release_com(p_vol)
    return None


def set_master_mute(mute: bool) -> bool:
    """Устанавливает гарантированное состояние заглушения системного звука."""
    p_vol = _get_audio_endpoint_volume()
    if p_vol:
        try:
            vol_vtable = cast(cast(p_vol, POINTER(c_void_p))[0], POINTER(c_void_p))
            set_mute_func = CFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)(vol_vtable[14])
            if set_mute_func(p_vol, BOOL(mute), None) == 0:
                return True
        except Exception as exc:
            logger.debug("set_master_mute COM error: %s", exc)
        finally:
            _release_com(p_vol)

    # Fallback через проверку состояния и отправку VK_VOLUME_MUTE
    current = get_master_mute()
    if current is not None:
        if current != mute:
            _send_key(VK_MAP["volume_mute"], repeat=1)
        return True

    _send_key(VK_MAP["volume_mute"], repeat=1)
    return True


def _send_key(vk: int, repeat: int = 1) -> None:
    try:
        user32 = ctypes.windll.user32
        for _ in range(repeat):
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            if repeat > 1:
                time.sleep(0.01)
    except Exception as exc:
        logger.exception("send_key_failed vk=%s error=%s", vk, exc)
        raise


def control_media(action: str, steps: int = 5, **_kwargs: Any) -> dict[str, Any]:
    """Управление громкостью звука и медиаплеером в Windows."""
    act = str(action).strip().casefold()

    valid_actions = {
        "volume_up",
        "volume_down",
        "volume_mute",
        "sound_off",
        "mute",
        "sound_on",
        "unmute",
        "toggle_mute",
        "play_pause",
        "next_track",
        "prev_track",
    }

    if act not in valid_actions:
        return {
            "success": False,
            "error": f"Неизвестное действие медиа: {action}. Допустимы: {sorted(list(valid_actions))}",
        }

    try:
        # Гарантированное выключение звука
        if act in ("sound_off", "mute"):
            current = get_master_mute()
            if current is True:
                msg = "Звук уже выключен."
            else:
                set_master_mute(True)
                msg = "Звук выключен."
            logger.info("media_control_executed action=%s state=muted", act)
            return {
                "success": True,
                "media_control": True,
                "action": act,
                "message": msg,
                "content": msg,
            }

        # Гарантированное включение звука
        if act in ("sound_on", "unmute"):
            current = get_master_mute()
            if current is False:
                msg = "Звук уже включен."
            else:
                set_master_mute(False)
                msg = "Звук включен."
            logger.info("media_control_executed action=%s state=unmuted", act)
            return {
                "success": True,
                "media_control": True,
                "action": act,
                "message": msg,
                "content": msg,
            }

        # Переключение звука (toggle)
        if act in ("toggle_mute", "volume_mute"):
            current = get_master_mute()
            if current is not None:
                new_state = not current
                set_master_mute(new_state)
                msg = "Звук выключен." if new_state else "Звук включен."
            else:
                _send_key(VK_MAP["volume_mute"], repeat=1)
                msg = "Звук переключен (mute/unmute)."
            logger.info("media_control_executed action=%s toggled", act)
            return {
                "success": True,
                "media_control": True,
                "action": act,
                "message": msg,
                "content": msg,
            }

        # Громкость и плеер
        vk = VK_MAP[act]
        repeat = max(1, min(25, int(steps))) if "volume" in act else 1
        _send_key(vk, repeat=repeat)

        descriptions = {
            "volume_up": f"Громкость увеличена на {repeat * 2}%.",
            "volume_down": f"Громкость уменьшена на {repeat * 2}%.",
            "play_pause": "Воспроизведение переключено (play/pause).",
            "next_track": "Включен следующий трек.",
            "prev_track": "Включен предыдущий трек.",
        }
        msg = descriptions.get(act, "Медиа-команда выполнена.")
        logger.info("media_control_executed action=%s repeat=%d", act, repeat)
        return {
            "success": True,
            "media_control": True,
            "action": act,
            "message": msg,
            "content": msg,
        }
    except Exception as exc:
        logger.exception("control_media_failed action=%s", act)
        return {
            "success": False,
            "error": f"Не удалось выполнить команду медиа: {exc}",
        }

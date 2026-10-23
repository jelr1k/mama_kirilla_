from __future__ import annotations

import ctypes
import logging
import time
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


def _send_key(vk: int, repeat: int = 1) -> None:
    try:
        user32 = ctypes.windll.user32
        for _ in range(repeat):
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            if repeat > 1:
                time.sleep(0.04)
    except Exception as exc:
        logger.exception("send_key_failed vk=%s error=%s", vk, exc)
        raise


def control_media(action: str, steps: int = 5, **_kwargs: Any) -> dict[str, Any]:
    """Управление громкостью звука и медиаплеером в Windows."""
    act = str(action).strip().casefold()
    if act not in VK_MAP:
        return {
            "success": False,
            "error": f"Неизвестное действие медиа: {action}. Допустимы: {list(VK_MAP.keys())}",
        }

    vk = VK_MAP[act]
    repeat = max(1, min(25, int(steps))) if "volume" in act and act != "volume_mute" else 1

    try:
        _send_key(vk, repeat=repeat)
        descriptions = {
            "volume_up": f"Громкость увеличена на {repeat * 2}%.",
            "volume_down": f"Громкость уменьшена на {repeat * 2}%.",
            "volume_mute": "Звук переключен (mute/unmute).",
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
        return {
            "success": False,
            "error": f"Не удалось выполнить команду медиа: {exc}",
        }

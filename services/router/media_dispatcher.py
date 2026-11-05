from __future__ import annotations

from typing import Callable
from services.command_catalog import match_command_definition
from tools.executor import ToolExecutor

MEDIA_COMMAND_MAPPING: tuple[tuple[str, str], ...] = (
    ("media_volume_up", "volume_up"),
    ("media_volume_down", "volume_down"),
    ("media_sound_off", "sound_off"),
    ("media_sound_on", "sound_on"),
    ("media_mute_toggle", "toggle_mute"),
    ("media_stop", "stop"),
    ("media_play_pause", "play_pause"),
    ("media_next", "next_track"),
    ("media_prev", "prev_track"),
)


def dispatch_media_command(
    text: str,
    executor: ToolExecutor,
    reply_fn: Callable[[dict], str],
) -> str | None:
    """Обрабатывает команды управления системным звуком и медиаплеером."""
    for media_cmd, media_act in MEDIA_COMMAND_MAPPING:
        match = match_command_definition(media_cmd, text)
        if match and executor._is_enabled("control_media"):
            steps = 5
            if match.groups() and match.group(1):
                try:
                    steps = max(1, min(25, int(match.group(1)) // 2))
                except ValueError:
                    pass
            return reply_fn(executor.execute("control_media", {"action": media_act, "steps": steps}))
    return None

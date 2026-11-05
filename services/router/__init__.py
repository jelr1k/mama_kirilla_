from __future__ import annotations

from services.router.media_dispatcher import dispatch_media_command
from services.router.site_dispatcher import dispatch_site_command
from services.router.protocols_dispatcher import dispatch_protocol_command
from services.router.system_dispatcher import (
    dispatch_system_command,
    dispatch_jarvis_window_command,
)
from services.router.app_dispatcher import (
    dispatch_file_command,
    dispatch_app_management_command,
    dispatch_ollama_control_command,
)

__all__ = [
    "dispatch_media_command",
    "dispatch_site_command",
    "dispatch_protocol_command",
    "dispatch_system_command",
    "dispatch_jarvis_window_command",
    "dispatch_file_command",
    "dispatch_app_management_command",
    "dispatch_ollama_control_command",
]

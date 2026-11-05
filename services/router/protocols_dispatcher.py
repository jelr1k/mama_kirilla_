from __future__ import annotations

from typing import Any
from services.command_catalog import match_command_definition
from services.stark_protocols import StarkProtocols

PROTOCOLS_MAPPING: tuple[tuple[str, str], ...] = (
    ("protocol_morning", "morning"),
    ("protocol_lockdown", "lockdown"),
    ("protocol_cinema", "cinema"),
    ("protocol_game", "game"),
    ("protocol_clean_desk", "clean_desk"),
    ("protocol_work", "work"),
    ("protocol_default", "default"),
)


def dispatch_protocol_command(
    text: str,
    protocols_manager: Any,
    config: Any,
) -> str | None:
    """Обрабатывает фирменные и пользовательские протоколы Jarvis."""
    if protocols_manager is not None:
        matched_proto = protocols_manager.find_protocol_by_phrase(text)
        if matched_proto is not None:
            ollama_url = getattr(config, "ollama_url", None)
            model = config.get("model") if hasattr(config, "get") else None
            return StarkProtocols.execute_protocol(matched_proto, ollama_url=ollama_url, model=model)

    for proto_cmd, proto_id in PROTOCOLS_MAPPING:
        if match_command_definition(proto_cmd, text):
            return StarkProtocols.execute_protocol(proto_id)

    return None

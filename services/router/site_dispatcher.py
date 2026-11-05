from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Callable

from services.command_catalog import match_command_definition
from tools.executor import ToolExecutor


def dispatch_site_command(
    text: str,
    executor: ToolExecutor,
    reply_fn: Callable[[dict], str],
    direct_tool_fn: Callable,
    confirmation_callback=None,
) -> str | None:
    """Обрабатывает веб-поиск (Google, YouTube, Яндекс) и прямое открытие URL."""
    for search_cmd, engine in (
        ("search_google", "google"),
        ("search_youtube", "youtube"),
        ("search_yandex", "yandex"),
    ):
        match = match_command_definition(search_cmd, text)
        if match:
            query = match.group(1).strip()
            if engine == "youtube":
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return f"Ищу «{query}» на YouTube."
            elif engine == "yandex":
                url = f"https://ya.ru/search/?text={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return f"Ищу «{query}» в Яндексе."
            else:
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return f"Ищу «{query}» в Google."

    match = match_command_definition("open_url", text)
    if match and executor._is_enabled("open_url"):
        return direct_tool_fn("open_url", {"url": match.group(1)}, confirmation_callback)

    return None

from __future__ import annotations

import logging
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any, Callable

logger = logging.getLogger("jarvis.protocol_adapters")

CHROMIUM_BROWSERS = {
    "vivaldi",
    "chrome",
    "google chrome",
    "opera",
    "opera gx",
    "msedge",
    "edge",
    "brave",
    "yandex",
    "chromium",
}

FIREFOX_BROWSERS = {
    "firefox",
    "mozilla firefox",
    "librewolf",
    "waterfox",
}


def resolve_role_token(token: str, roles: dict[str, str] | None = None) -> str:
    """Разрешает токен вида 'role:browser' в конкретный app_key из карты ролей."""
    raw = str(token or "").strip()
    if not raw:
        return ""
    if raw.lower().startswith("role:"):
        role_name = raw.split(":", 1)[1].strip().lower()
        if roles and role_name in roles and str(roles[role_name]).strip():
            return str(roles[role_name]).strip()
        return role_name
    return raw


def expand_app_match_tokens(app_key: str, patterns_fn: Callable[[str], list[str]] | None = None) -> set[str]:
    """Собирает нормализованные токены для сопоставления приложения (ключ, .exe, имя без .exe)."""
    norm = str(app_key or "").strip().lower()
    if not norm:
        return set()
    tokens = {norm}
    if norm.endswith(".exe"):
        tokens.add(norm[:-4])
    else:
        tokens.add(f"{norm}.exe")
    if patterns_fn is not None:
        try:
            for pat in patterns_fn(norm):
                p = str(pat or "").strip().lower()
                if p:
                    tokens.add(p)
                    if p.endswith(".exe"):
                        tokens.add(p[:-4])
        except Exception:
            pass
    return tokens


def is_app_in_lock_list(
    app_token: str,
    lock_list: list[str] | set[str] | None,
    roles: dict[str, str] | None = None,
    patterns_fn: Callable[[str], list[str]] | None = None,
) -> bool:
    """Проверяет, попадает ли приложение (или его роль) в список исключений протокола."""
    if not lock_list:
        return False
    resolved_target = resolve_role_token(app_token, roles)
    target_tokens = expand_app_match_tokens(app_token, patterns_fn) | expand_app_match_tokens(
        resolved_target, patterns_fn
    )
    for item in lock_list:
        resolved_item = resolve_role_token(str(item), roles)
        item_tokens = expand_app_match_tokens(str(item), patterns_fn) | expand_app_match_tokens(
            resolved_item, patterns_fn
        )
        if target_tokens & item_tokens:
            return True
    return False


class BrowserAdapter:
    """Универсальный адаптер для запуска URL и профилей в Chromium- и Firefox-браузерах."""

    @staticmethod
    def detect_family(browser_key: str, exe_path: Path | None = None) -> str:
        candidates = [str(browser_key or "").strip().lower()]
        if exe_path is not None:
            candidates.append(exe_path.stem.lower())
        for cand in candidates:
            if any(name in cand for name in FIREFOX_BROWSERS):
                return "firefox"
            if any(name in cand for name in CHROMIUM_BROWSERS):
                return "chromium"
        return "chromium"

    @classmethod
    def build_launch_args(
        cls,
        browser_key: str,
        urls: list[str],
        profile: str | None = None,
        new_window: bool = False,
        exe_path: Path | None = None,
    ) -> list[str]:
        family = cls.detect_family(browser_key, exe_path=exe_path)
        args: list[str] = []
        clean_profile = str(profile or "").strip()
        clean_urls = [str(u).strip() for u in urls if str(u).strip()]

        if family == "firefox":
            if clean_profile:
                args.extend(["-P", clean_profile])
            if new_window and clean_urls:
                args.extend(["-new-window", clean_urls[0]])
                for url in clean_urls[1:]:
                    args.extend(["-new-tab", url])
            else:
                for url in clean_urls:
                    args.extend(["-new-tab", url])
        else:
            if clean_profile:
                args.append(f"--profile-directory={clean_profile}")
            if new_window:
                args.append("--new-window")
            args.extend(clean_urls)

        return args

    @classmethod
    def open_urls(
        cls,
        browser_key: str,
        urls: list[str],
        profile: str | None = None,
        new_window: bool = False,
        resolve_path_fn: Callable[[str], Path | None] | None = None,
        focus_fn: Callable[[str], bool] | None = None,
    ) -> tuple[bool, str]:
        clean_urls = [str(u).strip() for u in urls if str(u).strip()]
        if not clean_urls:
            return False, "Не указаны ссылки для открытия"

        exe_path = resolve_path_fn(browser_key) if resolve_path_fn else None
        if not exe_path or not exe_path.is_file():
            return False, f"Браузер '{browser_key}' не найден в системе"

        args = cls.build_launch_args(
            browser_key=browser_key,
            urls=clean_urls,
            profile=profile,
            new_window=new_window,
            exe_path=exe_path,
        )
        try:
            cmd = [str(exe_path), *args]
            popen_kwargs: dict[str, Any] = {"cwd": str(exe_path.parent)}
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0
                )
            subprocess.Popen(cmd, **popen_kwargs)
            if focus_fn is not None:
                focus_fn(browser_key)
            return True, f"открыто ссылок: {len(clean_urls)}"
        except Exception as exc:
            logger.exception("browser_adapter_open_urls_failed browser=%s", browser_key)
            return False, str(exc)


class GenericAppAdapter:
    """Адаптер запуска произвольных программ с аргументами и ожиданием окна через WinAPI."""

    @staticmethod
    def parse_args(raw_args: str | list[str] | None) -> str:
        if raw_args is None:
            return ""
        if isinstance(raw_args, list):
            parts = [str(x).strip() for x in raw_args if str(x).strip()]
            return subprocess.list2cmdline(parts) if parts else ""
        return str(raw_args).strip()

    @classmethod
    def launch(
        cls,
        app_key: str,
        args: str | list[str] | None = None,
        wait_window: bool = True,
        focus: bool = True,
        resolve_path_fn: Callable[[str], Path | None] | None = None,
        is_running_fn: Callable[[str], bool] | None = None,
        focus_fn: Callable[[str], bool] | None = None,
        wait_window_fn: Callable[[str, float], bool] | None = None,
        launch_winapi_fn: Callable[[Path, str | None], None] | None = None,
    ) -> tuple[bool, str]:
        param_str = cls.parse_args(args)

        if not param_str and is_running_fn and is_running_fn(app_key):
            if focus and focus_fn:
                focus_fn(app_key)
            return True, "уже запущено"

        exe_path = resolve_path_fn(app_key) if resolve_path_fn else None
        if not exe_path or not exe_path.exists():
            return False, f"Приложение '{app_key}' не обнаружено в системе"

        try:
            if launch_winapi_fn is not None:
                launch_winapi_fn(exe_path, param_str or None)
            else:
                cmd = [str(exe_path)]
                if param_str:
                    cmd.extend(shlex.split(param_str, posix=False))
                subprocess.Popen(cmd, cwd=str(exe_path.parent))

            if wait_window and wait_window_fn is not None:
                wait_window_fn(app_key, 4.0)
            elif focus and focus_fn is not None:
                focus_fn(app_key)

            return True, "запущено"
        except Exception as exc:
            logger.exception("generic_app_adapter_launch_failed app=%s", app_key)
            return False, str(exc)

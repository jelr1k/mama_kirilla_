from __future__ import annotations

import logging
import statistics
import time
from pathlib import Path
from typing import Any, Iterable

import psutil

from core.vpn.constants import (
    CLIENTS,
    _CLICKABLE_TYPES,
    _CONNECT_WORDS,
    _DISCONNECT_WORDS,
    _EXCLUDE_WORDS,
)
from core.vpn.discovery import process_running

logger = logging.getLogger("jarvis.vpn.uia")


def is_flclash_vpn_running(definition: dict[str, Any], *, proc_checker: Any = None) -> bool:
    """Проверяет запущенность службы или виртуального интерфейса FlClashX."""
    is_running = proc_checker or process_running
    if is_running(definition.get("daemon_process_names", ())):
        return True
    if is_running(definition.get("gui_process_names", ())):
        try:
            for iface in psutil.net_if_addrs():
                lower_name = iface.casefold()
                if any(x in lower_name for x in ("clash", "mihomo", "meta", "sing-box", "flclash", "tun")):
                    return True
        except Exception:
            pass
    return False


def collect_pids(definition: dict[str, Any]) -> set[int]:
    """Собирает PID всех процессов, соответствующих GUI-клиенту."""
    wanted = {name.casefold() for name in definition["gui_process_names"]}
    pids: set[int] = set()
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = str(proc.info.get("name") or "").casefold()
            exe_name = Path(str(proc.info.get("exe") or "")).name.casefold()
            if name in wanted or exe_name in wanted:
                pids.add(int(proc.info["pid"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, KeyError):
            continue
    return pids


def find_uia_window(auto: Any, pids: set[int]) -> Any:
    """Находит главное окно UIA по списку PID процессов."""
    if not pids:
        return None
    try:
        root = auto.GetRootControl()
        for window in root.GetChildren():
            try:
                if window.ProcessId not in pids:
                    continue
                if window.ControlTypeName != "WindowControl":
                    continue
                if not window.Name and not window.BoundingRectangle:
                    continue
                return window
            except Exception:
                continue
    except Exception:
        return None
    return None


def iter_uia_controls(control: Any, max_depth: int = 14, max_count: int = 900) -> Iterable[Any]:
    """Обходит дерево UIA элементов в глубину с ограничениями."""
    stack = [(control, 0)]
    yielded = 0
    while stack and yielded < max_count:
        current, depth = stack.pop()
        yield current
        yielded += 1
        if depth >= max_depth:
            continue
        try:
            children = current.GetChildren()
        except Exception:
            children = []
        for child in reversed(children):
            stack.append((child, depth + 1))


def control_text(control: Any) -> str:
    """Извлекает нормализованный текстовый лейбл из элемента управления UIA."""
    parts = []
    for attribute in ("Name", "AutomationId", "HelpText"):
        try:
            value = getattr(control, attribute, "")
            if value:
                parts.append(str(value))
        except Exception:
            continue
    return " ".join(parts).casefold().replace("ё", "е")


def control_area(control: Any) -> int:
    """Возвращает площадь прямоугольника элемента управления."""
    try:
        rect = control.BoundingRectangle
        width = max(0, int(rect.right - rect.left))
        height = max(0, int(rect.bottom - rect.top))
        return width * height
    except Exception:
        return 0


def find_clickable(
    controls: list[Any],
    words: Iterable[str],
    *,
    exclude: Iterable[str] = (),
) -> list[Any]:
    """Находит кликабельные элементы управления, содержащие заданные ключевые слова."""
    words = tuple(str(word).casefold() for word in words)
    exclude = tuple(str(word).casefold() for word in exclude)
    result = []
    for control in controls:
        try:
            if control.ControlTypeName not in _CLICKABLE_TYPES:
                continue
            if not control.IsEnabled or control.IsOffscreen:
                continue
        except Exception:
            continue
        text = control_text(control)
        if not text:
            continue
        if any(word in text for word in exclude):
            continue
        if any(word in text for word in words):
            result.append(control)
    return result


def largest_unlabeled_button(controls: list[Any]) -> Any | None:
    """Эвристика поиска основной круглой/большой кнопки без текста (типично для VPN-клиентов)."""
    buttons = []
    for control in controls:
        try:
            if control.ControlTypeName != "ButtonControl":
                continue
            if not control.IsEnabled or control.IsOffscreen:
                continue
            name = str(control.Name or "").strip()
            if name:
                continue
        except Exception:
            continue
        area = control_area(control)
        if area >= 2500:
            buttons.append((area, control))
    if not buttons:
        return None
    buttons.sort(key=lambda item: item[0], reverse=True)
    areas = [area for area, _ in buttons]
    median = statistics.median(areas)
    if len(buttons) == 1 or buttons[0][0] >= max(median * 2.5, 2500):
        return buttons[0][1]
    return None


def activate_with_uia(key: str, timeout: float = 14.0, *, driver: Any = None) -> tuple[bool, bool, str]:
    """
    Пытается найти окно запущенного клиента и нажать кнопку подключения через Windows UIAutomation.
    Возвращает кортеж: (успех_активации, уже_было_активно, описание_действия).
    """
    try:
        import uiautomation as auto
    except ImportError:
        logger.warning("uiautomation_not_installed")
        return False, False, "модуль uiautomation не установлен"

    fn_collect_pids = getattr(driver, "_collect_pids", collect_pids)
    fn_find_window = getattr(driver, "_find_uia_window", find_uia_window)
    fn_iter_controls = getattr(driver, "_iter_uia_controls", iter_uia_controls)
    fn_find_clickable = getattr(driver, "_find_clickable", find_clickable)
    fn_control_text = getattr(driver, "_control_text", control_text)
    fn_control_area = getattr(driver, "_control_area", control_area)
    fn_largest_btn = getattr(driver, "_largest_unlabeled_button", largest_unlabeled_button)

    deadline = time.monotonic() + timeout
    definition = CLIENTS[key]
    last_error = "окно клиента не найдено"

    try:
        with auto.UIAutomationInitializerInThread():
            window = None
            while time.monotonic() < deadline:
                pids = fn_collect_pids(definition)
                window = fn_find_window(auto, pids)
                if window is not None:
                    break
                time.sleep(0.5)
            if window is None:
                return False, False, last_error

            try:
                window.SetActive()
                window.SetFocus()
            except Exception:
                pass

            controls = list(fn_iter_controls(window, max_depth=14, max_count=900))
            logger.info("uia_controls_collected key=%s count=%d", key, len(controls))

            disconnect = fn_find_clickable(controls, _DISCONNECT_WORDS, exclude=_CONNECT_WORDS)
            candidates = fn_find_clickable(controls, _CONNECT_WORDS, exclude=_EXCLUDE_WORDS)
            candidates.sort(key=lambda ctrl: (ctrl.ControlTypeName != "ButtonControl", -fn_control_area(ctrl)))

            for candidate in candidates[:6]:
                name = fn_control_text(candidate)
                try:
                    candidate.Click(simulateMove=False)
                    return True, False, f"нажата кнопка «{name}»"
                except Exception as exc:
                    last_error = f"не удалось нажать «{name}»: {exc}"
                    try:
                        candidate.GetInvokePattern().Invoke()
                        return True, False, f"нажата кнопка «{name}»"
                    except Exception:
                        continue

            if disconnect:
                return True, True, f"найдена кнопка «{fn_control_text(disconnect[0])}»"

            fallback = fn_largest_btn(controls)
            if fallback is not None:
                try:
                    fallback.Click(simulateMove=False)
                    return True, False, "нажата самая крупная кнопка на экране"
                except Exception as exc:
                    last_error = f"не удалось нажать крупную кнопку: {exc}"
    except Exception as exc:
        logger.exception("uia_activation_failed key=%s", key)
        last_error = str(exc)

    return False, False, last_error

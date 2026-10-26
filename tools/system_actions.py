from __future__ import annotations

import ctypes
import logging
import sys

logger = logging.getLogger("jarvis.tools.system_actions")

SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004


def empty_recycle_bin() -> dict:
    """Очищает корзину Windows через системный Shell API без всплывающих диалогов."""
    logger.info("empty_recycle_bin_called")
    if sys.platform != "win32":
        return {"success": False, "error": "Очистка корзины поддерживается только на Windows."}

    try:
        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        logger.info("recycle_bin_emptied_result code=%s", res)
        # 0 = S_OK
        return {"success": True, "content": "Корзина очищена."}
    except Exception as exc:
        logger.exception("recycle_bin_failed")
        return {"success": False, "error": f"Не удалось очистить корзину: {exc}"}

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure tests don't fail with PermissionError if Windows locks AppData\Local\Temp\pytest-of-<user>
_base_tmp = Path(tempfile.gettempdir())
_safe_tmp = _base_tmp if _base_tmp.name == "jt" else _base_tmp / "jt"
try:
    _safe_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(_safe_tmp)
    os.environ["TMP"] = str(_safe_tmp)
    tempfile.tempdir = str(_safe_tmp)
except Exception:
    pass

# Hermetic test isolation: redirect APPDATA and LOCALAPPDATA so tests never touch
# user's live session token, real logs, or persistent settings.
_test_local = _safe_tmp / "test_localappdata"
_test_roaming = _safe_tmp / "test_appdata"
try:
    _test_local.mkdir(parents=True, exist_ok=True)
    _test_roaming.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(_test_local)
    os.environ["APPDATA"] = str(_test_roaming)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure core.app_paths uses the isolated directories
import core.app_paths as _ap  # noqa: E402

_ap._LOCAL_BASE = _test_local
_ap._PRIMARY_LOCAL = _test_local / "Assistant"
_ap._LEGACY_LOCAL = _test_local / "Jarvis"
_ap.LOCAL_DATA_DIR = _ap._PRIMARY_LOCAL
_ap.LOG_DIR = _ap.LOCAL_DATA_DIR / "logs"
_ap.MODELS_DIR = _ap.LOCAL_DATA_DIR / "models"
_ap.SESSION_TOKEN_PATH = _ap.LOCAL_DATA_DIR / "session.token"

_ap._ROAMING_BASE = _test_roaming
_ap._PRIMARY_ROAMING = _test_roaming / "Assistant"
_ap._LEGACY_ROAMING = _test_roaming / "Jarvis"
_ap.APP_DATA_DIR = _ap._PRIMARY_ROAMING
_ap.CONFIG_FILE = _ap.APP_DATA_DIR / "settings.json"
_ap.ALIASES_FILE = _ap.APP_DATA_DIR / "aliases.json"
_ap.WEBSITES_FILE = _ap.APP_DATA_DIR / "websites.json"
_ap.PROTOCOLS_FILE = _ap.APP_DATA_DIR / "protocols.json"

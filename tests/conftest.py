from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Ensure tests don't fail with PermissionError if Windows locks AppData\Local\Temp\pytest-of-<user>
_safe_tmp = Path(tempfile.gettempdir()) / "jarvis_pytest_temp"
try:
    _safe_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(_safe_tmp)
    os.environ["TMP"] = str(_safe_tmp)
    tempfile.tempdir = str(_safe_tmp)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



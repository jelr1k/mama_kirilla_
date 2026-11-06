from __future__ import annotations

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories that must not have hardcoded developer paths or drive letters
PRODUCTION_DIRS = [
    REPO_ROOT / "core",
    REPO_ROOT / "services",
    REPO_ROOT / "tools",
]

# Patterns of forbidden hardcoded paths
FORBIDDEN_PATTERNS = [
    re.compile(r"D:[/\\]rzz[/\\]steam", re.IGNORECASE),
    re.compile(r"[A-Za-z]:[/\\]Users[/\\]", re.IGNORECASE),
]


def test_no_hardcoded_developer_paths_in_production():
    violations = []
    for pdir in PRODUCTION_DIRS:
        for py_file in pdir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(content.splitlines(), start=1):
                # Skip comments or docstrings that document forbidden paths
                stripped = line.strip()
                if stripped.startswith("#") or '"""' in stripped or "'''" in stripped:
                    continue
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        rel_path = py_file.relative_to(REPO_ROOT)
                        violations.append(f"{rel_path}:{line_no}: {line.strip()}")

    assert not violations, "Found forbidden hardcoded developer paths:\n" + "\n".join(violations)


def test_stark_protocols_steam_resolution():
    from services.stark_protocols import StarkProtocols

    # Verify that Steam resolution uses SteamManager / winreg rather than hardcoded D:/rzz
    path = StarkProtocols._resolve_app_path("steam")
    # Even if Steam is not installed or found on this test runner, it should not be D:/rzz/steam
    if path:
        assert "rzz" not in str(path).lower()

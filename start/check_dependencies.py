"""Quick check for required packages declared in requirements.txt."""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from importlib.metadata import distribution, PackageNotFoundError
except ImportError:  # pragma: no cover
    distribution = None
    PackageNotFoundError = Exception


def get_missing_dependencies(requirements_file: Path) -> list[str]:
    """Return a list of package names that are missing from the current Python environment."""
    if not requirements_file.is_file() or distribution is None:
        return []

    missing: list[str] = []
    try:
        content = requirements_file.read_text(encoding="utf-8")
    except OSError:
        return []

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Environment markers like: pywin32; platform_system == "Windows"
        if ";" in line:
            spec, marker = line.split(";", 1)
            marker = marker.strip()
            if "platform_system" in marker and "Windows" in marker and sys.platform != "win32":
                continue
        else:
            spec = line

        pkg_name = re.split(r"[<>=!~ ]", spec.strip())[0].strip()
        if not pkg_name:
            continue
        try:
            distribution(pkg_name)
        except PackageNotFoundError:
            missing.append(pkg_name)
        except Exception:
            missing.append(pkg_name)

    return missing


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "start" else script_dir
    req_file = project_root / "config" / "requirements.txt"
    if not req_file.is_file():
        req_file = project_root / "requirements.txt"

    missing = get_missing_dependencies(req_file)
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

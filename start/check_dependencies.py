from __future__ import annotations

import argparse
import importlib.metadata
import logging
import re
import sys
from pathlib import Path

try:
    from packaging.requirements import Requirement
except ImportError:  # pragma: no cover
    Requirement = None

logger = logging.getLogger("jarvis.dependencies_check")


def check_requirements_file(requirements_path: Path | str) -> tuple[bool, list[str]]:
    """Быстро проверяет, установлены ли все зависимости из requirements.txt без вызова pip.
    
    Возвращает (all_satisfied, missing_or_invalid_list).
    """
    path = Path(requirements_path)
    if not path.is_file():
        return True, []

    missing: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if Requirement is not None:
            try:
                req = Requirement(line)
                if req.marker and not req.marker.evaluate():
                    continue
                dist = importlib.metadata.distribution(req.name)
                if req.specifier and not req.specifier.contains(dist.version, prereleases=True):
                    missing.append(f"{req.name} ({dist.version} не соответствует {req.specifier})")
            except Exception:
                missing.append(line)
        else:
            # Fallback без библиотеки packaging
            if ";" in line:
                marker_part = line.split(";", 1)[1].strip()
                if 'platform_system == "Windows"' in marker_part and sys.platform != "win32":
                    continue
                line = line.split(";", 1)[0].strip()

            name_match = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
            if not name_match:
                continue
            pkg_name = name_match.group(1)
            try:
                importlib.metadata.distribution(pkg_name)
            except Exception:
                missing.append(pkg_name)

    return len(missing) == 0, missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Быстрая проверка установленных зависимостей Jarvis.")
    parser.add_argument("requirements_file", nargs="?", default="", help="Путь к requirements.txt")
    parser.add_argument("--quiet", "-q", action="store_true", help="Не выводить лишний текст")
    args = parser.parse_args()

    req_file = args.requirements_file
    if not req_file:
        root = Path(__file__).resolve().parent.parent
        for candidate in (root / "config" / "requirements.txt", root / "requirements.txt"):
            if candidate.is_file():
                req_file = str(candidate)
                break

    if not req_file:
        if not args.quiet:
            print("Файл requirements.txt не найден.")
        return 0

    satisfied, missing = check_requirements_file(req_file)
    if satisfied:
        if not args.quiet:
            print("Все зависимости Jarvis установлены.")
        return 0

    if not args.quiet:
        print(f"Обнаружены отсутствующие или несовместимые зависимости ({len(missing)}):")
        for item in missing:
            print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

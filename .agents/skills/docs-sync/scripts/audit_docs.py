#!/usr/bin/env python3
"""Deterministic documentation audit script for JARVIS (Kirieshka v2).

Auto-discovers source directories and active docs (excluding docs/archive/) so
normal codebase changes (new modules, routers, UI screens, docs) do not break
the audit script itself.

Checks:
1. Broken relative markdown links [label](target).
2. Local machine-specific file:/// links that break portability.
3. Broken backtick file/directory paths in prose.
4. Active docs/*.md missing from docs/INDEX.md.
5. Source files missing from docs/COMPONENTS_MAP.md (path-aware, not bare basename).
6. Version consistency across core/version.py, ui/package.json, tauri.conf.json, README.md.
7. Hardcoded test counts in docs vs quick static test count in tests/ and ui/src/.
8. Optional --facts snapshot of current routers, events, dispatchers, and UI views.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

IGNORED_TOP_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".pytest_temp",
    ".agents",
    ".gemini",
    ".github",
    "node_modules",
    "docs",
    "tests",
    "ui",
    "ui_archive",
    "logs",
    "workspace",
    "data",
    "scripts",
    "__pycache__",
}

UI_SOURCE_SUBDIRS = ("ui/src", "ui/src-tauri/src")

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".bat", ".vbs"}
CONFIG_TRACKED_FILES = {"config/settings.json", "config/models.json", "config/requirements.txt", "config/requirements-dev.txt"}

IGNORED_BASENAMES = {
    "__init__.py",
    "setupTests.js",
    "main.jsx",
    "index.js",
    "index.css",
    "Icons.jsx",
}

LEGACY_OR_META_PREFIXES = (
    "ui/",
    "ui_archive/",
    "tests/",
    "docs/",
    ".gemini/",
    ".agents/",
)

RUNTIME_OR_PLACEHOLDER_PREFIXES = (
    "workspace/",
    "logs/",
    "data/",
    "ui/dist",
    "ui/src-tauri/target",
    "ui/node_modules",
)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
ROUTER_RE = re.compile(r'@router\.(get|post|put|delete|patch|websocket)\(\s*["\']([^"\']+)["\']')
TEST_COUNT_LINE_RE = re.compile(r"\b(\d{2,4})\s+(?:тест\w*|passed|vitest)\b", re.IGNORECASE)
PY_TEST_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+test_", re.MULTILINE)
JS_TEST_DEF_RE = re.compile(r"\b(?:it|test)\s*\(")


def find_repo_root(start: Path) -> Path:
    """Walk upward from start until .git or AGENTS.md is found."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "AGENTS.md").exists():
            return candidate
    raise RuntimeError("Could not locate repository root (.git or AGENTS.md)")


def collect_active_docs(repo_root: Path) -> list[Path]:
    """Collect active markdown files excluding docs/archive."""
    docs: list[Path] = []
    for fixed in ("README.md", "AGENTS.md", ".gemini/rules.md"):
        p = repo_root / fixed
        if p.is_file():
            docs.append(p)

    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for p in sorted(docs_dir.glob("*.md")):
            docs.append(p)
    return docs


def discover_known_prefixes(repo_root: Path) -> tuple[str, ...]:
    """Build checkable path prefixes dynamically from repo root + known meta dirs."""
    prefixes: set[str] = set(LEGACY_OR_META_PREFIXES)
    for child in repo_root.iterdir():
        if child.is_dir() and child.name not in IGNORED_TOP_DIRS:
            prefixes.add(f"{child.name}/")
    return tuple(sorted(prefixes))


def extract_versions(repo_root: Path) -> dict[str, str | None]:
    """Read application version from core/version.py, UI configs, and README.md."""
    versions: dict[str, str | None] = {
        "core/version.py": None,
        "ui/package.json": None,
        "ui/src-tauri/tauri.conf.json": None,
        "README.md": None,
    }

    version_file = repo_root / "core" / "version.py"
    if version_file.is_file():
        text = version_file.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', text)
        versions["core/version.py"] = m.group(1) if m else None

    pkg_file = repo_root / "ui" / "package.json"
    if pkg_file.is_file():
        try:
            versions["ui/package.json"] = json.loads(pkg_file.read_text(encoding="utf-8")).get("version")
        except Exception:
            pass

    tauri_file = repo_root / "ui" / "src-tauri" / "tauri.conf.json"
    if tauri_file.is_file():
        try:
            versions["ui/src-tauri/tauri.conf.json"] = json.loads(tauri_file.read_text(encoding="utf-8")).get("version")
        except Exception:
            pass

    readme_file = repo_root / "README.md"
    if readme_file.is_file():
        head = "\n".join(readme_file.read_text(encoding="utf-8", errors="replace").splitlines()[:30])
        m = re.search(r"\bv?(\d+\.\d+\.\d+)\b", head)
        versions["README.md"] = m.group(1) if m else None

    return versions


def check_markdown_links(repo_root: Path, doc_path: Path, lines: list[str]) -> tuple[list[dict], list[dict]]:
    """Verify local relative markdown links and flag machine-specific file:// links."""
    broken: list[dict] = []
    local_abs: list[dict] = []
    rel_doc = doc_path.relative_to(repo_root).as_posix()

    for lineno, line in enumerate(lines, start=1):
        for match in LINK_RE.finditer(line):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith("#"):
                continue
            if raw_target.startswith("file://"):
                local_abs.append({"doc": rel_doc, "line": lineno, "target": raw_target})
                continue
            if raw_target.startswith(("http://", "https://", "mailto:")):
                continue

            target = raw_target.split()[0].split("#", 1)[0]
            if not target:
                continue

            resolved = (doc_path.parent / target).resolve()
            if not resolved.exists():
                broken.append({"doc": rel_doc, "line": lineno, "target": raw_target, "reason": "broken_link"})
    return broken, local_abs


def is_checkable_backtick_path(token: str, known_prefixes: tuple[str, ...]) -> bool:
    """Return True if backtick content looks like a concrete repo file/dir path."""
    if any(ch in token for ch in ("*", "<", ">", "{", "}", " ", "...", "|", ":")):
        return False
    if token.startswith(RUNTIME_OR_PLACEHOLDER_PREFIXES):
        return False
    return token.startswith(known_prefixes)


def check_backtick_paths(
    repo_root: Path, doc_path: Path, lines: list[str], known_prefixes: tuple[str, ...]
) -> list[dict]:
    """Verify concrete repo paths mentioned in backticks."""
    issues: list[dict] = []
    rel_doc = doc_path.relative_to(repo_root).as_posix()
    in_fence = False

    for lineno, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in BACKTICK_RE.finditer(line):
            token = match.group(1).strip()
            if not is_checkable_backtick_path(token, known_prefixes):
                continue

            candidate = repo_root / token.rstrip("/")
            if not candidate.exists():
                issues.append({"doc": rel_doc, "line": lineno, "target": token, "reason": "missing_path"})
    return issues


def collect_source_files(repo_root: Path) -> list[str]:
    """Auto-discover tracked source and key config files across the repository."""
    files: list[str] = []

    top_dirs: list[Path] = []
    for child in sorted(repo_root.iterdir()):
        if child.is_dir() and child.name not in IGNORED_TOP_DIRS:
            top_dirs.append(child)
    for ui_sub in UI_SOURCE_SUBDIRS:
        p = repo_root / ui_sub
        if p.is_dir():
            top_dirs.append(p)

    for root_dir in top_dirs:
        for p in sorted(root_dir.rglob("*")):
            if not p.is_file():
                continue
            if any(part in ("__pycache__", "node_modules", "dist", "target") for part in p.parts):
                continue
            rel = p.relative_to(repo_root).as_posix()
            if p.name in IGNORED_BASENAMES or ".test." in p.name:
                continue
            if p.suffix in SOURCE_SUFFIXES or rel in CONFIG_TRACKED_FILES:
                files.append(rel)

    return sorted(set(files))


def check_components_coverage(repo_root: Path, source_files: list[str]) -> list[str]:
    """Find source files not mentioned in docs/COMPONENTS_MAP.md (path-aware)."""
    cmap = repo_root / "docs" / "COMPONENTS_MAP.md"
    if not cmap.is_file():
        return source_files

    content = cmap.read_text(encoding="utf-8", errors="replace")
    uncovered: list[str] = []
    for rel_path in source_files:
        if rel_path in content:
            continue
        p = Path(rel_path)
        parent_dir = p.parent.as_posix() + "/"
        if parent_dir != "./" and parent_dir in content and p.name in content:
            continue
        uncovered.append(rel_path)
    return uncovered


def check_index_coverage(repo_root: Path, active_docs: list[Path]) -> list[str]:
    """Find docs/*.md files not listed in docs/INDEX.md."""
    index_file = repo_root / "docs" / "INDEX.md"
    if not index_file.is_file():
        return []
    index_text = index_file.read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for doc in active_docs:
        if doc.parent != repo_root / "docs" or doc.name == "INDEX.md":
            continue
        if doc.name not in index_text:
            missing.append(doc.relative_to(repo_root).as_posix())
    return missing


def count_static_tests(repo_root: Path) -> dict[str, int]:
    """Quickly count Python and JS/JSX test cases without spawning test runners."""
    py_count = 0
    tests_dir = repo_root / "tests"
    if tests_dir.is_dir():
        for p in tests_dir.rglob("test_*.py"):
            if "__pycache__" in p.parts:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            py_count += len(PY_TEST_DEF_RE.findall(text))

    ui_count = 0
    ui_src = repo_root / "ui" / "src"
    if ui_src.is_dir():
        for p in ui_src.rglob("*.test.*"):
            text = p.read_text(encoding="utf-8", errors="replace")
            ui_count += len(JS_TEST_DEF_RE.findall(text))

    return {"pytest_defs_approx": py_count, "vitest_cases_approx": ui_count}


def find_hardcoded_test_counts(repo_root: Path, active_docs: list[Path]) -> list[dict]:
    """Locate hardcoded test count claims in active documentation."""
    hits: list[dict] = []
    for doc in active_docs:
        rel_doc = doc.relative_to(repo_root).as_posix()
        for lineno, line in enumerate(doc.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if TEST_COUNT_LINE_RE.search(line):
                hits.append({"doc": rel_doc, "line": lineno, "text": line.strip()})
    return hits


def extract_code_facts(repo_root: Path) -> dict:
    """Extract live API routes, EventBus events, router dispatchers, and UI screens."""
    routes: list[str] = []
    routers_dir = repo_root / "services" / "gateway" / "routers"
    if routers_dir.is_dir():
        for p in sorted(routers_dir.glob("*.py")):
            if p.name == "__init__.py":
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            for method, path in ROUTER_RE.findall(text):
                routes.append(f"{method.upper()} {path} ({p.name})")

    events: list[str] = []
    ws_types: list[str] = []
    gw_file = repo_root / "services" / "gateway_service.py"
    if gw_file.is_file():
        text = gw_file.read_text(encoding="utf-8", errors="replace")
        events = sorted(set(re.findall(r'\.subscribe\(\s*["\']([^"\']+)["\']', text)))
        ws_types = sorted(set(re.findall(r'hub\.broadcast\(\s*\{\s*["\']type["\']\s*:\s*["\']([^"\']+)["\']', text)))

    dispatchers = sorted(
        p.name for p in (repo_root / "services" / "router").glob("*.py") if p.name != "__init__.py"
    ) if (repo_root / "services" / "router").is_dir() else []

    ui_views: list[str] = []
    for sub in ("ui/src/components", "ui/src/motion"):
        d = repo_root / sub
        if d.is_dir():
            for p in sorted(d.rglob("*.jsx")):
                if ".test." not in p.name and p.name != "Icons.jsx":
                    ui_views.append(p.relative_to(repo_root).as_posix())

    return {
        "gateway_routes": routes,
        "event_bus_subscriptions": events,
        "ws_broadcast_types": ws_types,
        "router_dispatchers": dispatchers,
        "ui_views": ui_views,
    }


def run_audit(repo_root: Path, include_facts: bool = False) -> dict:
    """Execute all deterministic documentation checks."""
    active_docs = collect_active_docs(repo_root)
    known_prefixes = discover_known_prefixes(repo_root)
    broken_links: list[dict] = []
    local_abs_links: list[dict] = []
    missing_paths: list[dict] = []

    for doc in active_docs:
        lines = doc.read_text(encoding="utf-8", errors="replace").splitlines()
        broken, local_abs = check_markdown_links(repo_root, doc, lines)
        broken_links.extend(broken)
        local_abs_links.extend(local_abs)
        missing_paths.extend(check_backtick_paths(repo_root, doc, lines, known_prefixes))

    source_files = collect_source_files(repo_root)
    uncovered = check_components_coverage(repo_root, source_files)
    unindexed = check_index_coverage(repo_root, active_docs)
    versions = extract_versions(repo_root)
    unique_versions = {v for v in versions.values() if v is not None}

    report: dict = {
        "repo_root": str(repo_root),
        "versions": versions,
        "version_mismatch": len(unique_versions) > 1 or versions.get("README.md") != versions.get("core/version.py"),
        "checked_docs": [p.relative_to(repo_root).as_posix() for p in active_docs],
        "unindexed_docs": unindexed,
        "broken_links": broken_links,
        "local_absolute_links": local_abs_links,
        "missing_backtick_paths": missing_paths,
        "uncovered_in_components_map": uncovered,
        "static_test_counts": count_static_tests(repo_root),
        "hardcoded_test_claims": find_hardcoded_test_counts(repo_root, active_docs),
    }
    if include_facts:
        report["facts"] = extract_code_facts(repo_root)
    return report


def print_human_report(report: dict) -> None:
    """Print readable summary for an agent or developer."""
    print("Versions:")
    for src, ver in report["versions"].items():
        print(f"  - {src}: {ver or 'not found'}")
    if report["version_mismatch"]:
        print("  [!] Version mismatch detected!")

    print(f"\nActive docs checked ({len(report['checked_docs'])}):")
    for doc in report["checked_docs"]:
        print(f"  - {doc}")

    print(f"\nDocs missing from docs/INDEX.md ({len(report['unindexed_docs'])}):")
    for doc in report["unindexed_docs"]:
        print(f"  - {doc}")

    print(f"\nBroken relative markdown links ({len(report['broken_links'])}):")
    for item in report["broken_links"]:
        print(f"  - {item['doc']}:{item['line']} -> {item['target']}")

    print(f"\nMachine-specific file:// links ({len(report['local_absolute_links'])}):")
    for item in report["local_absolute_links"]:
        print(f"  - {item['doc']}:{item['line']} -> {item['target']}")

    print(f"\nMissing backtick paths ({len(report['missing_backtick_paths'])}):")
    for item in report["missing_backtick_paths"]:
        print(f"  - {item['doc']}:{item['line']} -> `{item['target']}`")

    print(
        f"\nSource files missing from docs/COMPONENTS_MAP.md "
        f"({len(report['uncovered_in_components_map'])}):"
    )
    for rel in report["uncovered_in_components_map"]:
        print(f"  - {rel}")

    counts = report["static_test_counts"]
    print(
        f"\nStatic test defs (approx): pytest={counts['pytest_defs_approx']}, "
        f"vitest={counts['vitest_cases_approx']}"
    )
    print(f"Hardcoded test count claims in docs ({len(report['hardcoded_test_claims'])}):")
    for item in report["hardcoded_test_claims"]:
        print(f"  - {item['doc']}:{item['line']} -> {item['text']}")

    if "facts" in report:
        facts = report["facts"]
        print(f"\n--- Live Code Facts ---")
        print(f"Gateway routes ({len(facts['gateway_routes'])}):")
        for r in facts["gateway_routes"]:
            print(f"  - {r}")
        print(f"EventBus subscriptions ({len(facts['event_bus_subscriptions'])}): {', '.join(facts['event_bus_subscriptions'])}")
        print(f"WS broadcast types ({len(facts['ws_broadcast_types'])}): {', '.join(facts['ws_broadcast_types'])}")
        print(f"Router dispatchers: {', '.join(facts['router_dispatchers'])}")
        print(f"UI views ({len(facts['ui_views'])}): {', '.join(facts['ui_views'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit JARVIS docs against codebase.")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--facts", action="store_true", help="Include live code facts (routes, events, UI views)")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(__file__))
    report = run_audit(repo_root, include_facts=args.facts)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

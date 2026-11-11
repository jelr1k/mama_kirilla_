#!/usr/bin/env python3
"""Deterministic documentation audit script for JARVIS (Kirieshka v2).

Checks active markdown documentation against the repository tree:
1. Broken markdown links [label](target).
2. Broken backtick file/directory paths in prose.
3. Source files missing from docs/COMPONENTS_MAP.md.
4. Basic metadata from source (core/version.py APP_VERSION) for quick comparison.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_DIRS = (
    "core",
    "services",
    "tools",
    "modules",
    "voice",
    "security",
    "presentation",
    "start",
    "config",
    "ui/src",
    "ui/src-tauri/src",
)

IGNORED_BASENAMES = {
    "__init__.py",
    "setupTests.js",
    "main.jsx",
    "index.js",
    "index.css",
    "Icons.jsx",
}

IGNORED_SUFFIXES = {".pyc", ".css"}

KNOWN_PREFIXES = (
    "core/",
    "services/",
    "tools/",
    "modules/",
    "voice/",
    "security/",
    "presentation/",
    "start/",
    "config/",
    "ui/",
    "ui_archive/",
    "tests/",
    "docs/",
    ".gemini/",
    ".agents/",
)

# Runtime-generated paths or doc placeholders that should not be flagged as missing.
RUNTIME_OR_PLACEHOLDER_PREFIXES = (
    "workspace/",
    "logs/",
    "ui/dist",
    "ui/src-tauri/target",
)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")


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


def extract_app_version(repo_root: Path) -> str | None:
    """Read APP_VERSION from core/version.py if present."""
    version_file = repo_root / "core" / "version.py"
    if not version_file.is_file():
        return None
    text = version_file.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else None


def check_markdown_links(repo_root: Path, doc_path: Path, lines: list[str]) -> list[dict]:
    """Verify local relative markdown links in a document."""
    issues: list[dict] = []
    rel_doc = doc_path.relative_to(repo_root).as_posix()

    for lineno, line in enumerate(lines, start=1):
        for match in LINK_RE.finditer(line):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith("#"):
                continue
            if raw_target.startswith(("http://", "https://", "mailto:", "file://")):
                continue

            # Strip optional title and #anchor
            target = raw_target.split()[0].split("#", 1)[0]
            if not target:
                continue

            resolved = (doc_path.parent / target).resolve()
            if not resolved.exists():
                issues.append(
                    {
                        "doc": rel_doc,
                        "line": lineno,
                        "target": raw_target,
                        "reason": "broken_link",
                    }
                )
    return issues


def is_checkable_backtick_path(token: str) -> bool:
    """Return True if backtick content looks like a concrete repo file/dir path."""
    if any(ch in token for ch in ("*", "<", ">", "{", "}", " ", "...", "|")):
        return False
    if token.startswith(RUNTIME_OR_PLACEHOLDER_PREFIXES):
        return False
    return token.startswith(KNOWN_PREFIXES)


def check_backtick_paths(repo_root: Path, doc_path: Path, lines: list[str]) -> list[dict]:
    """Verify concrete repo paths mentioned in backticks."""
    issues: list[dict] = []
    rel_doc = doc_path.relative_to(repo_root).as_posix()
    in_fence = False

    for lineno, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in BACKTICK_RE.finditer(line):
            token = match.group(1).strip()
            if not is_checkable_backtick_path(token):
                continue

            candidate = repo_root / token.rstrip("/")
            if not candidate.exists():
                issues.append(
                    {
                        "doc": rel_doc,
                        "line": lineno,
                        "target": token,
                        "reason": "missing_path",
                    }
                )
    return issues


def collect_source_files(repo_root: Path) -> list[str]:
    """List relevant source/config files across tracked project directories."""
    files: list[str] = []
    for root_rel in SOURCE_DIRS:
        root_dir = repo_root / root_rel
        if not root_dir.is_dir():
            continue
        for p in sorted(root_dir.rglob("*")):
            if not p.is_file():
                continue
            if "__pycache__" in p.parts:
                continue
            if p.suffix in IGNORED_SUFFIXES:
                continue
            if p.name in IGNORED_BASENAMES:
                continue
            if ".test." in p.name or p.name.endswith(".md"):
                continue
            files.append(p.relative_to(repo_root).as_posix())
    return files


def check_components_coverage(repo_root: Path, source_files: list[str]) -> list[str]:
    """Find source files not mentioned in docs/COMPONENTS_MAP.md."""
    cmap = repo_root / "docs" / "COMPONENTS_MAP.md"
    if not cmap.is_file():
        return source_files

    content = cmap.read_text(encoding="utf-8", errors="replace")
    uncovered: list[str] = []
    for rel_path in source_files:
        basename = Path(rel_path).name
        if rel_path not in content and basename not in content:
            uncovered.append(rel_path)
    return uncovered


def run_audit(repo_root: Path) -> dict:
    """Execute all deterministic documentation checks."""
    active_docs = collect_active_docs(repo_root)
    broken_links: list[dict] = []
    missing_paths: list[dict] = []

    for doc in active_docs:
        lines = doc.read_text(encoding="utf-8", errors="replace").splitlines()
        broken_links.extend(check_markdown_links(repo_root, doc, lines))
        missing_paths.extend(check_backtick_paths(repo_root, doc, lines))

    source_files = collect_source_files(repo_root)
    uncovered = check_components_coverage(repo_root, source_files)

    return {
        "repo_root": str(repo_root),
        "app_version": extract_app_version(repo_root),
        "checked_docs": [p.relative_to(repo_root).as_posix() for p in active_docs],
        "broken_links": broken_links,
        "missing_backtick_paths": missing_paths,
        "uncovered_in_components_map": uncovered,
    }


def print_human_report(report: dict) -> None:
    """Print readable summary for an agent or developer."""
    print(f"APP_VERSION (core/version.py): {report['app_version'] or 'not found'}")
    print(f"Active docs checked ({len(report['checked_docs'])}):")
    for doc in report["checked_docs"]:
        print(f"  - {doc}")

    print(f"\nBroken markdown links ({len(report['broken_links'])}):")
    for item in report["broken_links"]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit JARVIS docs against codebase.")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(__file__))
    report = run_audit(repo_root)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from start.check_dependencies import get_missing_dependencies, main


def test_get_missing_dependencies_all_present(tmp_path: Path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("pytest\n", encoding="utf-8")
    assert get_missing_dependencies(req_file) == []


def test_get_missing_dependencies_detects_missing(tmp_path: Path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("non_existent_package_12345>=1.0\npytest\n", encoding="utf-8")
    missing = get_missing_dependencies(req_file)
    assert "non_existent_package_12345" in missing
    assert "pytest" not in missing


def test_get_missing_dependencies_handles_comments_and_blank_lines(tmp_path: Path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("# Comment\n\n  \npytest\n", encoding="utf-8")
    assert get_missing_dependencies(req_file) == []


def test_get_missing_dependencies_handles_missing_file(tmp_path: Path):
    req_file = tmp_path / "does_not_exist.txt"
    assert get_missing_dependencies(req_file) == []


def test_main_returns_zero_when_dependencies_satisfied(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("start.check_dependencies.get_missing_dependencies", lambda _path: [])
    assert main() == 0


def test_main_returns_one_when_dependencies_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("start.check_dependencies.get_missing_dependencies", lambda _path: ["pkg_x"])
    assert main() == 1

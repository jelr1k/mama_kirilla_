from __future__ import annotations

from pathlib import Path
from start.check_dependencies import check_requirements_file, main


def test_check_requirements_all_satisfied(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("pytest\nrequests\n", encoding="utf-8")

    satisfied, missing = check_requirements_file(req_file)
    assert satisfied is True
    assert missing == []


def test_check_requirements_detects_missing(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("totally_nonexistent_jarvis_package>=1.0\n", encoding="utf-8")

    satisfied, missing = check_requirements_file(req_file)
    assert satisfied is False
    assert len(missing) == 1
    assert "totally_nonexistent_jarvis_package" in missing[0]


def test_check_requirements_ignores_non_matching_markers(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("nonexistent_on_linux; platform_system == 'Linux'\n", encoding="utf-8")

    satisfied, missing = check_requirements_file(req_file)
    assert satisfied is True
    assert missing == []


def test_check_requirements_handles_comments_and_empty_lines(tmp_path):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("# Comment\n\n  \npytest\n", encoding="utf-8")

    satisfied, missing = check_requirements_file(req_file)
    assert satisfied is True
    assert missing == []


def test_check_requirements_missing_file():
    satisfied, missing = check_requirements_file(Path("nonexistent_path/req.txt"))
    assert satisfied is True
    assert missing == []

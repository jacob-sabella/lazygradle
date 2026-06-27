"""Unit tests for scripts/set-version.py — the release version source of truth."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "set-version.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("set_version", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setver = _load_module()


@pytest.mark.parametrize(
    "version,expected",
    [
        ("1.2.0", (1, 2, 0)),
        ("1.3.0b7", (1, 3, 0)),
        ("2.0.0rc1", (2, 0, 0)),
        ("1.4", (1, 4, 0)),
        ("10.20.30", (10, 20, 30)),
    ],
)
def test_base_of(version, expected):
    assert setver.base_of(version) == expected


@pytest.mark.parametrize(
    "version,part,expected",
    [
        ("1.3.0", "patch", "1.3.1"),
        ("1.3.0", "minor", "1.4.0"),
        ("1.3.5", "minor", "1.4.0"),
        ("1.3.5", "major", "2.0.0"),
        ("1.3.0b7", "patch", "1.3.1"),
    ],
)
def test_bump(version, part, expected):
    assert setver.bump(version, part) == expected


def test_write_and_read_roundtrip(tmp_path, monkeypatch):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[build-system]\n'
        'requires = ["setuptools>=61.0"]\n\n'
        '[project]\n'
        'name = "x"\n'
        'version = "1.2.0"\n'
        'requires-python = ">=3.13"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(setver, "PYPROJECT", pyproject)

    setver.write_version("1.3.0b9")

    assert setver.read_version() == "1.3.0b9"
    # Only the [project] version line is touched; build-system is untouched.
    assert 'requires = ["setuptools>=61.0"]' in pyproject.read_text(encoding="utf-8")


def test_checked_in_version_is_parseable():
    # The version committed to the repo must always have a usable release segment.
    assert setver.base_of(setver.read_version())

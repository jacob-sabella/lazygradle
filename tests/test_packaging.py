"""Packaging gates: sdist + wheel build + twine check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _has(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has("build"), reason="`build` not installed")
def test_build_produces_sdist_and_wheel(tmp_path):
    out = tmp_path / "dist"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    artifacts = list(out.iterdir())
    assert any(a.suffix == ".gz" for a in artifacts), "missing sdist"
    assert any(a.suffix == ".whl" for a in artifacts), "missing wheel"


@pytest.mark.skipif(
    not (_has("build") and _has("twine")), reason="`build` or `twine` not installed"
)
def test_twine_check_passes(tmp_path):
    out = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "twine", "check", *(str(p) for p in out.iterdir())],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASSED" in result.stdout

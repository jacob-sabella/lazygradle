"""Shared fixtures for the lazygradle test suite.

Two fixtures matter:

- `sample_project`: absolute path to `tests/fixtures/sample-project/`, a real
  Gradle project with a real `gradlew` wrapper. Tests interact with it the
  same way an end user would — running real `./gradlew` invocations against
  real tasks (`hello`, `slow`, `failing`, `withParams`).

- `gm`: a `GradleManager` whose config dir has been redirected to a tmp
  path. Tests can persist projects, themes, recent tasks, etc. without
  touching the user's real `~/.config/lazygradle/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gradle.gradle_manager import GradleManager  # noqa: E402


SAMPLE_PROJECT_DIR = REPO_ROOT / "tests" / "fixtures" / "sample-project"


@pytest.fixture
def sample_project() -> Path:
    if not (SAMPLE_PROJECT_DIR / "gradlew").exists():
        pytest.fail(f"fixture project missing gradlew: {SAMPLE_PROJECT_DIR}")
    return SAMPLE_PROJECT_DIR


@pytest.fixture
def gm(tmp_path, monkeypatch):
    """GradleManager with config redirected to a tmp dir."""
    cfg_dir = tmp_path / "lazygradle"
    monkeypatch.setattr(GradleManager, "CONFIG_DIR", cfg_dir, raising=True)
    monkeypatch.setattr(
        GradleManager, "CONFIG_FILE", cfg_dir / "gradle_cache.json", raising=True
    )
    return GradleManager()


@pytest.fixture
def gm_with_sample(gm, sample_project):
    """GradleManager pre-loaded with the fixture project + its tasks cached."""
    gm.add_project(str(sample_project))
    gm.update_project_tasks(str(sample_project))
    return gm

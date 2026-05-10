"""GradleManager: config persistence, project lifecycle, recent tasks, theme."""

from __future__ import annotations

import json

from gradle.gradle_manager import GradleManager


def test_add_project_persists_and_auto_selects(gm, sample_project, tmp_path):
    gm.add_project(str(sample_project))
    assert gm.get_selected_project() == str(sample_project)

    raw = json.loads(GradleManager.CONFIG_FILE.read_text())
    assert str(sample_project) in raw["projects"]
    assert raw["currently_selected"] == str(sample_project)


def test_select_project_switches_active(gm, sample_project, tmp_path):
    other = tmp_path / "other-proj"
    other.mkdir()
    gm.add_project(str(sample_project))
    gm.add_project(str(other))
    gm.select_project(str(other))
    assert gm.get_selected_project() == str(other)


def test_delete_project_promotes_remaining(gm, sample_project, tmp_path):
    other = tmp_path / "other-proj"
    other.mkdir()
    gm.add_project(str(sample_project))
    gm.add_project(str(other))
    gm.select_project(str(sample_project))

    assert gm.delete_project(str(sample_project)) is True
    assert gm.get_selected_project() == str(other)


def test_delete_last_project_clears_selection(gm, sample_project):
    gm.add_project(str(sample_project))
    gm.delete_project(str(sample_project))
    assert gm.get_selected_project() is None


def test_theme_persists_across_instances(gm, sample_project, monkeypatch):
    gm.add_project(str(sample_project))
    gm.set_theme("nord")

    fresh = GradleManager()
    assert fresh.get_theme() == "nord"


def test_recent_tasks_records_with_parameters(gm, sample_project):
    gm.add_project(str(sample_project))
    gm._record_task_execution("build", ["--info", "--stacktrace"])
    gm._record_task_execution("test", [])

    recent = gm.get_recent_tasks()
    assert recent[0]["task_name"] == "test"
    assert recent[1]["task_name"] == "build"
    assert recent[1]["parameters"] == "--info --stacktrace"


def test_output_settings_normalize_bad_input(gm):
    settings = gm.update_output_settings(default_zoom="not-an-int", clipboard_enabled="off")
    assert settings["default_zoom"] == 0
    assert settings["clipboard_enabled"] is False

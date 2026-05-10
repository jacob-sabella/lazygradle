"""TaskTracker state machine — fast, no subprocess, no Textual."""

from __future__ import annotations

from ui.task_tracker import TaskStatus, TaskTracker


def test_create_task_assigns_unique_ids():
    tracker = TaskTracker()
    a = tracker.create_task("build")
    b = tracker.create_task("test")
    assert a.task_id != b.task_id
    assert tracker.get_task(a.task_id) is a
    assert tracker.tasks[0] is b  # newest first


def test_history_capped_to_max():
    tracker = TaskTracker(max_history=3)
    for i in range(5):
        tracker.create_task(f"t{i}")
    assert len(tracker.tasks) == 3
    assert tracker.tasks[0].task_name == "t4"


def test_running_completed_split():
    tracker = TaskTracker()
    a = tracker.create_task("a")
    b = tracker.create_task("b")
    tracker.mark_completed(a.task_id)
    assert tracker.get_running_tasks() == [b]
    assert tracker.get_completed_tasks() == [a]


def test_mark_failed_records_error_line():
    tracker = TaskTracker()
    t = tracker.create_task("boom")
    tracker.mark_failed(t.task_id, "kaboom")
    assert t.status == TaskStatus.FAILED
    assert any("kaboom" in line for line in t.output_lines)


def test_clear_history_preserves_running():
    tracker = TaskTracker()
    a = tracker.create_task("a")
    b = tracker.create_task("b")
    tracker.mark_completed(a.task_id)
    tracker.clear_history()
    assert tracker.tasks == [b]


def test_update_callback_fires_on_state_changes():
    tracker = TaskTracker()
    calls = []
    tracker.set_update_callback(lambda: calls.append(1))
    t = tracker.create_task("x")
    tracker.append_output(t.task_id, "hi")
    tracker.mark_completed(t.task_id)
    assert len(calls) == 3


def test_display_name_includes_params_and_label():
    tracker = TaskTracker()
    t = tracker.create_task("build", parameters=["--info"], config_label="ci")
    assert t.get_display_name() == "build --info (ci)"

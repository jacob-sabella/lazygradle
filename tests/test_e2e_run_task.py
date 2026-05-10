"""End-to-end happy + sad paths: real ./gradlew driven through the TUI.

Configures the app with the fixture project, selects a task, fires the
same `action_run_task` the user's `r` keypress fires, and verifies the
output the user would see in the Task Manager tab.
"""

from __future__ import annotations

import asyncio

import pytest

from ui.lazy_gradle_app import LazyGradleApp
from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from ui.task_tracker import TaskStatus


async def _select_and_run(app, task_name: str):
    viewer = app.query_one(GradleProjectTaskViewer)
    viewer.selected_task = next(t for t in viewer.tasks if t.name == task_name)
    viewer.update_task_description(viewer.selected_task)
    # Call run_task directly: action_run_task re-derives selected_task from
    # the option list's highlighted index when the list has focus, which
    # would override our test selection.
    await viewer.run_task()
    if viewer.running_task is not None:
        await viewer.running_task
    return viewer


@pytest.mark.asyncio
async def test_happy_path_run_hello_streams_output(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        viewer = await _select_and_run(app, "hello")
        # Settle the post-completion callbacks scheduled via call_soon_threadsafe.
        for _ in range(5):
            await pilot.pause()

        tracked = viewer.task_tracker.tasks[0]
        assert tracked.status == TaskStatus.COMPLETED
        assert any("Hello from sample" in line for line in tracked.output_lines)


@pytest.mark.asyncio
async def test_failing_task_is_marked_failed(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        viewer = await _select_and_run(app, "failing")
        for _ in range(5):
            await pilot.pause()

        tracked = viewer.task_tracker.tasks[0]
        assert tracked.status == TaskStatus.FAILED

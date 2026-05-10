"""TUI smoke tests via Textual's headless pilot.

Verifies the major widgets mount without exception, tab keys switch
content, and the app survives a full boot/shutdown cycle. No real
gradle exec — uses a pre-cached project so task discovery doesn't run
during the test.
"""

from __future__ import annotations

import pytest

from ui.lazy_gradle_app import LazyGradleApp
from ui.widget import LazyGradleWidget
from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from ui.task_manager_widget import TaskManagerWidget


@pytest.mark.asyncio
async def test_app_boots_and_renders_setup_tab(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        widget = app.query_one(LazyGradleWidget)
        assert widget.current_tab_id == "current-setup"
        # Task viewer mounted with cached fixture tasks.
        viewer = app.query_one(GradleProjectTaskViewer)
        names = {t.name for t in viewer.tasks}
        assert {"hello", "slow", "failing", "withParams"}.issubset(names)


@pytest.mark.asyncio
async def test_tab_keys_switch_content(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()

        await pilot.press("2")
        await pilot.pause()
        widget = app.query_one(LazyGradleWidget)
        assert widget.current_tab_id == "task-manager-tab"
        app.query_one(TaskManagerWidget)  # must be mounted

        await pilot.press("1")
        await pilot.pause()
        assert widget.current_tab_id == "current-setup"
        app.query_one(GradleProjectTaskViewer)


@pytest.mark.asyncio
async def test_theme_persists_to_config(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        app.theme = "nord"
        await pilot.pause()

    # New app instance reads the persisted theme on mount.
    app2 = LazyGradleApp(gm_with_sample)
    async with app2.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        assert app2.theme == "nord"

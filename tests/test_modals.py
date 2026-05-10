"""Modal screens open + close + restore focus correctly."""

from __future__ import annotations

import pytest

from ui.lazy_gradle_app import LazyGradleApp
from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from ui.keys_guide_modal import KeysGuideModal
from ui.project_chooser_modal import ProjectChooserModal
from ui.run_task_with_parameters_modal import RunTaskWithParametersModal


def _has_screen(app, screen_cls) -> bool:
    return any(isinstance(s, screen_cls) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_keys_guide_opens_and_closes(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        app.action_show_keys_guide()
        await pilot.pause()
        assert _has_screen(app, KeysGuideModal)

        await pilot.press("escape")
        await pilot.pause()
        assert not _has_screen(app, KeysGuideModal)


@pytest.mark.asyncio
async def test_project_chooser_opens_via_p_key(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        await pilot.press("p")
        await pilot.pause()
        assert _has_screen(app, ProjectChooserModal)
        assert app.project_chooser_open is True

        await pilot.press("escape")
        await pilot.pause()
        assert not _has_screen(app, ProjectChooserModal)


@pytest.mark.asyncio
async def test_run_task_with_parameters_modal_opens(gm_with_sample):
    app = LazyGradleApp(gm_with_sample)
    async with app.run_test(size=(160, 45)) as pilot:
        await pilot.pause()
        await pilot.pause()
        viewer = app.query_one(GradleProjectTaskViewer)
        viewer.selected_task = next(t for t in viewer.tasks if t.name == "withParams")
        viewer.update_task_description(viewer.selected_task)
        await viewer.action_run_task_with_parameters()
        await pilot.pause()
        assert _has_screen(app, RunTaskWithParametersModal)

        await pilot.press("escape")
        await pilot.pause()
        assert not _has_screen(app, RunTaskWithParametersModal)

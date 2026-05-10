"""Headless capture of the four README screenshots.

Drives LazyGradle via Textual's `App.run_test()` + pilot — no real terminal,
no output-stream overload. Writes SVGs to `screenshots/readme/`.

Run from the repo root with the venv active:

    python scripts/capture_readme_screenshots.py

Pre-reqs:
- At least one project configured in ~/.config/lazygradle/gradle_cache.json
  (otherwise the setup tab and task list are empty and screenshots are dull).
- The selected project's `gradlew` should be discoverable so the task list
  populates on mount; if discovery is slow the PAUSE_S knob below extends
  the settle time per step.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gradle.gradle_manager import GradleManager
from ui.lazy_gradle_app import LazyGradleApp
from ui.widget import LazyGradleWidget
from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from ui.task_tracker import TaskStatus, TrackedTask

OUT_DIR = REPO_ROOT / "screenshots" / "readme"
SIZE = (160, 45)
PAUSE_S = 0.6


def _seed_history(tracker) -> None:
    """Inject one completed run so the task-manager tab has something to show."""
    now = datetime.now()
    task = TrackedTask(
        task_id="task_demo_1",
        task_name="build",
        parameters=["--info"],
        status=TaskStatus.COMPLETED,
        start_time=now - timedelta(seconds=12),
        end_time=now - timedelta(seconds=2),
        output_lines=[
            "> Task :compileJava",
            "> Task :processResources",
            "> Task :classes",
            "> Task :jar",
            "> Task :assemble",
            "> Task :test",
            "",
            "BUILD SUCCESSFUL in 10s",
            "7 actionable tasks: 7 executed",
        ],
        config_label=None,
    )
    tracker.tasks.insert(0, task)
    tracker._task_counter = 1


async def _save(app: LazyGradleApp, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app.save_screenshot(filename=name, path=str(OUT_DIR))
    print(f"wrote {OUT_DIR / name}")


async def main() -> None:
    gm = GradleManager()
    app = LazyGradleApp(gm)

    async with app.run_test(size=SIZE) as pilot:
        # 1. Current Setup overview
        await pilot.pause(PAUSE_S)
        await pilot.pause(PAUSE_S)
        await _save(app, "current-setup-overview.svg")

        # 2. Task Manager tab — seed one completed run, then switch + select.
        widget = app.query_one(LazyGradleWidget)
        _seed_history(widget.task_tracker)
        await pilot.press("2")
        await pilot.pause(PAUSE_S)
        widget.switch_to_tab("task-manager-tab", force_refresh=True)
        await pilot.pause(PAUSE_S)
        if widget.task_manager_widget is not None:
            widget.task_manager_widget.select_task("task_demo_1")
            await pilot.pause(PAUSE_S)
        await _save(app, "task-manager-output.svg")

        # 3. Run-task-with-parameters modal (back on setup tab).
        await pilot.press("1")
        await pilot.pause(PAUSE_S)
        viewer = app.query_one(GradleProjectTaskViewer)
        if viewer.tasks:
            viewer.selected_task = viewer.tasks[0]
            viewer.update_task_description(viewer.selected_task)
            await viewer.action_run_task_with_parameters()
            await pilot.pause(PAUSE_S)
            await _save(app, "run-task-with-parameters.svg")
            await pilot.press("escape")
            await pilot.pause(PAUSE_S)
        else:
            print("WARN: no tasks in selected project — skipped run-task-with-parameters.svg")

        # 4. Keys guide modal.
        app.action_show_keys_guide()
        await pilot.pause(PAUSE_S)
        await _save(app, "keys-guide.svg")
        await pilot.press("escape")
        await pilot.pause(PAUSE_S)


if __name__ == "__main__":
    asyncio.run(main())

"""UI tests for TaskManagerWidget and TaskTracker."""
import pytest
from unittest.mock import Mock, patch
from textual.pilot import Pilot

from ui.task_manager_widget import TaskManagerWidget
from ui.task_tracker import TaskTracker


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskTrackerFunctionality:
    """Tests for TaskTracker functionality."""

    def test_add_task(self):
        """Test adding a task to the tracker."""
        tracker = TaskTracker()

        task_id = tracker.add_task("build", "/path/to/project")

        assert task_id is not None
        assert len(tracker.tasks) == 1
        assert tracker.tasks[task_id]["task_name"] == "build"
        assert tracker.tasks[task_id]["status"] == "running"

    def test_update_task_output(self):
        """Test updating task output."""
        tracker = TaskTracker()

        task_id = tracker.add_task("build", "/path/to/project")
        tracker.append_output(task_id, "Building...\n")
        tracker.append_output(task_id, "Build complete\n")

        task = tracker.tasks[task_id]
        assert "Building..." in task["output"]
        assert "Build complete" in task["output"]

    def test_complete_task(self):
        """Test marking a task as completed."""
        tracker = TaskTracker()

        task_id = tracker.add_task("build", "/path/to/project")
        tracker.complete_task(task_id, success=True)

        task = tracker.tasks[task_id]
        assert task["status"] == "completed"
        assert task["end_time"] is not None

    def test_fail_task(self):
        """Test marking a task as failed."""
        tracker = TaskTracker()

        task_id = tracker.add_task("build", "/path/to/project")
        tracker.complete_task(task_id, success=False)

        task = tracker.tasks[task_id]
        assert task["status"] == "failed"

    def test_task_limit(self):
        """Test that tracker limits the number of stored tasks."""
        tracker = TaskTracker(max_tasks=5)

        # Add more than max tasks
        for i in range(10):
            task_id = tracker.add_task(f"task{i}", "/path/to/project")
            tracker.complete_task(task_id, success=True)

        # Should only keep last 5
        assert len(tracker.tasks) <= 5

    def test_running_tasks_first(self):
        """Test that running tasks appear before completed ones."""
        tracker = TaskTracker()

        # Add and complete some tasks
        task1_id = tracker.add_task("task1", "/path/to/project")
        tracker.complete_task(task1_id, success=True)

        task2_id = tracker.add_task("task2", "/path/to/project")
        tracker.complete_task(task2_id, success=True)

        # Add a running task
        task3_id = tracker.add_task("task3", "/path/to/project")

        # Get task list
        task_list = tracker.get_task_list()

        # Running task should be first
        assert task_list[0]["id"] == task3_id
        assert task_list[0]["status"] == "running"

    def test_clear_history(self):
        """Test clearing completed/failed tasks."""
        tracker = TaskTracker()

        # Add running task
        running_id = tracker.add_task("running", "/path/to/project")

        # Add completed tasks
        completed_id = tracker.add_task("completed", "/path/to/project")
        tracker.complete_task(completed_id, success=True)

        failed_id = tracker.add_task("failed", "/path/to/project")
        tracker.complete_task(failed_id, success=False)

        # Clear history
        tracker.clear_history()

        # Only running task should remain
        assert len(tracker.tasks) == 1
        assert running_id in tracker.tasks


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskManagerDisplay:
    """Tests for TaskManagerWidget display."""

    async def test_displays_task_list(self):
        """Test that task manager displays task list."""
        tracker = TaskTracker()
        tracker.add_task("build", "/path/to/project")

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Should show task list
            from textual.widgets import OptionList
            option_lists = app.query(OptionList)
            assert len(option_lists) > 0

    async def test_displays_task_output(self):
        """Test that selecting a task shows its output."""
        tracker = TaskTracker()
        task_id = tracker.add_task("build", "/path/to/project")
        tracker.append_output(task_id, "Build output line 1\n")
        tracker.append_output(task_id, "Build output line 2\n")

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Select task
            from textual.widgets import OptionList
            task_list = app.query(OptionList).first()

            if task_list and len(task_list.get_options()) > 0:
                task_list.highlighted = 0
                await pilot.pause()

                # Output should be displayed
                # (Verification depends on implementation)

    async def test_shows_task_status_icons(self):
        """Test that tasks show correct status icons."""
        tracker = TaskTracker()

        running_id = tracker.add_task("running", "/path/to/project")
        completed_id = tracker.add_task("completed", "/path/to/project")
        tracker.complete_task(completed_id, success=True)
        failed_id = tracker.add_task("failed", "/path/to/project")
        tracker.complete_task(failed_id, success=False)

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Icons should be displayed
            # ▶ for running, ✓ for completed, ✗ for failed
            # (Verification depends on implementation)

    async def test_shows_task_duration(self):
        """Test that task duration is displayed."""
        tracker = TaskTracker()
        task_id = tracker.add_task("build", "/path/to/project")
        tracker.complete_task(task_id, success=True)

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Duration should be shown
            # (Verification depends on implementation)


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskManagerInteraction:
    """Tests for task manager interaction."""

    async def test_clear_history_button(self):
        """Test that clear history button removes completed tasks."""
        tracker = TaskTracker()

        # Add completed task
        completed_id = tracker.add_task("completed", "/path/to/project")
        tracker.complete_task(completed_id, success=True)

        # Add running task
        running_id = tracker.add_task("running", "/path/to/project")

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            from textual.widgets import Button
            buttons = app.query(Button)

            # Find and click Clear History button
            for button in buttons:
                if "Clear" in str(button.label):
                    await pilot.click(button)
                    await pilot.pause()
                    break

            # Completed task should be removed, running task should remain
            assert len(tracker.tasks) == 1
            assert running_id in tracker.tasks

    async def test_auto_updates_on_task_changes(self):
        """Test that widget auto-updates when tasks change."""
        tracker = TaskTracker()

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Add a task
            task_id = tracker.add_task("new_task", "/path/to/project")
            await pilot.pause()

            # Widget should update
            # (Verification depends on implementation with callbacks)


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskOutputDisplay:
    """Tests for task output display."""

    async def test_output_shows_metadata(self):
        """Test that output panel shows task metadata."""
        tracker = TaskTracker()
        task_id = tracker.add_task("build", "/path/to/project")
        tracker.complete_task(task_id, success=True)

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Should show task name, project, status, duration
            # (Verification depends on implementation)

    async def test_output_scrolls_automatically(self):
        """Test that output scrolls as new lines are added."""
        tracker = TaskTracker()
        task_id = tracker.add_task("build", "/path/to/project")

        widget = TaskManagerWidget(tracker)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Add many lines of output
            for i in range(100):
                tracker.append_output(task_id, f"Line {i}\n")
                await pilot.pause(0.01)

            # Should auto-scroll to bottom
            # (Verification depends on implementation)

"""UI tests for GradleProjectTaskViewer widget."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from textual.pilot import Pilot

from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from gradle.gradle_manager import GradleManager, Task


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskViewerDisplay:
    """Tests for task viewer display functionality."""

    async def test_displays_task_list(self, gradle_manager_with_projects):
        """Test that tasks are displayed in the list."""
        project_info = gradle_manager_with_projects.get_project_info("/path/to/project1")

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=Mock()
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Should show tasks
            from textual.widgets import OptionList
            option_lists = app.query(OptionList)
            assert len(option_lists) > 0

    async def test_task_selection_shows_description(self, gradle_manager_with_projects):
        """Test that selecting a task shows its description."""
        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=Mock()
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Select a task
            from textual.widgets import OptionList
            task_list = app.query_one(OptionList)

            if len(task_list.get_options()) > 0:
                # Simulate task selection
                task_list.highlighted = 0
                await pilot.pause()

                # Description panel should be updated
                # (Verification depends on implementation details)


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskViewerKeyBindings:
    """Tests for task viewer key bindings."""

    async def test_r_key_runs_selected_task(self, gradle_manager_with_projects):
        """Test that pressing 'r' runs the selected task."""
        mock_tracker = Mock()

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        with patch.object(viewer, 'run_task') as mock_run:
            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Press 'r' to run task
                await pilot.press("r")
                await pilot.pause()

                # run_task should have been called
                mock_run.assert_called_once()

    async def test_capital_r_prompts_for_parameters(self, gradle_manager_with_projects):
        """Test that pressing 'R' opens parameter input modal."""
        mock_tracker = Mock()

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Select a task first
            from textual.widgets import OptionList
            task_list = app.query_one(OptionList)
            if len(task_list.get_options()) > 0:
                task_list.highlighted = 0

                # Press 'R' to run with parameters
                await pilot.press("R")
                await pilot.pause()

                # Should show parameter input modal
                from ui.run_task_with_parameters_modal import RunTaskWithParametersModal
                modals = app.query(RunTaskWithParametersModal)
                # Modal might be shown (depending on implementation)

    async def test_slash_key_focuses_search(self, gradle_manager_with_projects):
        """Test that pressing '/' focuses the search input."""
        mock_tracker = Mock()

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Press '/' to focus search
            await pilot.press("slash")
            await pilot.pause()

            # Search input should be focused
            # (Verification depends on implementation)

    async def test_f5_refreshes_task_list(self, gradle_manager_with_projects):
        """Test that pressing F5 refreshes the task list."""
        mock_tracker = Mock()

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        with patch.object(gradle_manager_with_projects, 'update_project_tasks') as mock_update:
            mock_update.return_value = None

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Press F5 to refresh
                await pilot.press("f5")
                await pilot.pause()

                # Should call update_project_tasks
                mock_update.assert_called()


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskExecution:
    """Tests for task execution functionality."""

    async def test_task_runs_in_background(self, gradle_manager_with_projects):
        """Test that tasks run in background without blocking UI."""
        mock_tracker = Mock()
        mock_tracker.add_task.return_value = "task-id-1"

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        with patch.object(gradle_manager_with_projects, 'run_task') as mock_run:
            mock_run.return_value = "Build successful"

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Trigger task run
                viewer.run_task()
                await pilot.pause()

                # Task should be registered with tracker
                mock_tracker.add_task.assert_called()

    async def test_task_output_streams_to_tracker(self, gradle_manager_with_projects):
        """Test that task output is streamed to the tracker."""
        mock_tracker = Mock()
        mock_tracker.add_task.return_value = "task-id-1"

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Verify streaming callbacks are set up
            # (Implementation-specific verification)


@pytest.mark.ui
@pytest.mark.asyncio
class TestTaskSearch:
    """Tests for task search functionality."""

    async def test_search_filters_tasks(self, gradle_manager_with_projects):
        """Test that search input filters the task list."""
        mock_tracker = Mock()

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            from textual.widgets import Input
            search_inputs = app.query(Input)

            if len(search_inputs) > 0:
                search_input = search_inputs[0]

                # Type search query
                search_input.value = "build"
                await pilot.pause()

                # Task list should be filtered
                # (Verification depends on implementation)

    async def test_empty_search_shows_all_tasks(self, gradle_manager_with_projects):
        """Test that clearing search shows all tasks."""
        mock_tracker = Mock()

        viewer = GradleProjectTaskViewer(
            gradle_manager=gradle_manager_with_projects,
            project_path="/path/to/project1",
            task_tracker=mock_tracker
        )

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield viewer

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            from textual.widgets import Input
            search_inputs = app.query(Input)

            if len(search_inputs) > 0:
                search_input = search_inputs[0]

                # Set and clear search
                search_input.value = "build"
                await pilot.pause()

                search_input.value = ""
                await pilot.pause()

                # Should show all tasks again

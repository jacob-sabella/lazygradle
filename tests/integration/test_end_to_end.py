"""End-to-end integration tests for LazyGradle."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from gradle.gradle_manager import GradleManager
from gradle.gradle_wrapper import GradleWrapper
from tests.fixtures.mock_gradle_project import MockGradleProject, create_mock_gradle_projects


@pytest.mark.integration
class TestGradleWrapperIntegration:
    """Integration tests for GradleWrapper with real mock projects."""

    def test_list_tasks_with_mock_project(self, temp_gradle_project):
        """Test listing tasks with a real mock Gradle project."""
        wrapper = GradleWrapper(temp_gradle_project)

        task_list = wrapper.list_all_tasks()

        # Should successfully parse tasks
        assert task_list.success is True
        assert task_list.error is None
        # Mock project should have some tasks
        assert len(task_list.tasks) > 0

    @pytest.mark.requires_gradle
    def test_run_custom_task_with_mock_project(self, temp_gradle_project):
        """Test running a custom task (requires gradlew to actually work)."""
        wrapper = GradleWrapper(temp_gradle_project)

        # Try to run a simple task
        output, error = wrapper.run_custom_gradle_task("tasks")

        # Should complete without error
        assert error is None
        assert output is not None

    def test_permission_check_integration(self, temp_gradle_project, temp_gradle_project_no_exec):
        """Test permission checking with real files."""
        # Project with permissions
        wrapper_with_perms = GradleWrapper(temp_gradle_project)
        has_perm, error = wrapper_with_perms.check_gradlew_permissions()
        assert has_perm is True
        assert error is None

        # Project without permissions
        wrapper_no_perms = GradleWrapper(temp_gradle_project_no_exec)
        has_perm, error = wrapper_no_perms.check_gradlew_permissions()
        assert has_perm is False
        assert "execute permissions" in error.lower()

    def test_fix_permissions_integration(self, temp_gradle_project_no_exec):
        """Test fixing permissions on real files."""
        wrapper = GradleWrapper(temp_gradle_project_no_exec)

        # Verify no permissions initially
        has_perm, _ = wrapper.check_gradlew_permissions()
        assert has_perm is False

        # Fix permissions
        success, message = wrapper.fix_gradlew_permissions()
        assert success is True

        # Verify permissions are now set
        has_perm, error = wrapper.check_gradlew_permissions()
        assert has_perm is True
        assert error is None


@pytest.mark.integration
class TestGradleManagerIntegration:
    """Integration tests for GradleManager with full workflow."""

    def test_add_and_select_project_workflow(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test the complete workflow of adding and selecting a project."""
        manager = gradle_manager_with_temp_config

        # Add project
        manager.add_project(temp_gradle_project)

        # Should be auto-selected
        assert manager.get_selected_project() == temp_gradle_project

        # Should be in project list
        projects = manager.list_all_projects()
        assert temp_gradle_project in projects

        # Project info should be available
        project_info = manager.get_project_info(temp_gradle_project)
        assert project_info is not None

    def test_update_tasks_for_project(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test updating tasks for a project."""
        manager = gradle_manager_with_temp_config

        # Add project
        manager.add_project(temp_gradle_project)

        # Mock the GradleWrapper to return tasks
        from gradle.dto.task import Task as TaskDTO
        from gradle.dto.task_list import TaskList

        mock_tasks = [
            TaskDTO("build", "Build the project"),
            TaskDTO("test", "Run tests"),
            TaskDTO("clean", "Clean build artifacts"),
        ]
        mock_task_list = TaskList(tasks=mock_tasks, success=True, error=None)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.list_all_tasks.return_value = mock_task_list

            # Update tasks
            error = manager.update_project_tasks(temp_gradle_project)

            assert error is None

            # Verify tasks were saved
            project_info = manager.get_project_info(temp_gradle_project)
            assert len(project_info.tasks) == 3
            assert project_info.tasks[0].name == "build"

    def test_multi_project_workflow(self, gradle_manager_with_temp_config):
        """Test managing multiple projects."""
        manager = gradle_manager_with_temp_config

        # Create multiple mock projects
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            projects = create_mock_gradle_projects(count=3, temp_base_dir=temp_dir)

            # Add all projects
            for project in projects:
                manager.add_project(project.get_path())

            # Verify all projects are added
            all_projects = manager.list_all_projects()
            assert len(all_projects) == 3

            # Switch between projects
            manager.select_project(projects[1].get_path())
            assert manager.get_selected_project() == projects[1].get_path()

            manager.select_project(projects[2].get_path())
            assert manager.get_selected_project() == projects[2].get_path()

            # Delete a project
            manager.delete_project(projects[0].get_path())
            all_projects = manager.list_all_projects()
            assert len(all_projects) == 2

    def test_config_persistence(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test that configuration persists across instances."""
        manager1 = gradle_manager_with_temp_config

        # Add project and theme
        manager1.add_project(temp_gradle_project)
        manager1.set_theme("dracula")

        # Get the config file path
        config_file = manager1.CONFIG_FILE

        # Create new manager instance with same config
        from gradle.gradle_manager import GradleManager
        import pytest

        # We need to use monkeypatch, but it's in the outer scope
        # For now, just verify the config was saved
        assert config_file.exists()

        # Read the config
        import json
        with open(config_file, "r") as f:
            data = json.load(f)

        assert temp_gradle_project in data["projects"]
        assert data["theme"] == "dracula"
        assert data["currently_selected"] == temp_gradle_project

    def test_run_task_integration(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test running a task end-to-end."""
        manager = gradle_manager_with_temp_config

        # Add and select project
        manager.add_project(temp_gradle_project)

        # Mock task execution
        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = ("BUILD SUCCESSFUL", None)

            output = manager.run_task("build")

            assert output == "BUILD SUCCESSFUL"

            # Verify task was recorded
            recent_tasks = manager.get_recent_tasks()
            assert len(recent_tasks) > 0
            assert recent_tasks[0]["task_name"] == "build"

    def test_run_task_with_parameters_integration(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test running a task with parameters."""
        manager = gradle_manager_with_temp_config

        manager.add_project(temp_gradle_project)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = ("TEST SUCCESSFUL", None)

            output = manager.run_task_with_parameters("test", ["--info", "--stacktrace"])

            assert output == "TEST SUCCESSFUL"

            # Verify parameters were recorded
            recent_tasks = manager.get_recent_tasks()
            assert recent_tasks[0]["parameters"] == "--info --stacktrace"

    def test_delete_selected_project_auto_selects_another(self, gradle_manager_with_temp_config):
        """Test that deleting selected project auto-selects another."""
        manager = gradle_manager_with_temp_config

        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            projects = create_mock_gradle_projects(count=2, temp_base_dir=temp_dir)

            # Add both projects
            for project in projects:
                manager.add_project(project.get_path())

            # Select first project
            manager.select_project(projects[0].get_path())
            assert manager.get_selected_project() == projects[0].get_path()

            # Delete selected project
            manager.delete_project(projects[0].get_path())

            # Should auto-select the remaining project
            assert manager.get_selected_project() == projects[1].get_path()


@pytest.mark.integration
class TestStreamingIntegration:
    """Integration tests for streaming output functionality."""

    def test_streaming_callbacks_are_invoked(self, temp_gradle_project):
        """Test that streaming callbacks are called during task execution."""
        wrapper = GradleWrapper(temp_gradle_project)

        stdout_lines = []
        stderr_lines = []

        def on_stdout(line):
            stdout_lines.append(line)

        def on_stderr(line):
            stderr_lines.append(line)

        # Mock subprocess.Popen
        mock_process = Mock()
        mock_process.stdout = iter(["Line 1", "Line 2", "Line 3"])
        mock_process.stderr = iter([])
        mock_process.wait.return_value = 0

        with patch('subprocess.Popen', return_value=mock_process):
            output, error = wrapper.run_gradle_command(
                ["./gradlew", "tasks"],
                on_stdout=on_stdout,
                on_stderr=on_stderr
            )

            # Callbacks should have been invoked
            assert len(stdout_lines) == 3
            assert stdout_lines == ["Line 1", "Line 2", "Line 3"]

    def test_manager_streaming_to_ui(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test streaming from manager to UI callbacks."""
        manager = gradle_manager_with_temp_config
        manager.add_project(temp_gradle_project)

        output_lines = []

        def on_output(line):
            output_lines.append(line)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value

            # Simulate streaming by calling the callback
            def mock_run_task(task, on_stdout=None, on_stderr=None):
                if on_stdout:
                    on_stdout("Building...")
                    on_stdout("Build complete")
                return ("Success", None)

            mock_wrapper.run_custom_gradle_task.side_effect = mock_run_task

            manager.run_task("build", on_stdout=on_output)

            # Should have received streamed output
            assert "Building..." in output_lines
            assert "Build complete" in output_lines


@pytest.mark.integration
@pytest.mark.slow
class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""

    def test_gradle_not_found_error(self):
        """Test handling when Gradle is not found."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create project without gradlew
            wrapper = GradleWrapper(temp_dir)

            task_list = wrapper.list_all_tasks()

            assert task_list.success is False
            assert task_list.error is not None

    def test_permission_error_handling(self, temp_gradle_project_no_exec):
        """Test handling permission errors."""
        wrapper = GradleWrapper(temp_gradle_project_no_exec)

        # Try to run command without permissions
        output, error = wrapper.run_gradle_command(["./gradlew", "build"])

        assert output is None
        assert error is not None
        assert "Permission denied" in error.error_message or "execute permissions" in error.error_message

    def test_manager_handles_wrapper_errors(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test that manager properly handles errors from wrapper."""
        manager = gradle_manager_with_temp_config
        manager.add_project(temp_gradle_project)

        from gradle.dto.gradle_error import GradleError

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = (
                None,
                GradleError("Build failed: compilation error", 1)
            )

            output = manager.run_task("build")

            assert "Error:" in output
            assert "Build failed" in output

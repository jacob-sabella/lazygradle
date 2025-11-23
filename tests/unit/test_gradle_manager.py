"""Unit tests for GradleManager class."""
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from gradle.gradle_manager import GradleManager, Task, Project, Config
from gradle.dto.task_list import TaskList
from gradle.dto.task_metadata import TaskMetadata
from gradle.dto.gradle_error import GradleError
from gradle.dto.task import Task as TaskDTO


@pytest.mark.unit
class TestGradleManagerInit:
    """Tests for GradleManager initialization."""

    def test_initialization_creates_config_dir(self, temp_config_dir, monkeypatch):
        """Test that initialization creates config directory."""
        config_dir = temp_config_dir / "new_config"
        config_file = config_dir / "gradle_cache.json"

        monkeypatch.setattr(GradleManager, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(GradleManager, "CONFIG_FILE", config_file)

        manager = GradleManager()

        assert config_dir.exists()
        assert manager.config is not None

    def test_initialization_loads_existing_config(self, gradle_manager_with_projects):
        """Test that initialization loads existing config."""
        manager = gradle_manager_with_projects

        assert len(manager.config.projects) == 2
        assert manager.config.currently_selected == "/path/to/project1"
        assert manager.config.theme == "nord"

    def test_initialization_empty_config(self, gradle_manager_with_temp_config):
        """Test initialization with no existing config."""
        manager = gradle_manager_with_temp_config

        assert len(manager.config.projects) == 0
        assert manager.config.currently_selected is None
        assert manager.config.theme is None


@pytest.mark.unit
class TestConfigPersistence:
    """Tests for configuration saving and loading."""

    def test_save_config(self, gradle_manager_with_temp_config):
        """Test saving configuration to file."""
        manager = gradle_manager_with_temp_config

        # Add a project
        test_project = Project()
        test_project.tasks = [Task("build", "Build the project")]
        manager.config.projects["/test/project"] = test_project
        manager.config.currently_selected = "/test/project"
        manager.config.theme = "dracula"

        manager._save_config()

        # Verify file was created
        assert manager.CONFIG_FILE.exists()

        # Load and verify contents
        with open(manager.CONFIG_FILE, "r") as f:
            data = json.load(f)

        assert "/test/project" in data["projects"]
        assert data["currently_selected"] == "/test/project"
        assert data["theme"] == "dracula"
        assert len(data["projects"]["/test/project"]["tasks"]) == 1

    def test_load_config(self, gradle_manager_with_projects):
        """Test loading configuration from file."""
        manager = gradle_manager_with_projects

        assert "/path/to/project1" in manager.config.projects
        assert len(manager.config.projects["/path/to/project1"].tasks) == 2
        assert manager.config.projects["/path/to/project1"].tasks[0].name == "build"


@pytest.mark.unit
class TestProjectManagement:
    """Tests for adding, selecting, and deleting projects."""

    def test_add_new_project(self, gradle_manager_with_temp_config):
        """Test adding a new project."""
        manager = gradle_manager_with_temp_config

        project_dir = "/test/new/project"
        manager.add_project(project_dir)

        assert project_dir in manager.config.projects
        # First project should be auto-selected
        assert manager.config.currently_selected == project_dir

    def test_add_existing_project(self, gradle_manager_with_projects):
        """Test adding a project that already exists."""
        manager = gradle_manager_with_projects

        initial_count = len(manager.config.projects)
        manager.add_project("/path/to/project1")

        # Should not create duplicate
        assert len(manager.config.projects) == initial_count

    def test_add_project_normalizes_path(self, gradle_manager_with_temp_config):
        """Test that project paths are normalized."""
        manager = gradle_manager_with_temp_config

        # Add with relative path
        relative_path = "relative/path"
        manager.add_project(relative_path)

        # Should be stored as absolute path
        absolute_path = os.path.abspath(relative_path)
        assert absolute_path in manager.config.projects

    def test_select_project(self, gradle_manager_with_projects):
        """Test selecting a project."""
        manager = gradle_manager_with_projects

        manager.select_project("/path/to/project2")

        assert manager.config.currently_selected == "/path/to/project2"

    def test_select_nonexistent_project(self, gradle_manager_with_projects):
        """Test selecting a project that doesn't exist."""
        manager = gradle_manager_with_projects

        original_selection = manager.config.currently_selected
        manager.select_project("/nonexistent/project")

        # Selection should not change
        assert manager.config.currently_selected == original_selection

    def test_delete_project(self, gradle_manager_with_projects):
        """Test deleting a project."""
        manager = gradle_manager_with_projects

        result = manager.delete_project("/path/to/project2")

        assert result is True
        assert "/path/to/project2" not in manager.config.projects

    def test_delete_selected_project_auto_selects_another(self, gradle_manager_with_projects):
        """Test that deleting the selected project auto-selects another."""
        manager = gradle_manager_with_projects

        # Delete the currently selected project
        manager.delete_project("/path/to/project1")

        # Should auto-select the remaining project
        assert manager.config.currently_selected == "/path/to/project2"

    def test_delete_last_project(self, gradle_manager_with_temp_config):
        """Test deleting the last remaining project."""
        manager = gradle_manager_with_temp_config

        manager.add_project("/test/project")
        manager.delete_project("/test/project")

        assert len(manager.config.projects) == 0
        assert manager.config.currently_selected is None

    def test_delete_nonexistent_project(self, gradle_manager_with_projects):
        """Test deleting a project that doesn't exist."""
        manager = gradle_manager_with_projects

        result = manager.delete_project("/nonexistent/project")

        assert result is False

    def test_get_selected_project(self, gradle_manager_with_projects):
        """Test retrieving the selected project."""
        manager = gradle_manager_with_projects

        selected = manager.get_selected_project()

        assert selected == "/path/to/project1"

    def test_get_selected_project_none(self, gradle_manager_with_temp_config):
        """Test getting selected project when none is selected."""
        manager = gradle_manager_with_temp_config

        selected = manager.get_selected_project()

        assert selected is None


@pytest.mark.unit
class TestThemeManagement:
    """Tests for theme management."""

    def test_get_theme(self, gradle_manager_with_projects):
        """Test retrieving the current theme."""
        manager = gradle_manager_with_projects

        theme = manager.get_theme()

        assert theme == "nord"

    def test_get_theme_none(self, gradle_manager_with_temp_config):
        """Test getting theme when none is set."""
        manager = gradle_manager_with_temp_config

        theme = manager.get_theme()

        assert theme is None

    def test_set_theme(self, gradle_manager_with_temp_config):
        """Test setting a theme."""
        manager = gradle_manager_with_temp_config

        manager.set_theme("dracula")

        assert manager.config.theme == "dracula"

        # Verify it was saved
        with open(manager.CONFIG_FILE, "r") as f:
            data = json.load(f)
        assert data["theme"] == "dracula"


@pytest.mark.unit
class TestTaskManagement:
    """Tests for task-related operations."""

    def test_update_project_tasks_success(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test updating tasks for a project."""
        manager = gradle_manager_with_temp_config

        # Add project first
        manager.add_project(temp_gradle_project)

        mock_tasks = [
            TaskDTO("build", "Build the project"),
            TaskDTO("test", "Run tests"),
        ]
        mock_task_list = TaskList(tasks=mock_tasks, success=True, error=None)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.list_all_tasks.return_value = mock_task_list

            error = manager.update_project_tasks(temp_gradle_project)

            assert error is None
            assert len(manager.config.projects[temp_gradle_project].tasks) == 2
            assert manager.config.projects[temp_gradle_project].tasks[0].name == "build"

    def test_update_project_tasks_failure(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test handling failure when updating tasks."""
        manager = gradle_manager_with_temp_config

        manager.add_project(temp_gradle_project)

        gradle_error = GradleError("Failed to list tasks", 1)
        mock_task_list = TaskList(tasks=[], success=False, error=gradle_error)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.list_all_tasks.return_value = mock_task_list

            error = manager.update_project_tasks(temp_gradle_project)

            assert error is not None
            assert "Failed to retrieve tasks" in error

    def test_get_project_info(self, gradle_manager_with_projects):
        """Test retrieving project information."""
        manager = gradle_manager_with_projects

        project_info = manager.get_project_info("/path/to/project1")

        assert project_info is not None
        assert len(project_info.tasks) == 2
        assert project_info.tasks[0].name == "build"

    def test_get_project_info_nonexistent(self, gradle_manager_with_projects):
        """Test getting info for nonexistent project."""
        manager = gradle_manager_with_projects

        project_info = manager.get_project_info("/nonexistent/project")

        assert project_info is None

    def test_list_all_projects(self, gradle_manager_with_projects):
        """Test listing all projects."""
        manager = gradle_manager_with_projects

        projects = manager.list_all_projects()

        assert len(projects) == 2
        assert "/path/to/project1" in projects
        assert "/path/to/project2" in projects


@pytest.mark.unit
class TestRecentTasks:
    """Tests for recent task tracking."""

    def test_record_task_execution(self, gradle_manager_with_projects):
        """Test recording a task execution."""
        manager = gradle_manager_with_projects

        initial_count = len(manager.config.projects["/path/to/project1"].recent_tasks)

        manager._record_task_execution("build", None)

        recent_tasks = manager.config.projects["/path/to/project1"].recent_tasks
        assert len(recent_tasks) == initial_count + 1
        assert recent_tasks[0]["task_name"] == "build"

    def test_record_task_execution_with_parameters(self, gradle_manager_with_projects):
        """Test recording task execution with parameters."""
        manager = gradle_manager_with_projects

        manager._record_task_execution("test", ["--info", "--stacktrace"])

        recent_tasks = manager.config.projects["/path/to/project1"].recent_tasks
        assert recent_tasks[0]["parameters"] == "--info --stacktrace"

    def test_recent_tasks_limit(self, gradle_manager_with_temp_config):
        """Test that recent tasks are limited to 10 entries."""
        manager = gradle_manager_with_temp_config

        manager.add_project("/test/project")
        manager.select_project("/test/project")

        # Add 15 tasks
        for i in range(15):
            manager._record_task_execution(f"task{i}")

        recent_tasks = manager.get_recent_tasks()
        assert len(recent_tasks) <= 10
        # Most recent should be first
        assert recent_tasks[0]["task_name"] == "task14"

    def test_get_recent_tasks(self, gradle_manager_with_projects):
        """Test retrieving recent tasks."""
        manager = gradle_manager_with_projects

        recent_tasks = manager.get_recent_tasks("/path/to/project1")

        assert len(recent_tasks) == 1
        assert recent_tasks[0]["task_name"] == "build"

    def test_get_recent_tasks_default_project(self, gradle_manager_with_projects):
        """Test getting recent tasks for currently selected project."""
        manager = gradle_manager_with_projects

        recent_tasks = manager.get_recent_tasks()

        assert len(recent_tasks) == 1

    def test_get_recent_tasks_no_selection(self, gradle_manager_with_temp_config):
        """Test getting recent tasks when no project is selected."""
        manager = gradle_manager_with_temp_config

        recent_tasks = manager.get_recent_tasks()

        assert recent_tasks == []


@pytest.mark.unit
class TestRunTask:
    """Tests for running tasks."""

    def test_run_task_success(self, gradle_manager_with_projects):
        """Test successfully running a task."""
        manager = gradle_manager_with_projects

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = ("Build successful", None)

            output = manager.run_task("build")

            assert output == "Build successful"
            mock_wrapper.run_custom_gradle_task.assert_called_once()

    def test_run_task_no_project_selected(self, gradle_manager_with_temp_config):
        """Test running task when no project is selected."""
        manager = gradle_manager_with_temp_config

        output = manager.run_task("build")

        assert output is None

    def test_run_task_with_error(self, gradle_manager_with_projects):
        """Test running task that fails."""
        manager = gradle_manager_with_projects

        error = GradleError("Build failed", 1)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = (None, error)

            output = manager.run_task("build")

            assert "Error:" in output
            assert "Build failed" in output

    def test_run_task_with_streaming(self, gradle_manager_with_projects):
        """Test running task with streaming callbacks."""
        manager = gradle_manager_with_projects

        stdout_lines = []

        def on_stdout(line):
            stdout_lines.append(line)

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = ("Success", None)

            manager.run_task("build", on_stdout=on_stdout)

            # Verify callback was passed
            call_args = mock_wrapper.run_custom_gradle_task.call_args
            assert call_args[1]['on_stdout'] == on_stdout

    def test_run_task_with_parameters_success(self, gradle_manager_with_projects):
        """Test running task with parameters."""
        manager = gradle_manager_with_projects

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = ("Test successful", None)

            output = manager.run_task_with_parameters("test", ["--info"])

            assert output == "Test successful"
            mock_wrapper.run_custom_gradle_task.assert_called_once_with(
                "test",
                options=["--info"],
                on_stdout=None,
                on_stderr=None
            )

    def test_run_task_with_parameters_no_project(self, gradle_manager_with_temp_config):
        """Test running task with parameters when no project selected."""
        manager = gradle_manager_with_temp_config

        output = manager.run_task_with_parameters("test", ["--info"])

        assert output is None

    def test_run_task_records_execution(self, gradle_manager_with_projects):
        """Test that running a task records the execution."""
        manager = gradle_manager_with_projects

        with patch('gradle.gradle_manager.GradleWrapper') as MockWrapper:
            mock_wrapper = MockWrapper.return_value
            mock_wrapper.run_custom_gradle_task.return_value = ("Success", None)

            manager.run_task("clean")

            recent_tasks = manager.get_recent_tasks()
            assert recent_tasks[0]["task_name"] == "clean"

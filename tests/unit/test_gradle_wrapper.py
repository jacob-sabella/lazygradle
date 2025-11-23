"""Unit tests for GradleWrapper class."""
import os
import stat
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from gradle.gradle_wrapper import GradleWrapper
from gradle.dto.gradle_error import GradleError
from gradle.dto.task_list import TaskList
from gradle.dto.task_metadata import TaskMetadata


@pytest.mark.unit
class TestGradleWrapperInit:
    """Tests for GradleWrapper initialization."""

    def test_initialization(self, temp_gradle_project):
        """Test that GradleWrapper initializes correctly."""
        wrapper = GradleWrapper(temp_gradle_project)
        assert wrapper.working_directory == temp_gradle_project
        assert wrapper.logger is not None

    def test_initialization_with_different_directory(self):
        """Test initialization with a specific directory."""
        test_dir = "/some/test/directory"
        wrapper = GradleWrapper(test_dir)
        assert wrapper.working_directory == test_dir


@pytest.mark.unit
class TestGradlewPermissions:
    """Tests for gradlew permission checking and fixing."""

    def test_check_gradlew_permissions_success(self, temp_gradle_project):
        """Test checking permissions on a valid gradlew file."""
        wrapper = GradleWrapper(temp_gradle_project)
        has_permission, error = wrapper.check_gradlew_permissions()

        assert has_permission is True
        assert error is None

    def test_check_gradlew_permissions_missing_file(self, temp_config_dir):
        """Test checking permissions when gradlew doesn't exist."""
        wrapper = GradleWrapper(str(temp_config_dir))
        has_permission, error = wrapper.check_gradlew_permissions()

        assert has_permission is False
        assert "not found" in error.lower()

    def test_check_gradlew_permissions_no_exec(self, temp_gradle_project_no_exec):
        """Test checking permissions when gradlew is not executable."""
        wrapper = GradleWrapper(temp_gradle_project_no_exec)
        has_permission, error = wrapper.check_gradlew_permissions()

        assert has_permission is False
        assert "execute permissions" in error.lower()

    def test_can_fix_gradlew_permissions_as_owner(self, temp_gradle_project_no_exec):
        """Test that owner can fix permissions."""
        wrapper = GradleWrapper(temp_gradle_project_no_exec)
        can_fix, message = wrapper.can_fix_gradlew_permissions()

        # Should be able to fix if we're the owner
        assert can_fix is True
        assert "permission" in message.lower()

    def test_fix_gradlew_permissions_success(self, temp_gradle_project_no_exec):
        """Test successfully adding execute permissions."""
        wrapper = GradleWrapper(temp_gradle_project_no_exec)

        # Verify it's not executable initially
        gradlew_path = os.path.join(temp_gradle_project_no_exec, "gradlew")
        initial_stat = os.stat(gradlew_path)
        assert not (initial_stat.st_mode & stat.S_IXUSR)

        # Fix permissions
        success, message = wrapper.fix_gradlew_permissions()

        assert success is True
        assert "success" in message.lower()

        # Verify it's now executable
        final_stat = os.stat(gradlew_path)
        assert final_stat.st_mode & stat.S_IXUSR


@pytest.mark.unit
class TestListAllTasks:
    """Tests for listing Gradle tasks."""

    def test_list_all_tasks_success(self, temp_gradle_project):
        """Test successfully listing tasks."""
        wrapper = GradleWrapper(temp_gradle_project)

        mock_output = """
> Task :tasks

------------------------------------------------------------
Tasks runnable from root project 'test-project'
------------------------------------------------------------

Build tasks
-----------
assemble - Assembles the outputs of this project.
build - Assembles and tests this project.
clean - Deletes the build directory.

Verification tasks
------------------
check - Runs all checks.
test - Runs the test suite.
"""

        with patch.object(wrapper, 'run_gradle_command', return_value=(mock_output, None)):
            task_list = wrapper.list_all_tasks()

            assert task_list.success is True
            assert task_list.error is None
            assert len(task_list.tasks) == 5

            # Verify task names
            task_names = [task.name for task in task_list.tasks]
            assert "assemble" in task_names
            assert "build" in task_names
            assert "clean" in task_names
            assert "check" in task_names
            assert "test" in task_names

    def test_list_all_tasks_failure(self, temp_gradle_project):
        """Test listing tasks when Gradle command fails."""
        wrapper = GradleWrapper(temp_gradle_project)

        error = GradleError("Build failed", 1)
        with patch.object(wrapper, 'run_gradle_command', return_value=(None, error)):
            task_list = wrapper.list_all_tasks()

            assert task_list.success is False
            assert task_list.error == error
            assert len(task_list.tasks) == 0

    def test_list_all_tasks_empty_output(self, temp_gradle_project):
        """Test handling empty output from Gradle."""
        wrapper = GradleWrapper(temp_gradle_project)

        with patch.object(wrapper, 'run_gradle_command', return_value=("", None)):
            task_list = wrapper.list_all_tasks()

            assert task_list.success is False
            assert task_list.error is not None


@pytest.mark.unit
class TestGetTaskMetadata:
    """Tests for retrieving task metadata."""

    def test_get_task_metadata_success(self, temp_gradle_project):
        """Test successfully retrieving task metadata."""
        wrapper = GradleWrapper(temp_gradle_project)

        mock_metadata = """
Detailed help for task 'build'

Path
     :build

Type
     Task (org.gradle.api.Task)

Description
     Assembles and tests this project.
"""

        with patch.object(wrapper, 'run_gradle_command', return_value=(mock_metadata, None)):
            metadata = wrapper.get_task_metadata("build")

            assert metadata.success is True
            assert metadata.error is None
            assert metadata.task_name == "build"
            assert metadata.metadata == mock_metadata

    def test_get_task_metadata_failure(self, temp_gradle_project):
        """Test metadata retrieval when command fails."""
        wrapper = GradleWrapper(temp_gradle_project)

        error = GradleError("Task not found", 1)
        with patch.object(wrapper, 'run_gradle_command', return_value=(None, error)):
            metadata = wrapper.get_task_metadata("nonexistent")

            assert metadata.success is False
            assert metadata.error == error
            assert metadata.task_name == "nonexistent"


@pytest.mark.unit
class TestRunGradleCommand:
    """Tests for running Gradle commands."""

    def test_run_gradle_command_success(self, temp_gradle_project):
        """Test successfully running a Gradle command."""
        wrapper = GradleWrapper(temp_gradle_project)

        mock_result = Mock()
        mock_result.stdout = b"Build successful\n"
        mock_result.stderr = b""
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            output, error = wrapper.run_gradle_command(["./gradlew", "build"])

            assert output == "Build successful"
            assert error is None
            mock_run.assert_called_once()

    def test_run_gradle_command_with_streaming(self, temp_gradle_project):
        """Test running command with stdout/stderr callbacks."""
        wrapper = GradleWrapper(temp_gradle_project)

        stdout_lines = []
        stderr_lines = []

        def on_stdout(line):
            stdout_lines.append(line)

        def on_stderr(line):
            stderr_lines.append(line)

        with patch.object(wrapper, '_run_with_streaming') as mock_streaming:
            mock_streaming.return_value = ("output", None)

            output, error = wrapper.run_gradle_command(
                ["./gradlew", "build"],
                on_stdout=on_stdout,
                on_stderr=on_stderr
            )

            # Verify streaming method was called
            mock_streaming.assert_called_once()

    def test_run_gradle_command_permission_error(self, temp_gradle_project):
        """Test handling PermissionError when running command."""
        wrapper = GradleWrapper(temp_gradle_project)

        with patch('subprocess.run', side_effect=PermissionError("Permission denied")):
            output, error = wrapper.run_gradle_command(["./gradlew", "build"])

            assert output is None
            assert error is not None
            assert "Permission denied" in error.error_message
            assert "execute permissions" in error.error_message

    def test_run_gradle_command_file_not_found(self, temp_gradle_project):
        """Test handling FileNotFoundError."""
        wrapper = GradleWrapper(temp_gradle_project)

        with patch('subprocess.run', side_effect=FileNotFoundError()):
            output, error = wrapper.run_gradle_command(["gradle", "build"])

            assert output is None
            assert error is not None
            assert "not found in PATH" in error.error_message

    def test_run_gradle_command_failed_execution(self, temp_gradle_project):
        """Test handling subprocess.CalledProcessError."""
        wrapper = GradleWrapper(temp_gradle_project)

        error_obj = subprocess.CalledProcessError(
            returncode=1,
            cmd=["./gradlew", "build"],
            stderr=b"Build failed: syntax error"
        )

        with patch('subprocess.run', side_effect=error_obj):
            output, error = wrapper.run_gradle_command(["./gradlew", "build"])

            assert output is None
            assert error is not None
            assert error.return_code == 1
            assert "Build failed" in error.error_message


@pytest.mark.unit
class TestRunCustomGradleTask:
    """Tests for running custom Gradle tasks."""

    def test_run_custom_task_without_options(self, temp_gradle_project):
        """Test running a custom task without additional options."""
        wrapper = GradleWrapper(temp_gradle_project)

        with patch.object(wrapper, 'run_gradle_command') as mock_run:
            mock_run.return_value = ("Task executed", None)

            output, error = wrapper.run_custom_gradle_task("build")

            assert output == "Task executed"
            assert error is None
            mock_run.assert_called_once_with(
                ["./gradlew", "build"],
                on_stdout=None,
                on_stderr=None
            )

    def test_run_custom_task_with_options(self, temp_gradle_project):
        """Test running a custom task with options."""
        wrapper = GradleWrapper(temp_gradle_project)

        with patch.object(wrapper, 'run_gradle_command') as mock_run:
            mock_run.return_value = ("Task executed", None)

            options = ["--info", "--stacktrace"]
            output, error = wrapper.run_custom_gradle_task("test", options=options)

            assert output == "Task executed"
            assert error is None
            mock_run.assert_called_once_with(
                ["./gradlew", "test", "--info", "--stacktrace"],
                on_stdout=None,
                on_stderr=None
            )

    def test_run_custom_task_with_streaming(self, temp_gradle_project):
        """Test running custom task with streaming callbacks."""
        wrapper = GradleWrapper(temp_gradle_project)

        stdout_lines = []

        def on_stdout(line):
            stdout_lines.append(line)

        with patch.object(wrapper, 'run_gradle_command') as mock_run:
            mock_run.return_value = ("Task executed", None)

            wrapper.run_custom_gradle_task("build", on_stdout=on_stdout)

            # Verify callback was passed through
            call_args = mock_run.call_args
            assert call_args[1]['on_stdout'] == on_stdout

    def test_run_custom_task_failure(self, temp_gradle_project):
        """Test handling task execution failure."""
        wrapper = GradleWrapper(temp_gradle_project)

        error = GradleError("Task failed", 1)
        with patch.object(wrapper, 'run_gradle_command', return_value=(None, error)):
            output, error_result = wrapper.run_custom_gradle_task("build")

            assert output is None
            assert error_result == error


@pytest.mark.unit
class TestRunWithStreaming:
    """Tests for the streaming command execution."""

    def test_streaming_success(self, temp_gradle_project):
        """Test successful streaming execution."""
        wrapper = GradleWrapper(temp_gradle_project)

        stdout_lines = []
        stderr_lines = []

        def on_stdout(line):
            stdout_lines.append(line)

        def on_stderr(line):
            stderr_lines.append(line)

        mock_process = Mock()
        mock_process.stdout = iter(["Line 1", "Line 2", "Line 3"])
        mock_process.stderr = iter([])
        mock_process.wait.return_value = 0

        with patch('subprocess.Popen', return_value=mock_process):
            output, error = wrapper._run_with_streaming(
                ["./gradlew", "build"],
                os.environ.copy(),
                on_stdout,
                on_stderr
            )

            assert error is None
            assert len(stdout_lines) == 3
            assert stdout_lines == ["Line 1", "Line 2", "Line 3"]

    def test_streaming_with_error(self, temp_gradle_project):
        """Test streaming when process returns non-zero."""
        wrapper = GradleWrapper(temp_gradle_project)

        mock_process = Mock()
        mock_process.stdout = iter([])
        mock_process.stderr = iter(["Error line 1", "Error line 2"])
        mock_process.wait.return_value = 1

        with patch('subprocess.Popen', return_value=mock_process):
            output, error = wrapper._run_with_streaming(
                ["./gradlew", "build"],
                os.environ.copy(),
                None,
                None
            )

            assert output is None
            assert error is not None
            assert error.return_code == 1
            assert "Error line 1" in error.error_message

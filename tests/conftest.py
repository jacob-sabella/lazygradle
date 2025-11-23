"""Pytest configuration and shared fixtures for LazyGradle tests."""
import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
from unittest.mock import MagicMock, Mock

from gradle.gradle_wrapper import GradleWrapper
from gradle.gradle_manager import GradleManager, Task, Project, Config
from gradle.dto.task import Task as TaskDTO
from gradle.dto.task_list import TaskList
from gradle.dto.task_metadata import TaskMetadata
from gradle.dto.gradle_error import GradleError


@pytest.fixture
def temp_gradle_project() -> Generator[str, None, None]:
    """Create a temporary directory that simulates a Gradle project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock gradlew script
        gradlew_path = os.path.join(temp_dir, "gradlew")
        with open(gradlew_path, "w") as f:
            f.write("#!/bin/bash\necho 'Mock Gradle'\n")
        os.chmod(gradlew_path, 0o755)

        # Create build.gradle
        build_gradle = os.path.join(temp_dir, "build.gradle")
        with open(build_gradle, "w") as f:
            f.write("// Mock build.gradle\n")

        yield temp_dir


@pytest.fixture
def temp_gradle_project_no_exec() -> Generator[str, None, None]:
    """Create a temporary Gradle project without execute permissions on gradlew."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock gradlew script without execute permissions
        gradlew_path = os.path.join(temp_dir, "gradlew")
        with open(gradlew_path, "w") as f:
            f.write("#!/bin/bash\necho 'Mock Gradle'\n")
        os.chmod(gradlew_path, 0o644)  # No execute permission

        yield temp_dir


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Create a temporary config directory for testing GradleManager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "lazygradle"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir


@pytest.fixture
def mock_gradle_wrapper(temp_gradle_project: str) -> GradleWrapper:
    """Create a GradleWrapper instance with a temporary project."""
    return GradleWrapper(temp_gradle_project)


@pytest.fixture
def mock_task_list() -> TaskList:
    """Create a mock TaskList with sample tasks."""
    tasks = [
        TaskDTO("build", "Assembles and tests this project"),
        TaskDTO("clean", "Deletes the build directory"),
        TaskDTO("test", "Runs the test suite"),
        TaskDTO("assemble", "Assembles the outputs of this project"),
        TaskDTO("check", "Runs all checks"),
    ]
    return TaskList(tasks=tasks, success=True, error=None)


@pytest.fixture
def mock_task_metadata() -> TaskMetadata:
    """Create mock task metadata."""
    return TaskMetadata(
        task_name="build",
        metadata="Detailed information about the build task",
        success=True,
        error=None
    )


@pytest.fixture
def mock_gradle_error() -> GradleError:
    """Create a mock GradleError."""
    return GradleError(
        error_message="Command failed with error",
        return_code=1
    )


@pytest.fixture
def sample_config_data() -> Dict[str, Any]:
    """Create sample configuration data for testing."""
    return {
        "projects": {
            "/path/to/project1": {
                "tasks": [
                    {"name": "build", "description": "Build the project"},
                    {"name": "test", "description": "Run tests"}
                ],
                "metadata": {
                    "build": "Build task metadata"
                },
                "recent_tasks": [
                    {
                        "task_name": "build",
                        "timestamp": "2024-01-01T12:00:00",
                        "parameters": ""
                    }
                ]
            },
            "/path/to/project2": {
                "tasks": [
                    {"name": "clean", "description": "Clean build artifacts"}
                ],
                "metadata": {},
                "recent_tasks": []
            }
        },
        "currently_selected": "/path/to/project1",
        "theme": "nord"
    }


@pytest.fixture
def gradle_manager_with_temp_config(temp_config_dir: Path, monkeypatch) -> GradleManager:
    """Create a GradleManager instance with a temporary config directory."""
    # Patch the CONFIG_DIR and CONFIG_FILE to use temp directory
    monkeypatch.setattr(GradleManager, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(GradleManager, "CONFIG_FILE", temp_config_dir / "gradle_cache.json")

    return GradleManager()


@pytest.fixture
def gradle_manager_with_projects(
    temp_config_dir: Path,
    sample_config_data: Dict[str, Any],
    monkeypatch
) -> GradleManager:
    """Create a GradleManager with pre-populated projects."""
    config_file = temp_config_dir / "gradle_cache.json"

    # Write sample config
    with open(config_file, "w") as f:
        json.dump(sample_config_data, f)

    # Patch the CONFIG_DIR and CONFIG_FILE
    monkeypatch.setattr(GradleManager, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(GradleManager, "CONFIG_FILE", config_file)

    return GradleManager()


@pytest.fixture
def mock_subprocess_run():
    """Create a mock for subprocess.run."""
    mock = Mock()
    mock.return_value = Mock(
        stdout=b"Mock output\n",
        stderr=b"",
        returncode=0
    )
    return mock


@pytest.fixture
def mock_subprocess_popen():
    """Create a mock for subprocess.Popen."""
    mock_process = Mock()
    mock_process.stdout = iter(["Line 1\n", "Line 2\n", "Line 3\n"])
    mock_process.stderr = iter([])
    mock_process.wait.return_value = 0

    mock = Mock(return_value=mock_process)
    return mock

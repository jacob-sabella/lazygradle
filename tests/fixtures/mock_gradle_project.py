"""Utilities for creating mock Gradle projects for testing."""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict


class MockGradleProject:
    """Creates a mock Gradle project structure for testing."""

    def __init__(self, temp_dir: str, with_permissions: bool = True):
        """
        Initialize a mock Gradle project.

        Args:
            temp_dir: Temporary directory to create the project in
            with_permissions: Whether gradlew should have execute permissions
        """
        self.project_dir = temp_dir
        self.with_permissions = with_permissions
        self._setup_project()

    def _setup_project(self):
        """Set up the mock Gradle project structure."""
        # Create gradlew script
        gradlew_path = os.path.join(self.project_dir, "gradlew")
        gradlew_content = """#!/bin/bash
# Mock Gradle Wrapper

case "$1" in
    tasks)
        echo "> Task :tasks"
        echo ""
        echo "------------------------------------------------------------"
        echo "Tasks runnable from root project 'mock-project'"
        echo "------------------------------------------------------------"
        echo ""
        echo "Build tasks"
        echo "-----------"
        echo "assemble - Assembles the outputs of this project."
        echo "build - Assembles and tests this project."
        echo "clean - Deletes the build directory."
        echo ""
        echo "Verification tasks"
        echo "------------------"
        echo "check - Runs all checks."
        echo "test - Runs the test suite."
        ;;
    help)
        echo "Detailed help for task '$3'"
        echo ""
        echo "Path"
        echo "     :$3"
        echo ""
        echo "Type"
        echo "     Task (org.gradle.api.Task)"
        echo ""
        echo "Description"
        echo "     Mock description for $3"
        ;;
    *)
        echo "BUILD SUCCESSFUL"
        echo ""
        echo "1 actionable task: 1 executed"
        ;;
esac
"""
        with open(gradlew_path, "w") as f:
            f.write(gradlew_content)

        if self.with_permissions:
            os.chmod(gradlew_path, 0o755)
        else:
            os.chmod(gradlew_path, 0o644)

        # Create build.gradle
        build_gradle = os.path.join(self.project_dir, "build.gradle")
        build_gradle_content = """
plugins {
    id 'java'
}

group = 'com.example'
version = '1.0.0'

repositories {
    mavenCentral()
}

dependencies {
    testImplementation 'junit:junit:4.13.2'
}
"""
        with open(build_gradle, "w") as f:
            f.write(build_gradle_content)

        # Create settings.gradle
        settings_gradle = os.path.join(self.project_dir, "settings.gradle")
        with open(settings_gradle, "w") as f:
            f.write("rootProject.name = 'mock-project'\n")

        # Create src directory structure
        src_main_java = Path(self.project_dir) / "src" / "main" / "java"
        src_main_java.mkdir(parents=True, exist_ok=True)

        src_test_java = Path(self.project_dir) / "src" / "test" / "java"
        src_test_java.mkdir(parents=True, exist_ok=True)

    def add_task_to_output(self, task_name: str, description: str):
        """
        Modify gradlew to include an additional task in the output.

        Args:
            task_name: Name of the task
            description: Description of the task
        """
        # This is a simplified implementation
        # In a real scenario, you might want to maintain a more complex mock
        pass

    def get_path(self) -> str:
        """Get the path to the mock project."""
        return self.project_dir

    def set_gradlew_permissions(self, executable: bool):
        """
        Set execute permissions on gradlew.

        Args:
            executable: Whether gradlew should be executable
        """
        gradlew_path = os.path.join(self.project_dir, "gradlew")
        if executable:
            os.chmod(gradlew_path, 0o755)
        else:
            os.chmod(gradlew_path, 0o644)

    def create_gradle_properties(self, properties: Dict[str, str]):
        """
        Create gradle.properties file with specified properties.

        Args:
            properties: Dictionary of properties to add
        """
        gradle_props = os.path.join(self.project_dir, "gradle.properties")
        with open(gradle_props, "w") as f:
            for key, value in properties.items():
                f.write(f"{key}={value}\n")

    def create_java_class(self, package: str, class_name: str, content: Optional[str] = None):
        """
        Create a Java class file in the project.

        Args:
            package: Java package name (e.g., "com.example")
            class_name: Name of the class
            content: Optional content, will generate basic class if not provided
        """
        package_dir = Path(self.project_dir) / "src" / "main" / "java" / package.replace(".", "/")
        package_dir.mkdir(parents=True, exist_ok=True)

        class_file = package_dir / f"{class_name}.java"

        if content is None:
            content = f"""package {package};

public class {class_name} {{
    public static void main(String[] args) {{
        System.out.println("Hello from {class_name}!");
    }}
}}
"""

        with open(class_file, "w") as f:
            f.write(content)


def create_mock_gradle_projects(count: int = 2, temp_base_dir: Optional[str] = None) -> List[MockGradleProject]:
    """
    Create multiple mock Gradle projects for testing.

    Args:
        count: Number of projects to create
        temp_base_dir: Base directory for projects (creates temp if not provided)

    Returns:
        List of MockGradleProject instances
    """
    if temp_base_dir is None:
        temp_base_dir = tempfile.mkdtemp(prefix="mock_gradle_projects_")

    projects = []
    for i in range(count):
        project_dir = os.path.join(temp_base_dir, f"project{i + 1}")
        os.makedirs(project_dir, exist_ok=True)
        projects.append(MockGradleProject(project_dir))

    return projects


class MockGradleOutput:
    """Mock Gradle command outputs for testing."""

    @staticmethod
    def tasks_output(tasks: List[tuple]) -> str:
        """
        Generate mock output for 'gradle tasks' command.

        Args:
            tasks: List of (task_name, description) tuples

        Returns:
            Mock Gradle tasks output
        """
        output = [
            "> Task :tasks",
            "",
            "------------------------------------------------------------",
            "Tasks runnable from root project 'mock-project'",
            "------------------------------------------------------------",
            "",
            "Build tasks",
            "-----------",
        ]

        for task_name, description in tasks:
            output.append(f"{task_name} - {description}")

        return "\n".join(output)

    @staticmethod
    def build_success_output() -> str:
        """Generate mock successful build output."""
        return """
> Task :compileJava
> Task :processResources NO-SOURCE
> Task :classes
> Task :jar
> Task :assemble
> Task :compileTestJava
> Task :processTestResources NO-SOURCE
> Task :testClasses
> Task :test
> Task :check
> Task :build

BUILD SUCCESSFUL in 2s
7 actionable tasks: 7 executed
"""

    @staticmethod
    def build_failure_output() -> str:
        """Generate mock failed build output."""
        return """
> Task :compileJava FAILED

FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':compileJava'.
> Compilation failed; see the compiler error output for details.

* Try:
> Run with --stacktrace option to get the stack trace.
> Run with --info or --debug option to get more log output.

BUILD FAILED in 1s
1 actionable task: 1 executed
"""

    @staticmethod
    def test_output(passed: int, failed: int) -> str:
        """
        Generate mock test execution output.

        Args:
            passed: Number of passed tests
            failed: Number of failed tests

        Returns:
            Mock test output
        """
        status = "FAILED" if failed > 0 else "SUCCESSFUL"
        return f"""
> Task :test

MockTest > testExample PASSED
MockTest > testAnother {'FAILED' if failed > 0 else 'PASSED'}

{passed + failed} tests completed, {failed} failed

BUILD {status}
"""

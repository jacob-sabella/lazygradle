import os
import subprocess
import logging
import threading
import stat
from typing import Optional, Tuple, List, Callable, Dict

from gradle.dto.gradle_error import GradleError
from gradle.dto.task import Task
from gradle.dto.task_list import TaskList
from gradle.dto.task_metadata import TaskMetadata


class GradleWrapper:
    def __init__(self, working_directory: str):
        """
        Initialize the GradleWrapper class with a specific working directory.

        Parameters:
        working_directory (str): The directory where the Gradle project resides.
        """
        self.working_directory = working_directory
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.debug(
            f"GradleWrapper initialized for directory: {self.working_directory}"
        )

    def check_gradlew_permissions(self) -> Tuple[bool, Optional[str]]:
        """
        Check if the gradlew file exists and has execute permissions.

        Returns:
        Tuple[bool, Optional[str]]: (has_execute_permission, error_message)
            - (True, None) if gradlew exists and is executable
            - (False, error_message) if there's an issue
        """
        gradlew_path = os.path.join(self.working_directory, "gradlew")

        if not os.path.exists(gradlew_path):
            return False, f"Gradle wrapper not found at {gradlew_path}"

        if not os.path.isfile(gradlew_path):
            return False, f"gradlew exists but is not a file"

        # Check if file has execute permissions
        file_stat = os.stat(gradlew_path)
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)

        if not is_executable:
            return False, f"gradlew exists but does not have execute permissions"

        return True, None

    def can_fix_gradlew_permissions(self) -> Tuple[bool, str]:
        """
        Check if we have permissions to chmod the gradlew file.

        Returns:
        Tuple[bool, str]: (can_fix, message)
            - (True, success_message) if we can chmod the file
            - (False, error_message) if we cannot
        """
        gradlew_path = os.path.join(self.working_directory, "gradlew")

        if not os.path.exists(gradlew_path):
            return False, "gradlew file does not exist"

        # Check if we own the file or have write access
        try:
            # Try to check if we can modify file permissions
            file_stat = os.stat(gradlew_path)

            # Check if we're the owner
            if file_stat.st_uid == os.getuid():
                return True, "You have permission to add execute permissions to gradlew"

            # Check if we have write access to the file
            if os.access(gradlew_path, os.W_OK):
                return True, "You have write access to add execute permissions to gradlew"

            return False, "You don't have permission to modify gradlew. You'll need to run: sudo chmod +x gradlew"
        except Exception as e:
            return False, f"Error checking permissions: {str(e)}"

    def fix_gradlew_permissions(self) -> Tuple[bool, str]:
        """
        Add execute permissions to the gradlew file.

        Returns:
        Tuple[bool, str]: (success, message)
        """
        gradlew_path = os.path.join(self.working_directory, "gradlew")

        try:
            # Get current permissions
            current_permissions = os.stat(gradlew_path).st_mode

            # Add execute permissions for user, group, and others
            new_permissions = current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH

            # Set the new permissions
            os.chmod(gradlew_path, new_permissions)

            self.logger.info(f"Successfully added execute permissions to {gradlew_path}")
            return True, "Execute permissions added successfully"
        except PermissionError:
            return False, "Permission denied. You may need to run: sudo chmod +x gradlew"
        except Exception as e:
            return False, f"Failed to add execute permissions: {str(e)}"

    def list_all_tasks(self) -> TaskList:
        """
        Lists all Gradle tasks in the project's working directory and returns a TaskList object.

        Returns:
        TaskList: A TaskList object containing a list of Task objects or an error.
        """
        self.logger.debug(
            f"Listing all Gradle tasks in directory: {self.working_directory}"
        )
        output, error = self.run_gradle_command(["./gradlew", "tasks", "--all"])

        if error:
            self.logger.error(f"Failed to list tasks: {error.error_message}")
            return TaskList(tasks=[], success=False, error=error)

        if not output:
            self.logger.warning(f"No values in task output")
            return TaskList(
                tasks=[],
                success=False,
                error=GradleError("No values in task output", -1),
            )

        # Process the output to extract tasks and descriptions
        tasks: List[Task] = []
        for line in output.splitlines():
            if (
                line.strip()
                and not line.startswith(">")
                and not line.startswith("Deprecated")
            ):
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    task_name, task_description = parts
                    tasks.append(Task(task_name.strip(), task_description.strip()))

        self.logger.debug(f"Found {len(tasks)} tasks.")
        return TaskList(tasks=tasks)

    def get_task_metadata(self, task_name: str) -> TaskMetadata:
        """
        Retrieves and returns detailed metadata about a specific Gradle task in the project's working directory.

        Parameters:
        task_name (str): The name of the Gradle task for which to retrieve metadata.

        Returns:
        TaskMetadata: A TaskMetadata object containing the metadata or an error.
        """
        self.logger.debug(
            f"Fetching metadata for task: {task_name} in directory: {self.working_directory}"
        )
        output, error = self.run_gradle_command(["gradle", "help", "--task", task_name])

        if error:
            self.logger.error(
                f"Failed to retrieve metadata for task '{task_name}': {error.error_message}"
            )
            return TaskMetadata(
                task_name=task_name, metadata="", success=False, error=error
            )

        if not output:
            self.logger.warning(f"No information returned for {task_name}")
            return TaskMetadata(
                task_name=task_name,
                metadata="",
                success=False,
                error=GradleError(f"No information returned for {task_name}", -1),
            )
        self.logger.debug(f"Metadata for task '{task_name}' retrieved successfully.")
        return TaskMetadata(task_name=task_name, metadata=output)

    def run_gradle_command(
        self, command: List[str], on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[str], Optional[GradleError]]:
        """
        Runs a Gradle command in the project's working directory using the subprocess module.

        Parameters:
        command (List[str]): The command to run as a list of strings.
        on_stdout (Optional[Callable[[str], None]]): Optional callback for stdout lines.
        on_stderr (Optional[Callable[[str], None]]): Optional callback for stderr lines.
        env_vars (Optional[Dict[str, str]]): Optional environment variables to merge.

        Returns:
        Tuple[Optional[str], Optional[GradleError]]: The output and any error that occurred.
        """
        try:
            self.logger.debug(
                f"Running command: {' '.join(command)} in {self.working_directory}"
            )
            env = os.environ.copy()

            # Merge custom environment variables
            if env_vars:
                self.logger.debug(f"Applying custom env vars: {env_vars}")
                env.update(env_vars)

            # If callbacks are provided, use streaming mode with Popen
            if on_stdout or on_stderr:
                return self._run_with_streaming(command, env, on_stdout, on_stderr)

            # Otherwise, use the simple subprocess.run approach
            result = subprocess.run(
                command,
                check=True,
                cwd=self.working_directory,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                close_fds=True
            )

            output = result.stdout.decode().strip()
            self.logger.debug(f"Command output: {output}")
            return output, None
        except PermissionError as e:
            self.logger.error(f"Permission denied when executing gradlew: {str(e)}")
            gradlew_path = os.path.join(self.working_directory, "gradlew")
            return None, GradleError(
                f"Permission denied: {gradlew_path} does not have execute permissions. "
                f"Run 'chmod +x gradlew' in the project directory.",
                -1
            )
        except FileNotFoundError:
            self.logger.error(
                "Gradle executable not found. Ensure it is installed and in PATH."
            )
            return None, GradleError("Gradle not found in PATH", -1)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed with error: {e.stderr.decode()}")
            return None, GradleError(e.stderr.decode(), e.returncode)

    def _run_with_streaming(
        self, command: List[str], env: dict,
        on_stdout: Optional[Callable[[str], None]],
        on_stderr: Optional[Callable[[str], None]]
    ) -> Tuple[Optional[str], Optional[GradleError]]:
        """
        Runs a command with streaming output via callbacks using threading.

        Parameters:
        command (List[str]): The command to run.
        env (dict): Environment variables.
        on_stdout (Optional[Callable[[str], None]]): Callback for stdout lines.
        on_stderr (Optional[Callable[[str], None]]): Callback for stderr lines.

        Returns:
        Tuple[Optional[str], Optional[GradleError]]: The output and any error.
        """
        try:
            process = subprocess.Popen(
                command,
                cwd=self.working_directory,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                universal_newlines=True,
                bufsize=1,
                close_fds=True
            )

            stdout_lines = []
            stderr_lines = []

            def read_stdout():
                for line in process.stdout:
                    line = line.rstrip()
                    stdout_lines.append(line)
                    if on_stdout:
                        on_stdout(line)

            def read_stderr():
                for line in process.stderr:
                    line = line.rstrip()
                    stderr_lines.append(line)
                    if on_stderr:
                        on_stderr(line)

            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.start()
            stderr_thread.start()

            # Wait for the process to complete
            return_code = process.wait()

            # Wait for threads to finish reading
            stdout_thread.join()
            stderr_thread.join()

            if return_code != 0:
                error_message = "\n".join(stderr_lines) if stderr_lines else "Command failed"
                self.logger.error(f"Command failed with return code {return_code}: {error_message}")
                return None, GradleError(error_message, return_code)

            output = "\n".join(stdout_lines)
            self.logger.debug(f"Command completed successfully")
            return output, None

        except PermissionError as e:
            self.logger.error(f"Permission denied when executing gradlew: {str(e)}")
            gradlew_path = os.path.join(self.working_directory, "gradlew")
            return None, GradleError(
                f"Permission denied: {gradlew_path} does not have execute permissions. "
                f"Run 'chmod +x gradlew' in the project directory.",
                -1
            )
        except FileNotFoundError:
            self.logger.error(
                "Gradle executable not found. Ensure it is installed and in PATH."
            )
            return None, GradleError("Gradle not found in PATH", -1)
        except Exception as e:
            self.logger.error(f"Command failed with error: {str(e)}")
            return None, GradleError(str(e), -1)

    def run_custom_gradle_task(
        self, task: str, options: Optional[List[str]] = None,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[str], Optional[GradleError]]:
        """
        Runs a custom Gradle task in the project's working directory with optional arguments.

        Parameters:
        task (str): The name of the task to run.
        options (list): Optional list of additional arguments for the task.
        on_stdout (Optional[Callable[[str], None]]): Optional callback for stdout lines.
        on_stderr (Optional[Callable[[str], None]]): Optional callback for stderr lines.
        env_vars (Optional[Dict[str, str]]): Optional environment variables to merge.

        Returns:
        Tuple[str, GradleError]: The output of the Gradle task as a string and an error object if one occurs.
        """
        command = ["./gradlew", task]
        if options:
            command.extend(options)

        self.logger.debug(
            f"Running custom Gradle task: {task} with options: {options} in directory: {self.working_directory}"
        )
        output, error = self.run_gradle_command(
            command, on_stdout=on_stdout, on_stderr=on_stderr, env_vars=env_vars
        )

        if error:
            self.logger.error(
                f"Failed to run custom task '{task}': {error.error_message}"
            )
        else:
            self.logger.debug(f"Custom task '{task}' ran successfully.")
        return output, error

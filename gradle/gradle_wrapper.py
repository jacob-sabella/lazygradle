import subprocess
import logging
from typing import Optional, Tuple, List
from dto import *

class GradleProjectManager:
    def __init__(self, working_directory: str):
        """
        Initialize the GradleProjectManager class with a specific working directory.
        
        Parameters:
        working_directory (str): The directory where the Gradle project resides.
        """
        self.working_directory = working_directory
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"GradleProjectManager initialized for directory: {self.working_directory}")

    def run_gradle_command(self, command: List[str]) -> Tuple[Optional[str], Optional[GradleError]]:
        """
        Runs a Gradle command in the project's working directory using the subprocess module.
        
        Parameters:
        command (list): A list containing the Gradle command and its arguments.
        
        Returns:
        Tuple[str, GradleError]: The output of the Gradle command as a string and an error object if one occurs.
        """
        try:
            self.logger.debug(f"Running command: {' '.join(command)} in {self.working_directory}")
            result = subprocess.run(command, check=True, cwd=self.working_directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode()
            self.logger.debug(f"Command output: {output}")
            return output, None
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed with error: {e.stderr.decode()}")
            return None, GradleError(e.stderr.decode(), e.returncode)

    def list_all_tasks(self) -> TaskList:
        """
        Lists all Gradle tasks in the project's working directory and returns a TaskList object.
        
        Returns:
        TaskList: A TaskList object containing a list of Task objects or an error.
        """
        self.logger.debug(f"Listing all Gradle tasks in directory: {self.working_directory}")
        output, error = self.run_gradle_command(["gradle", "tasks", "--all"])
        
        if error:
            self.logger.error(f"Failed to list tasks: {error.error_message}")
            return TaskList(tasks=[], success=False, error=error)
        
        if not output:
            self.logger.warn(f"No values in task output")
            return TaskList(tasks=[], success=False, error=GradleError("No values in task output", -1))

        # Process the output to extract tasks and descriptions
        tasks: List[Task] = []
        for line in output.splitlines():
            if line.strip() and not line.startswith(">") and not line.startswith("Deprecated"):
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
        self.logger.debug(f"Fetching metadata for task: {task_name} in directory: {self.working_directory}")
        output, error = self.run_gradle_command(["gradle", "help", "--task", task_name])
        
        if error:
            self.logger.error(f"Failed to retrieve metadata for task '{task_name}': {error.error_message}")
            return TaskMetadata(task_name=task_name, metadata="", success=False, error=error)
       
        if not output:
            self.logger.warning(f"No information returned for {task_name}")
            return TaskMetadata(task_name=task_name, metadata="", success=False, error=GradleError(f"No information returned for {task_name}", -1))
        self.logger.debug(f"Metadata for task '{task_name}' retrieved successfully.")
        return TaskMetadata(task_name=task_name, metadata=output)

    def run_custom_gradle_task(self, task: str, options: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[GradleError]]:
        """
        Runs a custom Gradle task in the project's working directory with optional arguments.
        
        Parameters:
        task (str): The name of the task to run.
        options (list): Optional list of additional arguments for the task.
        
        Returns:
        Tuple[str, GradleError]: The output of the Gradle task as a string and an error object if one occurs.
        """
        command = ["gradle", task]
        if options:
            command.extend(options)

        self.logger.debug(f"Running custom Gradle task: {task} with options: {options} in directory: {self.working_directory}")
        output, error = self.run_gradle_command(command)
        
        if error:
            self.logger.error(f"Failed to run custom task '{task}': {error.error_message}")
        else:
            self.logger.debug(f"Custom task '{task}' ran successfully.")
        return output, error



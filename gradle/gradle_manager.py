import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from gradle.gradle_wrapper import GradleWrapper, TaskList, TaskMetadata


class Task:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __getitem__(self, key: str):
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        setattr(self, key, value)


class Project:
    def __init__(self, tasks: Optional[List[Task]] = None, metadata: Optional[Dict[str, dict]] = None):
        self.tasks = tasks or []
        self.metadata = metadata or {}

    def __getitem__(self, key: str):
        if key == "tasks":
            return self.tasks
        elif key == "metadata":
            return self.metadata
        else:
            raise KeyError(f"{key} not found in Project.")

    def __setitem__(self, key: str, value):
        if key == "tasks":
            self.tasks = value
        elif key == "metadata":
            self.metadata = value
        else:
            raise KeyError(f"Cannot set value for {key}, not found in Project.")


class Config:
    def __init__(self, projects: Optional[Dict[str, Project]] = None, currently_selected: Optional[str] = None):
        self.projects = projects or {}
        self.currently_selected = currently_selected

    def __getitem__(self, key: str):
        return self.projects[key]

    def __setitem__(self, key: str, value: Project):
        self.projects[key] = value


class GradleManager:
    CONFIG_DIR = Path.home() / ".config/lazygradle"
    CONFIG_FILE = CONFIG_DIR / "gradle_cache.json"

    def __init__(self):
        """
        Initialize the GradleManager class, which manages Gradle projects and retains metadata in a config file.
        """
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logger()
        self.config = self._load_config()

        self.logger.debug("GradleManager initialized.")

    def _setup_logger(self):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        return logging.getLogger(__name__)

    def _load_config(self) -> Config:
        """
        Load the configuration file which contains previously used Gradle repositories.

        Returns:
        Config: A Config object with Gradle repositories and the currently selected project.
        """
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, "r") as f:
                self.logger.debug(f"Loading config from {self.CONFIG_FILE}")
                data = json.load(f)
                projects = {
                    key: Project(
                        tasks=[Task(**task) for task in value.get("tasks", [])],
                        metadata=value.get("metadata", {})
                    )
                    for key, value in data.get("projects", {}).items()
                }
                return Config(projects=projects, currently_selected=data.get("currently_selected"))
        else:
            self.logger.debug(f"No config found, creating a new one at {self.CONFIG_FILE}")
            return Config()

    def _save_config(self) -> None:
        """
        Save the current configuration to the config file.
        """
        config_dict = {
            "projects": {
                key: {
                    "tasks": [{"name": task.name, "description": task.description} for task in value.tasks],
                    "metadata": value.metadata,
                }
                for key, value in self.config.projects.items()
            },
            "currently_selected": self.config.currently_selected,
        }
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(config_dict, f, indent=4)
        self.logger.debug(f"Configuration saved to {self.CONFIG_FILE}")

    def add_project(self, project_dir: str) -> None:
        """
        Add a new Gradle project to the configuration and initialize its metadata.

        Parameters:
        project_dir (str): The directory of the Gradle project.
        """
        project_dir = os.path.abspath(project_dir)
        if project_dir not in self.config.projects:
            self.logger.debug(f"Adding new project: {project_dir}")
            self.config.projects[project_dir] = Project()

            # Set as the currently selected project if none is selected
            if not self.config.currently_selected:
                self.logger.debug(f"Setting {project_dir} as the currently selected project.")
                self.config.currently_selected = project_dir

            self._save_config()
        else:
            self.logger.debug(f"Project {project_dir} already exists in config.")

    def select_project(self, project_dir: str) -> None:
        """
        Select a project as the currently active one.

        Parameters:
        project_dir (str): The directory of the Gradle project to select.
        """
        project_dir = os.path.abspath(project_dir)
        if project_dir in self.config.projects:
            self.logger.debug(f"Selecting {project_dir} as the currently selected project.")
            self.config.currently_selected = project_dir
            self._save_config()
        else:
            self.logger.debug(f"Project {project_dir} not found in config.")

    def get_selected_project(self) -> Optional[str]:
        """
        Get the currently selected project.

        Returns:
        Optional[str]: The directory of the currently selected project, or None if no project is selected.
        """
        return self.config.currently_selected

    def update_project_tasks(self, project_dir: str) -> Optional[str]:
        """
        Update the task list for a specific project and store it in the config.

        Parameters:
        project_dir (str): The directory of the Gradle project.

        Returns:
        Optional[str]: Error message if an error occurs, else None.
        """
        self.logger.debug(f"Updating tasks for project: {project_dir}")
        gradle_manager = GradleWrapper(project_dir)
        task_list: TaskList = gradle_manager.list_all_tasks()

        if not task_list.success:
            return f"Failed to retrieve tasks for project {project_dir}: {task_list.error.error_message}"

        self.config.projects[project_dir].tasks = [Task(task.name, task.description) for task in task_list.tasks]
        self._save_config()
        self.logger.debug(f"Tasks updated for project {project_dir}")
        return None

    def update_task_metadata(self, project_dir: str, task_name: str) -> Optional[str]:
        """
        Update the metadata for a specific task in a project.

        Parameters:
        project_dir (str): The directory of the Gradle project.
        task_name (str): The name of the task to retrieve metadata for.

        Returns:
        Optional[str]: Error message if an error occurs, else None.
        """
        self.logger.debug(f"Updating metadata for task {task_name} in project: {project_dir}")
        gradle_manager = GradleWrapper(project_dir)
        task_metadata: TaskMetadata = gradle_manager.get_task_metadata(task_name)

        if not task_metadata.success:
            return f"Failed to retrieve metadata for task '{task_name}' in project {project_dir}: {task_metadata.error.error_message}"

        # Ensure project exists in the configuration
        if project_dir in self.config.projects:
            project = self.config.projects[project_dir]

            # Verify that task_metadata.metadata is a dictionary
            if isinstance(task_metadata.metadata, dict):
                project.metadata[task_name] = task_metadata.metadata  # Assign the metadata dict
                self._save_config()
                self.logger.debug(f"Metadata updated for task '{task_name}' in project {project_dir}")
                return None
            else:
                # Log and return an error if the metadata is not a dictionary
                self.logger.error(
                    f"Expected metadata to be a dictionary, but got {type(task_metadata.metadata)} instead.")
                return f"Invalid metadata format for task '{task_name}' in project {project_dir}."
        else:
            self.logger.debug(f"Project directory {project_dir} not found in config.")
            return f"Project directory {project_dir} not found."

    def get_project_info(self, project_dir: str) -> Optional[Project]:
        """
        Retrieve all stored data about a specific project.

        Parameters:
        project_dir (str): The directory of the Gradle project.

        Returns:
        Optional[Project]: The Project object containing the task list and metadata, or None if the project does not exist.
        """
        project_dir = os.path.abspath(project_dir)
        return self.config.projects.get(project_dir)

    def list_all_projects(self) -> Dict[str, Project]:
        """
        List all Gradle projects stored in the configuration.

        Returns:
        Dict[str, Project]: Dictionary containing all Gradle projects indexed by their directory.
        """
        return self.config.projects

    def run_task(self, task_name: str) -> Optional[str]:
        """
        Run a task from the currently selected project.

        Parameters:
        task_name (str): The name of the Gradle task to run.

        Returns:
        Optional[str]: The output of the Gradle task, or None if no project is selected.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to run the task.")
            return None

        gradle_wrapper = GradleWrapper(selected_project)
        output, error = gradle_wrapper.run_custom_gradle_task(task_name)

        if error:
            self.logger.error(
                f"Failed to run task '{task_name}' for project '{selected_project}': {error.error_message}")
            return f"Error: {error.error_message}"

        self.logger.debug(f"Task '{task_name}' executed successfully.")
        return output

    def run_task_with_parameters(self, task_name: str, parameters: List[str]) -> Optional[str]:
        """
        Run a task from the currently selected project with additional parameters.

        Parameters:
        task_name (str): The name of the Gradle task to run.
        parameters (List[str]): The list of parameters to pass to the Gradle task.

        Returns:
        Optional[str]: The output of the Gradle task, or None if no project is selected.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to run the task.")
            return None

        gradle_wrapper = GradleWrapper(selected_project)
        output, error = gradle_wrapper.run_custom_gradle_task(task_name, options=parameters)

        if error:
            self.logger.error(
                f"Failed to run task '{task_name}' with parameters '{parameters}' for project '{selected_project}': {error.error_message}")
            return f"Error: {error.error_message}"

        self.logger.debug(f"Task '{task_name}' with parameters '{parameters}' executed successfully.")
        return output


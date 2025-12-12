import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Callable
from datetime import datetime
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
    def __init__(self, tasks: Optional[List[Task]] = None, metadata: Optional[Dict[str, dict]] = None,
                 recent_tasks: Optional[List[Dict[str, str]]] = None,
                 saved_executions: Optional[List[Dict]] = None):
        self.tasks = tasks or []
        self.metadata = metadata or {}
        self.recent_tasks = recent_tasks or []  # List of {task_name, timestamp, parameters}
        self.saved_executions = saved_executions or []  # List of saved execution configurations

    def __getitem__(self, key: str):
        if key == "tasks":
            return self.tasks
        elif key == "metadata":
            return self.metadata
        elif key == "recent_tasks":
            return self.recent_tasks
        elif key == "saved_executions":
            return self.saved_executions
        else:
            raise KeyError(f"{key} not found in Project.")

    def __setitem__(self, key: str, value):
        if key == "tasks":
            self.tasks = value
        elif key == "metadata":
            self.metadata = value
        elif key == "recent_tasks":
            self.recent_tasks = value
        elif key == "saved_executions":
            self.saved_executions = value
        else:
            raise KeyError(f"Cannot set value for {key}, not found in Project.")


class Config:
    def __init__(self, projects: Optional[Dict[str, Project]] = None, currently_selected: Optional[str] = None, theme: Optional[str] = None):
        self.projects = projects or {}
        self.currently_selected = currently_selected
        self.theme = theme  # Store selected theme name

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
                        metadata=value.get("metadata", {}),
                        recent_tasks=value.get("recent_tasks", []),
                        saved_executions=value.get("saved_executions", [])
                    )
                    for key, value in data.get("projects", {}).items()
                }
                return Config(
                    projects=projects,
                    currently_selected=data.get("currently_selected"),
                    theme=data.get("theme")
                )
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
                    "recent_tasks": value.recent_tasks,
                    "saved_executions": value.saved_executions,
                }
                for key, value in self.config.projects.items()
            },
            "currently_selected": self.config.currently_selected,
            "theme": self.config.theme,
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

    def delete_project(self, project_dir: str) -> bool:
        """
        Delete a project from the configuration.

        Parameters:
        project_dir (str): The directory of the Gradle project to delete.

        Returns:
        bool: True if the project was deleted, False if it didn't exist.
        """
        project_dir = os.path.abspath(project_dir)
        if project_dir in self.config.projects:
            self.logger.debug(f"Deleting project: {project_dir}")
            del self.config.projects[project_dir]

            # If this was the currently selected project, clear the selection
            if self.config.currently_selected == project_dir:
                self.logger.debug(f"Clearing currently selected project")
                # Select another project if available
                remaining_projects = list(self.config.projects.keys())
                if remaining_projects:
                    self.config.currently_selected = remaining_projects[0]
                    self.logger.debug(f"Auto-selecting first remaining project: {self.config.currently_selected}")
                else:
                    self.config.currently_selected = None
                    self.logger.debug(f"No projects remaining, clearing selection")

            self._save_config()
            return True
        else:
            self.logger.debug(f"Project {project_dir} not found in config, cannot delete.")
            return False

    def get_selected_project(self) -> Optional[str]:
        """
        Get the currently selected project.

        Returns:
        Optional[str]: The directory of the currently selected project, or None if no project is selected.
        """
        return self.config.currently_selected

    def get_theme(self) -> Optional[str]:
        """
        Get the currently selected theme.

        Returns:
        Optional[str]: The name of the selected theme, or None if no theme is set.
        """
        return self.config.theme

    def set_theme(self, theme_name: str) -> None:
        """
        Set the selected theme and save to config.

        Parameters:
        theme_name (str): The name of the theme to set.
        """
        self.logger.debug(f"Setting theme to: {theme_name}")
        self.config.theme = theme_name
        self._save_config()

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

    def _record_task_execution(self, task_name: str, parameters: Optional[List[str]] = None) -> None:
        """
        Record a task execution in the recent tasks list for the current project.

        Parameters:
        task_name (str): The name of the task that was executed.
        parameters (Optional[List[str]]): The parameters passed to the task.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            return

        if selected_project not in self.config.projects:
            return

        project = self.config.projects[selected_project]

        # Create task execution record
        task_record = {
            "task_name": task_name,
            "timestamp": datetime.now().isoformat(),
            "parameters": " ".join(parameters) if parameters else ""
        }

        # Add to recent tasks (keep last 10)
        project.recent_tasks.insert(0, task_record)
        project.recent_tasks = project.recent_tasks[:10]

        self._save_config()
        self.logger.debug(f"Recorded task execution: {task_name}")

    def get_recent_tasks(self, project_dir: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get the list of recently run tasks for a project.

        Parameters:
        project_dir (Optional[str]): The project directory. If None, uses currently selected project.

        Returns:
        List[Dict[str, str]]: List of recent task records.
        """
        if project_dir is None:
            project_dir = self.get_selected_project()

        if not project_dir or project_dir not in self.config.projects:
            return []

        return self.config.projects[project_dir].recent_tasks

    def run_task(self, task_name: str, on_stdout: Optional[Callable[[str], None]] = None,
                 on_stderr: Optional[Callable[[str], None]] = None,
                 env_vars: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Run a task from the currently selected project.

        Parameters:
        task_name (str): The name of the Gradle task to run.
        on_stdout (Optional[Callable[[str], None]]): Optional callback for stdout lines.
        on_stderr (Optional[Callable[[str], None]]): Optional callback for stderr lines.
        env_vars (Optional[Dict[str, str]]): Optional environment variables to merge.

        Returns:
        Optional[str]: The output of the Gradle task, or None if no project is selected.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to run the task.")
            return None

        gradle_wrapper = GradleWrapper(selected_project)
        output, error = gradle_wrapper.run_custom_gradle_task(
            task_name, on_stdout=on_stdout, on_stderr=on_stderr, env_vars=env_vars
        )

        if error:
            self.logger.error(
                f"Failed to run task '{task_name}' for project '{selected_project}': {error.error_message}")
            return f"Error: {error.error_message}"

        self.logger.debug(f"Task '{task_name}' executed successfully.")
        self._record_task_execution(task_name)
        return output

    def run_task_with_parameters(self, task_name: str, parameters: List[str],
                                  on_stdout: Optional[Callable[[str], None]] = None,
                                  on_stderr: Optional[Callable[[str], None]] = None,
                                  env_vars: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Run a task from the currently selected project with additional parameters.

        Parameters:
        task_name (str): The name of the Gradle task to run.
        parameters (List[str]): The list of parameters to pass to the Gradle task.
        on_stdout (Optional[Callable[[str], None]]): Optional callback for stdout lines.
        on_stderr (Optional[Callable[[str], None]]): Optional callback for stderr lines.
        env_vars (Optional[Dict[str, str]]): Optional environment variables to merge.

        Returns:
        Optional[str]: The output of the Gradle task, or None if no project is selected.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to run the task.")
            return None

        gradle_wrapper = GradleWrapper(selected_project)
        output, error = gradle_wrapper.run_custom_gradle_task(
            task_name, options=parameters, on_stdout=on_stdout, on_stderr=on_stderr, env_vars=env_vars
        )

        if error:
            self.logger.error(
                f"Failed to run task '{task_name}' with parameters '{parameters}' for project '{selected_project}': {error.error_message}")
            return f"Error: {error.error_message}"

        self.logger.debug(f"Task '{task_name}' with parameters '{parameters}' executed successfully.")
        self._record_task_execution(task_name, parameters)
        return output

    def get_saved_executions(self, task_name: str, project_dir: Optional[str] = None) -> List[Dict]:
        """
        Get saved execution configurations for a specific task.

        Parameters:
        task_name (str): The name of the task to filter by.
        project_dir (Optional[str]): The project directory. Defaults to currently selected project.

        Returns:
        List[Dict]: List of saved execution configurations for the task.
        """
        if project_dir is None:
            project_dir = self.get_selected_project()

        if not project_dir or project_dir not in self.config.projects:
            return []

        all_saved = self.config.projects[project_dir].saved_executions
        return [s for s in all_saved if s.get("task_name") == task_name]

    def save_execution_config(self, task_name: str, label: str,
                              parameters: List[str], env_vars: Dict[str, str]) -> Optional[str]:
        """
        Save a task execution configuration.

        Parameters:
        task_name (str): The name of the task.
        label (str): User-provided label for this configuration.
        parameters (List[str]): List of parameters for the task.
        env_vars (Dict[str, str]): Environment variables for the task.

        Returns:
        Optional[str]: The ID of the saved configuration, or None if failed.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to save execution configuration.")
            return None

        execution_id = f"saved_{int(datetime.now().timestamp() * 1000)}"
        saved_config = {
            "id": execution_id,
            "label": label,
            "task_name": task_name,
            "parameters": parameters,
            "env_vars": env_vars,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }

        project = self.config.projects[selected_project]
        project.saved_executions.append(saved_config)
        self._save_config()
        self.logger.debug(f"Saved execution configuration '{label}' for task '{task_name}'.")
        return execution_id

    def update_saved_execution(self, execution_id: str, label: str,
                               parameters: List[str], env_vars: Dict[str, str]) -> bool:
        """
        Update an existing saved execution configuration.

        Parameters:
        execution_id (str): The ID of the configuration to update.
        label (str): New label for the configuration.
        parameters (List[str]): New list of parameters.
        env_vars (Dict[str, str]): New environment variables.

        Returns:
        bool: True if update was successful, False otherwise.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to update execution configuration.")
            return False

        project = self.config.projects[selected_project]
        for execution in project.saved_executions:
            if execution["id"] == execution_id:
                execution["label"] = label
                execution["parameters"] = parameters
                execution["env_vars"] = env_vars
                self._save_config()
                self.logger.debug(f"Updated execution configuration '{execution_id}'.")
                return True

        self.logger.warning(f"Execution configuration '{execution_id}' not found.")
        return False

    def delete_saved_execution(self, execution_id: str) -> bool:
        """
        Delete a saved execution configuration by ID.

        Parameters:
        execution_id (str): The ID of the configuration to delete.

        Returns:
        bool: True if deletion was successful, False otherwise.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            self.logger.error("No project selected to delete execution configuration.")
            return False

        project = self.config.projects[selected_project]
        original_length = len(project.saved_executions)
        project.saved_executions = [
            s for s in project.saved_executions if s["id"] != execution_id
        ]

        if len(project.saved_executions) < original_length:
            self._save_config()
            self.logger.debug(f"Deleted execution configuration '{execution_id}'.")
            return True

        self.logger.warning(f"Execution configuration '{execution_id}' not found.")
        return False

    def mark_saved_execution_used(self, execution_id: str) -> None:
        """
        Update the last_used timestamp for a saved execution configuration.

        Parameters:
        execution_id (str): The ID of the configuration.
        """
        selected_project = self.get_selected_project()
        if not selected_project:
            return

        project = self.config.projects[selected_project]
        for execution in project.saved_executions:
            if execution["id"] == execution_id:
                execution["last_used"] = datetime.now().isoformat()
                self._save_config()
                self.logger.debug(f"Marked execution configuration '{execution_id}' as used.")
                break


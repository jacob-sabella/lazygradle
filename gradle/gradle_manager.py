import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from gradle_wrapper import GradleProjectManager, TaskList, TaskMetadata

class GradleManager:
    CONFIG_DIR = Path.home() / ".config/lazygit"
    CONFIG_FILE = CONFIG_DIR / "gradle_cache.json"
    
    def __init__(self):
        """
        Initialize the GradleManager class, which manages Gradle projects and retains metadata in a config file.
        """
        # Ensure the config directory exists
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Set up logger
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.config = self._load_config()
        self.logger.debug("GradleManager initialized.")
    
    def _load_config(self) -> Dict[str, dict]:
        """
        Load the configuration file which contains previously used Gradle repositories.
        
        Returns:
        dict: A dictionary of Gradle repositories indexed by their directory.
        """
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, "r") as f:
                self.logger.debug(f"Loading config from {self.CONFIG_FILE}")
                return json.load(f)
        self.logger.debug(f"No config found, creating a new one at {self.CONFIG_FILE}")
        return {}
    
    def _save_config(self) -> None:
        """
        Save the current configuration to the config file.
        """
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
        self.logger.debug(f"Configuration saved to {self.CONFIG_FILE}")
    
    def add_project(self, project_dir: str) -> None:
        """
        Add a new Gradle project to the configuration and initialize its metadata.
        
        Parameters:
        project_dir (str): The directory of the Gradle project.
        """
        project_dir = os.path.abspath(project_dir)
        if project_dir not in self.config:
            self.logger.debug(f"Adding new project: {project_dir}")
            self.config[project_dir] = {
                "tasks": [],
                "metadata": {}
            }
            self._save_config()
        else:
            self.logger.debug(f"Project {project_dir} already exists in config.")
    
    def update_project_tasks(self, project_dir: str) -> Optional[str]:
        """
        Update the task list for a specific project and store it in the config.
        
        Parameters:
        project_dir (str): The directory of the Gradle project.
        
        Returns:
        Optional[str]: Error message if an error occurs, else None.
        """
        self.logger.debug(f"Updating tasks for project: {project_dir}")
        gradle_manager = GradleProjectManager(project_dir)
        task_list: TaskList = gradle_manager.list_all_tasks()
        
        if not task_list.success:
            return f"Failed to retrieve tasks for project {project_dir}: {task_list.error.error_message}"
        
        self.config[project_dir]["tasks"] = [{"name": task.name, "description": task.description} for task in task_list.tasks]
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
        gradle_manager = GradleProjectManager(project_dir)
        task_metadata: TaskMetadata = gradle_manager.get_task_metadata(task_name)
        
        if not task_metadata.success:
            return f"Failed to retrieve metadata for task '{task_name}' in project {project_dir}: {task_metadata.error.error_message}"
        
        self.config[project_dir]["metadata"][task_name] = task_metadata.metadata
        self._save_config()
        self.logger.debug(f"Metadata updated for task '{task_name}' in project {project_dir}")
        return None
    
    def get_project_info(self, project_dir: str) -> Optional[dict]:
        """
        Retrieve all stored data about a specific project.
        
        Parameters:
        project_dir (str): The directory of the Gradle project.
        
        Returns:
        Optional[dict]: Dictionary containing the task list and metadata, or None if the project does not exist.
        """
        project_dir = os.path.abspath(project_dir)
        return self.config.get(project_dir)
    
    def list_all_projects(self) -> Dict[str, dict]:
        """
        List all Gradle projects stored in the configuration.
        
        Returns:
        Dict[str, dict]: Dictionary containing all Gradle projects indexed by their directory.
        """
        return self.config


if __name__ == "__main__":
    manager = GradleManager()
    
    # Example usage:
    project_path = "/home/soulofset/Documents/projects/sockbowl-game"
    
    # Add a project
    manager.add_project(project_path)
    
    # Update the tasks for the project
    error = manager.update_project_tasks(project_path)
    if error:
        print(error)
    
    # Retrieve the tasks and metadata
    project_info = manager.get_project_info(project_path)
    if project_info:
        print(f"Tasks for project {project_path}: {project_info['tasks']}")
        
        # Update metadata for a specific task
        task_name = project_info['tasks'][0]['name'] if project_info['tasks'] else None
        if task_name:
            error = manager.update_task_metadata(project_path, task_name)
            if error:
                print(error)
            else:
                print(f"Metadata for task {task_name}: {project_info['metadata'][task_name]}")
    
    # List all projects
    all_projects = manager.list_all_projects()
    print(f"All stored projects: {all_projects}")


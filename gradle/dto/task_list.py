from typing import List, Optional

from gradle.dto.gradle_error import GradleError
from gradle.dto.task import Task


class TaskList:
    """
    Represents the list of Gradle tasks in the project.
    """
    def __init__(self, tasks: List[Task], success: bool = True, error: Optional['GradleError'] = None) -> None:
        self.tasks: List[Task] = tasks  # A list of Task objects
        self.success: bool = success
        self.error: Optional[GradleError] = error  # Will hold a GradleError if there's an error

from typing import Optional
from .gradle_error import GradleError

class TaskMetadata:
    """
    Represents metadata about a specific Gradle task.
    """
    def __init__(self, task_name: str, metadata: str, success: bool = True, error: Optional[GradleError] = None) -> None:
        self.task_name: str = task_name
        self.metadata: str = metadata  # The detailed metadata as a string
        self.success: bool = success
        self.error: Optional[GradleError] = error  # Will hold a GradleError if there's an error


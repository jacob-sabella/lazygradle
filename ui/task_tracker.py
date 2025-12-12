import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrackedTask:
    """Represents a tracked Gradle task execution."""
    task_id: str  # Unique identifier
    task_name: str
    parameters: List[str]
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output_lines: List[str] = field(default_factory=list)
    asyncio_task: Optional[asyncio.Task] = None  # Reference to running asyncio task
    config_label: Optional[str] = None  # Label of saved config if used

    def get_display_name(self) -> str:
        """Get formatted display name for the task."""
        base_name = self.task_name
        if self.parameters:
            base_name = f"{self.task_name} {' '.join(self.parameters)}"

        # Add config label if present (escaped for Rich markup)
        if self.config_label:
            return f"{base_name} ({self.config_label})"
        return base_name

    def get_duration(self) -> str:
        """Get formatted duration string."""
        end = self.end_time or datetime.now()
        duration = (end - self.start_time).total_seconds()

        if duration < 60:
            return f"{int(duration)}s"
        elif duration < 3600:
            minutes = int(duration / 60)
            seconds = int(duration % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(duration / 3600)
            minutes = int((duration % 3600) / 60)
            return f"{hours}h {minutes}m"


class TaskTracker:
    """Manages tracking of running and completed Gradle tasks."""

    def __init__(self, max_history: int = 50):
        self.tasks: List[TrackedTask] = []
        self.max_history = max_history
        self._task_counter = 0
        self._update_callback: Optional[Callable] = None

    def set_update_callback(self, callback: Callable):
        """Set callback to be called when tasks are updated."""
        self._update_callback = callback

    def _notify_update(self):
        """Notify listeners that tasks have been updated."""
        if self._update_callback:
            try:
                self._update_callback()
            except Exception as e:
                logging.error(f"Error in update callback: {e}")

    def create_task(self, task_name: str, parameters: List[str] = None, config_label: str = None) -> TrackedTask:
        """Create a new tracked task and add it to the list."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}_{int(datetime.now().timestamp())}"

        task = TrackedTask(
            task_id=task_id,
            task_name=task_name,
            parameters=parameters or [],
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            config_label=config_label
        )

        # Add to beginning of list (most recent first)
        self.tasks.insert(0, task)

        # Limit history
        if len(self.tasks) > self.max_history:
            self.tasks = self.tasks[:self.max_history]

        self._notify_update()
        logging.info(f"Created tracked task: {task_id} - {task.get_display_name()}")
        return task

    def get_task(self, task_id: str) -> Optional[TrackedTask]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def append_output(self, task_id: str, line: str):
        """Append an output line to a task."""
        task = self.get_task(task_id)
        if task:
            task.output_lines.append(line)
            self._notify_update()

    def mark_completed(self, task_id: str):
        """Mark a task as completed."""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            self._notify_update()
            logging.info(f"Task completed: {task_id} - {task.get_display_name()}")

    def mark_failed(self, task_id: str, error_message: str = None):
        """Mark a task as failed."""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.end_time = datetime.now()
            if error_message:
                task.output_lines.append(f"[ERROR] {error_message}")
            self._notify_update()
            logging.info(f"Task failed: {task_id} - {task.get_display_name()}")

    def mark_cancelled(self, task_id: str):
        """Mark a task as cancelled."""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            task.end_time = datetime.now()
            self._notify_update()
            logging.info(f"Task cancelled: {task_id} - {task.get_display_name()}")

    def set_asyncio_task(self, task_id: str, asyncio_task: asyncio.Task):
        """Set the asyncio task for cancellation support."""
        task = self.get_task(task_id)
        if task:
            task.asyncio_task = asyncio_task
            logging.debug(f"Set asyncio task for {task_id}")

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task. Returns True if cancelled, False otherwise."""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING and task.asyncio_task:
            logging.info(f"Cancelling task: {task_id} - {task.get_display_name()}")
            task.asyncio_task.cancel()
            task.output_lines.append("[bold yellow]⚠ Task cancelled by user[/bold yellow]")
            self.mark_cancelled(task_id)
            return True
        return False

    def get_running_tasks(self) -> List[TrackedTask]:
        """Get all currently running tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.RUNNING]

    def get_completed_tasks(self) -> List[TrackedTask]:
        """Get all completed/failed tasks."""
        return [t for t in self.tasks if t.status != TaskStatus.RUNNING]

    def get_all_tasks(self) -> List[TrackedTask]:
        """Get all tasks (running first, then history)."""
        return self.tasks

    def clear_history(self):
        """Clear all completed/failed tasks."""
        self.tasks = [t for t in self.tasks if t.status == TaskStatus.RUNNING]
        self._notify_update()

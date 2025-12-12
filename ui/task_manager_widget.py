import logging
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static, OptionList, RichLog, Button
from textual.widgets._option_list import Option

from ui.task_tracker import TaskTracker, TaskStatus, TrackedTask


class TaskManagerWidget(Widget):
    """Widget for displaying task execution history and output."""

    BINDINGS = [
        Binding("c", "cancel_task", "Cancel Task"),
        Binding("C", "cancel_task", "Cancel Task"),
    ]

    def __init__(self, task_tracker: TaskTracker, **kwargs):
        super().__init__(**kwargs)
        self.task_tracker = task_tracker
        self.selected_task_id = None
        self.task_list = None
        self.output_log = None

        # Set callback for task updates
        self.task_tracker.set_update_callback(self._on_tasks_updated)

    def compose(self) -> ComposeResult:
        """Compose the task manager layout."""
        with Horizontal(classes="task-manager-container"):
            # Left panel: Task list
            with Vertical(classes="task-list-panel"):
                yield Static("Task History", classes="section-title")
                yield Button("Clear History", id="clear-history-btn", variant="warning", classes="clear-history-button")
                self.task_list = OptionList(id="task-list", classes="task-manager-list")
                yield self.task_list

            # Right panel: Task output
            with Vertical(classes="task-output-panel"):
                yield Static("Task Output", id="task-output-title", classes="section-title")
                with VerticalScroll(classes="task-output-scroll"):
                    self.output_log = RichLog(
                        id="task-manager-log",
                        highlight=True,
                        markup=False,
                        wrap=True,
                        auto_scroll=True,
                        classes="task-manager-output"
                    )
                    yield self.output_log

    def on_mount(self) -> None:
        """Initialize the widget when mounted."""
        self._refresh_task_list()

    def _on_tasks_updated(self):
        """Callback when tasks are updated."""
        if not self.is_mounted:
            return

        try:
            # Refresh the task list
            self._refresh_task_list()

            # If a task is selected, refresh its output
            if self.selected_task_id:
                self._refresh_output()
        except Exception as e:
            logging.error(f"Error updating task manager: {e}", exc_info=True)

    def _refresh_task_list(self):
        """Refresh the task list display."""
        if not self.task_list:
            return

        # Remember current selection
        current_selection = self.selected_task_id

        # Clear and rebuild list
        self.task_list.clear_options()

        # Separate running and completed tasks
        running_tasks = self.task_tracker.get_running_tasks()
        completed_tasks = self.task_tracker.get_completed_tasks()

        if not running_tasks and not completed_tasks:
            self.task_list.add_option(Option(
                "[dim]No tasks run yet[/dim]",
                id="no-tasks",
                disabled=True
            ))
            return

        # Add running tasks section
        if running_tasks:
            self.task_list.add_option(Option(
                "[bold]Running Tasks[/bold]",
                id="running-header",
                disabled=True
            ))
            for task in running_tasks:
                status_icon = self._get_status_icon(task.status)
                duration = task.get_duration()
                display_name = task.get_display_name()
                label = f"{status_icon} [bold cyan]{display_name}[/bold cyan] - {duration}"
                self.task_list.add_option(Option(label, id=task.task_id))

        # Add separator if we have both sections
        if running_tasks and completed_tasks:
            self.task_list.add_option(Option(
                "[dim]" + "─" * 40 + "[/dim]",
                id="separator",
                disabled=True
            ))

        # Add history section
        if completed_tasks:
            self.task_list.add_option(Option(
                "[bold]History[/bold]",
                id="history-header",
                disabled=True
            ))
            for task in completed_tasks:
                status_icon = self._get_status_icon(task.status)
                duration = task.get_duration()
                display_name = task.get_display_name()

                if task.status == TaskStatus.COMPLETED:
                    label = f"{status_icon} {display_name} - {duration}"
                elif task.status == TaskStatus.FAILED:
                    label = f"{status_icon} [red]{display_name}[/red] - {duration}"
                else:
                    label = f"{status_icon} {display_name} - {duration}"

                self.task_list.add_option(Option(label, id=task.task_id))

        # Restore selection if possible
        if current_selection:
            try:
                # Search in running tasks first
                for idx, task in enumerate(running_tasks):
                    if task.task_id == current_selection:
                        # Position = "Running Tasks" header (1) + task index
                        actual_idx = 1 + idx
                        self.task_list.highlighted = actual_idx
                        return

                # Search in completed tasks
                for idx, task in enumerate(completed_tasks):
                    if task.task_id == current_selection:
                        # Position = headers + running tasks + separators
                        actual_idx = 0
                        if running_tasks:
                            actual_idx += 1  # "Running Tasks" header
                            actual_idx += len(running_tasks)  # all running tasks
                            actual_idx += 1  # separator
                        actual_idx += 1  # "History" header
                        actual_idx += idx  # position in completed tasks
                        self.task_list.highlighted = actual_idx
                        return
            except Exception as e:
                logging.debug(f"Could not restore selection: {e}")

    def _get_status_icon(self, status: TaskStatus) -> str:
        """Get icon for task status."""
        if status == TaskStatus.RUNNING:
            return "▶"
        elif status == TaskStatus.COMPLETED:
            return "✓"
        elif status == TaskStatus.FAILED:
            return "✗"
        elif status == TaskStatus.CANCELLED:
            return "⚠"
        return "•"

    def _refresh_output(self):
        """Refresh the output display for the selected task."""
        if not self.output_log or not self.selected_task_id:
            return

        task = self.task_tracker.get_task(self.selected_task_id)
        if not task:
            return

        # Clear and redisplay all output
        self.output_log.clear()

        # Header
        self.output_log.write(f"Task: {task.get_display_name()}")
        self.output_log.write(f"Started: {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if task.end_time:
            self.output_log.write(f"Ended: {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.output_log.write(f"Duration: {task.get_duration()}")
        self.output_log.write(f"Status: {task.status.value.upper()}")
        self.output_log.write("=" * 80)
        self.output_log.write("")

        # Output lines
        for line in task.output_lines:
            self.output_log.write(line)

        # Update title
        try:
            title = self.query_one("#task-output-title", Static)
            title.update(f"Task Output - {task.get_display_name()}")
        except Exception as e:
            logging.debug(f"Could not update title: {e}")


    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handle task selection."""
        # Skip non-task items (headers, separators)
        skip_ids = {"no-tasks", "running-header", "separator", "history-header"}
        if event.option_list.id == "task-list" and event.option.id not in skip_ids:
            self.selected_task_id = event.option.id
            self._refresh_output()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        """Handle task highlighting with keyboard."""
        # Skip non-task items (headers, separators)
        skip_ids = {"no-tasks", "running-header", "separator", "history-header"}
        if event.option_list.id == "task-list" and event.option.id not in skip_ids:
            self.selected_task_id = event.option.id
            self._refresh_output()

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "clear-history-btn":
            self.task_tracker.clear_history()
            self.selected_task_id = None
            self._refresh_task_list()

            # Clear output
            if self.output_log:
                self.output_log.clear()
                self.output_log.write("Select a task to view its output")

            try:
                title = self.query_one("#task-output-title", Static)
                title.update("Task Output")
            except:
                pass

    def append_output_to_task(self, task_id: str, line: str):
        """Append output to a specific task and update display if selected."""
        self.task_tracker.append_output(task_id, line)

        # If this is the currently selected task, append to display
        if task_id == self.selected_task_id and self.output_log:
            self.output_log.write(line)

    def select_task(self, task_id: str):
        """Programmatically select a task by ID."""
        if not self.is_mounted or not self.task_list:
            # Store for later if not mounted yet
            self.selected_task_id = task_id
            return

        # Find the task index
        tasks = self.task_tracker.get_all_tasks()
        for idx, task in enumerate(tasks):
            if task.task_id == task_id:
                try:
                    self.task_list.highlighted = idx
                    self.selected_task_id = task_id
                    self._refresh_output()
                    logging.info(f"Auto-selected task: {task_id}")
                    break
                except Exception as e:
                    logging.error(f"Error selecting task: {e}")

    def action_cancel_task(self):
        """Cancel the currently selected running task."""
        if not self.selected_task_id:
            logging.info("No task selected to cancel")
            return

        task = self.task_tracker.get_task(self.selected_task_id)
        if not task:
            logging.error("Selected task not found")
            return

        if task.status != TaskStatus.RUNNING:
            logging.info(f"Cannot cancel task with status: {task.status}")
            return

        # Attempt to cancel
        if self.task_tracker.cancel_task(self.selected_task_id):
            logging.info(f"Successfully cancelled task: {self.selected_task_id}")
            # Refresh output to show cancellation message
            self._refresh_output()
        else:
            logging.warning(f"Failed to cancel task: {self.selected_task_id}")

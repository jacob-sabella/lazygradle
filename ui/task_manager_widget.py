import logging
from rich.markup import escape
from textual.app import ComposeResult
from textual import events
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static, OptionList, Button
from textual.widgets._option_list import Option

from ui.task_tracker import TaskTracker, TaskStatus
from ui.task_output_viewer import TaskOutputViewer


class TaskManagerWidget(Widget):
    """Widget for displaying task execution history and output."""

    BINDINGS = [
        Binding("c", "cancel_task", "Cancel Task"),
        Binding("C", "clear_history", "Clear History"),
        Binding("ctrl+h", "focus_left_pane", show=False, priority=True),
        Binding("ctrl+j", "focus_down_pane", show=False, priority=True),
        Binding("ctrl+k", "focus_up_pane", show=False, priority=True),
        Binding("ctrl+l", "focus_right_pane", show=False, priority=True),
        Binding("ctrl+left", "focus_left_pane", show=False, priority=True),
        Binding("ctrl+down", "focus_down_pane", show=False, priority=True),
        Binding("ctrl+up", "focus_up_pane", show=False, priority=True),
        Binding("ctrl+right", "focus_right_pane", show=False, priority=True),
    ]

    def __init__(self, task_tracker: TaskTracker, **kwargs):
        super().__init__(**kwargs)
        self.task_tracker = task_tracker
        self.selected_task_id = None
        self.task_list = None
        self.output_log = None
        self.output_status = None
        # Only panes that exist in the Task Manager tab.
        self.details_scroll = None
        self.saved_executions_list = None
        self.recent_tasks_list = None
        self.task_list_panel = None
        self.task_output_panel = None
        self._status_clear_timer = None

        # Set callback for task updates
        self.task_tracker.set_update_callback(self._on_tasks_updated)

    def compose(self) -> ComposeResult:
        """Compose the task manager layout."""
        with Horizontal(classes="task-manager-container"):
            # Left panel: Task list
            with Vertical(classes="task-list-panel") as task_list_panel:
                self.task_list_panel = task_list_panel
                yield Static("Task History", classes="section-title")
                yield Button("Clear History", id="clear-history-btn", variant="warning", classes="clear-history-button")
                self.task_list = OptionList(id="task-list", classes="task-manager-list")
                yield self.task_list

            # Right panel: Task output
            with Vertical(classes="task-output-panel") as task_output_panel:
                self.task_output_panel = task_output_panel
                yield Static("Task Output", id="task-output-title", classes="section-title")
                self.output_status = Static(
                    "Output viewer has Vim-style motions; press v/y to select/yank.",
                    id="task-output-status",
                    classes="task-output-status",
                )
                yield self.output_status
                self.output_log = TaskOutputViewer(
                    id="task-manager-log",
                    classes="task-manager-output",
                    on_status=self._set_output_status,
                    focus_router=self._focus_output_neighbor,
                    on_state_change=self._update_output_guide,
                )
                yield self.output_log

    def on_click(self, event: events.Click) -> None:
        control = event.control
        if self._is_descendant(control, self.task_list_panel) and self.task_list:
            self.task_list.focus()
            return
        if self._is_descendant(control, self.task_output_panel) and self.output_log:
            self.output_log.focus()
            return

    @staticmethod
    def _is_descendant(control, ancestor) -> bool:
        if not control or not ancestor:
            return False
        widget = control
        while widget is not None:
            if widget is ancestor:
                return True
            widget = getattr(widget, "parent", None)
        return False

    def on_mount(self) -> None:
        """Initialize the widget when mounted."""
        if self.output_log:
            self.output_log.set_config(
                self.task_tracker.gradle_manager.get_output_settings()
                if hasattr(self.task_tracker, "gradle_manager")
                else None
            )
            self.output_log.set_lines(["Select a task to view its output"])
        self._update_output_guide()
        self._refresh_task_list()
        if self.task_list:
            self.task_list.focus()

    def _output_guide_text(self) -> str:
        viewer = self.output_log
        if not viewer:
            return ""
        in_output = self.app and getattr(self.app, "focused", None) is viewer
        if viewer.visual_mode:
            prefix = "VISUAL" if in_output else "VISUAL (output)"
            return (
                f"[dim]{prefix}: j/k or arrows move, y yank selection, Esc exit, v toggle[/]"
            )
        prefix = "OUTPUT" if in_output else "OUTPUT (focus)"
        return (
            f"[dim]{prefix}: j/k or arrows move, h/l or arrows scroll, v visual, yy yank line, +/- zoom (readability)[/]"
        )

    def _update_output_guide(self) -> None:
        if not self.output_status:
            return
        self.output_status.update(self._output_guide_text())
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
                display_name = escape(task.get_display_name())
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
                display_name = escape(task.get_display_name())

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

        # Header
        lines = [
            f"Task: {escape(task.get_display_name())}",
            f"Started: {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if task.end_time:
            lines.append(f"Ended: {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        lines.extend(
            [
                f"Duration: {task.get_duration()}",
                f"Status: {task.status.value.upper()}",
                "=" * 80,
                "",
            ]
        )

        # Output lines
        lines.extend(task.output_lines)
        previous_task_id = self.output_log.task_context.get("task_id")
        if previous_task_id != task.task_id:
            self.output_log.clear()
            self.output_log.current_line = max(len(lines) - 1, 0)
        self.output_log.set_context(
            task_id=task.task_id,
            task_name=task.task_name,
            project_path=getattr(self.task_tracker, "project_path", None),
        )
        self.output_log.set_lines(lines)

        # Update title
        try:
            title = self.query_one("#task-output-title", Static)
            title.update(f"Task Output - {escape(task.get_display_name())}")
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
            self.action_clear_history()

    def append_output_to_task(self, task_id: str, line: str):
        """Append output to a specific task and update display if selected."""
        self.task_tracker.append_output(task_id, line)

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
                    if self.output_log:
                        self.output_log.focus()
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

    def action_clear_history(self):
        self.task_tracker.clear_history()
        self.selected_task_id = None
        self._refresh_task_list()

        if self.output_log:
            self.output_log.clear()
            self.output_log.set_lines(["Select a task to view its output"])

        try:
            title = self.query_one("#task-output-title", Static)
            title.update("Task Output")
        except Exception:
            pass

    def action_focus_left_pane(self):
        if self.task_list:
            self.task_list.focus()

    def action_focus_right_pane(self):
        if self.output_log:
            self.output_log.focus()

    def action_focus_up_pane(self):
        self._cycle_focus(-1)

    def action_focus_down_pane(self):
        self._cycle_focus(1)

    def _cycle_focus(self, delta: int) -> None:
        order = [pane for pane in (self.task_list, self.output_log) if pane]
        if not order:
            return

        focused = self.app.focused if self.app else None
        current_idx = -1
        for idx, pane in enumerate(order):
            if pane is focused:
                current_idx = idx
                break

        next_idx = (current_idx + delta) % len(order)
        order[next_idx].focus()

    def _focus_output_neighbor(self, direction: str) -> None:
        if direction in {"h", "k"} and self.task_list:
            self.task_list.focus()
        elif direction in {"l", "j"} and self.output_log:
            self.output_log.focus()

    def _set_output_status(self, message: str, is_error: bool) -> None:
        if not self.output_status:
            return
        style = "bold red" if is_error else "dim"
        self.output_status.update(f"[{style}]{escape(message)}[/]")

        # Make status lines transient so they don't stick around forever.
        if self._status_clear_timer and hasattr(self._status_clear_timer, "stop"):
            self._status_clear_timer.stop()
        delay = 5 if is_error else 2
        if hasattr(self, "set_timer"):
            self._status_clear_timer = self.set_timer(delay, self._clear_output_status)

    def _clear_output_status(self) -> None:
        self._update_output_guide()

"""Gradle project task viewer widget.

This module provides the main task management interface for viewing, searching,
and executing Gradle tasks. It includes task list display, search functionality,
task execution with streaming output, and recent task history.
"""

import logging
import asyncio
import re

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.widgets import Static, Label, OptionList, Button, Input
from textual.widgets._option_list import Option

from ui.run_task_with_parameters_modal import RunTaskWithParametersModal
from ui.confirmation_modal import ConfirmationModal
from gradle.gradle_manager import GradleManager
from ui.task_tracker import TaskTracker


class GradleProjectTaskViewer(Static):
    """Widget for viewing and executing Gradle tasks.

    Provides a two-panel interface with task list on the left and task details on the
    right. Supports task search, keyboard navigation, task execution with or without
    parameters, and displays recent task history. All task executions run in background
    threads with real-time output streaming to maintain UI responsiveness.

    Attributes:
        gradle_manager: Manager for Gradle project operations.
        parent_widget: Reference to LazyGradleWidget for tab navigation.
        task_tracker: Tracker for task execution history and status.
        tasks: Complete list of available Gradle tasks.
        filtered_tasks: Tasks matching the current search filter.
        selected_task: Currently selected task for execution.
        is_refreshing: Flag to prevent concurrent task list refreshes.
        running_task: Reference to currently executing background task.
    """

    BINDINGS = [
        Binding("r", "run_task", "Run Task"),
        Binding("enter", "run_task", "Run Task"),
        Binding("R", "run_task_with_parameters", "Run Task with Parameters"),
        Binding("/", "focus_search", "Search Tasks"),
        Binding("f5", "refresh_tasks", "Refresh Tasks")
    ]

    def __init__(self, gradle_manager: GradleManager, parent_widget, task_tracker: TaskTracker, **kwargs):
        """Initialize the task viewer widget.

        Args:
            gradle_manager: GradleManager instance for Gradle operations.
            parent_widget: Reference to parent LazyGradleWidget for tab navigation.
            task_tracker: TaskTracker instance for managing task execution history.
            **kwargs: Additional arguments passed to the Static widget constructor.
        """
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.parent_widget = parent_widget
        self.task_tracker = task_tracker
        self.tasks = []
        self.filtered_tasks = []
        self.selected_task = None
        self.search_input = Input(placeholder="Search tasks... (press / to focus)", classes="task-search")
        self.task_option_list = None
        self.task_name_label = Static("", classes="task-name-label")
        self.description_widget = Static("Select a task from the list to view its description.",
                                         classes="task-description-text")
        self.recent_tasks_list = None
        self.saved_executions_list = None
        self.running_task = None
        self.is_refreshing = False

    def compose(self) -> ComposeResult:
        """Compose the task viewer layout.

        Creates a two-panel layout with task list and details if a project is selected,
        or displays a warning message if no project is available. Task list starts empty
        and will be populated during the mount lifecycle.

        Yields:
            Horizontal container with task list and details panels, or a Label widget
            if no project is selected.
        """
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            logging.debug(f"Composing task viewer for {selected_project}")
            self.tasks = []
            self.filtered_tasks = []

            yield Horizontal(
                Vertical(
                    Static("Available Tasks", classes="section-title"),
                    self.search_input,
                    self.render_task_list(),
                    classes="task-list-panel"
                ),
                Vertical(
                    Static("Task Details", classes="section-title"),
                    VerticalScroll(
                        self.task_name_label,
                        self.description_widget,
                        classes="task-details-scroll"
                    ),
                    self.render_buttons(),
                    Static("Saved Configurations", classes="section-title saved-configs-title"),
                    self.render_saved_executions(),
                    self.render_saved_execution_buttons(),
                    Static("Recently Run Tasks", classes="section-title recent-tasks-title"),
                    self.render_recent_tasks(),
                    classes="task-details-panel"
                ),
                classes="main-content"
            )
        else:
            yield Label("No project selected.", classes="no-project")

    def on_mount(self) -> None:
        """Trigger background task refresh after widget is mounted.

        Schedules an automatic refresh of the task list after the UI is fully rendered
        to populate the initially empty task list with current Gradle tasks.
        Only refreshes if tasks haven't been cached in GradleManager yet.
        """
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            # Check if GradleManager already has cached tasks for this project
            project_info = self.gradle_manager.get_project_info(selected_project)
            if project_info and project_info.tasks:
                # Load cached tasks without refreshing
                logging.debug(f"Loading {len(project_info.tasks)} cached tasks from GradleManager")
                self.tasks = sorted(project_info.tasks, key=self._task_sort_key)
                self._update_tasks_after_refresh("")
            else:
                # No cached tasks, trigger a refresh
                logging.debug("No cached tasks found, scheduling task list refresh after mount")
                self.call_after_refresh(lambda: asyncio.create_task(self.action_refresh_tasks()))

    def render_task_list(self):
        """Create and populate the task list widget.

        Builds an OptionList widget containing filtered tasks. If no tasks are available,
        displays a loading placeholder that will be replaced after the background refresh
        completes.

        Returns:
            OptionList widget populated with task names or a loading indicator.
        """
        self.task_option_list = OptionList(id="task-option-list", classes="task-option-list")
        logging.debug(f"Rendering {len(self.filtered_tasks)} tasks to option list")

        if len(self.filtered_tasks) == 0:
            self.task_option_list.add_option(
                Option("[dim]Loading tasks...[/dim]", disabled=True)
            )
        else:
            for task in self.filtered_tasks:
                self.task_option_list.add_option(Option(task.name))
                logging.debug(f"Added task: {task.name}")
        return self.task_option_list

    @staticmethod
    def render_buttons():
        """Create the task action buttons panel.

        Builds a horizontal container with buttons for running tasks with or without
        parameters. Button labels include keyboard shortcut hints.

        Returns:
            Horizontal container with Run Task and Run with Params buttons.
        """
        return Horizontal(
            Button("▶ Run Task (r)", id="run_task_button", variant="success", classes="action-button"),
            Button("⚙ Run with Params (R)", id="run_task_with_params_button", variant="primary", classes="action-button"),
            classes="task-actions"
        )

    def render_saved_executions(self):
        """Create and populate the saved execution configurations widget.

        Builds an OptionList showing saved configurations for the currently selected task.

        Returns:
            OptionList widget populated with saved configurations or a placeholder message.
        """
        self.saved_executions_list = OptionList(
            id="saved-executions-list",
            classes="saved-executions-list"
        )

        if self.selected_task:
            saved_configs = self.gradle_manager.get_saved_executions(self.selected_task.name)
            if saved_configs:
                for config in saved_configs:
                    label = config.get("label", "Unnamed")
                    params = config.get("parameters", [])
                    env_vars = config.get("env_vars", {})

                    # Create display string
                    display = f"▶ {label}"
                    if params:
                        params_preview = " ".join(params)
                        if len(params_preview) > 30:
                            params_preview = params_preview[:27] + "..."
                        display += f" [dim]({params_preview})[/dim]"
                    if env_vars:
                        env_count = len(env_vars)
                        display += f" [dim]{env_count} env var{'s' if env_count != 1 else ''}[/dim]"

                    self.saved_executions_list.add_option(
                        Option(display, id=config["id"])
                    )
            else:
                self.saved_executions_list.add_option(
                    Option("[dim]No saved configurations[/dim]",
                           id="no_saved", disabled=True)
                )
        else:
            self.saved_executions_list.add_option(
                Option("[dim]Select a task first[/dim]",
                       id="no_task", disabled=True)
            )

        return self.saved_executions_list

    def render_saved_execution_buttons(self):
        """Render management buttons for saved executions.

        Returns:
            Horizontal container with buttons for running, editing, and deleting configurations.
        """
        return Horizontal(
            Button("▶ Run", id="run_saved_config_button",
                   variant="success", classes="small-action-button"),
            Button("✎ Edit", id="edit_saved_config_button",
                   variant="default", classes="small-action-button"),
            Button("🗑 Delete", id="delete_saved_config_button",
                   variant="warning", classes="small-action-button"),
            classes="saved-execution-actions"
        )

    def update_saved_executions_list(self):
        """Refresh the saved executions list for the current task.

        Clears and repopulates the saved executions OptionList based on the currently
        selected task. If no task is selected or no configurations exist, displays
        appropriate placeholder messages.
        """
        if not self.saved_executions_list or not self.selected_task:
            return

        self.saved_executions_list.clear_options()
        saved_configs = self.gradle_manager.get_saved_executions(self.selected_task.name)

        if saved_configs:
            for config in saved_configs:
                label = config.get("label", "Unnamed")
                params = config.get("parameters", [])
                env_vars = config.get("env_vars", {})

                display = f"▶ {label}"
                if params:
                    params_preview = " ".join(params)
                    if len(params_preview) > 30:
                        params_preview = params_preview[:27] + "..."
                    display += f" [dim]({params_preview})[/dim]"
                if env_vars:
                    env_count = len(env_vars)
                    display += f" [dim]{env_count} env var{'s' if env_count != 1 else ''}[/dim]"

                self.saved_executions_list.add_option(
                    Option(display, id=config["id"])
                )
        else:
            self.saved_executions_list.add_option(
                Option("[dim]No saved configurations[/dim]",
                       id="no_saved", disabled=True)
            )

    def render_recent_tasks(self):
        """Create and populate the recent tasks widget.

        Builds an OptionList showing recently executed tasks with timestamps, task names,
        and parameters. Each task is clickable to re-run with the same parameters.

        Returns:
            OptionList widget populated with recent task history or a placeholder message.
        """
        from datetime import datetime

        recent_tasks = self.gradle_manager.get_recent_tasks()
        self.recent_tasks_list = OptionList(id="recent-tasks-list", classes="recent-tasks-list")

        if recent_tasks:
            for idx, task_record in enumerate(recent_tasks):
                task_name = task_record.get("task_name", "Unknown")
                parameters = task_record.get("parameters", "")
                timestamp = task_record.get("timestamp", "")

                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    time_str = ""

                display = f"{task_name} {parameters}" if parameters else task_name
                if time_str:
                    display = f"[dim]{time_str}[/dim] {display}"

                self.recent_tasks_list.add_option(Option(display, id=f"recent_{idx}"))
        else:
            self.recent_tasks_list.add_option(
                Option("[dim]No tasks run yet[/dim]", id="no_tasks", disabled=True)
            )

        return self.recent_tasks_list

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes and filter task list.

        Filters the task list based on the search query, matching against both task
        names and descriptions. Updates the UI to show only matching tasks.

        Args:
            event: Input changed event containing the new search query value.
        """
        if event.input == self.search_input:
            search_query = event.value.lower().strip()
            logging.debug(f"Search query: {search_query}")

            if search_query:
                self.filtered_tasks = [
                    task for task in self.tasks
                    if search_query in task.name.lower() or search_query in task.description.lower()
                ]
                logging.debug(f"Filtered to {len(self.filtered_tasks)} tasks")
            else:
                self.filtered_tasks = self.tasks
                logging.debug(f"Showing all {len(self.filtered_tasks)} tasks")

            self.update_task_list()

    def update_task_list(self):
        """Refresh the task option list with current filtered tasks.

        Clears and repopulates the task list widget with filtered tasks. If no tasks
        match the current filter, displays a "no matches" message and clears the
        task selection.
        """
        if self.task_option_list:
            self.task_option_list.clear_options()
            for task in self.filtered_tasks:
                self.task_option_list.add_option(Option(task.name))

            if not self.filtered_tasks:
                self.task_name_label.update("[dim]No tasks match your search[/dim]")
                self.description_widget.update("")
                self.selected_task = None

    def action_focus_search(self):
        """Focus the search input."""
        self.search_input.focus()

    async def action_refresh_tasks(self):
        """Refresh the task list from the Gradle project (non-blocking).

        Performs a background refresh of available Gradle tasks. Guards against
        concurrent refreshes and validates project selection before proceeding.
        """
        if self.is_refreshing:
            logging.debug("Already refreshing tasks, skipping")
            return

        selected_project = self.gradle_manager.get_selected_project()
        if not selected_project:
            logging.warning("No project selected, cannot refresh tasks")
            return

        logging.info("Starting task list refresh")
        self.is_refreshing = True
        search_query = self.search_input.value

        self._show_refresh_loading_ui()
        asyncio.create_task(self._execute_task_refresh(selected_project, search_query))

    def _show_refresh_loading_ui(self):
        """Display loading indicators during task refresh."""
        if self.task_option_list:
            self.task_option_list.clear_options()
            self.task_option_list.add_option(
                Option("[bold yellow]⟳ Refreshing tasks...[/bold yellow]", disabled=True)
            )

        self.task_name_label.update("[bold yellow]Refreshing...[/bold yellow]")
        self.description_widget.update("[dim]Loading tasks from Gradle project...[/dim]")
        self.selected_task = None

    def _show_refresh_error(self, error_message: str):
        """Display error message when task refresh fails.

        Args:
            error_message: The error message to display.
        """
        if self.task_option_list:
            self.task_option_list.clear_options()
            self.task_option_list.add_option(
                Option(f"[bold red]✗ Error: {error_message}[/bold red]", disabled=True)
            )
        self.task_name_label.update("[bold red]Refresh Failed[/bold red]")
        self.description_widget.update(f"[red]{error_message}[/red]")

    def _show_no_tasks_found(self):
        """Display message when no tasks are found in the project."""
        if self.task_option_list:
            self.task_option_list.clear_options()
            self.task_option_list.add_option(
                Option("[dim]No tasks found in project[/dim]", disabled=True)
            )
        self.task_name_label.update("[yellow]No Tasks Found[/yellow]")
        self.description_widget.update("[dim]This project has no Gradle tasks.[/dim]")

    def _update_tasks_after_refresh(self, search_query: str):
        """Update task list UI after successful refresh.

        Sorts tasks, applies search filter if present, and updates the task list widget
        with success message.

        Args:
            search_query: Current search query to re-apply after refresh.
        """
        if search_query:
            self.filtered_tasks = [
                task for task in self.tasks
                if search_query in task.name.lower() or search_query in task.description.lower()
            ]
        else:
            self.filtered_tasks = self.tasks

        if self.task_option_list:
            self.task_option_list.clear_options()
            for task in self.filtered_tasks:
                self.task_option_list.add_option(Option(task.name))

            self.task_name_label.update(f"[bold green]✓ Refreshed {len(self.tasks)} tasks[/bold green]")
            self.description_widget.update("[dim]Select a task from the list to view its description.[/dim]")

            if self.filtered_tasks:
                self.task_option_list.focus()

    async def _execute_task_refresh(self, selected_project: str, search_query: str):
        """Execute the task refresh operation in background.

        Runs the Gradle task fetch in a separate thread to avoid blocking the UI.
        Handles success, error, and exception cases.

        Args:
            selected_project: Path to the selected Gradle project.
            search_query: Current search query to preserve during refresh.
        """
        try:
            logging.debug("Fetching tasks in background thread")
            error_message = await asyncio.to_thread(
                self.gradle_manager.update_project_tasks,
                selected_project
            )

            if error_message:
                logging.error(f"Error refreshing tasks: {error_message}")
                self._show_refresh_error(error_message)
            else:
                logging.info("Tasks refreshed successfully")
                project_info = self.gradle_manager.get_project_info(selected_project)

                if project_info and project_info.tasks:
                    self.tasks = sorted(project_info.tasks, key=self._task_sort_key)
                    self._update_tasks_after_refresh(search_query)
                else:
                    logging.warning("No tasks found after refresh")
                    self._show_no_tasks_found()

        except Exception as e:
            logging.error(f"Exception during task refresh: {e}", exc_info=True)
            self._show_refresh_error(str(e))
        finally:
            self.is_refreshing = False
            logging.debug("Task refresh completed")

    async def action_run_task(self):
        """Action handler for 'r' key to run the selected task."""
        logging.info(f"action_run_task called, selected_task: {self.selected_task}")
        if self.selected_task:
            await self.run_task()
        else:
            logging.warning("No task selected!")

    async def action_run_task_with_parameters(self):
        """Action handler for 'R' key to run the selected task with parameters."""
        if self.selected_task:
            await self.run_task_with_parameters()

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        if event.button.id == "run_task_button" and self.selected_task:
            await self.run_task()
        elif event.button.id == "run_task_with_params_button" and self.selected_task:
            await self.run_task_with_parameters()
        elif event.button.id == "run_saved_config_button":
            await self.action_run_saved_config()
        elif event.button.id == "save_new_config_button" and self.selected_task:
            await self.action_save_new_config()
        elif event.button.id == "edit_saved_config_button":
            await self.action_edit_saved_config()
        elif event.button.id == "delete_saved_config_button":
            await self.action_delete_saved_config()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handle option selection from task list, saved executions, or recent tasks list.

        For main task list selections, updates the task description panel.
        For saved executions selections, runs the saved configuration.
        For recent task selections, re-executes the task with its original parameters.

        Args:
            event: Option selection event containing the selected option and source list.
        """
        # Handle saved executions list - just select, don't run
        if event.option_list.id == "saved-executions-list":
            # Selection is handled automatically, no action needed
            return

        if event.option_list.id == "recent-tasks-list":
            task_id = event.option.id
            if task_id and task_id.startswith("recent_"):
                try:
                    idx = int(task_id.split("_")[1])
                    recent_tasks = self.gradle_manager.get_recent_tasks()
                    if 0 <= idx < len(recent_tasks):
                        task_record = recent_tasks[idx]
                        task_name = task_record.get("task_name")
                        parameters = task_record.get("parameters", "")

                        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)
                        if self.selected_task:
                            self.update_task_description(self.selected_task)

                        if parameters:
                            param_list = parameters.split()
                            await self._run_task_with_params_impl(param_list)
                        else:
                            await self.run_task()
                except (ValueError, IndexError) as e:
                    logging.error(f"Error parsing recent task ID: {e}")
            return

        task_name = event.option.prompt
        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)

        if self.selected_task:
            self.update_task_description(self.selected_task)

    async def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        """Update task description when navigating with keyboard.

        Updates the description panel as the user highlights different tasks using
        arrow keys, without requiring Enter to be pressed.

        Args:
            event: Option highlighted event containing the highlighted task name.
        """
        task_name = event.option.prompt
        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)

        if self.selected_task:
            self.update_task_description(self.selected_task)

    def update_task_description(self, task):
        """Update the task details panel with selected task information.

        Updates both the task name label and description widget with the selected
        task's information. Falls back to a placeholder message if no description exists.

        Args:
            task: The GradleTask object to display.
        """
        logging.debug(f"Selected task: {task.name}")
        self.task_name_label.update(f"[bold cyan]{task.name}[/bold cyan]")

        description_text = task.description if task.description else "[dim]No description available[/dim]"
        self.description_widget.update(description_text)

        # Update saved executions list for this task
        self.update_saved_executions_list()

    def _task_sort_key(self, task):
        """Generate sort key for task ordering with natural sorting.

        Root-level tasks (without colon) are sorted first.
        Submodule tasks (containing colon like core:build or :app:test) are sorted second.
        Within each group, tasks are sorted alphanumerically using natural sort,
        so 'build2' comes before 'build10'.

        Args:
            task: GradleTask object to generate sort key for.

        Returns:
            Tuple of (is_submodule, natural_sort_parts) for sorting.
        """
        name = task.name
        is_submodule = ':' in name

        # Split into alphabetic and numeric parts for natural sorting
        parts = []
        for part in re.split(r'(\d+)', name):
            if part.isdigit():
                parts.append(int(part))
            else:
                parts.append(part.lower())

        return (is_submodule, parts)

    async def run_task(self):
        """Execute the selected Gradle task without parameters.

        Creates a tracked task execution, switches to the output tab, and runs the
        Gradle task in a background thread. Output is streamed in real-time to the
        task manager widget using thread-safe callbacks.
        """
        if self.selected_task:
            logging.info(f"Running task: {self.selected_task.name}")

            tracked_task = self.task_tracker.create_task(self.selected_task.name, [])
            task_id = tracked_task.task_id

            self.parent_widget.activate_output_tab(task_id=task_id)
            await asyncio.sleep(0.1)

            task_manager = self.parent_widget.task_manager_widget
            if not task_manager:
                logging.error("Task manager widget is None!")
                return

            loop = asyncio.get_event_loop()

            def on_stdout(line: str):
                logging.debug(f"Callback stdout: {line}")
                try:
                    loop.call_soon_threadsafe(task_manager.append_output_to_task, task_id, line)
                except Exception as e:
                    logging.error(f"Error in on_stdout callback: {e}", exc_info=True)

            def on_stderr(line: str):
                logging.debug(f"Callback stderr: {line}")
                try:
                    loop.call_soon_threadsafe(task_manager.append_output_to_task, task_id, f"[red]{line}[/red]")
                except Exception as e:
                    logging.error(f"Error in on_stderr callback: {e}", exc_info=True)

            async def execute_task():
                try:
                    logging.debug("Starting task execution in thread")
                    result = await asyncio.to_thread(
                        self.gradle_manager.run_task,
                        self.selected_task.name,
                        on_stdout=on_stdout,
                        on_stderr=on_stderr
                    )
                    logging.info("Task execution completed")
                    # Check if result indicates an error
                    if result and result.startswith("Error:"):
                        loop.call_soon_threadsafe(self.task_tracker.mark_failed, task_id, result)
                    else:
                        loop.call_soon_threadsafe(self.task_tracker.mark_completed, task_id)
                except Exception as e:
                    logging.error(f"Task execution failed: {e}", exc_info=True)
                    loop.call_soon_threadsafe(self.task_tracker.mark_failed, task_id, str(e))
                finally:
                    self.running_task = None

            logging.debug("Creating background task")
            self.running_task = asyncio.create_task(execute_task())
            self.task_tracker.set_asyncio_task(task_id, self.running_task)
            logging.debug("Background task created, UI is now responsive")

    async def run_task_with_parameters(self):
        """Open parameter input modal and execute task with user-provided parameters.

        Displays a modal dialog for parameter entry. If the user confirms (even with
        no parameters), executes the task. If cancelled, no action is taken.
        """
        if self.selected_task:
            logging.info(f"Running task with parameters: {self.selected_task.name}")

            async def execute_task(result):
                logging.debug(f"Modal callback received result: {result}")
                if result is not None:
                    param_list, env_vars, save_config, execution_id = result

                    # Save configuration if requested
                    if save_config:
                        if execution_id:
                            # Update existing configuration
                            self.gradle_manager.update_saved_execution(
                                execution_id,
                                save_config["label"],
                                save_config["parameters"],
                                save_config["env_vars"]
                            )
                        else:
                            # Create new configuration
                            self.gradle_manager.save_execution_config(
                                save_config["task_name"],
                                save_config["label"],
                                save_config["parameters"],
                                save_config["env_vars"]
                            )
                        self.update_saved_executions_list()

                    # Run task only if param_list is not None (None indicates save-only)
                    if param_list is not None or env_vars is not None:
                        logging.info(f"Starting task execution with params: {param_list}, env: {env_vars}")
                        await self._run_task_with_params_impl(param_list or [], env_vars)
                    else:
                        logging.debug("Configuration saved without running task")
                else:
                    logging.debug("User cancelled parameter entry")

            await self.app.push_screen(
                RunTaskWithParametersModal(self.selected_task, self.gradle_manager),
                callback=execute_task
            )

    async def _run_task_with_params_impl(self, parameters, env_vars=None, config_label=None):
        """Execute the selected Gradle task with parameters and optional environment variables.

        Internal implementation for running tasks with parameters. Creates a tracked
        task execution, switches to the output tab, and runs the Gradle task in a
        background thread with real-time output streaming.

        Args:
            parameters: List of command-line parameters to pass to the Gradle task.
            env_vars: Optional dictionary of environment variables to set.
            config_label: Optional label of the saved configuration being used.
        """
        logging.info(f"Running task with parameters: {parameters}, env_vars: {env_vars}, config_label: {config_label}")

        tracked_task = self.task_tracker.create_task(self.selected_task.name, parameters, config_label)
        task_id = tracked_task.task_id

        self.parent_widget.activate_output_tab(task_id=task_id)
        await asyncio.sleep(0.1)

        task_manager = self.parent_widget.task_manager_widget
        if not task_manager:
            logging.error("Task manager widget is None!")
            return

        loop = asyncio.get_event_loop()

        def on_stdout(line: str):
            logging.debug(f"Callback stdout: {line}")
            try:
                loop.call_soon_threadsafe(task_manager.append_output_to_task, task_id, line)
            except Exception as e:
                logging.error(f"Error in on_stdout callback: {e}", exc_info=True)

        def on_stderr(line: str):
            logging.debug(f"Callback stderr: {line}")
            try:
                loop.call_soon_threadsafe(task_manager.append_output_to_task, task_id, f"[red]{line}[/red]")
            except Exception as e:
                logging.error(f"Error in on_stderr callback: {e}", exc_info=True)

        async def execute_task():
            try:
                logging.debug("Starting task with parameters execution in thread")
                result = await asyncio.to_thread(
                    self.gradle_manager.run_task_with_parameters,
                    self.selected_task.name,
                    parameters,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr,
                    env_vars=env_vars
                )
                logging.info("Task with parameters execution completed")
                # Check if result indicates an error
                if result and result.startswith("Error:"):
                    loop.call_soon_threadsafe(self.task_tracker.mark_failed, task_id, result)
                else:
                    loop.call_soon_threadsafe(self.task_tracker.mark_completed, task_id)
            except Exception as e:
                logging.error(f"Task execution failed: {e}", exc_info=True)
                loop.call_soon_threadsafe(self.task_tracker.mark_failed, task_id, str(e))
            finally:
                self.running_task = None

        logging.debug("Creating background task")
        self.running_task = asyncio.create_task(execute_task())
        self.task_tracker.set_asyncio_task(task_id, self.running_task)
        logging.debug("Background task created, UI is now responsive")

    async def action_save_new_config(self):
        """Open modal to save a new execution configuration."""
        if not self.selected_task:
            return

        async def on_modal_dismiss(result):
            if result:
                param_list, env_vars, save_config, _ = result
                if save_config:
                    # Save the configuration
                    self.gradle_manager.save_execution_config(
                        save_config["task_name"],
                        save_config["label"],
                        save_config["parameters"],
                        save_config["env_vars"]
                    )
                    # Refresh the saved executions list
                    self.update_saved_executions_list()
                    logging.info(f"Saved new configuration: {save_config['label']}")

                # Run the task only if param_list or env_vars is not None
                if param_list is not None or env_vars is not None:
                    await self._run_task_with_params_impl(param_list or [], env_vars)

        await self.app.push_screen(
            RunTaskWithParametersModal(self.selected_task, self.gradle_manager),
            callback=on_modal_dismiss
        )

    async def action_run_saved_config(self):
        """Run the selected saved configuration."""
        if not self.saved_executions_list:
            return

        # Get highlighted config from the list
        try:
            highlighted_option = self.saved_executions_list.get_option_at_index(
                self.saved_executions_list.highlighted
            )
        except Exception as e:
            logging.error(f"Failed to get highlighted option: {e}")
            return

        if not highlighted_option or highlighted_option.id.startswith("no_"):
            logging.info("No valid saved config selected to run")
            return

        config_id = highlighted_option.id
        await self._run_saved_execution(config_id)

    async def action_edit_saved_config(self):
        """Edit the selected saved configuration."""
        if not self.saved_executions_list:
            return

        # Get highlighted config from the list
        try:
            highlighted_option = self.saved_executions_list.get_option_at_index(
                self.saved_executions_list.highlighted
            )
        except Exception as e:
            logging.error(f"Failed to get highlighted option: {e}")
            return

        if not highlighted_option or highlighted_option.id.startswith("no_"):
            logging.info("No valid saved config selected to edit")
            return

        config_id = highlighted_option.id

        # Get the selected project
        project_dir = self.gradle_manager.get_selected_project()
        if not project_dir or project_dir not in self.gradle_manager.config.projects:
            logging.error("No project selected")
            return

        # Get config by ID
        all_saved = self.gradle_manager.config.projects[project_dir].saved_executions
        config = next((c for c in all_saved if c["id"] == config_id), None)

        if not config:
            return

        # Get the task for this config
        task_name = config.get("task_name")
        if task_name and self.tasks:
            task = next((t for t in self.tasks if t.name == task_name), None)
        else:
            task = self.selected_task

        async def on_modal_dismiss(result):
            if result:
                param_list, env_vars, save_config, execution_id = result
                if save_config and execution_id:
                    # Update existing configuration
                    self.gradle_manager.update_saved_execution(
                        execution_id,
                        save_config["label"],
                        save_config["parameters"],
                        save_config["env_vars"]
                    )
                    self.update_saved_executions_list()
                    logging.info(f"Updated configuration: {save_config['label']}")

                # Run if requested
                if param_list is not None or env_vars is not None:
                    await self._run_task_with_params_impl(param_list or [], env_vars)

        await self.app.push_screen(
            RunTaskWithParametersModal(
                task,
                self.gradle_manager,
                saved_execution=config
            ),
            callback=on_modal_dismiss
        )

    async def action_delete_saved_config(self):
        """Delete the selected saved configuration."""
        if not self.saved_executions_list:
            return

        try:
            highlighted_option = self.saved_executions_list.get_option_at_index(
                self.saved_executions_list.highlighted
            )
        except Exception as e:
            logging.error(f"Failed to get highlighted option: {e}")
            return

        if not highlighted_option or highlighted_option.id.startswith("no_"):
            return

        config_id = highlighted_option.id

        # Show confirmation modal
        async def on_confirm(confirmed):
            if confirmed:
                if self.gradle_manager.delete_saved_execution(config_id):
                    self.update_saved_executions_list()
                    logging.info(f"Deleted saved configuration: {config_id}")

        await self.app.push_screen(
            ConfirmationModal("Delete this saved configuration?"),
            callback=on_confirm
        )

    async def _run_saved_execution(self, config_id: str):
        """Run a saved execution configuration."""
        # Get the selected project
        project_dir = self.gradle_manager.get_selected_project()
        if not project_dir:
            logging.error("No project selected")
            return

        # Get all saved executions for this project
        if project_dir not in self.gradle_manager.config.projects:
            logging.error(f"Project {project_dir} not found in config")
            return

        all_saved = self.gradle_manager.config.projects[project_dir].saved_executions
        config = next((c for c in all_saved if c["id"] == config_id), None)

        if not config:
            logging.error(f"Saved config {config_id} not found")
            return

        # Get the task name from the config
        task_name = config.get("task_name")
        if not task_name:
            logging.error(f"Saved config {config_id} has no task_name")
            return

        # Find and select the task
        if not self.tasks:
            logging.error("No tasks loaded")
            return

        task = next((t for t in self.tasks if t.name == task_name), None)
        if not task:
            logging.error(f"Task {task_name} not found")
            return

        # Select the task
        self.selected_task = task

        # Mark as used
        self.gradle_manager.mark_saved_execution_used(config_id)

        # Run with parameters and env vars
        param_list = config.get("parameters", [])
        env_vars = config.get("env_vars", {})
        config_label = config.get("label")

        logging.info(f"Running saved execution: {config_label}")
        await self._run_task_with_params_impl(param_list, env_vars, config_label)

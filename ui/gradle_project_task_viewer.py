import logging
import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.widgets import Static, Label, OptionList, Button, Input
from textual.widgets._option_list import Option

from ui.run_task_with_parameters_modal import RunTaskWithParametersModal
from gradle.gradle_manager import GradleManager
from ui.task_tracker import TaskTracker


class GradleProjectTaskViewer(Static):
    BINDINGS = [
        Binding("r", "run_task", "Run Task"),
        Binding("R", "run_task_with_parameters", "Run Task with Parameters"),
        Binding("/", "focus_search", "Search Tasks"),
        Binding("f5", "refresh_tasks", "Refresh Tasks")
    ]

    def __init__(self, gradle_manager: GradleManager, parent_widget, task_tracker: TaskTracker, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.parent_widget = parent_widget  # Reference to LazyGradleWidget
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
        self.running_task = None  # Track currently running background task
        self.is_refreshing = False  # Track if we're currently refreshing the task list

    def compose(self) -> ComposeResult:
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            project_info = self.gradle_manager.get_project_info(selected_project)
            self.gradle_manager.update_project_tasks(selected_project)

            if project_info and project_info.tasks:
                # Sort tasks alphabetically by name
                self.tasks = sorted(project_info.tasks, key=lambda task: task.name.lower())
                self.filtered_tasks = self.tasks  # Initially show all tasks
                logging.info(f"Project info: {project_info}")
                logging.info(f"Tasks: {self.tasks}")
            else:
                logging.error(f"No tasks found for project: {selected_project}")

            yield Horizontal(
                # Left panel: Task list with search
                Vertical(
                    Static("Available Tasks", classes="section-title"),
                    self.search_input,
                    self.render_task_list(),
                    classes="task-list-panel"
                ),
                # Right panel: Task details, actions, and recent tasks
                Vertical(
                    Static("Task Details", classes="section-title"),
                    VerticalScroll(
                        self.task_name_label,
                        self.description_widget,
                        classes="task-details-scroll"
                    ),
                    self.render_buttons(),
                    Static("Recently Run Tasks", classes="section-title recent-tasks-title"),
                    self.render_recent_tasks(),
                    classes="task-details-panel"
                ),
                classes="main-content"
            )
        else:
            yield Label("No project selected.", classes="no-project")

    def on_mount(self) -> None:
        """Set focus on the task list when mounted."""
        if self.task_option_list and len(self.filtered_tasks) > 0:
            self.task_option_list.focus()

    def render_task_list(self):
        """Render the task list on the left."""
        self.task_option_list = OptionList(id="task-option-list", classes="task-option-list")
        logging.info(f"Rendering {len(self.filtered_tasks)} tasks to option list")
        for task in self.filtered_tasks:
            self.task_option_list.add_option(Option(task.name))
            logging.debug(f"Added task: {task.name}")
        return self.task_option_list

    @staticmethod
    def render_buttons():
        """Render the Run Task and Run Task with Parameters buttons."""
        return Horizontal(
            Button("▶ Run Task (r)", id="run_task_button", variant="success", classes="action-button"),
            Button("⚙ Run with Params (R)", id="run_task_with_params_button", variant="primary", classes="action-button"),
            classes="task-actions"
        )

    def render_recent_tasks(self):
        """Render the recent tasks list."""
        recent_tasks = self.gradle_manager.get_recent_tasks()
        self.recent_tasks_list = OptionList(id="recent-tasks-list", classes="recent-tasks-list")

        if recent_tasks:
            from datetime import datetime
            for idx, task_record in enumerate(recent_tasks):
                task_name = task_record.get("task_name", "Unknown")
                parameters = task_record.get("parameters", "")
                timestamp = task_record.get("timestamp", "")

                # Format timestamp nicely
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = ""

                # Build display text
                if parameters:
                    display = f"{task_name} {parameters}"
                else:
                    display = task_name

                if time_str:
                    display = f"[dim]{time_str}[/dim] {display}"

                # Use unique ID combining index to avoid duplicates
                unique_id = f"recent_{idx}"
                self.recent_tasks_list.add_option(Option(display, id=unique_id))
        else:
            self.recent_tasks_list.add_option(Option("[dim]No tasks run yet[/dim]", id="no_tasks", disabled=True))

        return self.recent_tasks_list

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input == self.search_input:
            search_query = event.value.lower().strip()
            logging.info(f"Search query: {search_query}")

            # Filter tasks based on search query
            if search_query:
                self.filtered_tasks = [
                    task for task in self.tasks
                    if search_query in task.name.lower() or search_query in task.description.lower()
                ]
                logging.info(f"Filtered to {len(self.filtered_tasks)} tasks")
            else:
                self.filtered_tasks = self.tasks
                logging.info(f"Showing all {len(self.filtered_tasks)} tasks")

            # Update the task list
            self.update_task_list()

    def update_task_list(self):
        """Update the task option list with filtered tasks."""
        if self.task_option_list:
            self.task_option_list.clear_options()
            for task in self.filtered_tasks:
                self.task_option_list.add_option(Option(task.name))

            # If no tasks match, show a message
            if not self.filtered_tasks:
                self.task_name_label.update("[dim]No tasks match your search[/dim]")
                self.description_widget.update("")
                self.selected_task = None

    def action_focus_search(self):
        """Focus the search input."""
        self.search_input.focus()

    async def action_refresh_tasks(self):
        """Refresh the task list from the Gradle project (non-blocking)."""
        if self.is_refreshing:
            logging.info("Already refreshing tasks, skipping...")
            return

        selected_project = self.gradle_manager.get_selected_project()
        if not selected_project:
            logging.warning("No project selected, cannot refresh tasks")
            return

        logging.info("Starting task list refresh...")
        self.is_refreshing = True

        # Clear the task list and show loading indicator
        if self.task_option_list:
            self.task_option_list.clear_options()
            self.task_option_list.add_option(
                Option("[bold yellow]⟳ Refreshing tasks...[/bold yellow]", disabled=True)
            )

        # Clear task description
        self.task_name_label.update("[bold yellow]Refreshing...[/bold yellow]")
        self.description_widget.update("[dim]Loading tasks from Gradle project...[/dim]")
        self.selected_task = None

        # Clear search input
        search_query = self.search_input.value

        # Perform the refresh in a background thread to avoid blocking
        async def refresh_in_background():
            try:
                logging.info("Fetching tasks in background thread...")
                # Run the potentially slow update_project_tasks in a thread
                error_message = await asyncio.to_thread(
                    self.gradle_manager.update_project_tasks,
                    selected_project
                )

                if error_message:
                    logging.error(f"Error refreshing tasks: {error_message}")
                    # Show error in task list
                    if self.task_option_list:
                        self.task_option_list.clear_options()
                        self.task_option_list.add_option(
                            Option(f"[bold red]✗ Error: {error_message}[/bold red]", disabled=True)
                        )
                    self.task_name_label.update("[bold red]Refresh Failed[/bold red]")
                    self.description_widget.update(f"[red]{error_message}[/red]")
                else:
                    # Successfully refreshed - reload tasks
                    logging.info("Tasks refreshed successfully, updating UI...")
                    project_info = self.gradle_manager.get_project_info(selected_project)

                    if project_info and project_info.tasks:
                        # Sort tasks alphabetically by name
                        self.tasks = sorted(project_info.tasks, key=lambda task: task.name.lower())

                        # Re-apply search filter if there was one
                        if search_query:
                            self.filtered_tasks = [
                                task for task in self.tasks
                                if search_query in task.name.lower() or search_query in task.description.lower()
                            ]
                        else:
                            self.filtered_tasks = self.tasks

                        # Update the task list UI
                        if self.task_option_list:
                            self.task_option_list.clear_options()
                            for task in self.filtered_tasks:
                                self.task_option_list.add_option(Option(task.name))

                            # Show success message briefly
                            self.task_name_label.update(f"[bold green]✓ Refreshed {len(self.tasks)} tasks[/bold green]")
                            self.description_widget.update("[dim]Select a task from the list to view its description.[/dim]")

                            # Focus the task list
                            if len(self.filtered_tasks) > 0:
                                self.task_option_list.focus()
                        else:
                            logging.error("task_option_list is None!")
                    else:
                        logging.warning("No tasks found after refresh")
                        if self.task_option_list:
                            self.task_option_list.clear_options()
                            self.task_option_list.add_option(
                                Option("[dim]No tasks found in project[/dim]", disabled=True)
                            )
                        self.task_name_label.update("[yellow]No Tasks Found[/yellow]")
                        self.description_widget.update("[dim]This project has no Gradle tasks.[/dim]")

            except Exception as e:
                logging.error(f"Exception during task refresh: {e}", exc_info=True)
                if self.task_option_list:
                    self.task_option_list.clear_options()
                    self.task_option_list.add_option(
                        Option(f"[bold red]✗ Exception: {str(e)}[/bold red]", disabled=True)
                    )
                self.task_name_label.update("[bold red]Refresh Failed[/bold red]")
                self.description_widget.update(f"[red]{str(e)}[/red]")
            finally:
                self.is_refreshing = False
                logging.info("Task refresh completed")

        # Start the background refresh
        asyncio.create_task(refresh_in_background())

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

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handle task selection and update the description on mouse click or enter key."""
        # Check if this is from the recent tasks list
        if event.option_list.id == "recent-tasks-list":
            # User selected a recent task - re-run it
            task_id = event.option.id
            if task_id and task_id.startswith("recent_"):
                # Extract the index from the ID
                try:
                    idx = int(task_id.split("_")[1])
                    recent_tasks = self.gradle_manager.get_recent_tasks()
                    if 0 <= idx < len(recent_tasks):
                        task_record = recent_tasks[idx]
                        task_name = task_record.get("task_name")
                        parameters = task_record.get("parameters", "")

                        # Set selected task for display
                        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)
                        if self.selected_task:
                            self.update_task_description(self.selected_task)

                        # Re-run the task with or without parameters
                        if parameters:
                            # Parse parameters back into a list
                            param_list = parameters.split()
                            await self._run_task_with_params_impl(param_list)
                        else:
                            await self.run_task()
                except (ValueError, IndexError) as e:
                    logging.error(f"Error parsing recent task ID: {e}")
            return

        # Otherwise, this is from the main task list
        task_name = event.option.prompt  # Get the selected task name
        # Search in all tasks, not just filtered ones, to get the full task object
        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)

        if self.selected_task:
            self.update_task_description(self.selected_task)

    async def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        """Handle task description update when navigating with keyboard."""
        task_name = event.option.prompt
        # Search in all tasks, not just filtered ones, to get the full task object
        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)

        if self.selected_task:
            self.update_task_description(self.selected_task)

    def update_task_description(self, task):
        """Update the task description in the description widget."""
        logging.debug(f"Selected task: {task.name}")
        self.task_name_label.update(f"[bold cyan]{task.name}[/bold cyan]")

        # Format the description with better styling
        description_text = task.description if task.description else "[dim]No description available[/dim]"
        self.description_widget.update(description_text)
        # No need to refresh - update() already triggers a refresh on the specific widgets

    async def run_task(self):
        """Run the selected task without parameters."""
        if self.selected_task:
            logging.info(f"Running task: {self.selected_task.name}")

            # Switch to the output tab first
            self.parent_widget.activate_output_tab()

            # Give the event loop time to process mount events
            await asyncio.sleep(0.1)

            # Create a tracked task
            tracked_task = self.task_tracker.create_task(self.selected_task.name, [])
            task_id = tracked_task.task_id

            # Get the task manager widget
            task_manager = self.parent_widget.task_manager_widget
            if not task_manager:
                logging.error("Task manager widget is None!")
                return

            # Get the asyncio event loop for thread-safe calls
            loop = asyncio.get_event_loop()

            # Create callbacks that write to the tracked task
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

            # Define the task execution coroutine
            async def execute_task():
                try:
                    logging.info("Starting task execution in thread")
                    await asyncio.to_thread(
                        self.gradle_manager.run_task,
                        self.selected_task.name,
                        on_stdout=on_stdout,
                        on_stderr=on_stderr
                    )
                    logging.info("Task execution completed")
                    loop.call_soon_threadsafe(self.task_tracker.mark_completed, task_id)
                except Exception as e:
                    logging.error(f"Task execution failed: {e}", exc_info=True)
                    loop.call_soon_threadsafe(self.task_tracker.mark_failed, task_id, str(e))
                finally:
                    self.running_task = None

            # Run the task in the background without blocking
            logging.info("Creating background task")
            self.running_task = asyncio.create_task(execute_task())
            logging.info("Background task created, UI is now responsive")

    async def run_task_with_parameters(self):
        """Open a modal to enter parameters for the selected task and run it."""
        if self.selected_task:
            logging.info(f"Running task with parameters: {self.selected_task.name}")

            # Pass a callback to handle task execution after modal closes
            async def execute_task(parameters):
                # This will be called when the modal closes with parameters
                # Note: parameters can be an empty list [] if no params entered, which is valid
                logging.info(f"Modal callback received parameters: {parameters}")
                if parameters is not None:
                    logging.info(f"Starting task execution with parameters: {parameters}")
                    # Directly await the coroutine
                    await self._run_task_with_params_impl(parameters)
                else:
                    logging.info("User cancelled - parameters is None")

            await self.app.push_screen(
                RunTaskWithParametersModal(self.selected_task, self.gradle_manager),
                callback=execute_task
            )

    async def _run_task_with_params_impl(self, parameters):
        """Internal method to run task with parameters and stream to output tab."""
        logging.info(f"_run_task_with_params_impl called with parameters: {parameters}")

        # Switch to the output tab first
        self.parent_widget.activate_output_tab()

        # Give the event loop time to process mount events
        await asyncio.sleep(0.1)

        # Create a tracked task
        tracked_task = self.task_tracker.create_task(self.selected_task.name, parameters)
        task_id = tracked_task.task_id

        # Get the task manager widget
        task_manager = self.parent_widget.task_manager_widget
        if not task_manager:
            logging.error("Task manager widget is None!")
            return

        # Get the asyncio event loop for thread-safe calls
        loop = asyncio.get_event_loop()

        # Create callbacks that write to the tracked task
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

        # Define the task execution coroutine
        async def execute_task():
            try:
                logging.info("Starting task with parameters execution in thread")
                await asyncio.to_thread(
                    self.gradle_manager.run_task_with_parameters,
                    self.selected_task.name,
                    parameters,
                    on_stdout=on_stdout,
                    on_stderr=on_stderr
                )
                logging.info("Task with parameters execution completed")
                loop.call_soon_threadsafe(self.task_tracker.mark_completed, task_id)
            except Exception as e:
                logging.error(f"Task execution failed: {e}", exc_info=True)
                loop.call_soon_threadsafe(self.task_tracker.mark_failed, task_id, str(e))
            finally:
                self.running_task = None

        # Run the task in the background without blocking
        logging.info("Creating background task")
        self.running_task = asyncio.create_task(execute_task())
        logging.info("Background task created, UI is now responsive")

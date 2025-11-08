import logging
import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.widgets import Static, Label, OptionList, Button, Input
from textual.widgets._option_list import Option

from ui.run_task_with_parameters_modal import RunTaskWithParametersModal
from gradle.gradle_manager import GradleManager


class GradleProjectTaskViewer(Static):
    BINDINGS = [
        Binding("r", "run_task", "Run Task"),
        Binding("R", "run_task_with_parameters", "Run Task with Parameters"),
        Binding("/", "focus_search", "Search Tasks")
    ]

    def __init__(self, gradle_manager: GradleManager, parent_widget, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.parent_widget = parent_widget  # Reference to LazyGradleWidget
        self.tasks = []
        self.filtered_tasks = []
        self.selected_task = None
        self.search_input = Input(placeholder="Search tasks... (press / to focus)", classes="task-search")
        self.task_option_list = None
        self.task_name_label = Static("", classes="task-name-label")
        self.description_widget = Static("Select a task from the list to view its description.",
                                         classes="task-description-text")
        self.recent_tasks_list = None

    def compose(self) -> ComposeResult:
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            project_info = self.gradle_manager.get_project_info(selected_project)
            self.gradle_manager.update_project_tasks(selected_project)

            if project_info and project_info.tasks:
                self.tasks = project_info.tasks
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

            # Switch to the output tab first to ensure widget is mounted
            self.parent_widget.activate_output_tab()

            # Give the event loop time to process mount events
            await asyncio.sleep(0.1)

            # Wait for the widget to be mounted and composed (with timeout)
            max_wait = 2.0  # 2 seconds max
            wait_interval = 0.05  # Check every 50ms
            elapsed = 0.0

            while elapsed < max_wait:
                output_widget = self.parent_widget.output_widget
                if output_widget and output_widget.is_mounted:
                    # Also verify the RichLog child exists
                    try:
                        output_widget.query_one("#task-output-log")
                        break  # Widget is fully ready
                    except:
                        pass  # Child not ready yet, keep waiting
                await asyncio.sleep(wait_interval)
                elapsed += wait_interval

            # Get the output widget
            output_widget = self.parent_widget.output_widget
            if output_widget is None:
                logging.error("Output widget is None after waiting!")
                return

            if not output_widget.is_mounted:
                logging.error(f"Output widget still not mounted after {elapsed}s!")
                return

            logging.info(f"Got output widget: {output_widget}, mounted: {output_widget.is_mounted} (waited {elapsed}s)")

            # Clear and prepare output
            logging.info("Clearing output widget")
            output_widget.clear_output()

            # Write a test message directly
            output_widget.write_line(f"[bold cyan]Starting task: {self.selected_task.name}[/bold cyan]")
            output_widget.write_line("")

            # Get the asyncio event loop for thread-safe calls
            loop = asyncio.get_event_loop()

            # Create callbacks that write to the output widget
            def on_stdout(line: str):
                logging.debug(f"Callback stdout: {line}")
                try:
                    loop.call_soon_threadsafe(output_widget.write_line, line)
                except Exception as e:
                    logging.error(f"Error in on_stdout callback: {e}", exc_info=True)

            def on_stderr(line: str):
                logging.debug(f"Callback stderr: {line}")
                try:
                    loop.call_soon_threadsafe(output_widget.write_error, line)
                except Exception as e:
                    logging.error(f"Error in on_stderr callback: {e}", exc_info=True)

            # Run the task in a thread to avoid blocking the UI
            logging.info("Starting task execution in thread")
            await asyncio.to_thread(
                self.gradle_manager.run_task,
                self.selected_task.name,
                on_stdout=on_stdout,
                on_stderr=on_stderr
            )
            logging.info("Task execution completed")

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
        # Switch to the output tab first to ensure widget is mounted
        logging.info("About to activate output tab")
        self.parent_widget.activate_output_tab()
        logging.info("Output tab activated")

        # Give the event loop time to process mount events
        logging.info("Sleeping 0.1s")
        await asyncio.sleep(0.1)
        logging.info("Sleep completed, starting wait loop")

        # Wait for the widget to be mounted and composed (with timeout)
        max_wait = 2.0  # 2 seconds max
        wait_interval = 0.05  # Check every 50ms
        elapsed = 0.0

        while elapsed < max_wait:
            output_widget = self.parent_widget.output_widget
            logging.debug(f"Wait loop: widget={output_widget}, mounted={output_widget.is_mounted if output_widget else 'N/A'}, elapsed={elapsed}")
            if output_widget and output_widget.is_mounted:
                # Also verify the RichLog child exists
                try:
                    output_widget.query_one("#task-output-log")
                    logging.info(f"Widget ready after {elapsed}s")
                    break  # Widget is fully ready
                except Exception as e:
                    logging.debug(f"RichLog not ready yet: {e}")
                    pass  # Child not ready yet, keep waiting
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

        # Get the output widget
        output_widget = self.parent_widget.output_widget
        logging.info(f"After wait loop: elapsed={elapsed}s, widget={output_widget}")

        if output_widget is None:
            logging.error("Output widget is None after waiting!")
            return

        if not output_widget.is_mounted:
            logging.error(f"Output widget still not mounted after {elapsed}s!")
            return

        logging.info(f"Got output widget: {output_widget}, mounted: {output_widget.is_mounted} (waited {elapsed}s)")

        # Clear and prepare output
        logging.info("Clearing output widget")
        output_widget.clear_output()

        # Write a test message directly
        output_widget.write_line(f"[bold cyan]Starting task: {self.selected_task.name}[/bold cyan]")
        output_widget.write_line("")

        # Get the asyncio event loop for thread-safe calls
        loop = asyncio.get_event_loop()

        # Create callbacks that write to the output widget
        def on_stdout(line: str):
            logging.debug(f"Callback stdout: {line}")
            try:
                loop.call_soon_threadsafe(output_widget.write_line, line)
            except Exception as e:
                logging.error(f"Error in on_stdout callback: {e}", exc_info=True)

        def on_stderr(line: str):
            logging.debug(f"Callback stderr: {line}")
            try:
                loop.call_soon_threadsafe(output_widget.write_error, line)
            except Exception as e:
                logging.error(f"Error in on_stderr callback: {e}", exc_info=True)

        # Run the task in a thread to avoid blocking the UI
        logging.info("Starting task with parameters execution in thread")
        await asyncio.to_thread(
            self.gradle_manager.run_task_with_parameters,
            self.selected_task.name,
            parameters,
            on_stdout=on_stdout,
            on_stderr=on_stderr
        )
        logging.info("Task with parameters execution completed")

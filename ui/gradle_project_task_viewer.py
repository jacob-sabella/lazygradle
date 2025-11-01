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
                # Right panel: Task details and actions
                Vertical(
                    Static("Task Details", classes="section-title"),
                    VerticalScroll(
                        self.task_name_label,
                        self.description_widget,
                        classes="task-details-scroll"
                    ),
                    self.render_buttons(),
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

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        if event.button.id == "run_task_button" and self.selected_task:
            await self.run_task()
        elif event.button.id == "run_task_with_params_button" and self.selected_task:
            await self.run_task_with_parameters()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handle task selection and update the description on mouse click or enter key."""
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
        logging.info(task.description)
        self.task_name_label.update(f"[bold cyan]{task.name}[/bold cyan]")

        # Format the description with better styling
        description_text = task.description if task.description else "[dim]No description available[/dim]"
        self.description_widget.update(description_text)
        self.refresh()

    async def run_task(self):
        """Run the selected task without parameters."""
        if self.selected_task:
            logging.info(f"Running task: {self.selected_task.name}")

            # Switch to the output tab first to ensure widget is mounted
            self.parent_widget.activate_output_tab()

            # Small delay to ensure widget is fully mounted
            await asyncio.sleep(0.2)

            # Get the output widget and clear it
            output_widget = self.parent_widget.output_widget
            if output_widget is None:
                logging.error("Output widget is None!")
                return

            logging.info(f"Got output widget: {output_widget}, mounted: {output_widget.is_mounted}")

            # Wait a bit more if not mounted yet
            if not output_widget.is_mounted:
                logging.info("Widget not mounted yet, waiting...")
                await asyncio.sleep(0.3)

            if not output_widget.is_mounted:
                logging.error("Output widget still not mounted after waiting!")
                return

            logging.info("Clearing output widget")
            output_widget.clear_output()

            # Write a test message directly
            output_widget.write_line(f"[bold cyan]Starting task: {self.selected_task.name}[/bold cyan]")
            output_widget.write_line("")

            # Create callbacks that write to the output widget
            def on_stdout(line: str):
                logging.info(f"Callback stdout: {line}")
                self.app.call_from_thread(output_widget.write_line, line)

            def on_stderr(line: str):
                logging.error(f"Callback stderr: {line}")
                self.app.call_from_thread(output_widget.write_error, line)

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
            def execute_task(parameters):
                # This will be called when the modal closes with parameters
                if parameters:
                    asyncio.create_task(self._run_task_with_params_impl(parameters))

            await self.app.push_screen(
                RunTaskWithParametersModal(self.selected_task, self.gradle_manager),
                callback=execute_task
            )

    async def _run_task_with_params_impl(self, parameters):
        """Internal method to run task with parameters and stream to output tab."""
        # Switch to the output tab first to ensure widget is mounted
        self.parent_widget.activate_output_tab()

        # Small delay to ensure widget is fully mounted
        await asyncio.sleep(0.2)

        # Get the output widget and clear it
        output_widget = self.parent_widget.output_widget
        if output_widget is None:
            logging.error("Output widget is None!")
            return

        logging.info(f"Got output widget: {output_widget}, mounted: {output_widget.is_mounted}")

        # Wait a bit more if not mounted yet
        if not output_widget.is_mounted:
            logging.info("Widget not mounted yet, waiting...")
            await asyncio.sleep(0.3)

        if not output_widget.is_mounted:
            logging.error("Output widget still not mounted after waiting!")
            return

        logging.info("Clearing output widget")
        output_widget.clear_output()

        # Write a test message directly
        output_widget.write_line(f"[bold cyan]Starting task: {self.selected_task.name}[/bold cyan]")
        output_widget.write_line("")

        # Create callbacks that write to the output widget
        def on_stdout(line: str):
            logging.info(f"Callback stdout: {line}")
            self.app.call_from_thread(output_widget.write_line, line)

        def on_stderr(line: str):
            logging.error(f"Callback stderr: {line}")
            self.app.call_from_thread(output_widget.write_error, line)

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

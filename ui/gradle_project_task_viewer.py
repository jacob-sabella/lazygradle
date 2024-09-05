import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Label, OptionList, Button
from textual.widgets._option_list import Option

from ui.run_task_with_parameters_modal import RunTaskWithParametersModal
from gradle.gradle_manager import GradleManager


class GradleProjectTaskViewer(Static):
    BINDINGS = [
        Binding("p", "run_task", "Run Task"),
        Binding("P", "run_task_with_parameters", "Run Task with Parameters")
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.tasks = []
        self.selected_task = None
        self.description_widget = Static("Select a task to view its description.", expand=True,
                                         classes="task-description")

    def compose(self) -> ComposeResult:
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            project_info = self.gradle_manager.get_project_info(selected_project)
            self.gradle_manager.update_project_tasks(selected_project)

            if project_info and project_info.tasks:
                self.tasks = project_info.tasks
                logging.info(f"Project info: {project_info}")
                logging.info(f"Tasks: {self.tasks}")
            else:
                logging.error(f"No tasks found for project: {selected_project}")

            yield Horizontal(
                self.render_task_list(),
                Vertical(
                    self.description_widget,  # Use the description widget directly
                    self.render_buttons(),  # Add buttons below the description
                    classes="task-info"
                ),
                classes="main-layout"
            )
        else:
            yield Label("No project selected.", classes="no-project")

    def render_task_list(self):
        """Render the task list on the left."""
        option_list = OptionList()
        for task in self.tasks:
            option_list.add_option(Option(task.name))
        return option_list

    @staticmethod
    def render_buttons():
        """Render the Run Task and Run Task with Parameters buttons."""
        return Vertical(
            Button("Run Task", id="run_task_button", variant="primary"),
            Button("Run Task with Parameters", id="run_task_with_params_button", variant="warning"),
            classes="task-buttons"
        )

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button press events."""
        if event.button.id == "run_task_button" and self.selected_task:
            await self.run_task()
        elif event.button.id == "run_task_with_params_button" and self.selected_task:
            await self.run_task_with_parameters()

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handle task selection and update the description on mouse click or enter key."""
        task_name = event.option.prompt  # Get the selected task name
        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)

        if self.selected_task:
            self.update_task_description(self.selected_task)

    async def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        """Handle task description update when navigating with keyboard."""
        task_name = event.option.prompt
        self.selected_task = next((task for task in self.tasks if task.name == task_name), None)

        if self.selected_task:
            self.update_task_description(self.selected_task)

    def update_task_description(self, task):
        """Update the task description in the description widget."""
        logging.info(task.description)
        self.description_widget.update(task.description)
        self.refresh()

    async def run_task(self):
        """Run the selected task without parameters."""
        if self.selected_task:
            logging.info(f"Running task: {self.selected_task.name}")
            self.gradle_manager.run_task(self.selected_task.name)

    async def run_task_with_parameters(self):
        """Open a modal to enter parameters for the selected task and run it."""
        if self.selected_task:
            logging.info(f"Running task with parameters: {self.selected_task.name}")
            await self.app.push_screen(RunTaskWithParametersModal(self.selected_task, self.gradle_manager))

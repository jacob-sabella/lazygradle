import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button

from gradle.gradle_manager import GradleManager


class RunTaskWithParametersModal(ModalScreen):
    """ModalScreen that handles entering parameters for a Gradle task."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close the modal"),
    ]

    def __init__(self, selected_task, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.selected_task = selected_task
        self.gradle_manager = gradle_manager
        self.param_input = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"Running task: {self.selected_task.name}"),
            self.render_input_field(),
            self.render_buttons(),
            classes="modal-layout"
        )

    def render_input_field(self):
        """Render an input field for parameters."""
        self.param_input = Static("Enter task parameters here", classes="input-field")
        return self.param_input

    def render_buttons(self):
        """Render the Confirm and Cancel buttons."""
        return Horizontal(
            Button("Run", id="run_button", variant="primary"),
            Button("Cancel", id="cancel_button", variant="warning"),
            classes="modal-buttons"
        )

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle the button presses in the modal."""
        if event.button.id == "run_button":
            parameters = self.param_input.content  # Get parameters entered by the user
            logging.info(f"Running {self.selected_task.name} with parameters: {parameters}")
            # self.gradle_manager.(self.selected_task.name, parameters)
            self.dismiss()
        elif event.button.id == "cancel_button":
            self.dismiss()

    def dismiss_modal(self):
        """Dismiss the modal and return to the previous screen."""
        self.dismiss()

    def action_dismiss_modal(self):
        """Dismiss modal using the Escape key."""
        self.dismiss_modal()

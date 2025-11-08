import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input

from gradle.gradle_manager import GradleManager


class RunTaskWithParametersModal(ModalScreen):
    """ModalScreen that handles entering parameters for a Gradle task."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("enter", "run_task", "Run Task"),
    ]

    def __init__(self, selected_task, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.selected_task = selected_task
        self.gradle_manager = gradle_manager
        self.param_input = None

    def compose(self) -> ComposeResult:
        # Modal container matching project chooser style
        description = (
            self.selected_task.description
            if self.selected_task.description
            else "No description available"
        )

        yield Vertical(
            Static("Run Task with Parameters", classes="modal-title"),
            Vertical(
                Static(
                    f"[bold cyan]{self.selected_task.name}[/bold cyan]",
                    classes="modal-section-title",
                ),
                VerticalScroll(
                    Static(
                        f"[dim]{description}[/dim]", classes="run-params-description"
                    ),
                    classes="modal-scroll",
                ),
                Static("[bold]Parameters[/bold]", classes="modal-section-title"),
                self.render_input_field(),
                Static(
                    "[dim]Example: --info --stacktrace or -x test[/dim]",
                    classes="status-message",
                ),
                self.render_buttons(),
                classes="modal-content",
            ),
            classes="run-params-modal",
        )

    def on_mount(self) -> None:
        """Focus the input field when modal opens."""
        if self.param_input:
            self.param_input.focus()

    def render_input_field(self):
        """Render an input field for parameters."""
        self.param_input = Input(
            placeholder="e.g., --info --stacktrace", classes="project-search"
        )
        return self.param_input

    def render_buttons(self):
        """Render the Run and Cancel buttons."""
        return Horizontal(
            Button(
                "▶ Run Task", id="run_button", variant="success", classes="modal-button"
            ),
            Button(
                "Cancel", id="cancel_button", variant="default", classes="modal-button"
            ),
            classes="modal-button-bar",
        )

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle the button presses in the modal."""
        if event.button.id == "run_button":
            await self.action_run_task()
        elif event.button.id == "cancel_button":
            self.dismiss(None)

    async def action_run_task(self):
        """Run the task with the entered parameters."""
        parameters = self.param_input.value if self.param_input else ""
        logging.info(
            f"Modal: Running {self.selected_task.name} with parameters: '{parameters}'"
        )
        # Split the parameters string into a list
        param_list = parameters.split() if parameters else []
        logging.info(f"Modal: Dismissing with param_list: {param_list}")
        self.dismiss(param_list)

    def action_dismiss_modal(self):
        """Dismiss modal using the Escape key."""
        self.dismiss(None)

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button

from gradle.gradle_wrapper import GradleWrapper


class GradlewPermissionModal(ModalScreen):
    """Modal that handles gradlew permission issues and offers to fix them."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
    ]

    def __init__(self, project_path: str, **kwargs):
        super().__init__(**kwargs)
        self.project_path = project_path
        self.gradle_wrapper = GradleWrapper(project_path)
        self.can_fix = False
        self.fix_message = ""

    def compose(self) -> ComposeResult:
        # Check if we can fix the permissions
        self.can_fix, self.fix_message = self.gradle_wrapper.can_fix_gradlew_permissions()

        gradlew_path = f"{self.project_path}/gradlew"

        yield Vertical(
            Static("Gradle Wrapper Permission Issue", classes="modal-title"),
            Vertical(
                Static(
                    "[bold red]Execute Permission Missing[/bold red]",
                    classes="modal-section-title",
                ),
                Static(
                    f"The gradlew file does not have execute permissions:\n[dim]{gradlew_path}[/dim]",
                    classes="modal-content",
                ),
                Static(""),
                Static(
                    f"[bold]Status:[/bold] {self.fix_message}",
                    classes="modal-content",
                ),
                Static(""),
                self.render_solution(),
                self.render_buttons(),
                classes="modal-content",
            ),
            classes="gradlew-permission-modal",
        )

    def render_solution(self):
        """Render the solution instructions."""
        if self.can_fix:
            return Static(
                "[bold green]Solution:[/bold green] Click 'Fix Permissions' below to automatically "
                "add execute permissions to the gradlew file.",
                classes="modal-content",
            )
        else:
            return Static(
                "[bold yellow]Manual Fix Required:[/bold yellow]\n"
                f"Please run the following command in your terminal:\n"
                f"[bold cyan]cd {self.project_path} && chmod +x gradlew[/bold cyan]\n\n"
                "Or if you need elevated permissions:\n"
                f"[bold cyan]cd {self.project_path} && sudo chmod +x gradlew[/bold cyan]",
                classes="modal-content",
            )

    def render_buttons(self):
        """Render the buttons based on whether we can fix the issue."""
        if self.can_fix:
            return Horizontal(
                Button(
                    "Fix Permissions",
                    id="fix_button",
                    variant="success",
                    classes="modal-button",
                ),
                Button(
                    "Cancel",
                    id="cancel_button",
                    variant="default",
                    classes="modal-button",
                ),
                classes="modal-button-bar",
            )
        else:
            return Horizontal(
                Button(
                    "OK",
                    id="ok_button",
                    variant="primary",
                    classes="modal-button",
                ),
                classes="modal-button-bar",
            )

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses in the modal."""
        if event.button.id == "fix_button":
            await self.action_fix_permissions()
        elif event.button.id == "cancel_button" or event.button.id == "ok_button":
            self.dismiss(False)

    async def action_fix_permissions(self):
        """Attempt to fix the gradlew permissions."""
        success, message = self.gradle_wrapper.fix_gradlew_permissions()

        if success:
            logging.info(f"Successfully fixed gradlew permissions: {message}")
            self.dismiss(True)  # Return True to indicate success
        else:
            logging.error(f"Failed to fix gradlew permissions: {message}")
            # Update the modal to show the error
            try:
                # Find the solution static and update it with error message
                self.query_one(".modal-content")
                # For simplicity, just dismiss with failure
                self.dismiss(False)
            except:
                self.dismiss(False)

    def action_dismiss_modal(self):
        """Dismiss modal using the Escape key."""
        self.dismiss(False)

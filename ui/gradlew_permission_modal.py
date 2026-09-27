import logging

from rich.markup import escape

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
            Static("Gradle wrapper can't run", classes="modal-title"),
            Vertical(
                Static(
                    "[bold $text-error]gradlew is missing execute permission[/]\n"
                    f"[$text-muted]{escape(gradlew_path)}[/]\n\n"
                    f"[bold]Status:[/bold] {escape(self.fix_message)}\n\n"
                    f"{self.render_solution()}",
                    classes="modal-message permission-body",
                ),
                classes="modal-content",
            ),
            self.render_buttons(),
            classes="gradlew-permission-modal",
        )

    def render_solution(self) -> str:
        """Return the solution instructions as markup."""
        project = escape(self.project_path)
        if self.can_fix:
            return (
                "[bold $text-success]Fix:[/] choose [bold]Fix Permissions[/bold] to run "
                "chmod +x on gradlew for you."
            )
        return (
            "[bold $text-warning]Manual fix required.[/] Run this in your terminal:\n"
            f"[bold $text-accent]cd {project} && chmod +x gradlew[/]\n\n"
            "If that is denied, use elevated permissions:\n"
            f"[bold $text-accent]cd {project} && sudo chmod +x gradlew[/]"
        )

    def render_buttons(self):
        """Render the buttons based on whether we can fix the issue."""
        if self.can_fix:
            return Horizontal(
                Button(
                    "✓ Fix Permissions",
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
            self.dismiss(False)

    def action_dismiss_modal(self):
        """Dismiss modal using the Escape key."""
        self.dismiss(False)

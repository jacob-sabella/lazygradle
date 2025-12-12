import logging
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button


class ConfirmationModal(ModalScreen):
    """Simple confirmation dialog modal."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("Confirmation", classes="modal-title"),
            Vertical(
                Static(self.message, classes="modal-message"),
                Horizontal(
                    Button(
                        "Yes",
                        id="confirm_button",
                        variant="error",
                        classes="modal-button",
                    ),
                    Button(
                        "No",
                        id="cancel_button",
                        variant="default",
                        classes="modal-button",
                    ),
                    classes="modal-button-bar",
                ),
                classes="modal-content",
            ),
            classes="confirmation-modal",
        )

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses in the modal."""
        if event.button.id == "confirm_button":
            self.dismiss(True)
        elif event.button.id == "cancel_button":
            self.dismiss(False)

    def action_confirm(self):
        """Confirm via Enter key."""
        self.dismiss(True)

    def action_dismiss_modal(self):
        """Dismiss modal via Escape key."""
        self.dismiss(False)

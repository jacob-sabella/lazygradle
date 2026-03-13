from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static


class KeysGuideModal(ModalScreen):
    """A verbose key guide, grouped by global/tab/pane context."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", show=False, priority=True),
        Binding("q", "dismiss_modal", show=False, priority=True),
    ]

    def __init__(self, title: str, body: str, **kwargs):
        super().__init__(**kwargs)
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._title, classes="modal-title"),
            VerticalScroll(
                Static(self._body, classes="keys-guide-body"),
                classes="keys-guide-scroll",
            ),
            classes="keys-guide-modal",
        )

    def on_mount(self) -> None:
        # Ensure the modal gets focus so Esc/q works immediately without a click.
        try:
            self.query_one(VerticalScroll).focus()
        except Exception:
            pass

    def action_dismiss_modal(self) -> None:
        self.dismiss()

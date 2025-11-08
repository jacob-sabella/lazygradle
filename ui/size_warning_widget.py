from textual.app import ComposeResult
from textual.containers import Vertical, Center
from textual.widget import Widget
from textual.widgets import Static


class SizeWarningWidget(Widget):
    """Widget displayed when terminal is too small."""

    def __init__(self, current_width: int, current_height: int, min_width: int, min_height: int, **kwargs):
        super().__init__(**kwargs)
        self.current_width = current_width
        self.current_height = current_height
        self.min_width = min_width
        self.min_height = min_height

    def compose(self) -> ComposeResult:
        yield Center(
            Vertical(
                Static(
                    f"[bold red]⚠ Terminal Too Small[/bold red]\n\n"
                    f"[bold]Current size:[/bold] {self.current_width}x{self.current_height}\n"
                    f"[bold]Minimum required:[/bold] {self.min_width}x{self.min_height}\n\n"
                    f"[dim]Please resize your terminal to continue[/dim]",
                    classes="size-warning-message"
                )
            ),
            classes="size-warning-container"
        )

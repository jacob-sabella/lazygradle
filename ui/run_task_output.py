import logging
from textual.widgets import RichLog
from textual.containers import VerticalScroll
from textual.app import ComposeResult


class RunTaskOutput(VerticalScroll):
    """Widget for displaying streaming Gradle task output."""

    # Enable scrolling for the container
    can_focus = True

    def compose(self) -> ComposeResult:
        """Compose the widget with a RichLog for output display."""
        yield RichLog(
            id="task-output-log",
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
            classes="output-log",
        )

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        logging.info("RunTaskOutput widget mounted")
        logging.info(f"Widget ID: {self.id}, Visible: {self.visible}, Display: {self.display}")

        # Make sure the widget can receive focus for scrolling
        self.focus()

        try:
            log = self.query_one("#task-output-log", RichLog)
            logging.info(f"RichLog found - ID: {log.id}, Visible: {log.visible}, Display: {log.display}")
            log.write("[bold green]Task Output[/bold green]")
            log.write("=" * 80)
            log.write("")
            log.write("[dim]Waiting for task execution...[/dim]")
            log.write("[dim]Use arrow keys or mouse wheel to scroll[/dim]")
            logging.info("Initial message written to output log")
        except Exception as e:
            logging.error(f"Error in on_mount: {e}", exc_info=True)

    def clear_output(self):
        """Clear the output log."""
        logging.info("Clearing output log")
        try:
            log = self.query_one("#task-output-log", RichLog)
            log.clear()
            log.write("[bold green]Task Output[/bold green]")
            log.write("=" * 80)
        except Exception as e:
            logging.error(f"Error clearing output: {e}")

    def write_line(self, line: str):
        """Write a line to the output log."""
        logging.debug(f"Writing to output: {line}")
        if not self.is_mounted:
            logging.error("Widget is not mounted!")
            return
        try:
            log = self.query_one("#task-output-log", RichLog)
            if not log.is_mounted:
                logging.error("RichLog is not mounted!")
                return
            log.write(line)
            # Ensure we scroll to the bottom to show latest output
            log.scroll_end(animate=False)
        except Exception as e:
            logging.error(f"Error writing line: {e}", exc_info=True)

    def write_error(self, line: str):
        """Write an error line to the output log in red."""
        logging.debug(f"Writing stderr to output: {line}")
        if not self.is_mounted:
            logging.error("Widget is not mounted!")
            return
        try:
            log = self.query_one("#task-output-log", RichLog)
            if not log.is_mounted:
                logging.error("RichLog is not mounted!")
                return
            log.write(f"[bold red]{line}[/bold red]")
            # Ensure we scroll to the bottom to show latest output
            log.scroll_end(animate=False)
        except Exception as e:
            logging.error(f"Error writing error line: {e}", exc_info=True)

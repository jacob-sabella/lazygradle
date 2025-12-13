"""LazyGradle main application module.

This module provides the primary Textual application for managing Gradle projects.
It handles theme persistence, project switching, and coordinates between the UI
and Gradle management layers.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer
from textual.containers import Container

from gradle.gradle_manager import GradleManager
from ui.project_chooser_modal import ProjectChooserModal
from ui.widget import LazyGradleWidget


class LazyGradleApp(App):
    """Main application for LazyGradle TUI.

    Provides a Textual-based interface for managing Gradle tasks across multiple
    projects. Handles theme persistence, project switching via modal dialogs,
    and maintains the main application layout.

    Attributes:
        gradle_manager: Manager for Gradle project operations and configuration.
        project_chooser_open: Flag to prevent multiple project chooser modals.
        CSS_PATH: Path to the application stylesheet.
        BINDINGS: Key bindings for application actions.
    """

    CSS_PATH = "lazy_gradle_app.css"

    BINDINGS = [
        Binding("p", "show_project_chooser", "Show Project Chooser", priority=True),
    ]

    ENABLE_COMMAND_PALETTE = True

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        """Initialize the application.

        Args:
            gradle_manager: GradleManager instance for project operations.
            **kwargs: Additional arguments passed to the App constructor.
        """
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.project_chooser_open = False

    def compose(self) -> ComposeResult:
        """Compose the application layout.

        Yields:
            Header, main container, and footer widgets.
        """
        yield Header()
        yield Container(id="main-container")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize application state on mount.

        Loads and applies the saved theme from configuration, then schedules
        content rendering after the DOM is ready.
        """
        saved_theme = self.gradle_manager.get_theme()
        if saved_theme:
            self.theme = saved_theme

        self.call_after_refresh(self._update_content)

    def _update_content(self) -> None:
        """Update the main container with the LazyGradle widget.

        Safely replaces container contents after ensuring the DOM is ready.
        Silently skips if the container is not yet available.
        """
        try:
            container = self.query_one("#main-container", Container)
        except Exception:
            return

        container.remove_children()
        container.mount(LazyGradleWidget(self.gradle_manager))

    def action_show_project_chooser(self):
        """Display the project chooser modal.

        Opens the project selection modal if not already open. On dismissal,
        refreshes the current tab if changes were made.
        """
        if not self.project_chooser_open:
            self.project_chooser_open = True

            def on_dismiss(should_refresh=None):
                import logging

                self.project_chooser_open = False

                if should_refresh:
                    logging.info("Refresh has been flagged")
                    try:
                        widget = self.query_one(LazyGradleWidget)
                        if widget:
                            logging.info(
                                "Found LazyGradleWidget, calling refresh_current_tab()"
                            )
                            widget.refresh_current_tab()
                        else:
                            logging.warning("LazyGradleWidget not found")
                    except Exception as e:
                        logging.error(
                            f"Error refreshing after project chooser: {e}",
                            exc_info=True,
                        )
                else:
                    logging.info("Project chooser dismissed without changes")

            self.push_screen(
                ProjectChooserModal(self.gradle_manager), callback=on_dismiss
            )

    def on_screen_dismissed(self):
        """Handle screen dismissal events.

        Resets the project chooser flag when any screen is dismissed.
        """
        self.project_chooser_open = False

    def watch_theme(self, theme_name: str) -> None:
        """Persist theme changes to configuration.

        Args:
            theme_name: Name of the newly selected theme.
        """
        self.gradle_manager.set_theme(theme_name)

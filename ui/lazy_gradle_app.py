"""LazyGradle main application module.

This module provides the primary Textual application for managing Gradle projects.
It handles theme persistence, project switching, and coordinates between the UI
and Gradle management layers.
"""

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.widgets import Header, Footer
from textual.containers import Container

from gradle.gradle_manager import GradleManager
from ui.project_chooser_modal import ProjectChooserModal
from ui.widget import LazyGradleWidget
from ui.keys_guide_modal import KeysGuideModal


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

    def get_system_commands(self, screen):
        # Replace Textual's built-in "Keys" help panel with our own keys guide.
        for command in super().get_system_commands(screen):
            if getattr(command, "title", None) == "Keys":
                continue
            yield command
        yield SystemCommand(
            "Keys Guide",
            "Show a verbose key guide (global/tab/pane specific)",
            self.action_show_keys_guide,
        )

    def action_show_keys_guide(self) -> None:
        title, body = self._build_keys_guide()
        self.push_screen(KeysGuideModal(title, body))

    def _build_keys_guide(self) -> tuple[str, str]:
        tab_id = None
        try:
            widget = self.query_one(LazyGradleWidget)
            tab_id = getattr(widget, "current_tab_id", None)
        except Exception:
            tab_id = None

        focused = getattr(self, "focused", None)
        focused_name = focused.__class__.__name__ if focused is not None else "None"
        focused_id = getattr(focused, "id", None)
        focus_desc = f"{focused_name}" + (f" (id={focused_id})" if focused_id else "")

        tab_label = {
            "current-setup": "Current Setup",
            "task-manager-tab": "Task Manager",
        }.get(tab_id or "", "Unknown")

        title = f"Keys Guide [{tab_label}]"
        body = (
            f"[dim]Context:[/] tab={tab_id or 'unknown'} focused={focus_desc}\n\n"
            "[bold]This Guide[/bold]\n"
            "  Esc or q: close\n\n"
            "[bold]Global[/bold]\n"
            "  1: switch to Current Setup tab\n"
            "  2: switch to Task Manager tab\n"
            "  p: project chooser\n"
            "  Ctrl+h/j/k/l: move focus between panes (current tab)\n"
            "  Ctrl+Arrow keys: same as Ctrl+h/j/k/l\n"
            "  Terminal font size: global (your terminal emulator)\n"
            "    Common: Ctrl+Plus / Ctrl+Minus / Ctrl+0 (reset)\n"
            "    macOS: Cmd+Plus / Cmd+Minus / Cmd+0 (reset)\n\n"
            "[bold]Current Setup Tab[/bold]\n"
            "  /: focus task search\n"
            "  Enter (in search): jump to first result (highlights it)\n"
            "  Enter (on a task): run task (same as r)\n"
            "  r: run task\n"
            "  R: run task with parameters\n"
            "  F5: refresh tasks\n\n"
            "[bold]Task Manager Tab[/bold]\n"
            "  C (Shift+C): clear task history\n"
            "  c: cancel running task\n\n"
            "[bold]Task Output Pane[/bold]\n"
            "  j/k or Arrow Up/Down: move cursor line\n"
            "  h/l or Arrow Left/Right: horizontal scroll\n"
            "  gg: top, G: bottom\n"
            "  Ctrl+d / Ctrl+u: page down / up\n"
            "  0 / $: horizontal start / end\n"
            "  + / -: zoom (readability, not terminal font size)\n"
            "  Mouse drag: visual select\n"
            "  v: toggle visual select\n"
            "  Esc: exit visual select\n"
            "  VISUAL y: yank selection\n"
            "  yy: yank current line\n"
        )
        return title, body

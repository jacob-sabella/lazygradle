from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer
from textual.containers import Container

from gradle.gradle_manager import GradleManager
from ui.project_chooser_modal import ProjectChooserModal
from ui.widget import LazyGradleWidget
from ui.size_warning_widget import SizeWarningWidget


class LazyGradleApp(App):
    CSS_PATH = "lazy_gradle_app.css"

    # Minimum terminal size requirements
    MIN_WIDTH = 100
    MIN_HEIGHT = 30

    BINDINGS = [
        Binding("p", "show_project_chooser", "Show Project Chooser", priority=True),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.project_chooser_open = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(id="main-container")
        yield Footer()

    def on_mount(self) -> None:
        """Check size and render appropriate content on mount."""
        # Load and apply saved theme
        saved_theme = self.gradle_manager.get_theme()
        if saved_theme:
            self.theme = saved_theme

        self._update_content()

    def on_resize(self) -> None:
        """Check size and update content when terminal is resized."""
        self._update_content()

    def _update_content(self) -> None:
        """Update the main content based on terminal size."""
        container = self.query_one("#main-container", Container)
        container.remove_children()

        # Get terminal size
        width = self.size.width
        height = self.size.height

        # Check if terminal is large enough
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            # Show size warning
            container.mount(SizeWarningWidget(
                current_width=width,
                current_height=height,
                min_width=self.MIN_WIDTH,
                min_height=self.MIN_HEIGHT
            ))
        else:
            # Show normal content
            container.mount(LazyGradleWidget(self.gradle_manager))

    def action_show_project_chooser(self):
        # Only allow project chooser if terminal is large enough
        if self.size.width < self.MIN_WIDTH or self.size.height < self.MIN_HEIGHT:
            return

        if not self.project_chooser_open:
            self.project_chooser_open = True

            def on_dismiss(result=None):
                self.project_chooser_open = False
                # Only refresh if LazyGradleWidget exists
                try:
                    widget = self.query_one(LazyGradleWidget)
                    widget.refresh_current_tab()
                except:
                    pass

            self.push_screen(ProjectChooserModal(self.gradle_manager), callback=on_dismiss)

    def on_screen_dismissed(self):
        self.project_chooser_open = False

    def watch_theme(self, theme_name: str) -> None:
        """Watch for theme changes and save to config."""
        # Save the new theme to config
        self.gradle_manager.set_theme(theme_name)

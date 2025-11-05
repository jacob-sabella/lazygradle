from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from gradle.gradle_manager import GradleManager
from ui.project_chooser_modal import ProjectChooserModal
from ui.widget import LazyGradleWidget


class LazyGradleApp(App):
    CSS_PATH = "lazy_gradle_app.css"

    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("p", "show_project_chooser", "Show Project Chooser", priority=True),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.project_chooser_open = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield LazyGradleWidget(self.gradle_manager)
        yield Footer()

    def action_show_project_chooser(self):
        if not self.project_chooser_open:
            self.project_chooser_open = True

            def on_dismiss(result=None):
                self.project_chooser_open = False
                widget = self.query_one(LazyGradleWidget)
                widget.refresh_current_tab()

            self.push_screen(ProjectChooserModal(self.gradle_manager), callback=on_dismiss)

    def on_screen_dismissed(self):
        self.project_chooser_open = False

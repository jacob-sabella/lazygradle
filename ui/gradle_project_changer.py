from textual.app import ComposeResult
from textual.widgets import Static, Label

from gradle.gradle_manager import GradleManager


class GradleProjectChanger(Static):
    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager

    def compose(self) -> ComposeResult:
        selected_project = self.gradle_manager.get_selected_project()
        yield Label(f"Currently selected project: {selected_project if selected_project else 'None'}")

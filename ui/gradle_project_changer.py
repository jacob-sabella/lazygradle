from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Label

from gradle.gradle_manager import GradleManager
import os


class GradleProjectChanger(Static):
    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager

    def compose(self) -> ComposeResult:
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            project_name = os.path.basename(selected_project)
            project_path = selected_project
            yield Horizontal(
                Static("📁 Project:", classes="project-label"),
                Static(f"[bold cyan]{project_name}[/bold cyan]", classes="project-name"),
                Static(f"[dim]{project_path}[/dim]", classes="project-path"),
                classes="project-header"
            )
        else:
            yield Static("⚠ No project selected. Press [bold]p[/bold] to choose a project.", classes="project-warning")

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget

from gradle.gradle_manager import GradleManager
from ui.gradle_project_changer import GradleProjectChanger
from ui.gradle_project_task_viewer import GradleProjectTaskViewer


class LazyGradleWidget(Widget):
    """Containing widget to hold the layout with Static components."""

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager

    def compose(self) -> ComposeResult:
        yield Vertical(
            GradleProjectChanger(self.gradle_manager, classes="header-label"),
            GradleProjectTaskViewer(self.gradle_manager, classes="task-viewer"),
            classes="main-layout"
        )

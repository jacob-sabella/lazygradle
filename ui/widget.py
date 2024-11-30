from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Tab, Tabs, Static

from gradle.gradle_manager import GradleManager
from ui.gradle_project_changer import GradleProjectChanger
from ui.gradle_project_task_viewer import GradleProjectTaskViewer


class LazyGradleWidget(Widget):
    """Containing widget to hold the layout with Tabs."""

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager

    def compose(self) -> ComposeResult:
        # Create Tabs container
        yield Tabs(
            Tab("Current Setup", id="current-setup"),
            Tab("Dummy Tab 1", id="dummy-tab-1"),
            Tab("Dummy Tab 2", id="dummy-tab-2"),
            id="gradle-tabs",
            classes="tab-container"
        )
        # Add the tab content container
        yield Vertical(id="tab-content-container", classes="tab-content")

    def on_mount(self) -> None:
        # Initialize the default content for the selected tab
        self.switch_to_tab("current-setup")

    def switch_to_tab(self, tab_id: str) -> None:
        """Switch content based on the selected tab."""
        tab_content_container = self.query_one("#tab-content-container")
        tab_content_container.remove_children()

        if tab_id == "current-setup":
            tab_content_container.mount(
                Vertical(
                    GradleProjectChanger(self.gradle_manager, classes="header-label"),
                    GradleProjectTaskViewer(self.gradle_manager, classes="task-viewer"),
                    classes="main-layout"
                )
            )
        elif tab_id == "dummy-tab-1":
            tab_content_container.mount(Static("Content for Dummy Tab 1", classes="dummy-content"))
        elif tab_id == "dummy-tab-2":
            tab_content_container.mount(Static("Content for Dummy Tab 2", classes="dummy-content"))

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        self.switch_to_tab(event.tab.id)

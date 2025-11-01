from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Tab, Tabs, Static

from gradle.gradle_manager import GradleManager
from ui.gradle_project_changer import GradleProjectChanger
from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from ui.run_task_output import RunTaskOutput


class LazyGradleWidget(Widget):
    """Containing widget to hold the layout with Tabs."""

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.output_widget = None

    def compose(self) -> ComposeResult:
        # Create Tabs container
        yield Tabs(
            Tab("Current Setup", id="current-setup"),
            Tab("Output", id="output-tab"),
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
        import logging
        tab_content_container = self.query_one("#tab-content-container")
        tab_content_container.remove_children()

        if tab_id == "current-setup":
            tab_content_container.mount(
                Vertical(
                    GradleProjectChanger(self.gradle_manager, classes="header-label"),
                    GradleProjectTaskViewer(self.gradle_manager, self, classes="task-viewer"),
                    classes="main-layout"
                )
            )
        elif tab_id == "output-tab":
            # Always create a fresh output widget since removed widgets can't be remounted
            logging.info("Creating fresh output widget")
            self.output_widget = RunTaskOutput(classes="output-widget")
            logging.info("Mounting output widget")
            tab_content_container.mount(self.output_widget)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        self.switch_to_tab(event.tab.id)

    def activate_output_tab(self) -> None:
        """Programmatically activate the output tab."""
        tabs = self.query_one("#gradle-tabs", Tabs)
        tabs.active = "output-tab"
        self.switch_to_tab("output-tab")

    def refresh_current_tab(self) -> None:
        """Refresh the current tab by re-rendering its content."""
        tabs = self.query_one("#gradle-tabs", Tabs)
        if tabs.active_tab:
            self.switch_to_tab(tabs.active_tab.id)

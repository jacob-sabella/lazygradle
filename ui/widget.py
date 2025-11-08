from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Tab, Tabs, Static

from gradle.gradle_manager import GradleManager
from ui.gradle_project_changer import GradleProjectChanger
from ui.gradle_project_task_viewer import GradleProjectTaskViewer
from ui.task_manager_widget import TaskManagerWidget
from ui.task_tracker import TaskTracker


class LazyGradleWidget(Widget):
    """Containing widget to hold the layout with Tabs."""

    BINDINGS = [
        Binding("1", "switch_tab('current-setup')", "Switch to Setup tab"),
        Binding("2", "switch_tab('task-manager-tab')", "Switch to Task Manager tab"),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.task_tracker = TaskTracker()
        self.task_manager_widget = None

    def compose(self) -> ComposeResult:
        # Create Tabs container with numbered labels
        yield Tabs(
            Tab("[1] Current Setup", id="current-setup"),
            Tab("[2] Task Manager", id="task-manager-tab"),
            id="gradle-tabs",
            classes="tab-container"
        )
        # Add the tab content container
        yield Vertical(id="tab-content-container", classes="tab-content")

    def action_switch_tab(self, tab_id: str) -> None:
        """Action to switch tabs via number keys."""
        tabs = self.query_one("#gradle-tabs", Tabs)
        tabs.active = tab_id
        self.switch_to_tab(tab_id)

    def on_mount(self) -> None:
        # Initialize the default content for the selected tab
        # Use call_after_refresh to ensure DOM is ready
        self.call_after_refresh(self.switch_to_tab, "current-setup")

    def switch_to_tab(self, tab_id: str) -> None:
        """Switch content based on the selected tab."""
        import logging
        tab_content_container = self.query_one("#tab-content-container")
        tab_content_container.remove_children()

        if tab_id == "current-setup":
            tab_content_container.mount(
                Vertical(
                    GradleProjectChanger(self.gradle_manager, classes="header-label"),
                    GradleProjectTaskViewer(self.gradle_manager, self, self.task_tracker, classes="task-viewer"),
                    classes="main-layout"
                )
            )
        elif tab_id == "task-manager-tab":
            # Always create a fresh task manager widget since removed widgets can't be remounted
            logging.info("Creating fresh task manager widget")
            self.task_manager_widget = TaskManagerWidget(self.task_tracker, classes="task-manager-widget")
            logging.info("Mounting task manager widget")
            tab_content_container.mount(self.task_manager_widget)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        self.switch_to_tab(event.tab.id)

    def activate_output_tab(self, task_id: str = None) -> None:
        """Programmatically activate the task manager tab and optionally select a task."""
        tabs = self.query_one("#gradle-tabs", Tabs)
        tabs.active = "task-manager-tab"
        # Always manually call switch_to_tab to ensure we get a fresh widget
        # This might get called twice (once here, once from event), but that's okay
        # because we remove children first, so the second call just ensures it's ready
        self.switch_to_tab("task-manager-tab")

        # Select the specific task if provided
        if task_id and self.task_manager_widget:
            import asyncio
            # Give the widget a moment to mount and compose
            async def select_after_mount():
                await asyncio.sleep(0.05)
                if self.task_manager_widget and self.task_manager_widget.is_mounted:
                    self.task_manager_widget.select_task(task_id)

            asyncio.create_task(select_after_mount())

    def refresh_current_tab(self) -> None:
        """Refresh the current tab by re-rendering its content."""
        tabs = self.query_one("#gradle-tabs", Tabs)
        if tabs.active_tab:
            self.switch_to_tab(tabs.active_tab.id)

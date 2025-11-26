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
        self.current_tab_id = None  # Track which tab is currently mounted

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

    def switch_to_tab(self, tab_id: str, force_refresh: bool = False) -> None:
        """Switch content based on the selected tab.

        Args:
            tab_id: The ID of the tab to switch to
            force_refresh: If True, force a remount even if already on this tab
        """
        import logging

        # Skip remounting if we're already on this tab and not forcing refresh
        if self.current_tab_id == tab_id and not force_refresh:
            logging.info(f"Already on tab {tab_id}, skipping remount")
            return

        logging.info(f"Switching to tab {tab_id} (force_refresh={force_refresh})")
        tab_content_container = self.query_one("#tab-content-container")
        tab_content_container.remove_children()
        self.current_tab_id = tab_id

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
        # Force a refresh to ensure we get a fresh widget when launching a task
        self.switch_to_tab("task-manager-tab", force_refresh=True)

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
            self.switch_to_tab(tabs.active_tab.id, force_refresh=True)

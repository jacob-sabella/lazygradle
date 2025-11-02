from pathlib import Path
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Static, OptionList, DirectoryTree, Button, Tabs, Tab, Input
from textual.widgets._option_list import Option

from gradle.gradle_manager import GradleManager


class ProjectChooserModal(ModalScreen):
    """ModalScreen that handles the project chooser logic with two tabs."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close the modal"),
        Binding("1", "switch_tab('switch-projects')", "Switch Projects"),
        Binding("2", "switch_tab('add-project')", "Add New Project"),
        Binding("/", "focus_search", "Search Projects"),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.selected_path = None  # Track the selected path
        self.all_projects = []
        self.filtered_projects = []
        self.search_input = Input(placeholder="Search projects... (press / to focus)", classes="project-search")

    def compose(self) -> ComposeResult:
        # Modal container
        yield Container(
            Static("Project Manager", classes="modal-title"),
            Tabs(
                Tab("[1] Switch Projects", id="switch-projects"),
                Tab("[2] Add New Project", id="add-project"),
                id="project-tabs",
                classes="modal-tabs"
            ),
            Vertical(id="modal-tab-content", classes="modal-content"),
            classes="project-chooser-modal"
        )

    def on_mount(self) -> None:
        """Initialize with the first tab."""
        # Load projects
        self.all_projects = list(self.gradle_manager.list_all_projects().keys())
        self.filtered_projects = self.all_projects
        self.switch_to_tab("switch-projects")

    def action_switch_tab(self, tab_id: str) -> None:
        """Action to switch tabs via number keys."""
        tabs = self.query_one("#project-tabs", Tabs)
        tabs.active = tab_id
        self.switch_to_tab(tab_id)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        self.switch_to_tab(event.tab.id)

    def switch_to_tab(self, tab_id: str) -> None:
        """Switch content based on the selected tab."""
        content_container = self.query_one("#modal-tab-content")
        content_container.remove_children()

        if tab_id == "switch-projects":
            # Project list with search
            project_option_list = OptionList(id="project-list", classes="modal-option-list")
            for project_path in self.filtered_projects:
                project_name = os.path.basename(project_path)
                project_option_list.add_option(Option(f"[bold cyan]{project_name}[/bold cyan]\n[dim]{project_path}[/dim]", id=project_path))

            content_container.mount(
                Vertical(
                    Static("[bold]Select a Project[/bold]", classes="modal-section-title"),
                    self.search_input,
                    VerticalScroll(
                        project_option_list,
                        classes="modal-scroll"
                    ),
                    classes="tab-content-area"
                )
            )
        elif tab_id == "add-project":
            # Directory tree to add new project
            self.dir_tree = DirectoryTree(Path.home(), id="project-dir-tree")
            content_container.mount(
                Vertical(
                    Static("[bold]Select a Directory[/bold]", classes="modal-section-title"),
                    Static("", id="status_label", classes="status-message"),
                    VerticalScroll(
                        self.dir_tree,
                        classes="modal-scroll"
                    ),
                    Horizontal(
                        Button("✓ Confirm", id="confirm_button", variant="success", classes="modal-button"),
                        Button("✗ Cancel", id="cancel_button", variant="error", classes="modal-button"),
                        classes="modal-button-bar"
                    ),
                    classes="tab-content-area"
                )
            )

    def refresh_static(self, message: str):
        """Refresh the static text for visual feedback."""
        try:
            static_label = self.query_one("#status_label", Static)
            static_label.update(message)
        except NoMatches:
            pass

    def action_focus_search(self):
        """Focus the search input."""
        try:
            self.search_input.focus()
        except:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input == self.search_input:
            search_query = event.value.lower().strip()

            # Filter projects based on search query
            if search_query:
                self.filtered_projects = [
                    project for project in self.all_projects
                    if search_query in project.lower() or search_query in os.path.basename(project).lower()
                ]
            else:
                self.filtered_projects = self.all_projects

            # Refresh the project list
            self.switch_to_tab("switch-projects")

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        """Handles the event when a user selects an existing project."""
        # Get the project path from the option ID
        selected_project = event.option.id
        if selected_project:
            self.gradle_manager.select_project(selected_project)
            self.dismiss_modal()

    async def on_directory_tree_selected(self, directory_tree: DirectoryTree.DirectorySelected):
        """Handles the event when a user selects a directory from the tree."""
        self.selected_path = Path(directory_tree.path)  # Capture the selected path
        self.refresh_static(f"Selected: {self.selected_path}")

    async def on_directory_tree_file_selected(self, directory_tree: DirectoryTree.FileSelected):
        """Handle file selection explicitly."""
        self.selected_path = Path(directory_tree.path)
        self.refresh_static(f"File Selected: {self.selected_path}")

    async def on_directory_tree_directory_selected(self, directory_tree: DirectoryTree.DirectorySelected):
        """Handle directory selection explicitly."""
        self.selected_path = Path(directory_tree.path)
        self.refresh_static(f"Directory Selected: {self.selected_path}")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle the Confirm and Cancel button press events."""
        button = event.button  # Access the Button that was pressed
        if button.id == "confirm_button":
            if self.selected_path is not None and self.selected_path.exists():
                gradle_files = list(self.selected_path.glob('*.gradle'))

                if gradle_files:
                    self.gradle_manager.add_project(str(self.selected_path))
                    self.gradle_manager.select_project(str(self.selected_path))
                    self.dismiss_modal()
                else:
                    self.refresh_static("No .gradle files found in the selected directory!")
        elif button.id == "cancel_button":
            self.dismiss_modal()

    def dismiss_modal(self):
        """Dismiss the modal and reset the flag in the main app."""
        self.app.project_chooser_open = False  # Reset the flag here
        self.dismiss()

    def action_dismiss_modal(self):
        """Close the modal when Escape is pressed."""
        self.dismiss_modal()

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import TabbedContent, TabPane, Static, OptionList, DirectoryTree, Button

from gradle.gradle_manager import GradleManager


class ProjectChooserModal(ModalScreen):
    """ModalScreen that handles the project chooser logic with two tabs."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close the modal"),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.selected_path = None  # Track the selected path

    def compose(self) -> ComposeResult:
        # Use TabbedContent for two tabs: "Switch Projects" and "Add New Project"
        with TabbedContent("Switch Projects", "Add New Project"):
            # First Tab: Switch Between Cached Projects
            with TabPane("Switch Projects"):
                yield Static("Switch between cached projects")
                # List of cached projects
                option_list = OptionList()
                for project in self.gradle_manager.list_all_projects():
                    option_list.add_option(project)
                yield option_list

            # Second Tab: Add New Project
            with TabPane("Add New Project"):
                yield Static("Status:", id="status_label")  # Ensure correct ID
                with Vertical():
                    # Directory tree to add a new project
                    self.dir_tree = DirectoryTree(Path.home())
                    yield self.dir_tree

                    # Confirmation and cancel buttons
                    with Horizontal():
                        yield Button("Confirm", id="confirm_button")
                        yield Button("Cancel", id="cancel_button")

    def refresh_static(self, message: str):
        """Refresh the static text for visual feedback."""
        try:
            static_label = self.query_one("#status_label", Static)
            static_label.update(message)
        except NoMatches:
            print("Static widget not found!")

    def on_mount(self) -> None:
        """Set focus to the DirectoryTree when the screen is mounted."""
        self.set_focus(self.dir_tree)

    async def on_option_list_option_selected(self, option_list: OptionList.OptionSelected):
        """Handles the event when a user selects an existing project."""
        selected_project = option_list.option.prompt  # Extract the path as a string
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

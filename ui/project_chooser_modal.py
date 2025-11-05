from pathlib import Path
import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Static, OptionList, DirectoryTree, Button, TabbedContent, TabPane, Input
from textual.widgets._option_list import Option

from gradle.gradle_manager import GradleManager


class ProjectChooserModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close the modal"),
        Binding("1", "switch_tab('switch-projects')", "Switch Projects"),
        Binding("2", "switch_tab('add-project')", "Add New Project"),
        Binding("/", "focus_search", "Search Projects"),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.selected_path = None
        self.all_projects = []
        self.filtered_projects = []

    def compose(self) -> ComposeResult:
        with Container(classes="project-chooser-modal"):
            yield Static("Project Manager", classes="modal-title")
            with TabbedContent(initial="switch-projects", id="project-tabs"):
                with TabPane("Switch Projects", id="switch-projects"):
                    yield Vertical(id="switch-projects-content")
                with TabPane("Add New Project", id="add-project"):
                    yield Vertical(id="add-project-content")

    def action_switch_tab(self, tab_id: str) -> None:
        tabbed_content = self.query_one("#project-tabs", TabbedContent)
        tabbed_content.active = tab_id

    def on_mount(self) -> None:
        self.all_projects = list(self.gradle_manager.list_all_projects().keys())
        self.filtered_projects = self.all_projects

        switch_content = self.query_one("#switch-projects-content", Vertical)
        project_option_list = OptionList()
        for project_path in self.filtered_projects:
            project_name = os.path.basename(project_path)
            project_option_list.add_option(Option(f"[bold cyan]{project_name}[/bold cyan]\n[dim]{project_path}[/dim]", id=project_path))

        switch_content.mount(
            Static("[bold]Select a Project[/bold]", classes="modal-section-title"),
            Input(placeholder="Search projects... (press / to focus)", classes="project-search"),
            project_option_list
        )

        add_content = self.query_one("#add-project-content", Vertical)
        self.dir_tree = DirectoryTree(Path.home())
        add_content.mount(
            Static("[bold]Select a Directory[/bold]", classes="modal-section-title"),
            Static("", classes="status-message"),
            self.dir_tree,
            Horizontal(
                Button("✓ Confirm", id="confirm_button", variant="success", classes="modal-button"),
                Button("✗ Cancel", id="cancel_button", variant="error", classes="modal-button"),
                classes="modal-button-bar"
            )
        )

    def action_focus_search(self):
        try:
            search_input = self.query_one(".project-search", Input)
            search_input.focus()
        except:
            pass

    def refresh_static(self, message: str):
        try:
            static_label = self.query_one(".status-message", Static)
            static_label.update(message)
        except NoMatches:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.has_class("project-search"):
            search_query = event.value.lower().strip()

            if search_query:
                self.filtered_projects = [
                    project for project in self.all_projects
                    if search_query in project.lower() or search_query in os.path.basename(project).lower()
                ]
            else:
                self.filtered_projects = self.all_projects

            try:
                option_list = self.query_one(OptionList)
                option_list.clear_options()
                for project_path in self.filtered_projects:
                    project_name = os.path.basename(project_path)
                    option_list.add_option(Option(f"[bold cyan]{project_name}[/bold cyan]\n[dim]{project_path}[/dim]", id=project_path))
            except:
                pass

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        selected_project = event.option.id
        if selected_project:
            self.gradle_manager.select_project(selected_project)
            self.dismiss_modal()

    async def on_directory_tree_directory_selected(self, directory_tree: DirectoryTree.DirectorySelected):
        self.selected_path = Path(directory_tree.path)
        self.refresh_static(f"Selected: {self.selected_path}")

    async def on_button_pressed(self, event: Button.Pressed):
        button = event.button
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
        self.app.project_chooser_open = False
        self.dismiss()

    def action_dismiss_modal(self):
        self.dismiss_modal()

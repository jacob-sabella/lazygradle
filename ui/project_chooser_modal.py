from pathlib import Path
import os

from rich.markup import escape

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import (
    Static,
    OptionList,
    DirectoryTree,
    Button,
    TabbedContent,
    TabPane,
    Input,
)
from textual.widgets._option_list import Option
from textual import events

from gradle.gradle_manager import GradleManager
from gradle.gradle_wrapper import GradleWrapper
from ui.gradlew_permission_modal import GradlewPermissionModal


class ProjectChooserModal(ModalScreen):
    SWITCH_HINT = "Enter opens the highlighted project · d removes it from this list · / searches"
    ADD_HINT = (
        "Highlight a folder that contains a Gradle build "
        "(build.gradle, settings.gradle, .kts, or gradlew), then choose Add Project."
    )
    GRADLE_MARKERS = (
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradlew",
    )

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close the modal"),
        Binding("1", "switch_tab('switch-projects')", "Switch Projects"),
        Binding("2", "switch_tab('add-project')", "Add New Project"),
        Binding("/", "focus_search", "Search Projects"),
        Binding("d", "delete_project", "Remove Project"),
        Binding("enter", "select_project", "Select Project"),
    ]

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager
        self.selected_path = None
        self.all_projects = []
        self.filtered_projects = []
        self.highlighted_project = None  # Track the highlighted project for deletion

    def compose(self) -> ComposeResult:
        with Container(classes="project-chooser-modal"):
            yield Static("Project Manager", classes="modal-title")
            with TabbedContent(initial="switch-projects", id="project-tabs"):
                with TabPane("[1] Switch Projects", id="switch-projects"):
                    yield Vertical(id="switch-projects-content")
                with TabPane("[2] Add New Project", id="add-project"):
                    yield Vertical(id="add-project-content")

    def action_switch_tab(self, tab_id: str) -> None:
        tabbed_content = self.query_one("#project-tabs", TabbedContent)
        tabbed_content.active = tab_id

    def on_mount(self) -> None:
        self.all_projects = list(self.gradle_manager.list_all_projects().keys())
        self.filtered_projects = self.all_projects

        switch_content = self.query_one("#switch-projects-content", Vertical)
        project_option_list = OptionList()
        self._fill_project_options(project_option_list)

        switch_content.mount(
            Static(self.SWITCH_HINT, classes="status-message"),
            Input(
                placeholder="Search projects  ( / )",
                classes="project-search",
            ),
            project_option_list,
            Horizontal(
                Button(
                    "✓ Open Project (Enter)",
                    id="select_project_button",
                    variant="success",
                    classes="modal-button",
                ),
                Button(
                    "✗ Remove (d)",
                    id="delete_project_button",
                    variant="error",
                    classes="modal-button",
                ),
                classes="modal-button-bar",
            ),
        )

        add_content = self.query_one("#add-project-content", Vertical)
        self.dir_tree = DirectoryTree(Path.home())
        add_content.mount(
            Static(self.ADD_HINT, classes="status-message"),
            self.dir_tree,
            Horizontal(
                Button(
                    "✓ Add Project",
                    id="confirm_button",
                    variant="success",
                    classes="modal-button",
                ),
                Button(
                    "Cancel (Esc)",
                    id="cancel_button",
                    variant="default",
                    classes="modal-button",
                ),
                classes="modal-button-bar",
            ),
        )

    def _fill_project_options(self, option_list: OptionList) -> None:
        """Populate the project list from filtered_projects, with an empty state."""
        option_list.clear_options()
        for project_path in self.filtered_projects:
            project_name = os.path.basename(project_path)
            option_list.add_option(
                Option(
                    f"[bold $text-accent]{escape(project_name)}[/]\n[dim]{escape(project_path)}[/dim]",
                    id=project_path,
                )
            )
        if not self.filtered_projects:
            message = (
                "[dim]No projects match your search.[/dim]"
                if self.all_projects
                else "[dim]No projects yet. Press 2 to add a Gradle project folder.[/dim]"
            )
            option_list.add_option(Option(message, disabled=True))

    def action_focus_search(self):
        try:
            search_input = self.query_one(".project-search", Input)
            search_input.focus()
        except:
            pass

    def refresh_static(self, message: str):
        """Update the status message in the add-project tab."""
        try:
            # Query specifically within the add-project-content to avoid TooManyMatches
            add_content = self.query_one("#add-project-content", Vertical)
            static_label = add_content.query_one(".status-message", Static)
            static_label.update(message)
        except NoMatches:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.has_class("project-search"):
            search_query = event.value.lower().strip()

            if search_query:
                self.filtered_projects = [
                    project
                    for project in self.all_projects
                    if search_query in project.lower()
                    or search_query in os.path.basename(project).lower()
                ]
            else:
                self.filtered_projects = self.all_projects

            try:
                self._fill_project_options(self.query_one(OptionList))
            except NoMatches:
                pass

    async def on_key(self, event: events.Key) -> None:
        """Handle key presses, specifically Enter to select project."""
        if event.key == "enter":
            # Check if we're in the switch-projects tab
            try:
                tabbed_content = self.query_one("#project-tabs", TabbedContent)
                if tabbed_content.active == "switch-projects":
                    # Check if the OptionList has focus
                    focused = self.app.focused
                    if isinstance(focused, OptionList) and focused.id != "recent-tasks-list":
                        # Prevent default OptionList behavior and call our select action
                        event.prevent_default()
                        await self.action_select_project()
            except:
                pass

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        # Clicking a project only highlights it (doesn't select and dismiss)
        # Track the highlighted project
        if event.option_list.id != "recent-tasks-list":
            self.highlighted_project = event.option.id

    async def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        # Track the currently highlighted project
        self.highlighted_project = event.option.id

    async def on_directory_tree_directory_selected(
        self, directory_tree: DirectoryTree.DirectorySelected
    ):
        self.selected_path = Path(directory_tree.path)
        if self._is_gradle_project(self.selected_path):
            self.refresh_static(
                f"[$text-success]✓ Gradle build found:[/] {escape(str(self.selected_path))}"
            )
        else:
            self.refresh_static(f"Selected: {escape(str(self.selected_path))}")

    def _is_gradle_project(self, path: Path) -> bool:
        return any((path / marker).exists() for marker in self.GRADLE_MARKERS) or any(
            path.glob("*.gradle")
        )

    async def on_button_pressed(self, event: Button.Pressed):
        button = event.button
        if button.id == "confirm_button":
            if self.selected_path is None or not self.selected_path.exists():
                self.refresh_static(
                    "[$text-warning]Highlight a folder in the tree and press Enter on it first.[/]"
                )
            elif self._is_gradle_project(self.selected_path):
                # Check gradlew permissions before adding the project
                await self.check_and_add_project(str(self.selected_path))
            else:
                self.refresh_static(
                    f"[$text-warning]No Gradle build in {escape(str(self.selected_path))}.[/] "
                    "Pick the folder that holds build.gradle(.kts) or settings.gradle(.kts)."
                )
        elif button.id == "cancel_button":
            self.dismiss_modal(should_refresh=False)
        elif button.id == "select_project_button":
            await self.action_select_project()
        elif button.id == "delete_project_button":
            await self.action_delete_project()

    async def check_and_add_project(self, project_path: str):
        """Check gradlew permissions and add the project if valid."""
        gradle_wrapper = GradleWrapper(project_path)
        has_permission, error_message = gradle_wrapper.check_gradlew_permissions()

        if not has_permission:
            # Show permission modal to fix or inform the user
            self.refresh_static(f"[$text-warning]{escape(error_message)}[/]")

            def on_permission_fixed(fixed: bool):
                if fixed:
                    # Permissions were fixed, now add the project
                    self.gradle_manager.add_project(project_path)
                    self.gradle_manager.select_project(project_path)
                    self.dismiss_modal()
                else:
                    # User chose not to fix or couldn't fix
                    self.refresh_static(
                        "[$text-error]Project not added: gradlew needs execute permission.[/]"
                    )

            # Push the permission modal
            self.app.push_screen(
                GradlewPermissionModal(project_path), callback=on_permission_fixed
            )
        else:
            # Permissions are fine, add the project normally
            self.gradle_manager.add_project(project_path)
            self.gradle_manager.select_project(project_path)
            self.dismiss_modal()

    def dismiss_modal(self, should_refresh: bool = True):
        self.app.project_chooser_open = False
        self.dismiss(should_refresh)

    def action_dismiss_modal(self):
        self.dismiss_modal(should_refresh=False)

    async def action_select_project(self):
        """Select the currently highlighted project and dismiss the modal."""
        if not self.highlighted_project:
            # Show message if no project is highlighted
            try:
                static_label = self.query_one("#switch-projects-content .status-message", Static)
                static_label.update("[$text-warning]No project highlighted. Use the arrow keys to pick one, then press Enter.[/]")
            except:
                pass
            return

        # Select the highlighted project
        self.gradle_manager.select_project(self.highlighted_project)
        self.dismiss_modal()

    async def action_delete_project(self):
        """Delete the currently highlighted project."""
        if not self.highlighted_project:
            # Show message if no project is highlighted
            try:
                # Try to get the status message in the switch-projects tab
                static_label = self.query_one("#switch-projects-content .status-message", Static)
                static_label.update("[$text-warning]No project highlighted. Pick one, then press d to remove it.[/]")
            except:
                pass
            return

        project_to_delete = self.highlighted_project
        project_name = os.path.basename(project_to_delete)

        # Delete the project from the configuration
        success = self.gradle_manager.delete_project(project_to_delete)

        if success:
            # Refresh the project list
            self.all_projects = list(self.gradle_manager.list_all_projects().keys())

            # Re-apply search filter if there was one
            try:
                search_input = self.query_one(".project-search", Input)
                search_query = search_input.value.lower().strip()

                if search_query:
                    self.filtered_projects = [
                        project
                        for project in self.all_projects
                        if search_query in project.lower()
                        or search_query in os.path.basename(project).lower()
                    ]
                else:
                    self.filtered_projects = self.all_projects
            except:
                self.filtered_projects = self.all_projects

            # Update the project list UI
            try:
                self._fill_project_options(self.query_one(OptionList))

                # Show success message
                try:
                    static_label = self.query_one("#switch-projects-content .status-message", Static)
                    static_label.update(
                        f"[$text-success]Removed {escape(project_name)} from lazygradle.[/] "
                        "[dim]No files were touched.[/dim]"
                    )
                except NoMatches:
                    pass

            except Exception as e:
                import logging
                logging.error(f"Error updating project list after deletion: {e}")

            # Clear the highlighted project
            self.highlighted_project = None
        else:
            # Show error message
            try:
                static_label = self.query_one("#switch-projects-content .status-message", Static)
                static_label.update(f"[$text-error]Could not remove {escape(project_name)}.[/]")
            except:
                pass

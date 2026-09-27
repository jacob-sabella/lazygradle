"""Gradle project display widget.

This module provides a widget for displaying the currently selected Gradle project
in the LazyGradle TUI interface.
"""

import os

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from gradle.gradle_manager import GradleManager


class GradleProjectChanger(Static):
    """Widget for displaying the currently selected Gradle project.

    Shows the project name and path in a formatted header, or displays a warning
    message if no project is currently selected.

    Attributes:
        gradle_manager: Manager for Gradle project operations and configuration.
    """

    def __init__(self, gradle_manager: GradleManager, **kwargs):
        """Initialize the project display widget.

        Args:
            gradle_manager: GradleManager instance for accessing project information.
            **kwargs: Additional arguments passed to the Static widget constructor.
        """
        super().__init__(**kwargs)
        self.gradle_manager = gradle_manager

    def compose(self) -> ComposeResult:
        """Compose the project display widget.

        Yields either a horizontal container with project information (name and path)
        or a warning message if no project is selected.

        Yields:
            Static widgets displaying project information or a warning message.
        """
        selected_project = self.gradle_manager.get_selected_project()
        if selected_project:
            project_name = os.path.basename(selected_project)
            project_path = selected_project
            yield Horizontal(
                Static("Project", classes="project-label"),
                Static(
                    f"[bold $text-accent]{escape(project_name)}[/]", classes="project-name"
                ),
                Static(f"[$text-muted]{escape(project_path)}[/]", classes="project-path"),
                classes="project-header",
            )
        else:
            yield Static(
                "⚠ No project selected. Press [bold]p[/bold] to add or choose one.",
                classes="project-warning",
            )

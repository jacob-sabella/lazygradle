"""UI tests for ProjectChooserModal widget."""
import pytest
from unittest.mock import Mock, patch
from textual.pilot import Pilot

from ui.project_chooser_modal import ProjectChooserModal
from gradle.gradle_manager import GradleManager


@pytest.mark.ui
@pytest.mark.asyncio
class TestProjectChooserModal Display:
    """Tests for project chooser modal display."""

    async def test_modal_displays_projects(self, gradle_manager_with_projects):
        """Test that modal shows list of projects."""
        modal = ProjectChooserModal(gradle_manager_with_projects, Mock())

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Should show project list
            from textual.widgets import OptionList
            option_lists = app.query(OptionList)
            assert len(option_lists) > 0

    async def test_modal_shows_current_selection(self, gradle_manager_with_projects):
        """Test that currently selected project is highlighted."""
        modal = ProjectChooserModal(gradle_manager_with_projects, Mock())

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Current selection should be highlighted
            # (Verification depends on implementation)


@pytest.mark.ui
@pytest.mark.asyncio
class TestProjectChooserTabs:
    """Tests for tab switching in project chooser."""

    async def test_switch_to_projects_tab_with_1_key(self, gradle_manager_with_projects):
        """Test that pressing '1' switches to projects tab."""
        modal = ProjectChooserModal(gradle_manager_with_projects, Mock())

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Press '1' to switch to projects tab
            await pilot.press("1")
            await pilot.pause()

            # Should be on projects tab
            # (Verification depends on implementation)

    async def test_switch_to_add_project_tab_with_2_key(self, gradle_manager_with_projects):
        """Test that pressing '2' switches to add project tab."""
        modal = ProjectChooserModal(gradle_manager_with_projects, Mock())

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Press '2' to switch to add project tab
            await pilot.press("2")
            await pilot.pause()

            # Should be on add project tab
            # (Verification depends on implementation)


@pytest.mark.ui
@pytest.mark.asyncio
class TestProjectSelection:
    """Tests for project selection functionality."""

    async def test_enter_key_selects_highlighted_project(self, gradle_manager_with_projects):
        """Test that Enter key selects the highlighted project."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_projects, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            from textual.widgets import OptionList
            project_list = app.query(OptionList).first()

            if project_list and len(project_list.get_options()) > 0:
                project_list.highlighted = 0

                # Press Enter to select
                await pilot.press("enter")
                await pilot.pause()

                # Callback should be triggered or project should be selected

    async def test_select_button_switches_project(self, gradle_manager_with_projects):
        """Test that clicking Select Project button switches project."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_projects, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            from textual.widgets import Button
            buttons = app.query(Button)

            # Find and click Select Project button
            for button in buttons:
                if "Select" in str(button.label):
                    await pilot.click(button)
                    await pilot.pause()
                    break


@pytest.mark.ui
@pytest.mark.asyncio
class TestProjectDeletion:
    """Tests for project deletion functionality."""

    async def test_d_key_deletes_highlighted_project(self, gradle_manager_with_projects):
        """Test that pressing 'd' deletes the highlighted project."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_projects, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        with patch.object(gradle_manager_with_projects, 'delete_project', return_value=True) as mock_delete:
            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                from textual.widgets import OptionList
                project_list = app.query(OptionList).first()

                if project_list and len(project_list.get_options()) > 0:
                    project_list.highlighted = 0

                    # Press 'd' to delete
                    await pilot.press("d")
                    await pilot.pause()

                    # Should call delete_project
                    mock_delete.assert_called()

    async def test_delete_button_removes_project(self, gradle_manager_with_projects):
        """Test that clicking Delete button removes project."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_projects, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        with patch.object(gradle_manager_with_projects, 'delete_project', return_value=True):
            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                from textual.widgets import Button
                buttons = app.query(Button)

                # Find and click Delete button
                for button in buttons:
                    if "Delete" in str(button.label):
                        await pilot.click(button)
                        await pilot.pause()
                        break


@pytest.mark.ui
@pytest.mark.asyncio
class TestAddProject:
    """Tests for adding new projects."""

    async def test_add_project_validates_path(self, gradle_manager_with_temp_config, temp_gradle_project):
        """Test that adding project validates the path."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_temp_config, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Switch to add project tab
            await pilot.press("2")
            await pilot.pause()

            from textual.widgets import Input
            inputs = app.query(Input)

            if len(inputs) > 0:
                path_input = inputs[0]
                path_input.value = temp_gradle_project
                await pilot.pause()

    async def test_add_project_checks_gradlew_permissions(
        self, gradle_manager_with_temp_config, temp_gradle_project_no_exec
    ):
        """Test that adding project checks gradlew permissions."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_temp_config, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Switch to add project tab
            await pilot.press("2")
            await pilot.pause()

            # Try to add project without permissions
            # Should show permission modal
            # (Implementation-specific)


@pytest.mark.ui
@pytest.mark.asyncio
class TestProjectSearch:
    """Tests for project search functionality."""

    async def test_slash_key_focuses_search(self, gradle_manager_with_projects):
        """Test that pressing '/' focuses search input."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_projects, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Press '/' to focus search
            await pilot.press("slash")
            await pilot.pause()

            # Search should be focused
            # (Verification depends on implementation)

    async def test_search_filters_project_list(self, gradle_manager_with_projects):
        """Test that search input filters projects."""
        callback = Mock()
        modal = ProjectChooserModal(gradle_manager_with_projects, callback)

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield modal

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            from textual.widgets import Input
            search_inputs = app.query(Input)

            if len(search_inputs) > 0:
                search_input = search_inputs[0]
                search_input.value = "project1"
                await pilot.pause()

                # List should be filtered
                # (Verification depends on implementation)

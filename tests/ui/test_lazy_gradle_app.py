"""UI tests for LazyGradleApp using Textual's pilot framework."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from textual.pilot import Pilot

from ui.lazy_gradle_app import LazyGradleApp
from gradle.gradle_manager import GradleManager


@pytest.mark.ui
@pytest.mark.asyncio
class TestLazyGradleAppInit:
    """Tests for LazyGradleApp initialization."""

    async def test_app_starts_successfully(self, gradle_manager_with_temp_config):
        """Test that the app starts without errors."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            async with app.run_test() as pilot:
                # App should be running
                assert app.is_running

    async def test_app_loads_saved_theme(self, gradle_manager_with_projects):
        """Test that app loads saved theme from config."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_projects):
            app = LazyGradleApp()

            async with app.run_test() as pilot:
                # Theme should be loaded from config
                assert app.theme == "nord"

    async def test_app_with_no_saved_theme(self, gradle_manager_with_temp_config):
        """Test app with no saved theme uses default."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            async with app.run_test() as pilot:
                # Should have a default theme
                assert app.theme is not None


@pytest.mark.ui
@pytest.mark.asyncio
class TestAppSizeWarning:
    """Tests for terminal size warning functionality."""

    async def test_shows_warning_for_small_terminal(self, gradle_manager_with_temp_config):
        """Test that size warning appears for terminals below minimum size."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            # Use a small terminal size
            async with app.run_test(size=(50, 20)) as pilot:
                await pilot.pause()

                # Should show size warning widget
                from ui.size_warning_widget import SizeWarningWidget
                warning_widgets = app.query(SizeWarningWidget)
                assert len(warning_widgets) > 0

    async def test_shows_main_content_for_adequate_terminal(self, gradle_manager_with_temp_config):
        """Test that main content appears for terminals meeting minimum size."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            # Use adequate terminal size
            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Should show main widget
                from ui.widget import LazyGradleWidget
                main_widgets = app.query(LazyGradleWidget)
                assert len(main_widgets) > 0


@pytest.mark.ui
@pytest.mark.asyncio
class TestKeyBindings:
    """Tests for app-level key bindings."""

    async def test_p_key_opens_project_chooser(self, gradle_manager_with_projects):
        """Test that pressing 'p' opens the project chooser modal."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_projects):
            app = LazyGradleApp()

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Press 'p' to open project chooser
                await pilot.press("p")
                await pilot.pause()

                # Should show project chooser modal
                from ui.project_chooser_modal import ProjectChooserModal
                modals = app.query(ProjectChooserModal)
                assert len(modals) > 0

    async def test_ctrl_p_opens_theme_selector(self, gradle_manager_with_temp_config):
        """Test that Ctrl+P opens Textual's theme selector."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Press Ctrl+P for theme selector
                # Note: This uses Textual's built-in command palette
                # We just verify the binding exists
                assert "ctrl+p" in [binding.key for binding in app._bindings.keys.values()]


@pytest.mark.ui
@pytest.mark.asyncio
class TestThemePersistence:
    """Tests for theme persistence functionality."""

    async def test_theme_change_saves_to_config(self, gradle_manager_with_temp_config):
        """Test that changing theme saves to configuration."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Manually change theme
                app.theme = "dracula"
                await pilot.pause()

                # Config should be updated
                assert gradle_manager_with_temp_config.get_theme() == "dracula"


@pytest.mark.ui
@pytest.mark.asyncio
class TestProjectSelection:
    """Tests for project selection and display."""

    async def test_displays_current_project(self, gradle_manager_with_projects):
        """Test that current project is displayed."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_projects):
            app = LazyGradleApp()

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # Should show the selected project
                from ui.gradle_project_changer import GradleProjectChanger
                project_changers = app.query(GradleProjectChanger)
                assert len(project_changers) > 0

    async def test_no_project_selected_state(self, gradle_manager_with_temp_config):
        """Test app state when no project is selected."""
        with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_temp_config):
            app = LazyGradleApp()

            async with app.run_test(size=(120, 35)) as pilot:
                await pilot.pause()

                # App should handle no project gracefully
                assert app.is_running

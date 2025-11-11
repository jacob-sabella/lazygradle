# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LazyGradle is a TUI (Terminal User Interface) application built with Textual that provides a user-friendly interface for managing and running Gradle tasks. It allows users to switch between multiple Gradle projects, view available tasks, and execute them with or without parameters while streaming output in real-time.

## Development Setup

### Running the Application
```bash
python app.py
```

### Python Environment
- Python 3.13+ required
- Uses virtual environment at `venv/`
- Dependencies managed via `requirements.txt` (install with `pip install -r requirements.txt`)
- Main dependency: Textual (TUI framework)

## Architecture

### Core Components

**Entry Point**: `app.py`
- Initializes logging with both console and file output (`lazygradleapp.log`)
- Creates `GradleManager` instance
- Launches `LazyGradleApp`

**Gradle Layer** (`gradle/`):
- `GradleWrapper`: Low-level wrapper for executing Gradle commands with streaming support
  - Auto-detects `gradlew` vs system `gradle`
  - Streams stdout/stderr via callbacks using threading
  - Supports timeouts
  - Key methods: `list_all_tasks()`, `get_task_metadata()`, `run_custom_gradle_task()`
  - Permission checking: `check_gradlew_permissions()`, `can_fix_gradlew_permissions()`, `fix_gradlew_permissions()`
  - Enhanced error handling for PermissionError exceptions when executing gradlew

- `GradleManager`: High-level project and task manager
  - Manages multiple Gradle projects via config file at `~/.config/lazygradle/gradle_cache.json`
  - Caches task lists and metadata per project
  - Tracks currently selected project
  - Provides `run_task()` and `run_task_with_parameters()` with streaming handlers
  - Project management: `add_project()`, `delete_project()`, `select_project()`
  - Theme management: `get_theme()`, `set_theme()` for persisting UI theme preference
  - Auto-selects another project when deleting the currently selected one
  - Key classes: `Task`, `Project`, `Config`

**UI Layer** (`ui/`):
- `LazyGradleApp`: Main Textual app with tab system
  - Keybindings: `p` (show project chooser), `Ctrl+P` (Textual's built-in theme selector)
  - Manages app-level state and modals
  - Enforces minimum terminal size (100x30) - displays warning message if terminal is too small
  - Listens for resize events and dynamically switches between warning and main content
  - Uses Textual's built-in theme system (no custom dark mode toggle)
  - Theme persistence: Selected theme is automatically saved to config and restored on startup
  - Watches for theme changes via `watch_theme()` and saves them immediately

- `SizeWarningWidget`: Warning display for undersized terminals
  - Shows current terminal dimensions vs minimum required
  - Styled with error border and centered content
  - Auto-updates on terminal resize

- `LazyGradleWidget`: Tab container widget
  - Two tabs: "Current Setup", "Task Manager"
  - Dynamically mounts content based on selected tab via `switch_to_tab()`
  - Includes `refresh_current_tab()` method to re-render the active tab when data changes
  - Manages `TaskTracker` instance for tracking all task executions

- `GradleProjectTaskViewer`: Core task viewer (left: task list, right: description + buttons)
  - Keybindings: `r` (run task), `R` (run task with parameters), `/` (search tasks), `F5` (refresh task list)
  - Uses `OptionList` for task selection
  - Tasks are alphabetized by name (case-insensitive)
  - Runs tasks in background using `asyncio.create_task()` to keep UI responsive
  - Registers tasks with `TaskTracker` when executing
  - Streams task output to tracked tasks via callbacks using `asyncio.to_thread`
  - Task list refresh (F5): Non-blocking refresh that clears the list, shows loading indicator, and re-fetches tasks from Gradle

- `GradleProjectChanger`: Widget for displaying/switching current project

- `TaskTracker`: Manages running and historical task executions
  - Tracks up to 50 tasks (configurable)
  - Stores task status (running/completed/failed), timestamps, and output
  - Provides callbacks for UI updates when tasks change
  - Maintains task list with running tasks first, then history

- `TaskManagerWidget`: Task execution history and output viewer
  - Left panel: List of all tasks (running + history) with status icons and durations
  - Right panel: Selected task's full output with metadata
  - Status icons: ▶ (running), ✓ (completed), ✗ (failed)
  - Includes "Clear History" button to remove completed/failed tasks
  - Auto-updates display when tasks are updated or completed

- `ProjectChooserModal`: Modal for selecting/adding Gradle projects
  - Two tabs: "Switch Projects" and "Add New Project"
  - Keybindings: `1` (switch to projects tab), `2` (add project tab), `/` (search projects), `Enter` (select highlighted project), `d` (delete highlighted project)
  - **Selection behavior**: Clicking a project only highlights it; press Enter or click "Select Project" button to actually switch to it
  - Enter key handling: Intercepts Enter key via `on_key()` to prevent OptionList default behavior and trigger custom selection
  - Select button: Switches to the highlighted project and closes modal
  - Delete button: Removes highlighted project from configuration
  - Auto-selects another project if deleting the currently selected one
  - Validates gradlew permissions when adding new projects
  - Automatically shows `GradlewPermissionModal` if execute permissions are missing

- `GradlewPermissionModal`: Modal for handling gradlew permission issues
  - Detects if current user can fix permissions automatically
  - Shows "Fix Permissions" button if user has write access to gradlew file
  - Shows manual chmod instructions if elevated permissions are needed
  - Blocks project addition until permissions are fixed

- `RunTaskWithParametersModal`: Modal for entering task parameters before execution

**DTOs** (`gradle/dto/`):
- `Task`: Task name and description
- `TaskList`: List of tasks with success/error state
- `TaskMetadata`: Task metadata string with success/error state
- `GradleError`: Error message and return code

### Key Patterns

**Streaming Output & Background Execution**: All Gradle command execution supports optional `on_stdout` and `on_stderr` callbacks for real-time output streaming. Tasks run in background using `asyncio.create_task()` wrapping `asyncio.to_thread()` - this keeps the UI fully responsive during long-running Gradle operations. Callbacks use `loop.call_soon_threadsafe()` to safely update UI widgets from worker threads.

**Config Persistence**: `GradleManager` persists project information (tasks, metadata, selected project) to `~/.config/lazygradle/gradle_cache.json` using JSON serialization.

**Error Handling**: All Gradle operations return `Tuple[Optional[str], Optional[GradleError]]` where success returns `(output, None)` and failure returns `(None, error)`.

**Tab System**: The UI uses Textual's `Tabs` widget with dynamic content mounting - when a tab is activated, the old content is removed and new content is mounted to the container.

**Widget Refresh After Modals**: Since Textual widgets' `compose()` method only runs once at mount time, widgets showing dynamic data need to be refreshed after modal operations. This is handled by:
1. Passing a callback to `push_screen()` when opening modals
2. The callback triggers `refresh_current_tab()` on the `LazyGradleWidget`
3. `refresh_current_tab()` calls `switch_to_tab()` again, which remounts widgets with fresh data

## Common Tasks

### Adding a New Gradle Command
1. Add method to `GradleWrapper` that calls `run_gradle_command()` with appropriate command args
2. Add corresponding method to `GradleManager` that wraps the `GradleWrapper` call with proper error handling
3. If UI integration needed, add button/keybinding to appropriate widget

### Adding a New Tab
1. Add new `Tab` to `Tabs` widget in `LazyGradleWidget.compose()`
2. Add new case to `switch_to_tab()` method that mounts the appropriate content

### Modifying Task Execution
- Task execution happens in `GradleProjectTaskViewer.run_task()` and `run_task_with_parameters()`
- Output streaming is handled via callbacks that write to the `RunTaskOutput` widget
- Always use `asyncio.to_thread` to offload blocking Gradle calls

## Configuration

User configuration is stored at `~/.config/lazygradle/gradle_cache.json` with the following structure:
```json
{
  "projects": {
    "/path/to/project": {
      "tasks": [{"name": "build", "description": "Assembles and tests this project"}],
      "metadata": {"taskName": "metadata string"},
      "recent_tasks": []
    }
  },
  "currently_selected": "/path/to/project",
  "theme": "nord"
}
```

**Configuration fields:**
- `projects`: Dictionary of Gradle projects with their tasks, metadata, and recent task history
- `currently_selected`: Path to the currently active project
- `theme`: Name of the selected Textual theme (e.g., "nord", "dracula", "gruvbox", etc.)

## Styling

CSS is defined in `ui/lazy_gradle_app.css` and loaded by `LazyGradleApp.CSS_PATH`. Widgets use the `classes` parameter to apply styles.

## Known Issues & Solutions

### Subprocess and Working Directory
**Issue**: When using `subprocess.run()` with `shell=True`, the `cwd` parameter doesn't work correctly on Linux/Unix systems. Commands execute in the current working directory instead of the specified directory.

**Solution**: Never use `shell=True` in `GradleWrapper.run_gradle_command()`. Pass the command as a list without shell interpretation, and ensure Gradle wrapper commands use `./gradlew` (relative path) instead of `gradlew`.

### Widget State Not Updating
**Issue**: Textual widgets only call `compose()` once when mounted. If underlying data changes (e.g., after selecting a new project), the UI won't update automatically.

**Solution**: Implement a refresh mechanism by:
1. Adding a callback to `push_screen()` when showing modals
2. Having the callback trigger a re-mount of affected widgets
3. For `LazyGradleWidget`, use `refresh_current_tab()` to remount the active tab's content

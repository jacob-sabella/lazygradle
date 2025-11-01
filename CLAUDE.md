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

- `GradleManager`: High-level project and task manager
  - Manages multiple Gradle projects via config file at `~/.config/lazygradle/gradle_cache.json`
  - Caches task lists and metadata per project
  - Tracks currently selected project
  - Provides `run_task()` and `run_task_with_parameters()` with streaming handlers
  - Key classes: `Task`, `Project`, `Config`

**UI Layer** (`ui/`):
- `LazyGradleApp`: Main Textual app with tab system
  - Keybindings: `d` (toggle dark mode), `p` (show project chooser)
  - Manages app-level state and modals

- `LazyGradleWidget`: Tab container widget
  - Three tabs: "Current Setup", "Dummy Tab 1", "Dummy Tab 2"
  - Dynamically mounts content based on selected tab via `switch_to_tab()`
  - Includes `refresh_current_tab()` method to re-render the active tab when data changes

- `GradleProjectTaskViewer`: Core task viewer (left: task list, right: description + buttons)
  - Keybindings: `r` (run task), `R` (run task with parameters)
  - Uses `OptionList` for task selection
  - Streams task output via callbacks to `RunTaskOutput` widget using `asyncio.to_thread`

- `GradleProjectChanger`: Widget for displaying/switching current project

- `RunTaskOutput`: Output display using Textual's `RichLog` for streaming task output

- `ProjectChooserModal`: Modal for selecting/adding Gradle projects

- `RunTaskWithParametersModal`: Modal for entering task parameters before execution

**DTOs** (`gradle/dto/`):
- `Task`: Task name and description
- `TaskList`: List of tasks with success/error state
- `TaskMetadata`: Task metadata string with success/error state
- `GradleError`: Error message and return code

### Key Patterns

**Streaming Output**: All Gradle command execution supports optional `on_stdout` and `on_stderr` callbacks for real-time output streaming. Threading is used to stream output without blocking, and `asyncio.to_thread` is used in the UI layer to keep Textual's event loop responsive.

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
      "metadata": {"taskName": "metadata string"}
    }
  },
  "currently_selected": "/path/to/project"
}
```

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

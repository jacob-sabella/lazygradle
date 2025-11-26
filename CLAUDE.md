# CLAUDE.md

LazyGradle is a Textual-based TUI for managing Gradle tasks across multiple projects with real-time streaming output.

## Quick Reference

**Run app**: `python app.py`
**Python**: 3.13+ required, uses `venv/`, dependencies in `requirements.txt`
**Config**: `~/.config/lazygradle/gradle_cache.json`
**Entry**: `app.py` → `GradleManager` → `LazyGradleApp`

## Architecture

**Gradle Layer** (`gradle/`):
- `GradleWrapper`: Executes Gradle commands with streaming callbacks, auto-detects `gradlew` vs `gradle`, handles permissions
- `GradleManager`: Multi-project manager, caches tasks/metadata, provides `run_task()` with streaming, persists config

**UI Layer** (`ui/`):
- `LazyGradleApp`: Main app, enforces 100x30 min size, theme persistence via `watch_theme()`
- `LazyGradleWidget`: Tab container, uses `refresh_current_tab()` to remount after data changes
- `GradleProjectTaskViewer`: Task list + execution, runs tasks via `asyncio.create_task()` + `asyncio.to_thread()`
- `TaskTracker`: Manages running/historical task executions with callbacks
- `TaskManagerWidget`: Displays task history and output
- `ProjectChooserModal`: Project switcher, validates gradlew permissions, triggers `GradlewPermissionModal` if needed

## Critical Patterns

**Streaming & Threading**: All Gradle commands support `on_stdout`/`on_stderr` callbacks. Tasks use `asyncio.create_task(asyncio.to_thread())` to keep UI responsive. Callbacks use `loop.call_soon_threadsafe()` for thread safety.

**Widget Refresh**: Textual's `compose()` runs once at mount. After modals, pass callback to `push_screen()` that calls `refresh_current_tab()` to remount widgets with fresh data.

**Error Handling**: All Gradle operations return `Tuple[Optional[str], Optional[GradleError]]`.

## Known Issues

**subprocess with shell=True**: Never use `shell=True` in `GradleWrapper.run_gradle_command()`. The `cwd` parameter doesn't work on Linux/Unix. Pass commands as lists and use `./gradlew` (not `gradlew`).

## IMPORTANT

**Do not run this app inline in Claude Code** - it overloads the output stream. **Do not update CLAUDE.md unless explicitly asked.**

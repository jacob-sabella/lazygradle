# Testing Guide for LazyGradle

This document provides comprehensive guidance on testing the LazyGradle TUI application.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Use the test runner script
./scripts/run_tests.sh coverage
```

## Test Architecture

### Test Pyramid

LazyGradle follows the testing pyramid approach:

```
         /\
        /UI\        <- Fewer UI tests (complex, slower)
       /----\
      / Intg \      <- Integration tests (medium complexity)
     /--------\
    /   Unit   \    <- Many unit tests (simple, fast)
   /------------\
```

### Testing Layers

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions and classes in isolation
   - Fast execution
   - Heavy use of mocking
   - Examples: GradleWrapper methods, GradleManager operations

2. **Integration Tests** (`tests/integration/`)
   - Test interactions between components
   - Use real file system operations
   - Test complete workflows
   - Examples: Adding project → updating tasks → running task

3. **UI Tests** (`tests/ui/`)
   - Test Textual TUI components using Pilot framework
   - Test user interactions and key bindings
   - Verify widget composition and display
   - Examples: Key press simulations, modal interactions

## Test Fixtures

### Provided Fixtures

Located in `tests/conftest.py`:

#### Temporary Project Fixtures

```python
def test_with_temp_project(temp_gradle_project):
    """Test using a temporary Gradle project with executable gradlew."""
    wrapper = GradleWrapper(temp_gradle_project)
    # Test code here

def test_permission_issues(temp_gradle_project_no_exec):
    """Test using a project without execute permissions."""
    wrapper = GradleWrapper(temp_gradle_project_no_exec)
    # Test code here
```

#### Configuration Fixtures

```python
def test_with_empty_config(gradle_manager_with_temp_config):
    """Test with a fresh GradleManager."""
    manager = gradle_manager_with_temp_config
    # Test code here

def test_with_populated_config(gradle_manager_with_projects):
    """Test with pre-configured projects."""
    manager = gradle_manager_with_projects
    # manager has 2 projects already configured
```

#### Mock Data Fixtures

```python
def test_with_mock_tasks(mock_task_list):
    """Test with mock task data."""
    tasks = mock_task_list
    # tasks contains sample Gradle tasks

def test_with_mock_metadata(mock_task_metadata):
    """Test with mock metadata."""
    metadata = mock_task_metadata
    # metadata contains sample task info
```

## Testing Patterns

### Pattern 1: Testing Async UI Components

```python
import pytest
from textual.app import App

@pytest.mark.ui
@pytest.mark.asyncio
async def test_my_widget():
    """Test a Textual widget."""
    from ui.my_widget import MyWidget

    widget = MyWidget()

    class TestApp(App):
        def compose(self):
            yield widget

    app = TestApp()

    async with app.run_test(size=(120, 35)) as pilot:
        # Wait for rendering
        await pilot.pause()

        # Simulate key press
        await pilot.press("enter")
        await pilot.pause()

        # Assert expected behavior
        assert widget.some_property == expected_value
```

### Pattern 2: Testing with Mocked Subprocess

```python
from unittest.mock import patch, Mock

def test_gradle_command(temp_gradle_project):
    """Test Gradle command execution."""
    wrapper = GradleWrapper(temp_gradle_project)

    mock_result = Mock()
    mock_result.stdout = b"Build successful\n"
    mock_result.returncode = 0

    with patch('subprocess.run', return_value=mock_result):
        output, error = wrapper.run_gradle_command(["./gradlew", "build"])

        assert error is None
        assert output == "Build successful"
```

### Pattern 3: Testing Callbacks

```python
def test_streaming_callbacks(temp_gradle_project):
    """Test that streaming callbacks are invoked."""
    wrapper = GradleWrapper(temp_gradle_project)

    lines = []

    def on_stdout(line):
        lines.append(line)

    mock_process = Mock()
    mock_process.stdout = iter(["Line 1", "Line 2"])
    mock_process.stderr = iter([])
    mock_process.wait.return_value = 0

    with patch('subprocess.Popen', return_value=mock_process):
        wrapper.run_gradle_command(
            ["./gradlew", "build"],
            on_stdout=on_stdout
        )

        assert len(lines) == 2
        assert "Line 1" in lines
```

### Pattern 4: Testing Configuration Persistence

```python
def test_config_persists(temp_config_dir, monkeypatch):
    """Test that configuration saves and loads."""
    config_file = temp_config_dir / "gradle_cache.json"

    monkeypatch.setattr(GradleManager, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(GradleManager, "CONFIG_FILE", config_file)

    # Create and modify manager
    manager1 = GradleManager()
    manager1.set_theme("dracula")

    # Create new instance and verify it loaded the config
    manager2 = GradleManager()
    assert manager2.get_theme() == "dracula"
```

## Testing Utilities

### Mock Gradle Projects

Use `MockGradleProject` from `tests/fixtures/mock_gradle_project.py`:

```python
from tests.fixtures.mock_gradle_project import MockGradleProject
import tempfile

def test_with_mock_project():
    """Test using a mock Gradle project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project = MockGradleProject(temp_dir)

        # Add custom content
        project.create_java_class("com.example", "Main")
        project.create_gradle_properties({"org.gradle.daemon": "false"})

        # Use the project
        wrapper = GradleWrapper(project.get_path())
        # Test code here
```

### Mock Gradle Output

Generate realistic Gradle output:

```python
from tests.fixtures.mock_gradle_project import MockGradleOutput

def test_task_parsing():
    """Test parsing Gradle task output."""
    tasks = [
        ("build", "Assembles and tests this project"),
        ("clean", "Deletes the build directory"),
    ]

    output = MockGradleOutput.tasks_output(tasks)

    # Parse output
    parsed_tasks = parse_tasks(output)
    assert len(parsed_tasks) == 2
```

## Testing Best Practices

### 1. Test Naming Convention

```python
# Good: Descriptive test names
def test_gradle_wrapper_lists_all_tasks_successfully():
    pass

def test_gradle_wrapper_handles_permission_error():
    pass

# Bad: Vague test names
def test_wrapper():
    pass

def test_error():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_add_project():
    # Arrange
    manager = GradleManager()
    project_path = "/path/to/project"

    # Act
    manager.add_project(project_path)

    # Assert
    assert project_path in manager.list_all_projects()
```

### 3. One Assertion Per Test (When Possible)

```python
# Good: Single focused test
def test_project_is_added():
    manager = GradleManager()
    manager.add_project("/path/to/project")
    assert "/path/to/project" in manager.list_all_projects()

def test_added_project_is_auto_selected():
    manager = GradleManager()
    manager.add_project("/path/to/project")
    assert manager.get_selected_project() == "/path/to/project"

# Acceptable: Related assertions
def test_delete_project_updates_state():
    manager = GradleManager()
    manager.add_project("/project1")
    manager.add_project("/project2")

    manager.delete_project("/project1")

    projects = manager.list_all_projects()
    assert "/project1" not in projects  # Related assertion 1
    assert "/project2" in projects       # Related assertion 2
```

### 4. Isolate Tests

```python
# Good: Each test is independent
def test_feature_a(gradle_manager_with_temp_config):
    manager = gradle_manager_with_temp_config
    # Test doesn't depend on other tests

def test_feature_b(gradle_manager_with_temp_config):
    manager = gradle_manager_with_temp_config
    # Fresh fixture for each test

# Bad: Tests depend on each other
shared_manager = None

def test_setup():
    global shared_manager
    shared_manager = GradleManager()

def test_feature():  # Depends on test_setup
    global shared_manager
    # Tests are coupled
```

### 5. Use Markers Appropriately

```python
@pytest.mark.unit
def test_simple_function():
    """Fast unit test."""
    pass

@pytest.mark.integration
def test_full_workflow():
    """Integration test."""
    pass

@pytest.mark.slow
def test_long_running_operation():
    """Test that takes time."""
    pass

@pytest.mark.ui
@pytest.mark.asyncio
async def test_widget():
    """UI test with async."""
    pass
```

## Common Testing Scenarios

### Testing Error Conditions

```python
def test_handles_missing_gradlew():
    """Test behavior when gradlew is missing."""
    wrapper = GradleWrapper("/nonexistent/path")

    has_permission, error = wrapper.check_gradlew_permissions()

    assert has_permission is False
    assert "not found" in error
```

### Testing State Changes

```python
def test_theme_changes_are_persisted(gradle_manager_with_temp_config):
    """Test that theme changes are saved."""
    manager = gradle_manager_with_temp_config

    # Initial state
    assert manager.get_theme() is None

    # Change state
    manager.set_theme("dracula")

    # Verify change
    assert manager.get_theme() == "dracula"

    # Verify persistence
    config_file = manager.CONFIG_FILE
    import json
    with open(config_file) as f:
        data = json.load(f)
    assert data["theme"] == "dracula"
```

### Testing UI Interactions

```python
@pytest.mark.ui
@pytest.mark.asyncio
async def test_key_binding(gradle_manager_with_projects):
    """Test that key binding triggers action."""
    from ui.lazy_gradle_app import LazyGradleApp

    with patch('ui.lazy_gradle_app.GradleManager', return_value=gradle_manager_with_projects):
        app = LazyGradleApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Press key
            await pilot.press("p")
            await pilot.pause()

            # Verify modal is shown
            from ui.project_chooser_modal import ProjectChooserModal
            modals = app.query(ProjectChooserModal)
            assert len(modals) > 0
```

## Debugging Tests

### Run Single Test with Output

```bash
pytest tests/unit/test_gradle_wrapper.py::TestGradleWrapperInit::test_initialization -sv
```

### Use pdb for Debugging

```python
def test_debug_example():
    """Test with debugger."""
    import pdb; pdb.set_trace()

    # Code to debug
    result = some_function()
    assert result is not None
```

### Verbose Pytest Output

```bash
pytest -vv  # Extra verbose
pytest --tb=long  # Long traceback format
pytest -l  # Show local variables in tracebacks
```

## Continuous Integration

Tests run automatically on CI/CD. Ensure your tests:

1. Don't depend on external services
2. Clean up temporary resources
3. Are deterministic (no random failures)
4. Complete in reasonable time

## Coverage Goals

- **Overall**: > 80%
- **Core Components** (GradleWrapper, GradleManager): > 90%
- **UI Components**: > 70%
- **DTOs**: 100%

Check coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

## Further Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Textual Testing Guide](https://textual.textualize.io/guide/testing/)
- [Python Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

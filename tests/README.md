# LazyGradle Test Suite

Comprehensive test suite for the LazyGradle TUI application, covering unit tests, integration tests, and UI tests.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Categories](#test-categories)
- [Writing New Tests](#writing-new-tests)
- [Coverage](#coverage)
- [Continuous Integration](#continuous-integration)

## Overview

The LazyGradle test suite uses **pytest** as the testing framework and includes:

- **Unit Tests**: Testing individual components in isolation
- **Integration Tests**: Testing interactions between components
- **UI Tests**: Testing the Textual TUI interface using the Pilot framework
- **Mock Utilities**: Fixtures and helpers for creating test scenarios

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared pytest fixtures
├── README.md                   # This file
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── test_gradle_wrapper.py  # GradleWrapper tests
│   └── test_gradle_manager.py  # GradleManager tests
├── ui/                         # TUI tests using Textual pilot
│   ├── __init__.py
│   ├── test_lazy_gradle_app.py # Main app tests
│   ├── test_task_viewer.py     # Task viewer widget tests
│   ├── test_project_chooser_modal.py  # Project chooser tests
│   └── test_task_manager.py    # Task manager tests
├── integration/                # End-to-end integration tests
│   ├── __init__.py
│   └── test_end_to_end.py      # Full workflow tests
└── fixtures/                   # Test utilities and mocks
    ├── __init__.py
    └── mock_gradle_project.py  # Mock Gradle project creator
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# UI tests only
pytest -m ui

# Integration tests only
pytest -m integration

# Run tests in a specific file
pytest tests/unit/test_gradle_wrapper.py

# Run a specific test
pytest tests/unit/test_gradle_wrapper.py::TestGradleWrapperInit::test_initialization
```

### Run Tests with Coverage

```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Tests in Verbose Mode

```bash
pytest -v
```

### Run Tests with Output

```bash
# Show print statements
pytest -s

# Show print statements and verbose
pytest -sv
```

## Test Categories

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests across components
- `@pytest.mark.ui`: UI tests using Textual's pilot framework
- `@pytest.mark.slow`: Tests that take longer to run
- `@pytest.mark.requires_gradle`: Tests requiring actual Gradle installation

### Skip Slow Tests

```bash
pytest -m "not slow"
```

### Skip Tests Requiring Gradle

```bash
pytest -m "not requires_gradle"
```

## Writing New Tests

### Unit Test Example

```python
import pytest
from gradle.gradle_wrapper import GradleWrapper

@pytest.mark.unit
class TestMyFeature:
    """Tests for my new feature."""

    def test_basic_functionality(self, temp_gradle_project):
        """Test that my feature works."""
        wrapper = GradleWrapper(temp_gradle_project)

        # Test implementation
        result = wrapper.my_method()

        assert result is not None
```

### UI Test Example

```python
import pytest
from textual.pilot import Pilot
from ui.my_widget import MyWidget

@pytest.mark.ui
@pytest.mark.asyncio
class TestMyWidget:
    """Tests for MyWidget."""

    async def test_widget_displays(self):
        """Test that widget displays correctly."""
        widget = MyWidget()

        from textual.app import App

        class TestApp(App):
            def compose(self):
                yield widget

        app = TestApp()

        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause()

            # Verify widget state
            assert app.is_running
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

- `temp_gradle_project`: Temporary Gradle project with executable gradlew
- `temp_gradle_project_no_exec`: Temporary Gradle project without execute permissions
- `temp_config_dir`: Temporary config directory
- `gradle_manager_with_temp_config`: GradleManager with temporary config
- `gradle_manager_with_projects`: GradleManager with pre-populated projects
- `mock_task_list`: Mock TaskList with sample tasks

Example usage:

```python
def test_my_feature(gradle_manager_with_projects):
    """Test using the gradle_manager_with_projects fixture."""
    manager = gradle_manager_with_projects

    projects = manager.list_all_projects()
    assert len(projects) == 2
```

## Coverage

The test suite aims for high code coverage across all components:

- **Target Coverage**: >80% overall
- **Critical Components**: >90% (GradleWrapper, GradleManager)
- **UI Components**: >70% (harder to test, but using Textual pilot)

### View Coverage by Component

```bash
pytest --cov=gradle --cov=ui --cov-report=term-missing
```

### Generate HTML Coverage Report

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Test Scenarios Covered

### GradleWrapper Tests
- ✅ Initialization with different directories
- ✅ Permission checking and fixing
- ✅ Listing tasks from Gradle projects
- ✅ Running custom Gradle tasks
- ✅ Streaming output via callbacks
- ✅ Error handling (PermissionError, FileNotFoundError, CalledProcessError)

### GradleManager Tests
- ✅ Configuration loading and saving
- ✅ Adding, selecting, and deleting projects
- ✅ Theme management
- ✅ Task list updates
- ✅ Recent task tracking
- ✅ Running tasks with and without parameters
- ✅ Auto-selecting projects after deletion

### UI Tests
- ✅ App initialization and theme loading
- ✅ Terminal size warnings
- ✅ Key bindings (p, Ctrl+P, r, R, /, F5)
- ✅ Task list display and filtering
- ✅ Project chooser modal
- ✅ Task execution and output streaming
- ✅ Task manager and tracker

### Integration Tests
- ✅ End-to-end project workflow
- ✅ Multi-project management
- ✅ Configuration persistence
- ✅ Streaming callbacks integration
- ✅ Error handling across components

## Continuous Integration

The test suite is designed to run in CI/CD environments:

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Fail with Import Errors

Ensure you've installed the package in development mode:

```bash
pip install -e .
```

### UI Tests Hang

UI tests use `asyncio` and might need specific event loop configuration. Make sure you have:

```bash
pip install pytest-asyncio
```

### Mock Gradle Projects Not Working

Ensure the temp directories have proper permissions:

```bash
# On Linux/macOS
chmod +x /path/to/temp/gradlew
```

## Contributing

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure all tests pass: `pytest`
3. Check coverage: `pytest --cov`
4. Add appropriate markers (`@pytest.mark.unit`, etc.)
5. Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Textual Testing Documentation](https://textual.textualize.io/guide/testing/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

"""GradleWrapper run against the real fixture gradle project.

These tests invoke `./gradlew` for real. First run downloads the gradle
distribution (~30s); subsequent runs are seconds. CI caches
`~/.gradle/wrapper/dists` keyed on `gradle-wrapper.properties`.
"""

from __future__ import annotations

import os
import stat

from gradle.gradle_wrapper import GradleWrapper


def test_check_permissions_passes_on_real_wrapper(sample_project):
    wrapper = GradleWrapper(str(sample_project))
    ok, err = wrapper.check_gradlew_permissions()
    assert ok, err


def test_check_permissions_detects_missing(tmp_path):
    wrapper = GradleWrapper(str(tmp_path))
    ok, err = wrapper.check_gradlew_permissions()
    assert ok is False
    assert "not found" in err


def test_check_permissions_detects_non_executable(tmp_path):
    fake = tmp_path / "gradlew"
    fake.write_text("#!/bin/sh\necho hi\n")
    fake.chmod(0o644)
    wrapper = GradleWrapper(str(tmp_path))
    ok, err = wrapper.check_gradlew_permissions()
    assert ok is False
    assert "execute permissions" in err


def test_fix_permissions_adds_executable_bit(tmp_path):
    fake = tmp_path / "gradlew"
    fake.write_text("#!/bin/sh\necho hi\n")
    fake.chmod(0o644)

    wrapper = GradleWrapper(str(tmp_path))
    ok, _ = wrapper.fix_gradlew_permissions()
    assert ok is True
    assert os.stat(fake).st_mode & stat.S_IXUSR


def test_list_all_tasks_finds_fixture_tasks(sample_project):
    wrapper = GradleWrapper(str(sample_project))
    result = wrapper.list_all_tasks()
    assert result.success, result.error and result.error.error_message
    names = {t.name for t in result.tasks}
    assert {"hello", "slow", "failing", "withParams"}.issubset(names)


def test_run_task_captures_stdout(sample_project):
    wrapper = GradleWrapper(str(sample_project))
    output, error = wrapper.run_custom_gradle_task("hello", options=["-q"])
    assert error is None
    assert "Hello from sample" in output


def test_run_task_streams_lines_via_callback(sample_project):
    wrapper = GradleWrapper(str(sample_project))
    streamed = []
    output, error = wrapper.run_custom_gradle_task(
        "slow", options=["-q"], on_stdout=streamed.append
    )
    assert error is None
    body = "\n".join(streamed)
    for i in range(1, 6):
        assert f"line {i} of 5" in body


def test_run_failing_task_returns_gradle_error(sample_project):
    wrapper = GradleWrapper(str(sample_project))
    output, error = wrapper.run_custom_gradle_task("failing")
    assert error is not None
    assert error.error_code != 0


def test_run_task_with_parameters_passes_through(sample_project):
    wrapper = GradleWrapper(str(sample_project))
    output, error = wrapper.run_custom_gradle_task(
        "withParams", options=["-Pfoo=alpha", "-Pbar=beta", "-q"]
    )
    assert error is None
    assert "foo=alpha bar=beta" in output


def test_no_shell_true_regression_with_special_chars_in_path(tmp_path):
    """Regression: previously `cwd` was ignored on Linux when `shell=True`.
    Verify a path containing spaces still resolves correctly."""
    spaced = tmp_path / "dir with space"
    spaced.mkdir()
    fake = spaced / "gradlew"
    fake.write_text("#!/bin/sh\necho ok-from-spaced\n")
    fake.chmod(0o755)

    wrapper = GradleWrapper(str(spaced))
    output, error = wrapper.run_gradle_command(["./gradlew"])
    assert error is None
    assert "ok-from-spaced" in output

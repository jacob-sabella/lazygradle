"""Headless capture of the README screenshots and demo GIF.

Drives lazygradle via Textual's `App.run_test()` + pilot — no real terminal,
no output-stream overload. Uses a throwaway config with a demo project, so
your own ~/.config/lazygradle is never read or written, and Gradle is never
invoked (task runs are simulated with streamed demo output).

Run from the repo root with the venv active:

    python scripts/capture_readme_screenshots.py            # SVGs + PNG + GIF
    python scripts/capture_readme_screenshots.py --no-gif   # SVGs only

Writes to `screenshots/readme/`:
- current-setup-overview.svg / .png, task-manager-output.svg,
  run-task-with-parameters.svg, keys-guide.svg
- demo.gif

The PNG and GIF need `chromium` (or `google-chrome`) to rasterize the SVGs
faithfully and `ffmpeg` to assemble the GIF. ImageMagick and rsvg-convert
drop the non-breaking spaces Rich uses, so they are not used.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gradle.gradle_manager import GradleManager, Task  # noqa: E402
from ui import task_output_viewer  # noqa: E402
from ui.lazy_gradle_app import LazyGradleApp  # noqa: E402
from ui.widget import LazyGradleWidget  # noqa: E402
from ui.gradle_project_task_viewer import GradleProjectTaskViewer  # noqa: E402
from ui.task_tracker import TaskStatus, TrackedTask  # noqa: E402

OUT_DIR = REPO_ROOT / "screenshots" / "readme"
SIZE = (160, 45)
GIF_SIZE = (120, 34)
GIF_WIDTH = 1200
PAUSE_S = 0.4

DEMO_PROJECT = "/home/dev/work/orders-service"
OTHER_PROJECTS = ["/home/dev/work/payments-gateway", "/home/dev/work/inventory-api"]
DEMO_TASKS = [
    ("assemble", "Assembles the outputs of this project."),
    ("bootJar", "Assembles an executable jar archive containing the main classes and their dependencies."),
    ("bootRun", "Runs this project as a Spring Boot application."),
    ("build", "Assembles and tests this project."),
    ("buildDependents", "Assembles and tests this project and all projects that depend on it."),
    ("check", "Runs all checks."),
    ("clean", "Deletes the build directory."),
    ("dependencies", "Displays all dependencies declared in root project 'orders-service'."),
    ("integrationTest", "Runs the integration test suite."),
    ("jar", "Assembles a jar archive containing the classes of the 'main' feature."),
    ("javadoc", "Generates Javadoc API documentation for the 'main' feature."),
    ("projects", "Displays the sub-projects of root project 'orders-service'."),
    ("spotlessApply", "Applies code formatting steps to sourcecode in-place."),
    ("spotlessCheck", "Checks that sourcecode satisfies formatting steps."),
    ("tasks", "Displays the tasks runnable from root project 'orders-service'."),
    ("test", "Runs the test suite."),
]
BUILD_OUTPUT = [
    "> Task :compileJava",
    "> Task :processResources",
    "> Task :classes",
    "> Task :bootJar",
    "> Task :jar",
    "> Task :assemble",
    "> Task :compileTestJava",
    "> Task :processTestResources NO-SOURCE",
    "> Task :testClasses",
    "> Task :test",
    "",
    "OrderServiceTest > createsOrder() PASSED",
    "OrderServiceTest > rejectsEmptyCart() PASSED",
    "OrderControllerTest > returns404ForUnknownOrder() PASSED",
    "",
    "> Task :check",
    "> Task :build",
    "",
    "BUILD SUCCESSFUL in 14s",
    "9 actionable tasks: 9 executed",
]


class _NoClipboard:
    """Stand-in for pyperclip so yanking in the demo never touches your clipboard."""

    @staticmethod
    def copy(_text: str) -> None:
        pass


def make_gradle_manager() -> GradleManager:
    config_dir = Path(tempfile.mkdtemp(prefix="lazygradle-readme-"))
    GradleManager.CONFIG_DIR = config_dir
    GradleManager.CONFIG_FILE = config_dir / "gradle_cache.json"
    gm = GradleManager()
    for path in [DEMO_PROJECT, *OTHER_PROJECTS]:
        gm.add_project(path)
    gm.select_project(DEMO_PROJECT)
    gm.config.projects[DEMO_PROJECT].tasks = [Task(n, d) for n, d in DEMO_TASKS]
    gm.save_execution_config("build", "CI profile", ["--info", "-Pprofile=ci"], {"JAVA_OPTS": "-Xmx2g"})
    time.sleep(0.01)  # saved-config ids are millisecond timestamps
    gm.save_execution_config("build", "Skip tests", ["-x", "test"], {})
    now = datetime.now()
    gm.config.projects[DEMO_PROJECT].recent_tasks = [
        {"task_name": "test", "timestamp": (now - timedelta(minutes=4)).isoformat(), "parameters": ""},
        {"task_name": "build", "timestamp": (now - timedelta(minutes=12)).isoformat(), "parameters": "--info"},
        {"task_name": "clean", "timestamp": (now - timedelta(minutes=30)).isoformat(), "parameters": ""},
    ]

    def fake_run(task_name, on_stdout=None, on_stderr=None, env_vars=None, parameters=None):
        for line in BUILD_OUTPUT:
            time.sleep(0.12)
            if on_stdout:
                on_stdout(line)
        return ""

    gm.run_task = fake_run
    gm.run_task_with_parameters = (
        lambda task_name, parameters, on_stdout=None, on_stderr=None, env_vars=None:
        fake_run(task_name, on_stdout, on_stderr, env_vars, parameters)
    )
    return gm


def seed_history(tracker) -> None:
    """Inject past runs so the Task Manager tab has something to show."""
    now = datetime.now()
    tracker.tasks[:0] = [
        TrackedTask(
            "demo_test", "test", [], TaskStatus.FAILED,
            now - timedelta(minutes=4), now - timedelta(minutes=3, seconds=22),
            output_lines=[
                "> Task :compileJava UP-TO-DATE",
                "> Task :test FAILED",
                "",
                "[$text-error]OrderServiceTest > rejectsEmptyCart() FAILED[/]",
                "[$text-error]    java.lang.AssertionError at OrderServiceTest.java:42[/]",
                "",
                "[$text-error]FAILURE: Build failed with an exception.[/]",
                "BUILD FAILED in 38s",
            ],
        ),
        TrackedTask(
            "demo_build", "build", ["--info"], TaskStatus.COMPLETED,
            now - timedelta(minutes=12), now - timedelta(minutes=11, seconds=46),
            output_lines=list(BUILD_OUTPUT), config_label="CI profile",
        ),
        TrackedTask(
            "demo_clean", "clean", [], TaskStatus.COMPLETED,
            now - timedelta(minutes=30), now - timedelta(minutes=30) + timedelta(seconds=1),
            output_lines=["> Task :clean", "", "BUILD SUCCESSFUL in 1s", "1 actionable task: 1 executed"],
        ),
    ]


async def capture_screenshots() -> None:
    app = LazyGradleApp(make_gradle_manager())

    async def save(name: str) -> None:
        await pilot.pause(PAUSE_S)
        app.save_screenshot(filename=name, path=str(OUT_DIR))
        print(f"wrote {OUT_DIR / name}")

    async with app.run_test(size=SIZE) as pilot:
        # 1. Current Setup: "build" highlighted, showing its saved configurations.
        await pilot.pause(PAUSE_S)
        viewer = app.query_one(GradleProjectTaskViewer)
        viewer.task_option_list.focus()
        await pilot.press("down", "down", "down", "down")
        await save("current-setup-overview.svg")

        # 2. Task Manager with a completed run selected.
        widget = app.query_one(LazyGradleWidget)
        seed_history(widget.task_tracker)
        await pilot.press("2")
        await pilot.pause(PAUSE_S)
        widget.task_manager_widget.select_task("demo_build")
        await save("task-manager-output.svg")

        # 3. Run-with-parameters modal, filled in.
        await pilot.press("1")
        await pilot.pause(PAUSE_S)
        viewer = app.query_one(GradleProjectTaskViewer)
        viewer.selected_task = next(t for t in viewer.tasks if t.name == "build")
        viewer.update_task_description(viewer.selected_task)
        await viewer.action_run_task_with_parameters()
        await pilot.pause(PAUSE_S)
        await pilot.press(*"--info -Pprofile=ci")
        await save("run-task-with-parameters.svg")
        await pilot.press("escape")

        # 4. Keys guide.
        await pilot.pause(PAUSE_S)
        app.action_show_keys_guide()
        await save("keys-guide.svg")


async def capture_gif_frames(frame_dir: Path) -> list[tuple[Path, float]]:
    """Record the find → run → review loop as (svg, seconds-on-screen) frames."""
    app = LazyGradleApp(make_gradle_manager())
    frames: list[tuple[Path, float]] = []

    async def frame(hold: float, settle: float = 0.15) -> None:
        await pilot.pause(settle)
        name = f"frame-{len(frames):03d}.svg"
        app.save_screenshot(filename=name, path=str(frame_dir))
        frames.append((frame_dir / name, hold))

    async with app.run_test(size=GIF_SIZE) as pilot:
        await pilot.pause(PAUSE_S)
        widget = app.query_one(LazyGradleWidget)
        seed_history(widget.task_tracker)
        await frame(1.6)

        # Find: search for a task.
        await pilot.press("/")
        await frame(0.5)
        for key in "build":
            await pilot.press(key)
            await frame(0.18, settle=0.05)
        await frame(0.6)
        await pilot.press("enter")
        await frame(1.4)

        # Run: output streams into the Task Manager.
        await pilot.press("r")
        await frame(0.4, settle=0.2)
        for _ in range(12):
            await frame(0.25, settle=0.25)
        await pilot.pause(0.6)
        await frame(1.8)

        # Review: select the test results in visual mode and yank them.
        output = widget.task_manager_widget.output_log
        output.focus()
        await pilot.press("G")
        await frame(0.4, settle=0.05)
        for _ in range(6):
            await pilot.press("k")
            await frame(0.16, settle=0.05)
        await pilot.press("v")
        await frame(0.5)
        for key in ["k", "k"]:
            await pilot.press(key)
            await frame(0.25, settle=0.05)
        await pilot.press("y")
        await frame(1.6)

        # Repeat: re-run with parameters.
        await pilot.press("1")
        await pilot.pause(PAUSE_S)
        viewer = app.query_one(GradleProjectTaskViewer)
        viewer.task_option_list.focus()
        await frame(0.5)
        for _ in range(4):
            await pilot.press("down")
            await frame(0.16, settle=0.05)
        await frame(0.6)
        await pilot.press("R")
        await frame(0.6, settle=0.3)
        for chunk in ["--", "in", "fo", " -", "x ", "te", "st"]:
            await pilot.press(*chunk)
            await frame(0.15, settle=0.05)
        await frame(2.4)

    return frames


def find_chromium() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    return None


def rasterize(chromium: str, svg: Path, png: Path, width: int) -> None:
    """Render an SVG to PNG with headless Chromium at the SVG's aspect ratio."""
    view_box = svg.read_text().split('viewBox="', 1)[1].split('"', 1)[0].split()
    height = round(width * float(view_box[3]) / float(view_box[2]))
    page = svg.with_suffix(".html")
    page.write_text(
        f'<html><body style="margin:0;background:transparent">'
        f'<img src="{svg.name}" width="{width}" height="{height}"></body></html>'
    )
    subprocess.run(
        [chromium, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         "--allow-file-access-from-files", "--default-background-color=00000000",
         f"--window-size={width},{height}", f"--screenshot={png}", page.as_uri()],
        check=True, capture_output=True, timeout=60,
    )
    page.unlink()


def build_gif(chromium: str, frames: list[tuple[Path, float]], out: Path) -> None:
    concat = frames[0][0].parent / "frames.txt"
    lines = []
    for svg, hold in frames:
        png = svg.with_suffix(".png")
        rasterize(chromium, svg, png, GIF_WIDTH)
        lines += [f"file '{png}'", f"duration {hold}"]
    lines.append(f"file '{frames[-1][0].with_suffix('.png')}'")
    concat.write_text("\n".join(lines) + "\n")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-vf", "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];"
                "[b][p]paletteuse=dither=none:diff_mode=rectangle",
         "-loop", "0", str(out)],
        check=True,
    )
    print(f"wrote {out}")


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    task_output_viewer.pyperclip = _NoClipboard()
    await capture_screenshots()

    if "--no-gif" in sys.argv:
        return
    chromium = find_chromium()
    if not chromium or not shutil.which("ffmpeg"):
        print("WARN: chromium and ffmpeg are required for the PNG and GIF; skipped them.")
        return

    overview = OUT_DIR / "current-setup-overview.svg"
    rasterize(chromium, overview, overview.with_suffix(".png"), 1600)
    print(f"wrote {overview.with_suffix('.png')}")

    with tempfile.TemporaryDirectory(prefix="lazygradle-gif-") as tmp:
        frames = await capture_gif_frames(Path(tmp))
        build_gif(chromium, frames, OUT_DIR / "demo.gif")


if __name__ == "__main__":
    asyncio.run(main())

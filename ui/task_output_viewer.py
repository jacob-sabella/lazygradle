import logging
import os
import re
import subprocess
import threading
from typing import Callable, Optional

from textual import events
from textual.widgets import Static

try:
    import pyperclip
except ImportError:
    pyperclip = None


class TaskOutputViewer(Static):
    """Scrollable task output viewer with vim-like navigation and yanking."""

    can_focus = True

    MIN_ZOOM = -1
    MAX_ZOOM = 2

    def __init__(
        self,
        on_status: Optional[Callable[[str, bool], None]] = None,
        focus_router: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.on_status = on_status
        self.focus_router = focus_router
        self.on_state_change = on_state_change
        self.lines: list[str] = []
        self.current_line = 0
        self.visual_mode = False
        self.visual_anchor: Optional[int] = None
        self.pending_key: Optional[str] = None
        self.zoom_level = 0
        self.task_context: dict[str, str] = {}
        self.clipboard_enabled = True
        self.yank_hook = ""
        self._sent_focus_hint = False
        self._mouse_dragging = False
        self._mouse_dragged = False
        self._mouse_down_line: Optional[int] = None
        self._render_vertical_pad = 1
        self._render_line_block = 1

    def set_config(self, output_settings: Optional[dict]) -> None:
        settings = output_settings or {}
        self.zoom_level = max(
            self.MIN_ZOOM,
            min(self.MAX_ZOOM, int(settings.get("default_zoom", 0))),
        )
        self.clipboard_enabled = bool(settings.get("clipboard_enabled", True))
        self.yank_hook = (settings.get("yank_hook") or "").strip()
        self._refresh_display()

    def set_context(self, **context: Optional[str]) -> None:
        self.task_context = {key: value for key, value in context.items() if value}

    def set_lines(self, lines: list[str]) -> None:
        self.lines = list(lines)
        self.current_line = self._clamp_line(self.current_line)
        if self.visual_mode and self.visual_anchor is not None:
            self.visual_anchor = self._clamp_line(self.visual_anchor)
        self._refresh_display()
        self._scroll_to_cursor()

    def append_line(self, line: str) -> None:
        self.lines.append(line)
        self.current_line = self._clamp_line(self.current_line)
        self._refresh_display()
        self.scroll_end(animate=False)

    def clear(self) -> None:
        self.lines = []
        self.current_line = 0
        self._set_visual_mode(False)
        self.pending_key = None
        self._refresh_display()

    def on_focus(self) -> None:
        if not self._sent_focus_hint:
            self._sent_focus_hint = True
            self._set_status("Output focused", is_error=False)
        if self.on_state_change:
            self.on_state_change()

    def on_blur(self) -> None:
        if self.on_state_change:
            self.on_state_change()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if getattr(event, "button", 0) != 1:
            return
        # Any click resets visual mode.
        self._set_visual_mode(False)
        self.focus()
        self._mouse_dragging = True
        self._mouse_dragged = False
        line = self._line_from_y(getattr(event, "y", 0))
        self._mouse_down_line = line
        self.current_line = line
        self._refresh_display()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self._mouse_dragging:
            return
        line = self._line_from_y(getattr(event, "y", 0))
        if line == self.current_line and self.visual_mode:
            return
        if self._mouse_down_line is None:
            self._mouse_down_line = line
        if line != self.current_line:
            self._mouse_dragged = True
        if self._mouse_dragged and not self.visual_mode:
            self._set_visual_mode(True, anchor=self._mouse_down_line)
        self.current_line = line
        self._refresh_display()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if getattr(event, "button", 0) != 1:
            return
        self._mouse_dragging = False
        self._mouse_down_line = None
        # If it was just a click (no drag), don't force visual mode.

    def on_key(self, event) -> None:
        key = getattr(event, "key", "")
        character = getattr(event, "character", None)

        if key == "escape":
            self.pending_key = None
            self._set_visual_mode(False)
            self._refresh_display()
            self._stop_event(event)
            return

        if key == "up":
            self._move_cursor(-1)
            self._stop_event(event)
            return
        if key == "down":
            self._move_cursor(1)
            self._stop_event(event)
            return
        if key == "left":
            self.scroll_relative(x=-4, animate=False)
            self._stop_event(event)
            return
        if key == "right":
            self.scroll_relative(x=4, animate=False)
            self._stop_event(event)
            return

        if key in {"ctrl+h", "ctrl+j", "ctrl+k", "ctrl+l"}:
            self.pending_key = None
            direction = key[-1]
            if self.focus_router:
                self.focus_router(direction)
            self._stop_event(event)
            return

        if character == "g":
            if self.pending_key == "g":
                self.pending_key = None
                self._move_cursor_to(0)
            else:
                self.pending_key = "g"
            self._stop_event(event)
            return

        if character == "y":
            if self.visual_mode:
                self.pending_key = None
                self._yank_selection()
            elif self.pending_key == "y":
                self.pending_key = None
                self._yank_current_line()
            else:
                self.pending_key = "y"
            self._stop_event(event)
            return

        self.pending_key = None

        if character == "j":
            self._move_cursor(1)
        elif character == "k":
            self._move_cursor(-1)
        elif character == "h":
            self.scroll_relative(x=-4, animate=False)
        elif character == "l":
            self.scroll_relative(x=4, animate=False)
        elif character == "v":
            self._toggle_visual_mode()
        elif character == "G":
            self._move_cursor_to(max(len(self.lines) - 1, 0))
        elif character == "+" or key == "plus":
            self._adjust_zoom(1)
        elif character == "-" or key == "minus":
            self._adjust_zoom(-1)
        elif character == "0":
            self.scroll_to(x=0, animate=False)
        elif character == "$":
            self.scroll_to(x=10_000, animate=False)
        elif key == "ctrl+d":
            self._page_cursor(0.5)
        elif key == "ctrl+u":
            self._page_cursor(-0.5)
        else:
            return

        self._stop_event(event)

    def _toggle_visual_mode(self) -> None:
        if self.visual_mode:
            self._set_visual_mode(False)
            self._set_status("Visual mode disabled", is_error=False)
        else:
            self._set_visual_mode(True, anchor=self.current_line)
            self._set_status("Visual mode enabled", is_error=False)
        self._refresh_display()

    def _adjust_zoom(self, delta: int) -> None:
        old_zoom = self.zoom_level
        self.zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom_level + delta))
        if self.zoom_level != old_zoom:
            self._refresh_display()
            self._set_status(f"Output zoom: {self.zoom_level:+d}", is_error=False)

    def _page_cursor(self, page_factor: float) -> None:
        page_size = max(1, self.size.height - 4) if hasattr(self, "size") else 10
        self._move_cursor(int(page_size * page_factor))

    def _move_cursor(self, delta: int) -> None:
        self._move_cursor_to(self.current_line + delta)

    def _move_cursor_to(self, line_index: int) -> None:
        self.current_line = self._clamp_line(line_index)
        self._refresh_display()
        self._scroll_to_cursor()

    def _scroll_to_cursor(self) -> None:
        try:
            self.scroll_to(y=max(self.current_line, 0), animate=False)
        except Exception as error:
            logging.debug(f"Failed to scroll output viewer: {error}")

    def _clamp_line(self, line_index: int) -> int:
        if not self.lines:
            return 0
        return max(0, min(line_index, len(self.lines) - 1))

    def _line_from_y(self, y: int) -> int:
        if not self.lines:
            return 0
        scroll_y = int(getattr(self, "scroll_y", 0) or 0)
        local_y = int(y) + scroll_y
        vertical_pad = int(getattr(self, "_render_vertical_pad", 0) or 0)
        line_block = max(1, int(getattr(self, "_render_line_block", 1) or 1))
        adjusted = local_y - vertical_pad
        if adjusted < 0:
            return 0
        return self._clamp_line(adjusted // line_block)

    def _set_visual_mode(self, enabled: bool, anchor: Optional[int] = None) -> None:
        self.visual_mode = enabled
        self.visual_anchor = self._clamp_line(anchor) if enabled and anchor is not None else None
        if hasattr(self, "add_class") and hasattr(self, "remove_class"):
            if enabled:
                self.add_class("visual-mode")
            else:
                self.remove_class("visual-mode")
        if self.on_state_change:
            self.on_state_change()

    def _selected_range(self) -> tuple[int, int]:
        if not self.visual_mode or self.visual_anchor is None:
            return self.current_line, self.current_line
        start = min(self.visual_anchor, self.current_line)
        end = max(self.visual_anchor, self.current_line)
        return start, end

    def _refresh_display(self) -> None:
        # Terminal apps can't change font size. "Zoom" here is a readability tweak:
        # more/less padding and (for zoom > 0) bold text, without changing line height.
        horizontal_pad = max(0, 2 + self.zoom_level * 2)
        vertical_pad = 0 if self.zoom_level < 0 else 1
        self._render_vertical_pad = vertical_pad
        self._render_line_block = 1
        padding = " " * horizontal_pad

        if not self.lines:
            super().update("\n" * vertical_pad)
            return

        selected_start, selected_end = self._selected_range()
        rendered_lines: list[str] = []
        bold_all = self.zoom_level > 0

        for _ in range(vertical_pad):
            rendered_lines.append("")

        for line_index, line in enumerate(self.lines):
            prefix = "[bold cyan]›[/] " if line_index == self.current_line else "  "
            content = f"{prefix}{padding}{line}"
            if bold_all:
                content = f"[bold]{content}[/]"

            if self.visual_mode and selected_start <= line_index <= selected_end:
                content = f"[reverse]{content}[/]"
            elif line_index == self.current_line:
                content = f"[on #2d3d5a]{content}[/]"

            rendered_lines.append(content)

        for _ in range(vertical_pad):
            rendered_lines.append("")

        super().update("\n".join(rendered_lines))

    def _yank_current_line(self) -> None:
        if not self.lines:
            self._set_status("Nothing to yank", is_error=True)
            return
        self._copy_text(self._plain_text(self.lines[self.current_line]), "Yanked current line")

    def _yank_selection(self) -> None:
        if not self.lines:
            self._set_status("Nothing to yank", is_error=True)
            return

        start, end = self._selected_range()
        self._yank_range(start, end)

    def _yank_range(self, start: int, end: int) -> None:
        if not self.lines:
            self._set_status("Nothing to yank", is_error=True)
            return
        start = self._clamp_line(start)
        end = self._clamp_line(end)
        if end < start:
            start, end = end, start
        selected_text = "\n".join(self._plain_text(line) for line in self.lines[start : end + 1])
        self._copy_text(selected_text, f"Yanked {end - start + 1} lines")

    def _copy_text(self, text: str, success_message: str) -> None:
        if not self.clipboard_enabled:
            self._set_status("Clipboard yanking is disabled in config", is_error=True)
            return

        if pyperclip is None:
            self._set_status("pyperclip is not available", is_error=True)
            return

        try:
            pyperclip.copy(text)
        except Exception as error:
            self._set_status(f"Clipboard copy failed: {error}", is_error=True)
            return

        self._set_status(success_message, is_error=False)

        if self.yank_hook:
            self._run_hook_async(text)

    def _run_hook_async(self, text: str) -> None:
        thread = threading.Thread(target=self._run_hook, args=(text,), daemon=True)
        thread.start()

    def _run_hook(self, text: str) -> None:
        env = os.environ.copy()
        env.update(
            {
                "LAZYGRADLE_YANK_TEXT_LENGTH": str(len(text)),
                "LAZYGRADLE_TASK_ID": self.task_context.get("task_id", ""),
                "LAZYGRADLE_TASK_NAME": self.task_context.get("task_name", ""),
                "LAZYGRADLE_PROJECT_PATH": self.task_context.get("project_path", ""),
            }
        )

        try:
            subprocess.run(
                self.yank_hook,
                input=text,
                text=True,
                shell=True,
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as error:
            logging.error(f"Output yank hook failed: {error}")
            app = getattr(self, "app", None)
            if app and hasattr(app, "call_from_thread"):
                app.call_from_thread(
                    self._set_status,
                    f"Yank hook failed: {error}",
                    True,
                )

    def _set_status(self, message: str, is_error: bool) -> None:
        if self.on_status:
            self.on_status(message, is_error)

    @staticmethod
    def _plain_text(line: str) -> str:
        without_tags = re.sub(r"(?<!\\)\[/?[^\]]+\]", "", line)
        without_escapes = without_tags.replace("\\[", "[").replace("\\]", "]").replace("\\\\", "\\")
        return without_escapes

    @staticmethod
    def _stop_event(event) -> None:
        if hasattr(event, "stop"):
            event.stop()
        if hasattr(event, "prevent_default"):
            event.prevent_default()

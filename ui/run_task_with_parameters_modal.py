import logging
from typing import Optional, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, TextArea, Checkbox

try:
    import pyperclip
except ImportError:
    pyperclip = None

from gradle.gradle_manager import GradleManager


class RunTaskWithParametersModal(ModalScreen):
    """ModalScreen that handles entering parameters and environment variables for a Gradle task."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("enter", "run_task", "Run Task"),
        Binding("ctrl+s", "save_config", "Save Config"),
    ]

    def __init__(
        self,
        selected_task,
        gradle_manager: GradleManager,
        saved_execution: Optional[Dict] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.selected_task = selected_task
        self.gradle_manager = gradle_manager
        self.saved_execution = saved_execution  # For editing existing configuration
        self.param_input = None
        self.env_var_textarea = None
        self.save_checkbox = None
        self.label_input = None

    def compose(self) -> ComposeResult:
        # Get task description
        description = (
            self.selected_task.description
            if self.selected_task.description
            else "No description available"
        )

        # Pre-populate fields if editing existing configuration
        initial_params = ""
        initial_env_vars = ""
        initial_label = ""
        initial_save_checked = False

        if self.saved_execution:
            initial_params = " ".join(self.saved_execution.get("parameters", []))
            env_dict = self.saved_execution.get("env_vars", {})
            initial_env_vars = "\n".join([f"{k}={v}" for k, v in env_dict.items()])
            initial_label = self.saved_execution.get("label", "")
            initial_save_checked = True

        yield Vertical(
            Static("Run Task with Parameters", classes="modal-title"),
            Vertical(
                Static(
                    f"[bold cyan]{self.selected_task.name}[/bold cyan]",
                    classes="modal-section-title",
                ),
                VerticalScroll(
                    Static(
                        f"[dim]{description}[/dim]", classes="run-params-description"
                    ),
                    classes="modal-scroll",
                ),
                # Parameters section
                Static("[bold]Parameters[/bold]", classes="modal-section-title"),
                self.render_param_input(initial_params),
                Static(
                    "[dim]Example: --info --stacktrace or -x test[/dim]",
                    classes="status-message example-message",
                ),
                # Environment variables section
                Static(
                    "[bold]Environment Variables[/bold]",
                    classes="modal-section-title",
                ),
                self.render_env_var_input(initial_env_vars),
                Static(
                    "[dim]Format: KEY=VALUE (one per line)[/dim]",
                    classes="status-message format-message",
                ),
                Horizontal(
                    Button(
                        "📋 Paste from Clipboard",
                        id="paste_button",
                        variant="default",
                        classes="small-button",
                    ),
                    Button(
                        "Clear",
                        id="clear_env_button",
                        variant="default",
                        classes="small-button",
                    ),
                    classes="modal-button-bar",
                ),
                # Save configuration section
                self.render_save_section(initial_save_checked, initial_label),
                self.render_buttons(),
                classes="modal-content",
            ),
            classes="run-params-modal",
        )

    def on_mount(self) -> None:
        """Focus the parameter input field when modal opens."""
        if self.param_input:
            self.param_input.focus()

    def render_param_input(self, initial_value: str):
        """Render the parameters input field."""
        self.param_input = Input(
            value=initial_value,
            placeholder="e.g., --info --stacktrace",
            classes="project-search",
        )
        return self.param_input

    def render_env_var_input(self, initial_value: str):
        """Render the environment variables textarea."""
        self.env_var_textarea = TextArea(
            text=initial_value, language=None, classes="env-var-textarea"
        )
        return self.env_var_textarea

    def render_save_section(self, initial_checked: bool, initial_label: str):
        """Render the save configuration section."""
        self.save_checkbox = Checkbox(
            "Save this configuration", value=initial_checked, id="save_checkbox"
        )
        self.label_input = Input(
            value=initial_label,
            placeholder="Configuration name...",
            classes="project-search",
        )
        # Show label input only if checkbox is checked
        self.label_input.display = initial_checked

        return Vertical(self.save_checkbox, self.label_input, classes="save-section")

    def render_buttons(self):
        """Render the Run, Save, and Cancel buttons."""
        return Horizontal(
            Button(
                "▶ Run Task", id="run_button", variant="success", classes="modal-button"
            ),
            Button(
                "💾 Save Config", id="save_button", variant="primary", classes="modal-button"
            ),
            Button(
                "Cancel", id="cancel_button", variant="default", classes="modal-button"
            ),
            classes="modal-button-bar",
        )

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses in the modal."""
        if event.button.id == "run_button":
            await self.action_run_task()
        elif event.button.id == "save_button":
            await self.action_save_config()
        elif event.button.id == "cancel_button":
            self.dismiss(None)
        elif event.button.id == "paste_button":
            await self.action_paste_from_clipboard()
        elif event.button.id == "clear_env_button":
            if self.env_var_textarea:
                self.env_var_textarea.text = ""

    async def action_paste_from_clipboard(self):
        """Paste text from clipboard into environment variables textarea."""
        if pyperclip is None:
            logging.error("pyperclip not available - cannot paste from clipboard")
            return

        try:
            clipboard_text = pyperclip.paste()
            if clipboard_text and self.env_var_textarea:
                # Insert at cursor position
                current_text = self.env_var_textarea.text
                if current_text:
                    # Add newline before pasting if there's existing text
                    self.env_var_textarea.text = current_text + "\n" + clipboard_text
                else:
                    self.env_var_textarea.text = clipboard_text
                logging.debug(f"Pasted {len(clipboard_text)} characters from clipboard")
        except Exception as e:
            logging.error(f"Failed to paste from clipboard: {e}")

    def on_checkbox_changed(self, event: Checkbox.Changed):
        """Handle checkbox state changes."""
        if event.checkbox.id == "save_checkbox":
            # Show/hide label input based on checkbox state
            if self.label_input:
                self.label_input.display = event.value

    async def action_run_task(self):
        """Run the task with the entered parameters and environment variables."""
        # Parse parameters
        parameters = self.param_input.value if self.param_input else ""
        param_list = parameters.split() if parameters else []

        # Parse environment variables
        env_vars = self._parse_env_vars()

        # Check if should save configuration
        save_config = None
        if self.save_checkbox and self.save_checkbox.value:
            label = self.label_input.value.strip() if self.label_input else ""
            if not label:
                # Auto-generate label if empty
                label = f"{self.selected_task.name} configuration"

            save_config = {
                "label": label,
                "task_name": self.selected_task.name,
                "parameters": param_list,
                "env_vars": env_vars,
            }

        # Get execution ID if editing existing configuration
        execution_id = self.saved_execution["id"] if self.saved_execution else None

        logging.info(
            f"Modal: Running {self.selected_task.name} with parameters: {param_list}, env_vars: {env_vars}"
        )

        # Return tuple: (param_list, env_vars, save_config, execution_id)
        self.dismiss((param_list, env_vars, save_config, execution_id))

    def _parse_env_vars(self) -> Dict[str, str]:
        """Parse environment variables from textarea."""
        env_vars = {}
        if self.env_var_textarea:
            text = self.env_var_textarea.text
            for line in text.split("\n"):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    # Split on first '=' only to support values with '='
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
                else:
                    logging.warning(f"Invalid env var format (missing '='): {line}")

        return env_vars

    async def action_save_config(self):
        """Save the configuration without running the task."""
        # Parse parameters
        parameters = self.param_input.value if self.param_input else ""
        param_list = parameters.split() if parameters else []

        # Parse environment variables
        env_vars = self._parse_env_vars()

        # Get label for the configuration
        label = self.label_input.value.strip() if self.label_input else ""
        if not label:
            # Auto-generate label if empty
            label = f"{self.selected_task.name} configuration"

        save_config = {
            "label": label,
            "task_name": self.selected_task.name,
            "parameters": param_list,
            "env_vars": env_vars,
        }

        # Get execution ID if editing existing configuration
        execution_id = self.saved_execution["id"] if self.saved_execution else None

        logging.info(
            f"Modal: Saving config for {self.selected_task.name} with parameters: {param_list}, env_vars: {env_vars}"
        )

        # Return tuple with None for param_list to indicate save-only (no run)
        # Format: (None, None, save_config, execution_id)
        self.dismiss((None, None, save_config, execution_id))

    def action_dismiss_modal(self):
        """Dismiss modal using the Escape key."""
        self.dismiss(None)

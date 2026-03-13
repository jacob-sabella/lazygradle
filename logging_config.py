import logging
import os
from pathlib import Path


DEFAULT_LOG_FILE = "lazygradleapp.log"
LOG_FILE_ENV_VAR = "LAZYGRADLE_LOG_FILE"
LOG_LEVEL_ENV_VAR = "LAZYGRADLE_LOG_LEVEL"
_FALSEY_VALUES = {"", "0", "false", "no", "off"}
_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _resolve_log_file() -> str | None:
    raw_value = os.getenv(LOG_FILE_ENV_VAR)
    if raw_value is None:
        return None

    value = raw_value.strip()
    lowered = value.lower()

    if lowered in _FALSEY_VALUES:
        return None

    if lowered in _TRUTHY_VALUES:
        return DEFAULT_LOG_FILE

    return value


def configure_logging() -> None:
    log_file = _resolve_log_file()
    if not log_file:
        # Disable root logging entirely unless explicitly enabled.
        logging.basicConfig(handlers=[logging.NullHandler()], force=True)
        logging.getLogger().setLevel(logging.CRITICAL + 1)
        return

    log_path = Path(log_file).expanduser()
    if log_path.parent != Path("."):
        log_path.parent.mkdir(parents=True, exist_ok=True)

    log_level_name = os.getenv(LOG_LEVEL_ENV_VAR, "DEBUG").upper()
    log_level = getattr(logging, log_level_name, logging.DEBUG)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_path)],
        force=True,
    )


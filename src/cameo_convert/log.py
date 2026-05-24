"""Project logging.

The ``cameo_convert`` namespace logger is configured at DEBUG by default so
internal diagnostics show up automatically. Third-party packages keep their
own (typically WARNING) level — we set the root logger to WARNING so noise
from urllib, openpyxl, jinja2, etc. stays out of the way unless explicitly
raised.

Usage in module code:

    from cameo_convert.log import get_logger
    log = get_logger(__name__)
    log.debug("walked %d rows in %s", n_rows, sheet_name)
    log.info("wrote %s (%d bytes)", path.name, size)

CLI entry points should call ``configure(level)`` once at startup; pass a
string like "DEBUG" / "INFO" / "WARNING" / "CRITICAL".
"""

from __future__ import annotations

import logging
import os
import sys

PROJECT_LOGGER_NAME = "cameo_convert"

# Default per the user's preference: DEBUG for the project, WARNING for
# everything else.
_DEFAULT_PROJECT_LEVEL = "DEBUG"
_DEFAULT_ROOT_LEVEL = "WARNING"

_configured = False


def configure(
    project_level: str | int | None = None,
    *,
    root_level: str | int | None = None,
    stream=None,
) -> None:
    """Install a stderr handler on the project logger.

    - ``project_level`` (env override: ``CAMEO_CONVERT_LOG_LEVEL``) sets the
      ``cameo_convert.*`` logger level.
    - ``root_level`` sets the root logger level — controls third-party
      packages. Default WARNING so urllib / openpyxl noise stays muted.
    - Idempotent: re-configuring updates levels but doesn't add duplicate
      handlers.
    """
    global _configured
    if project_level is None:
        project_level = os.environ.get("CAMEO_CONVERT_LOG_LEVEL", _DEFAULT_PROJECT_LEVEL)
    if root_level is None:
        root_level = _DEFAULT_ROOT_LEVEL

    project_logger = logging.getLogger(PROJECT_LOGGER_NAME)
    project_logger.setLevel(_coerce_level(project_level))
    project_logger.propagate = False

    if not _configured:
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        project_logger.addHandler(handler)
        _configured = True

    logging.getLogger().setLevel(_coerce_level(root_level))


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the project namespace.

    Accepts either a full dotted name (``cameo_convert.reader``) or a short
    one (``reader``); both are mapped under ``cameo_convert.*``.
    """
    if not name.startswith(PROJECT_LOGGER_NAME):
        # Allow callers to pass __name__ from any module under the package
        # (e.g. ``cameo_convert.reader``) or a short label.
        name = f"{PROJECT_LOGGER_NAME}.{name}"
    return logging.getLogger(name)


def _coerce_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    upper = str(level).upper()
    val = logging.getLevelName(upper)
    if isinstance(val, int):
        return val
    raise ValueError(f"unknown log level: {level!r}")

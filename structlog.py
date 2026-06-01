# Author: Sarala Biswal
"""Small local fallback for structlog when dependencies are not installed."""

from __future__ import annotations

import logging


class _Logger:
    """Tiny logger shim matching the subset of structlog used in tests and demos."""
    def __init__(self, name: str | None = None) -> None:
        """Keep the optional logger name for compatibility with structlog callers."""
        self._logger = logging.getLogger(name or "regulated_decisioning")

    def info(self, event: str, **kwargs) -> None:
        """Emit an informational event through the fallback logger."""
        self._logger.info("%s %s", event, kwargs)

    def warning(self, event: str, **kwargs) -> None:
        """Emit a warning event through the fallback logger."""
        self._logger.warning("%s %s", event, kwargs)

    def error(self, event: str, **kwargs) -> None:
        """Emit an error event through the fallback logger."""
        self._logger.error("%s %s", event, kwargs)


def get_logger(name: str | None = None) -> _Logger:
    """Return the local structlog-compatible fallback logger."""
    return _Logger(name)

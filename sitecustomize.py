# Author: Sarala Biswal
"""Runtime compatibility for the architecture's top-level platform package."""

from __future__ import annotations

import platform as _stdlib_platform
from pathlib import Path

_project_platform = Path(__file__).parent / "platform"
if _project_platform.exists():
    paths = list(getattr(_stdlib_platform, "__path__", []))
    project_path = str(_project_platform)
    if project_path not in paths:
        paths.append(project_path)
    _stdlib_platform.__path__ = paths

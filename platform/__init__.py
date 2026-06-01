# Author: Sarala Biswal
"""Project platform package with stdlib platform compatibility.

The architecture uses a top-level ``platform`` package. Python dependencies also
import the standard-library module with this name, so expose its public
attributes here before project subpackages are imported.
"""

from __future__ import annotations

import importlib.util
import sysconfig
from pathlib import Path

_stdlib_platform_path = Path(sysconfig.get_path("stdlib")) / "platform.py"
_spec = importlib.util.spec_from_file_location("_stdlib_platform", _stdlib_platform_path)
if _spec and _spec.loader:
    _stdlib_platform = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_stdlib_platform)
    for _name in dir(_stdlib_platform):
        if not _name.startswith("__"):
            globals().setdefault(_name, getattr(_stdlib_platform, _name))

# Author: Sarala Biswal
from __future__ import annotations

import os
import platform as stdlib_platform
import sys
from pathlib import Path
from uuid import uuid4

os.environ["DATABASE_URL"] = f"sqlite:////private/tmp/regulated_decisioning_tests_{uuid4()}.db"

project_platform = Path(__file__).resolve().parents[1] / "platform"
paths = list(getattr(stdlib_platform, "__path__", []))
if str(project_platform) not in paths:
    paths.append(str(project_platform))
stdlib_platform.__path__ = paths
sys.modules["platform"] = stdlib_platform

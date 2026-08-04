"""Repository-owned test package for deterministic cross-module imports."""

from __future__ import annotations

import sys

from . import conftest as _conftest

# One frozen predecessor test imports the historical top-level name. Keep the
# alias inside the test package so collection has one conftest module/object.
sys.modules.setdefault("conftest", _conftest)

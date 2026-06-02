"""
test_imports.py
===============
Verify that every module in parsers/ can be imported without error.

These tests catch syntax errors, missing dependencies, and broken imports in
shared parser components before any workload parser is even run.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so "parsers.*" imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Collect all modules in parsers/
# ---------------------------------------------------------------------------
PARSERS_DIR = PROJECT_ROOT / "parsers"

_parser_modules = [
    f"parsers.{p.stem}"
    for p in sorted(PARSERS_DIR.glob("*.py"))
    if p.stem != "__init__"
]


@pytest.mark.parametrize("module_name", _parser_modules)
def test_parser_module_imports(module_name: str) -> None:
    """Each shared parser module must be importable without raising an exception."""
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(f"ImportError while importing {module_name}: {exc}")
    except SyntaxError as exc:
        pytest.fail(f"SyntaxError in {module_name}: {exc}")

"""
conftest.py - shared pytest fixtures for parsing-suite test suite
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TEST_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TEST_DIR / "fixtures"
PROJECT_ROOT = TEST_DIR.parent
TEST_CONFIG = FIXTURES_DIR / "config" / "test_config.json"

# Fixture data roots – one per workload parser scenario
FIXTURE_MS_MODEL        = FIXTURES_DIR / "ms_model"
FIXTURE_LLAMA           = FIXTURES_DIR / "llama"
FIXTURE_PHI             = FIXTURES_DIR / "phi"
FIXTURE_PARSEALL_INPUT  = FIXTURES_DIR / "parseall_input"
FIXTURE_COLLECTION_PWR  = FIXTURES_DIR / "collection_power"


# ---------------------------------------------------------------------------
# Helper: run a top-level parser script as a subprocess
# ---------------------------------------------------------------------------
def run_parser(script_name: str, args: list[str], cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess:
    """Run a parsing-suite script in a subprocess and return the result."""
    cmd = [sys.executable, str(PROJECT_ROOT / script_name)] + args
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def test_config() -> Path:
    return TEST_CONFIG


@pytest.fixture(scope="session")
def fixture_ms_model() -> Path:
    return FIXTURE_MS_MODEL


@pytest.fixture(scope="session")
def fixture_llama() -> Path:
    return FIXTURE_LLAMA


@pytest.fixture(scope="session")
def fixture_phi() -> Path:
    return FIXTURE_PHI


@pytest.fixture(scope="session")
def fixture_parseall_input() -> Path:
    return FIXTURE_PARSEALL_INPUT


@pytest.fixture(scope="session")
def fixture_collection_power() -> Path:
    return FIXTURE_COLLECTION_PWR


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Return a temporary output path prefix (no extension – parsers append _h.xlsx/_v.xlsx)."""
    return tmp_path / "test_out"

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_parseall_help_displays_usage():
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "ParseAll.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "-h"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    output = (result.stdout or "") + (result.stderr or "")
    assert "AI summary parser" in output or "usage" in output.lower()

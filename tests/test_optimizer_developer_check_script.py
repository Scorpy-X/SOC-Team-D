from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_optimizer_developer_check_script_exists_and_uses_validation_runner() -> None:
    script_path = PROJECT_ROOT / "scripts" / "run_optimizer_developer_check.py"
    command_path = PROJECT_ROOT / "Run Optimizer Developer Check.cmd"

    assert script_path.exists()
    assert command_path.exists()

    script_text = script_path.read_text(encoding="utf-8")
    ast.parse(script_text)
    assert "run_optimizer_validation.py" in script_text
    assert "test_optimizer_validation.py" in script_text

    command_text = command_path.read_text(encoding="utf-8")
    assert "scripts\\run_optimizer_developer_check.py" in command_text

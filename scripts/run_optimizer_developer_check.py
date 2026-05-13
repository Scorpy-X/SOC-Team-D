"""Run the optimizer developer evidence checks from one command.

This is a convenience wrapper for teammates. It does not replace the normal
test suite; it runs the optimizer-specific checks and then writes the validation
audit log.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def _run_step(label: str, args: list[str]) -> int:
    print(f"\n=== {label} ===")
    completed = subprocess.run(
        [str(PYTHON_EXE), *args],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return int(completed.returncode)


def main() -> int:
    if not PYTHON_EXE.exists():
        print("Repo virtual environment not found. Run Setup Dev.cmd first.")
        return 1

    steps = [
        (
            "Compile optimizer/advisor modules",
            ["-m", "compileall", "backend\\soc_advisor", "scripts"],
        ),
        (
            "Run optimizer-focused tests",
            [
                "-m",
                "pytest",
                "tests\\test_optimizer_validation.py",
                "tests\\test_portfolio_variant_b.py",
                "tests\\test_portfolio_data_loading.py",
                "--basetemp=tmp\\pytest-optimizer-developer-check",
            ],
        ),
        (
            "Write optimizer validation audit log",
            ["scripts\\run_optimizer_validation.py"],
        ),
    ]

    for label, args in steps:
        return_code = _run_step(label, args)
        if return_code != 0:
            print(f"\nFAILED: {label}")
            return return_code

    print("\nPASS: optimizer developer checks completed.")
    print("See data\\validation\\optimizer-validation-latest.txt for the audit log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for path in (BACKEND_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_advisor_flow_validation import exit_code_for_report  # noqa: E402
from soc_advisor.advisor_flow_validation import (  # noqa: E402
    AdvisorFlowScenario,
    AdvisorFlowValidationReport,
    render_advisor_flow_validation_report,
    run_advisor_flow_validation,
)


def test_advisor_flow_validation_script_and_launcher_exist() -> None:
    script_path = PROJECT_ROOT / "scripts" / "run_advisor_flow_validation.py"
    command_path = PROJECT_ROOT / "Run Advisor Flow Validation.cmd"

    assert script_path.exists()
    assert command_path.exists()
    ast.parse(script_path.read_text(encoding="utf-8"))
    assert "run_advisor_flow_validation" in script_path.read_text(encoding="utf-8")
    assert "scripts\\run_advisor_flow_validation.py" in command_path.read_text(encoding="utf-8")


def test_advisor_flow_validation_report_passes_required_scenarios() -> None:
    report = run_advisor_flow_validation()
    text = render_advisor_flow_validation_report(report)

    assert report.passed is True
    assert "Overall result: PASS" in text
    assert "Calculated questionnaire profile path" in text
    assert "Compatible manual override path" in text
    assert "Unknown manual override rejection" in text
    assert "Manual override automatic liquidity adjustment" in text
    assert "Scored profile automatic liquidity adjustment" in text
    assert "No compatible profile rejection" in text
    assert "Risk reality trace preserves override status" in text
    assert "explanation-trace completeness" in text
    assert "auto_adjusted_to_safer_profile" in text
    assert "profile_source=liquidity_adjusted_manual_profile" in text
    assert "profile_source=liquidity_adjusted_questionnaire" in text


def test_advisor_flow_validation_exit_code_reflects_failures() -> None:
    passing_report = AdvisorFlowValidationReport(
        generated_at=datetime.now(),
        scenarios=[AdvisorFlowScenario("example", True, "passed")],
    )
    failing_report = AdvisorFlowValidationReport(
        generated_at=datetime.now(),
        scenarios=[AdvisorFlowScenario("example", False, "failed")],
    )

    assert exit_code_for_report(passing_report) == 0
    assert exit_code_for_report(failing_report) == 1

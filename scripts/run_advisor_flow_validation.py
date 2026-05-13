"""Run the SOC advisor service-flow validation evidence pack."""

from __future__ import annotations

import sys
import logging
import warnings
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.advisor_flow_validation import (  # noqa: E402
    AdvisorFlowValidationReport,
    render_advisor_flow_validation_report,
    run_advisor_flow_validation,
    write_advisor_flow_validation_logs,
)


def configure_terminal_output() -> None:
    """Keep the advisor-flow report readable for click-run validation."""

    warnings.filterwarnings(
        "ignore",
        message="The covariance matrix is non positive semidefinite.*",
        category=UserWarning,
    )
    logging.getLogger("soc_advisor.portfolio").setLevel(logging.ERROR)


def exit_code_for_report(report: AdvisorFlowValidationReport) -> int:
    """Return the CLI status code for one validation report."""

    return 0 if report.passed else 1


def main() -> int:
    configure_terminal_output()
    report = run_advisor_flow_validation()
    report_text = render_advisor_flow_validation_report(report)
    print(report_text)

    latest_path, timestamped_path = write_advisor_flow_validation_logs(
        report_text,
        generated_at=report.generated_at,
    )
    print(f"Latest advisor-flow validation log: {latest_path}")
    print(f"Timestamped advisor-flow validation log: {timestamped_path}")

    return exit_code_for_report(report)


if __name__ == "__main__":
    raise SystemExit(main())

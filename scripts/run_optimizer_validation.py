"""Run the SOC advisor optimizer validation evidence pack."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings
from pathlib import Path


# Keep the click-run validation script stable on ordinary student machines.
# These defaults must be set before NumPy/SciPy/PyPortfolioOpt are imported.
for thread_env_var in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(thread_env_var, "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.optimizer_validation import (  # noqa: E402
    render_validation_report,
    run_optimizer_validation,
    write_validation_logs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run optimizer validation and write a terminal/log audit report."
    )
    parser.add_argument(
        "--portfolio-version",
        default=None,
        help="Portfolio config version to validate. Defaults to the active settings value.",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Print only; do not write data/validation logs.",
    )
    return parser


def configure_terminal_output() -> None:
    """Keep the validation report readable while preserving audit facts in text."""

    warnings.filterwarnings(
        "ignore",
        message="The covariance matrix is non positive semidefinite.*",
        category=UserWarning,
    )
    logging.getLogger("soc_advisor.portfolio").setLevel(logging.ERROR)


def main() -> int:
    args = build_parser().parse_args()
    configure_terminal_output()
    report = run_optimizer_validation(portfolio_version=args.portfolio_version)
    report_text = render_validation_report(report)
    print(report_text)

    if not args.no_log:
        latest_path, timestamped_path = write_validation_logs(
            report_text,
            generated_at=report.generated_at,
        )
        print(f"Latest validation log: {latest_path}")
        print(f"Timestamped validation log: {timestamped_path}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

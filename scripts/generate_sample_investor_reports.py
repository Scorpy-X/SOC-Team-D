"""Generate one local HTML report set for each configured investor profile."""

from __future__ import annotations

import argparse
import html
import os
import shutil
import sys
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory


# Keep local sample generation predictable on student machines.
for thread_env_var in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(thread_env_var, "1")
os.environ["ADVISOR_REPORT_USE_LLM"] = "0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "reports" / "samples" / "latest"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from soc_advisor import reporting as reporting_module  # noqa: E402
from soc_advisor.database import Base  # noqa: E402
from soc_advisor.report_llm import build_deterministic_report_prose  # noqa: E402
from soc_advisor.risk_reality import (  # noqa: E402
    build_risk_reality_estimate,
    build_risk_reality_trace,
)
from soc_advisor.services import (  # noqa: E402
    build_session_state,
    create_assessment_session,
    get_saved_decision_trace,
    load_questionnaire,
    preview_assessment_recommendation,
    submit_assessment,
    upsert_answer,
)
from soc_advisor.portfolio import load_portfolio_config  # noqa: E402


SAMPLE_PORTFOLIO_VALUE = 800000.0
SAMPLE_LIQUIDITY_ANSWERS: dict[str, dict[str, str | float]] = {
    "portfolio_value": {"numeric_value": SAMPLE_PORTFOLIO_VALUE},
    "major_expense_withdrawal_amount": {"numeric_value": 0.0},
    "essential_monthly_expenses": {"numeric_value": 0.0},
    "emergency_fund_months": {"option_id": "months_0"},
}

SAMPLE_PROFILE_ANSWERS: dict[str, dict[str, dict[str, str | float]]] = {
    "very_conservative": {
        "current_emergency_fund_months": {"option_id": "current_months_0"},
        "non_investment_income_stability": {"option_id": "unstable"},
        "dependents_obligations": {"option_id": "heavy_dependents"},
        "time_horizon": {"option_id": "years_5_or_less"},
        "investment_phase": {"option_id": "disbursement"},
        "market_drop_response": {"option_id": "sell_everything"},
        "short_term_loss_willingness": {"option_id": "very_unwilling"},
        "financial_knowledge": {"option_id": "limited_knowledge"},
        "investing_experience_length": {"option_id": "lt_1_year"},
        "hypothetical_30_loss_reaction": {"option_id": "move_safer_before_worse"},
    },
    "conservative": {
        "current_emergency_fund_months": {"option_id": "current_months_1_3"},
        "non_investment_income_stability": {"option_id": "moderately_stable"},
        "dependents_obligations": {"option_id": "heavy_dependents"},
        "time_horizon": {"option_id": "years_5_or_less"},
        "investment_phase": {"option_id": "disbursement"},
        "market_drop_response": {"option_id": "sell_portion"},
        "short_term_loss_willingness": {"option_id": "unwilling"},
        "financial_knowledge": {"option_id": "basic_understanding"},
        "investing_experience_length": {"option_id": "years_1_3"},
        "hypothetical_30_loss_reaction": {"option_id": "took_too_much_risk"},
    },
    "balanced": {
        "current_emergency_fund_months": {"option_id": "current_months_4_6"},
        "non_investment_income_stability": {"option_id": "moderately_stable"},
        "dependents_obligations": {"option_id": "some_dependents"},
        "time_horizon": {"option_id": "years_6_to_9"},
        "investment_phase": {"option_id": "disbursement"},
        "market_drop_response": {"option_id": "stay_invested"},
        "short_term_loss_willingness": {"option_id": "indifferent"},
        "financial_knowledge": {"option_id": "moderate_understanding"},
        "investing_experience_length": {"option_id": "years_4_10"},
        "hypothetical_30_loss_reaction": {"option_id": "declines_expected"},
    },
    "growth": {
        "current_emergency_fund_months": {"option_id": "current_months_4_6"},
        "non_investment_income_stability": {"option_id": "very_stable"},
        "dependents_obligations": {"option_id": "little_to_none"},
        "time_horizon": {"option_id": "years_6_to_9"},
        "investment_phase": {"option_id": "accumulation"},
        "market_drop_response": {"option_id": "stay_invested"},
        "short_term_loss_willingness": {"option_id": "willing"},
        "financial_knowledge": {"option_id": "moderate_understanding"},
        "investing_experience_length": {"option_id": "years_4_10"},
        "hypothetical_30_loss_reaction": {"option_id": "declines_expected"},
    },
    "aggressive": {
        "current_emergency_fund_months": {"option_id": "current_months_6_plus"},
        "non_investment_income_stability": {"option_id": "very_stable"},
        "dependents_obligations": {"option_id": "little_to_none"},
        "time_horizon": {"option_id": "years_10_plus"},
        "investment_phase": {"option_id": "accumulation"},
        "market_drop_response": {"option_id": "invest_more"},
        "short_term_loss_willingness": {"option_id": "very_willing"},
        "financial_knowledge": {"option_id": "advanced_knowledge"},
        "investing_experience_length": {"option_id": "years_10_plus"},
        "hypothetical_30_loss_reaction": {"option_id": "opportunity_invest_more"},
    },
}

def _reset_output_dir(output_dir: Path) -> None:
    """Clear the sample output folder without touching parent report history."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _write_index(output_dir: Path, generated_profiles: list[tuple[str, str]]) -> Path:
    rows = "\n".join(
        (
            "<li>"
            f"<a href=\"{html.escape(profile_id)}/portfolio-report.html\">"
            f"{html.escape(label)} user report</a>"
            " | "
            f"<a href=\"{html.escape(profile_id)}/portfolio-audit-report.html\">audit report</a>"
            "</li>"
        )
        for profile_id, label in generated_profiles
    )
    index_path = output_dir / "index.html"
    index_path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                "<html lang=\"en\">",
                "<head>",
                "  <meta charset=\"utf-8\">",
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
                "  <title>SOC Advisor Sample Investor Reports</title>",
                "  <style>",
                "    body { font-family: Aptos, 'Segoe UI', sans-serif; margin: 40px; line-height: 1.5; background: #f5efe3; color: #12263a; }",
                "    a { color: #1d5f8c; font-weight: 700; }",
                "    li { margin: 10px 0; }",
                "  </style>",
                "</head>",
                "<body>",
                "  <h1>SOC Advisor sample investor reports</h1>",
                f"  <p>Sample portfolio value: ${SAMPLE_PORTFOLIO_VALUE:,.2f}</p>",
                "  <ul>",
                rows,
                "  </ul>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )
    return index_path


def _sample_answers_for_profile(profile_id: str) -> dict[str, dict[str, str | float]]:
    try:
        profile_answers = SAMPLE_PROFILE_ANSWERS[profile_id]
    except KeyError as exc:
        raise ValueError(
            f"No representative sample answers configured for {profile_id}."
        ) from exc
    return {**SAMPLE_LIQUIDITY_ANSWERS, **profile_answers}


def _create_answered_session(db, *, profile_id: str):
    questionnaire = load_questionnaire("v4")
    session = create_assessment_session(
        db,
        questionnaire_version="v4",
        scoring_version="v5",
    )
    sample_answers = _sample_answers_for_profile(profile_id)
    for question in sorted(questionnaire["questions"], key=lambda item: item["order"]):
        payload = sample_answers[question["id"]]
        session = upsert_answer(
            db,
            session=session,
            questionnaire=questionnaire,
            question_id=question["id"],
            option_id=(
                str(payload["option_id"])
                if "option_id" in payload
                else None
            ),
            numeric_value=(
                float(payload["numeric_value"])
                if "numeric_value" in payload
                else None
            ),
        )
    return session


def generate_sample_reports(*, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Generate user and audit reports for every active investor profile."""

    warnings.filterwarnings(
        "ignore",
        message="The covariance matrix is non positive semidefinite.*",
        category=UserWarning,
    )
    output_dir = output_dir.resolve()
    _reset_output_dir(output_dir)

    # Keep sample reports deterministic and fast even if .env enables OpenAI prose.
    reporting_module.build_report_prose = build_deterministic_report_prose
    reporting_module.get_settings = lambda: type(
        "SampleReportSettings",
        (),
        {"advisor_reports_dir": output_dir},
    )()

    portfolio_config = load_portfolio_config("v3")
    questionnaire = load_questionnaire("v4")
    generated_profiles: list[tuple[str, str]] = []

    with TemporaryDirectory(prefix="soc-sample-reports-") as tmp_dir:
        db_path = Path(tmp_dir) / "sample_reports.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=engine)
        try:
            with SessionLocal() as db:
                for profile_id in portfolio_config["band_order"]:
                    label = str(portfolio_config["bands"][profile_id]["label"])
                    session = _create_answered_session(db, profile_id=profile_id)
                    state = build_session_state(session, questionnaire).model_copy(
                        update={"session_id": profile_id}
                    )
                    _preview_profile, preview_recommendation = preview_assessment_recommendation(
                        db,
                        session=session,
                    )
                    risk_estimate = build_risk_reality_estimate(
                        state=state,
                        recommendation=preview_recommendation,
                    )
                    risk_trace = build_risk_reality_trace(
                        risk_estimate,
                        user_action="continued_current_profile",
                        revised_question_ids=[],
                    )
                    submitted, profile, recommendation = submit_assessment(
                        db,
                        session=session,
                        risk_reality_check=risk_trace,
                    )
                    if profile.profile_band != profile_id:
                        raise RuntimeError(
                            "Representative sample answers for "
                            f"{profile_id} produced {profile.profile_band}."
                        )
                    state = build_session_state(submitted, questionnaire).model_copy(
                        update={"session_id": profile_id}
                    )
                    decision_trace = get_saved_decision_trace(submitted)
                    reporting_module.generate_portfolio_reports(
                        state=state,
                        profile=profile,
                        recommendation=recommendation,
                        decision_trace=decision_trace,
                    )
                    generated_profiles.append((profile_id, label))
        finally:
            engine.dispose()

    return _write_index(output_dir, generated_profiles)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate sample user and audit HTML reports for every investor profile."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Folder to write sample reports into. Defaults to data/reports/samples/latest.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    index_path = generate_sample_reports(output_dir=args.output_dir)
    print(f"Sample investor reports generated: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

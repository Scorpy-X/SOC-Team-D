"""Service-level advisor flow validation for profile override behavior.

This module validates advisor decision-flow behavior that does not belong in
the optimizer validation runner: calculated profiles, manual overrides,
liquidity downgrades, and risk-check trace persistence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .database import Base
from .schemas import RiskRealityCheckTrace
from .services import (
    create_assessment_session,
    get_saved_decision_trace,
    load_questionnaire,
    load_scoring,
    score_session,
    submit_assessment,
    upsert_answer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"


@dataclass(frozen=True)
class AdvisorFlowScenario:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AdvisorFlowValidationReport:
    generated_at: datetime
    scenarios: list[AdvisorFlowScenario]

    @property
    def passed(self) -> bool:
        return all(scenario.passed for scenario in self.scenarios)


def _base_answers(
    *,
    portfolio_value: float = 100000.0,
    major_expense: float = 0.0,
    monthly_expenses: float = 0.0,
    emergency_fund_months: str = "months_0",
) -> dict[str, dict[str, str | float]]:
    """Return aggressive-leaning complete answers for the active questionnaire."""

    return {
        "portfolio_value": {"numeric_value": portfolio_value},
        "major_expense_withdrawal_amount": {"numeric_value": major_expense},
        "essential_monthly_expenses": {"numeric_value": monthly_expenses},
        "emergency_fund_months": {"option_id": emergency_fund_months},
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
    }


def _create_answered_session(
    db: Session,
    *,
    answers: dict[str, dict[str, str | float]] | None = None,
):
    questionnaire = load_questionnaire("v4")
    session = create_assessment_session(
        db,
        questionnaire_version="v4",
        scoring_version="v5",
    )
    resolved_answers = answers or _base_answers()
    for question in sorted(questionnaire["questions"], key=lambda item: item["order"]):
        payload = resolved_answers[question["id"]]
        session = upsert_answer(
            db,
            session=session,
            questionnaire=questionnaire,
            question_id=question["id"],
            option_id=payload.get("option_id") if isinstance(payload.get("option_id"), str) else None,
            numeric_value=(
                float(payload["numeric_value"])
                if "numeric_value" in payload
                else None
            ),
        )
    return session


def _scenario(
    name: str,
    check: Callable[[], str],
) -> AdvisorFlowScenario:
    try:
        return AdvisorFlowScenario(name=name, passed=True, detail=check())
    except Exception as exc:  # noqa: BLE001 - validation should report every failure plainly.
        return AdvisorFlowScenario(name=name, passed=False, detail=f"{type(exc).__name__}: {exc}")


def _assert_contract_complete_trace(
    trace,
    *,
    expect_manual_override: bool,
    expect_liquidity_check: bool,
    expect_risk_check: bool,
) -> None:
    """Fail if the saved decision trace is missing contract-required facts."""

    assert trace.trace_version == "decision-trace-v1"
    assert trace.questionnaire_version
    assert trace.scoring_version
    assert trace.portfolio_version
    assert trace.profile_band
    assert trace.profile_label
    assert trace.profile_source
    assert trace.data_source in {"live_soc_api", "csv_snapshot"}
    assert trace.optimizer_objective
    assert isinstance(trace.risk_free_rate, float)
    assert len(trace.weight_bounds) == 2
    assert isinstance(trace.single_asset_cap, float)
    assert isinstance(trace.covariance_psd_repair_enabled, bool)
    assert isinstance(trace.applied_overlays, list)
    assert trace.super_class_minima
    assert trace.super_class_maxima
    assert isinstance(trace.limitations, list) and trace.limitations

    scoring = trace.scoring_policy_trace
    assert scoring is not None
    assert scoring.method == "weighted_normalized_sections"
    assert scoring.capacity_score is not None
    assert scoring.tolerance_score is not None
    assert 0.0 <= scoring.final_score_before_caps <= 1.0
    assert 0.0 <= scoring.final_score_after_caps <= 1.0
    assert scoring.draft_profile_band
    assert scoring.final_profile_band
    assert scoring.draft_profile_label
    assert scoring.final_profile_label
    assert "risk_capacity" in scoring.section_scores
    assert "risk_tolerance" in scoring.section_scores
    assert scoring.manual_override_used is expect_manual_override

    if expect_manual_override:
        assert scoring.manual_override_band
        assert scoring.manual_override_label
    else:
        assert scoring.manual_override_band is None
        assert scoring.manual_override_label is None

    if expect_liquidity_check:
        liquidity = trace.liquidity_policy_check
        assert liquidity is not None
        assert liquidity.required_liquidity_amount >= 0.0
        assert liquidity.liquidity_floor >= 0.0
        assert liquidity.selected_profile_band
        assert liquidity.selected_profile_label
    else:
        assert trace.liquidity_policy_check is not None

    if expect_risk_check:
        risk_check = trace.risk_reality_check
        assert risk_check is not None
        assert risk_check.method == "two_standard_deviation_volatility_proxy"
        assert risk_check.multiplier == 2.0
        assert risk_check.stress_percent >= 0.0
    else:
        assert trace.risk_reality_check is None


def _calculated_profile_path(db: Session) -> str:
    session = _create_answered_session(db)
    saved_session, profile, recommendation = submit_assessment(
        db,
        session=session,
        mock_profile_band=None,
    )
    trace = get_saved_decision_trace(saved_session)
    _assert_contract_complete_trace(
        trace,
        expect_manual_override=False,
        expect_liquidity_check=True,
        expect_risk_check=False,
    )
    assert profile.profile_source == "scored_questionnaire"
    assert trace.scoring_policy_trace is not None
    assert trace.scoring_policy_trace.manual_override_used is False
    assert recommendation.profile_band == profile.profile_band
    return f"Calculated profile {profile.profile_label}; manual override recorded as false."


def _compatible_manual_override(db: Session) -> str:
    session = _create_answered_session(db)
    saved_session, profile, recommendation = submit_assessment(
        db,
        session=session,
        mock_profile_band="growth",
    )
    trace = get_saved_decision_trace(saved_session)
    _assert_contract_complete_trace(
        trace,
        expect_manual_override=True,
        expect_liquidity_check=True,
        expect_risk_check=False,
    )
    assert profile.profile_band == "growth"
    assert profile.profile_source == "manual_mock_band"
    assert recommendation.profile_band == "growth"
    assert trace.scoring_policy_trace is not None
    assert trace.scoring_policy_trace.manual_override_used is True
    return "Growth override submitted and persisted as manual override."


def _unknown_manual_override_rejected(db: Session) -> str:
    session = _create_answered_session(db)
    try:
        submit_assessment(db, session=session, mock_profile_band="not_a_real_profile")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "mock_profile_band" in str(exc.detail)
        return "Unknown profile rejected with HTTP 400."
    raise AssertionError("Unknown manual override unexpectedly submitted.")


def _manual_override_auto_adjusts_liquidity_profile(db: Session) -> str:
    session = _create_answered_session(
        db,
        answers=_base_answers(major_expense=22000.0),
    )
    saved_session, profile, recommendation = submit_assessment(
        db,
        session=session,
        mock_profile_band="growth",
    )
    trace = get_saved_decision_trace(saved_session)
    _assert_contract_complete_trace(
        trace,
        expect_manual_override=True,
        expect_liquidity_check=True,
        expect_risk_check=False,
    )
    assert profile.profile_source == "liquidity_adjusted_manual_profile"
    assert profile.profile_band == "conservative"
    assert recommendation.profile_band == "conservative"
    assert trace.liquidity_policy_check is not None
    assert trace.liquidity_policy_check.selected_profile_band == "growth"
    assert trace.liquidity_policy_check.effective_profile_band == "conservative"
    assert trace.liquidity_policy_check.user_action == "auto_adjusted_to_safer_profile"
    return (
        "Growth override automatically adjusted to Conservative after liquidity check; "
        "action=auto_adjusted_to_safer_profile; "
        "profile_source=liquidity_adjusted_manual_profile."
    )


def _scored_profile_auto_adjusts_liquidity_profile(db: Session) -> str:
    session = _create_answered_session(
        db,
        answers=_base_answers(major_expense=22000.0),
    )
    questionnaire = load_questionnaire("v4")
    scoring = load_scoring("v5")
    scored_profile = score_session(session, questionnaire, scoring)
    saved_session, profile, recommendation = submit_assessment(
        db,
        session=session,
        mock_profile_band=None,
    )
    trace = get_saved_decision_trace(saved_session)
    _assert_contract_complete_trace(
        trace,
        expect_manual_override=False,
        expect_liquidity_check=True,
        expect_risk_check=False,
    )
    assert profile.profile_source == "liquidity_adjusted_questionnaire"
    assert recommendation.profile_band == profile.profile_band
    assert trace.scoring_policy_trace is not None
    assert trace.scoring_policy_trace.manual_override_used is False
    assert trace.liquidity_policy_check is not None
    assert trace.liquidity_policy_check.user_action == "auto_adjusted_to_safer_profile"
    return (
        f"Calculated {scored_profile.profile_label} profile adjusted to "
        f"{profile.profile_label} automatically after liquidity check; "
        "action=auto_adjusted_to_safer_profile; "
        "profile_source=liquidity_adjusted_questionnaire."
    )


def _no_compatible_profile_rejected(db: Session) -> str:
    session = _create_answered_session(
        db,
        answers=_base_answers(major_expense=50000.0),
    )
    try:
        submit_assessment(db, session=session, mock_profile_band="growth")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert isinstance(exc.detail, dict)
        assert exc.detail["selected_profile_band"] == "growth"
        assert exc.detail["suggested_profile_band"] is None
        assert exc.detail["user_action"] == "blocked_no_compatible_profile"
        return "No compatible profile rejected with clear liquidity policy detail."
    raise AssertionError("No-compatible-profile case unexpectedly submitted.")


def _risk_reality_trace_preserves_override(db: Session) -> str:
    session = _create_answered_session(db)
    risk_trace = RiskRealityCheckTrace(
        annual_volatility=0.072,
        stress_percent=0.144,
        portfolio_value=100000.0,
        stress_amount=14400.0,
        user_action="continued_current_profile",
        revised_question_ids=[],
    )
    saved_session, _profile, _recommendation = submit_assessment(
        db,
        session=session,
        mock_profile_band="growth",
        risk_reality_check=risk_trace,
    )
    trace = get_saved_decision_trace(saved_session)
    _assert_contract_complete_trace(
        trace,
        expect_manual_override=True,
        expect_liquidity_check=True,
        expect_risk_check=True,
    )
    assert trace.risk_reality_check is not None
    assert trace.risk_reality_check.user_action == "continued_current_profile"
    assert trace.scoring_policy_trace is not None
    assert trace.scoring_policy_trace.manual_override_used is True
    return "Risk reality trace stored and manual override flag preserved."


def _run_scenarios(db: Session) -> list[AdvisorFlowScenario]:
    scenario_specs: list[tuple[str, Callable[[Session], str]]] = [
        ("Calculated questionnaire profile path", _calculated_profile_path),
        ("Compatible manual override path", _compatible_manual_override),
        ("Unknown manual override rejection", _unknown_manual_override_rejected),
        ("Manual override automatic liquidity adjustment", _manual_override_auto_adjusts_liquidity_profile),
        ("Scored profile automatic liquidity adjustment", _scored_profile_auto_adjusts_liquidity_profile),
        ("No compatible profile rejection", _no_compatible_profile_rejected),
        ("Risk reality trace preserves override status", _risk_reality_trace_preserves_override),
    ]
    return [
        _scenario(name, lambda fn=fn: fn(db))
        for name, fn in scenario_specs
    ]


def run_advisor_flow_validation() -> AdvisorFlowValidationReport:
    """Run advisor-flow scenarios against an isolated SQLite database."""

    with TemporaryDirectory(prefix="soc-advisor-flow-") as tmp_dir:
        db_path = Path(tmp_dir) / "advisor_flow_validation.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        TestingSessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
        )
        Base.metadata.create_all(bind=engine)
        try:
            with TestingSessionLocal() as db:
                scenarios = _run_scenarios(db)
        finally:
            engine.dispose()

    return AdvisorFlowValidationReport(
        generated_at=datetime.now().astimezone(),
        scenarios=scenarios,
    )


def render_advisor_flow_validation_report(report: AdvisorFlowValidationReport) -> str:
    """Render a terminal/log friendly advisor-flow audit report."""

    lines = [
        "SOC Advisor Flow Validation",
        f"Generated: {report.generated_at.isoformat(timespec='seconds')}",
        "",
        f"Overall result: {'PASS' if report.passed else 'FAIL'}",
        "",
        "Validation claim",
        (
            "This report checks service-level advisor flow behavior: calculated profiles, "
            "manual overrides, liquidity adjustments, risk-check trace persistence, "
            "and explanation-trace completeness. It does not validate optimizer math; "
            "use run_optimizer_validation.py for that."
        ),
        "",
        "Scenario results",
    ]
    for scenario in report.scenarios:
        status = "PASS" if scenario.passed else "FAIL"
        lines.append(f"{status} - {scenario.name}: {scenario.detail}")
    return "\n".join(lines) + "\n"


def write_advisor_flow_validation_logs(
    report_text: str,
    *,
    generated_at: datetime,
) -> tuple[Path, Path]:
    """Write latest and timestamped advisor-flow validation logs."""

    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    latest_path = VALIDATION_DIR / "advisor-flow-validation-latest.txt"
    timestamp = generated_at.strftime("%Y-%m-%d-%H%M%S")
    timestamped_path = VALIDATION_DIR / f"advisor-flow-validation-{timestamp}.txt"
    latest_path.write_text(report_text, encoding="utf-8")
    timestamped_path.write_text(report_text, encoding="utf-8")
    return latest_path, timestamped_path

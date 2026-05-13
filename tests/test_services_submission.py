from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.services import (  # noqa: E402
    create_assessment_session,
    get_saved_decision_trace,
    get_saved_profile,
    load_questionnaire,
    preview_assessment_recommendation,
    submit_assessment,
    upsert_answer,
)
from soc_advisor.schemas import RiskRealityCheckTrace  # noqa: E402


def _set_major_expense(
    db_session,
    session,
    *,
    amount: float,
):
    questionnaire = load_questionnaire(session.questionnaire_version)
    return upsert_answer(
        db_session,
        session=session,
        questionnaire=questionnaire,
        question_id="major_expense_withdrawal_amount",
        numeric_value=amount,
    )


def _build_growth_scored_liquidity_session(db_session):
    questionnaire = load_questionnaire("v4")
    session = create_assessment_session(
        db_session,
        questionnaire_version="v4",
        scoring_version="v5",
    )
    answers = {
        "portfolio_value": {"numeric_value": 100000.0},
        "major_expense_withdrawal_amount": {"numeric_value": 20000.0},
        "essential_monthly_expenses": {"numeric_value": 0.0},
        "emergency_fund_months": {"option_id": "months_0"},
        "current_emergency_fund_months": {"option_id": "current_months_6_plus"},
        "non_investment_income_stability": {"option_id": "very_stable"},
        "dependents_obligations": {"option_id": "little_to_none"},
        "time_horizon": {"option_id": "years_6_to_9"},
        "investment_phase": {"option_id": "accumulation"},
        "market_drop_response": {"option_id": "stay_invested"},
        "short_term_loss_willingness": {"option_id": "indifferent"},
        "financial_knowledge": {"option_id": "moderate_understanding"},
        "investing_experience_length": {"option_id": "years_4_10"},
        "hypothetical_30_loss_reaction": {"option_id": "declines_expected"},
    }
    for question in questionnaire["questions"]:
        payload = answers[question["id"]]
        session = upsert_answer(
            db_session,
            session=session,
            questionnaire=questionnaire,
            question_id=question["id"],
            option_id=payload.get("option_id"),
            numeric_value=payload.get("numeric_value"),
        )
    return session


@pytest.mark.parametrize(
    "mock_profile_band",
    [
        "very_conservative",
        "conservative",
        "balanced",
        "growth",
        "aggressive",
    ],
)
def test_submit_assessment_accepts_manual_mock_bands(
    db_session,
    answered_session,
    mock_profile_band: str,
) -> None:
    compatible_session = _set_major_expense(db_session, answered_session, amount=0.0)
    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=compatible_session,
        mock_profile_band=mock_profile_band,
    )

    assert profile.profile_band == mock_profile_band
    assert profile.profile_source == "manual_mock_band"
    assert profile.profile_score is None
    assert recommendation.profile_band == mock_profile_band
    assert any("manual" in note.lower() for note in recommendation.notes)
    assert any("liquidity inputs are used" in note.lower() for note in recommendation.notes)
    assert recommendation.constraints.super_class_minima["Cash"] >= 0.0

    saved_profile = get_saved_profile(saved_session)
    assert saved_profile.profile_source == "manual_mock_band"
    assert saved_profile.profile_score is None

    decision_trace = get_saved_decision_trace(saved_session)
    assert decision_trace.profile_band == mock_profile_band
    assert decision_trace.profile_source == "manual_mock_band"
    assert decision_trace.data_source in {"live_soc_api", "csv_snapshot"}
    assert decision_trace.portfolio_version == recommendation.version
    assert decision_trace.optimizer_objective == recommendation.objective
    assert decision_trace.covariance_psd_repair_enabled is True
    assert decision_trace.captured_but_not_used == []
    assert decision_trace.liquidity_policy_check is not None
    assert decision_trace.liquidity_policy_check.effective_profile_band == mock_profile_band


def test_submit_assessment_preserves_scored_fallback(db_session, answered_session) -> None:
    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=answered_session,
        mock_profile_band=None,
    )

    assert profile.profile_source == "scored_questionnaire"
    assert profile.profile_score is not None
    assert recommendation.profile_band == profile.profile_band
    assert get_saved_profile(saved_session).profile_source == "scored_questionnaire"

    decision_trace = get_saved_decision_trace(saved_session)
    assert decision_trace.scoring_policy_trace is not None
    assert decision_trace.scoring_policy_trace.method == "weighted_normalized_sections"
    assert decision_trace.scoring_policy_trace.capacity_score is not None
    assert decision_trace.scoring_policy_trace.tolerance_score is not None
    assert decision_trace.scoring_policy_trace.manual_override_used is False


def test_preview_assessment_recommendation_does_not_submit_session(
    db_session,
    answered_session,
) -> None:
    compatible_session = _set_major_expense(db_session, answered_session, amount=0.0)
    state_before = answered_session.status

    profile, recommendation = preview_assessment_recommendation(
        db_session,
        session=compatible_session,
        mock_profile_band="growth",
    )

    assert state_before == "draft"
    assert answered_session.status == "draft"
    assert answered_session.result_json is None
    assert profile.profile_band == "growth"
    assert recommendation.profile_band == "growth"


def test_submit_assessment_persists_risk_reality_check_trace(
    db_session,
    answered_session,
) -> None:
    compatible_session = _set_major_expense(db_session, answered_session, amount=0.0)
    risk_trace = RiskRealityCheckTrace(
        annual_volatility=0.072,
        stress_percent=0.144,
        portfolio_value=100000.0,
        stress_amount=14400.0,
        user_action="continued_current_profile",
        revised_question_ids=["market_drop_response"],
    )

    saved_session, _profile, _recommendation = submit_assessment(
        db_session,
        session=compatible_session,
        mock_profile_band="growth",
        risk_reality_check=risk_trace,
    )

    decision_trace = get_saved_decision_trace(saved_session)
    assert decision_trace.risk_reality_check == risk_trace
    assert decision_trace.scoring_policy_trace is not None
    assert decision_trace.scoring_policy_trace.manual_override_used is True


def test_submit_assessment_rejects_unknown_mock_band(db_session, answered_session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        submit_assessment(
            db_session,
            session=answered_session,
            mock_profile_band="not_a_real_band",
        )

    assert exc_info.value.status_code == 400
    assert "mock_profile_band" in str(exc_info.value.detail)


def test_submit_assessment_auto_adjusts_incompatible_direct_profile(
    db_session,
    answered_session,
) -> None:
    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=answered_session,
        mock_profile_band="growth",
    )

    trace = get_saved_decision_trace(saved_session)
    assert profile.profile_band == "balanced"
    assert profile.profile_source == "liquidity_adjusted_manual_profile"
    assert recommendation.profile_band == "balanced"
    assert trace.liquidity_policy_check is not None
    assert trace.liquidity_policy_check.selected_profile_band == "growth"
    assert trace.liquidity_policy_check.effective_profile_band == "balanced"
    assert trace.liquidity_policy_check.profile_adjusted is True
    assert trace.liquidity_policy_check.user_action == "auto_adjusted_to_safer_profile"
    assert recommendation.constraints.super_class_minima["Cash"] == pytest.approx(0.20)


def test_submit_assessment_rejects_when_no_profile_can_support_liquidity(
    db_session,
    answered_session,
) -> None:
    high_liquidity_session = _set_major_expense(
        db_session,
        answered_session,
        amount=30000.0,
    )

    with pytest.raises(HTTPException) as exc_info:
        submit_assessment(
            db_session,
            session=high_liquidity_session,
            mock_profile_band="growth",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["selected_profile_band"] == "growth"
    assert exc_info.value.detail["suggested_profile_band"] is None
    assert exc_info.value.detail["liquidity_floor"] > 0.35


def test_submit_assessment_preserves_original_manual_override_after_liquidity_adjustment(
    db_session,
    answered_session,
) -> None:
    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=answered_session,
        mock_profile_band="growth",
    )

    trace = get_saved_decision_trace(saved_session)
    assert profile.profile_band == "balanced"
    assert recommendation.profile_band == "balanced"
    assert trace.scoring_policy_trace is not None
    assert trace.scoring_policy_trace.manual_override_used is True
    assert trace.scoring_policy_trace.manual_override_band == "growth"
    assert trace.scoring_policy_trace.manual_override_label == "Growth"


def test_scored_profile_can_be_adjusted_by_automatic_liquidity_policy(
    db_session,
) -> None:
    scored_session = _build_growth_scored_liquidity_session(db_session)

    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=scored_session,
        mock_profile_band=None,
    )

    trace = get_saved_decision_trace(saved_session)
    assert profile.profile_band == "balanced"
    assert profile.profile_source == "liquidity_adjusted_questionnaire"
    assert recommendation.profile_band == "balanced"
    assert trace.scoring_policy_trace is not None
    assert trace.scoring_policy_trace.manual_override_used is False
    assert trace.liquidity_policy_check is not None
    assert trace.liquidity_policy_check.selected_profile_band == "growth"
    assert trace.liquidity_policy_check.user_action == "auto_adjusted_to_safer_profile"

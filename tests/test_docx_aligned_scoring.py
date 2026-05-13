from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.schemas import QuestionnaireResponse  # noqa: E402
from soc_advisor.services import (  # noqa: E402
    create_assessment_session,
    load_questionnaire,
    load_scoring,
    score_session,
    upsert_answer,
)


def _answer_v4_session(db_session, answers: dict[str, str | float]):
    questionnaire = load_questionnaire("v4")
    session = create_assessment_session(
        db_session,
        questionnaire_version="v4",
        scoring_version="v5",
    )
    for question in sorted(questionnaire["questions"], key=lambda item: item["order"]):
        value = answers[question["id"]]
        if question["type"] == "currency_amount":
            session = upsert_answer(
                db_session,
                session=session,
                questionnaire=questionnaire,
                question_id=question["id"],
                numeric_value=float(value),
            )
        else:
            session = upsert_answer(
                db_session,
                session=session,
                questionnaire=questionnaire,
                question_id=question["id"],
                option_id=str(value),
            )
    return session


def _base_answers() -> dict[str, str | float]:
    return {
        "portfolio_value": 100000.0,
        "major_expense_withdrawal_amount": 0.0,
        "essential_monthly_expenses": 0.0,
        "emergency_fund_months": "months_0",
        "current_emergency_fund_months": "current_months_0",
        "non_investment_income_stability": "unstable",
        "dependents_obligations": "heavy_dependents",
        "time_horizon": "years_5_or_less",
        "investment_phase": "disbursement",
        "market_drop_response": "sell_everything",
        "short_term_loss_willingness": "very_unwilling",
        "financial_knowledge": "limited_knowledge",
        "investing_experience_length": "lt_1_year",
        "hypothetical_30_loss_reaction": "move_safer_before_worse",
    }


def _aggressive_answers() -> dict[str, str | float]:
    answers = _base_answers()
    answers.update(
        {
            "current_emergency_fund_months": "current_months_6_plus",
            "non_investment_income_stability": "very_stable",
            "dependents_obligations": "little_to_none",
            "time_horizon": "years_10_plus",
            "investment_phase": "accumulation",
            "market_drop_response": "invest_more",
            "short_term_loss_willingness": "very_willing",
            "financial_knowledge": "advanced_knowledge",
            "investing_experience_length": "years_10_plus",
            "hypothetical_30_loss_reaction": "opportunity_invest_more",
        }
    )
    return answers


def test_questionnaire_v4_validates_and_contains_docx_aligned_questions() -> None:
    questionnaire = load_questionnaire("v4")
    response = QuestionnaireResponse.model_validate(questionnaire)
    questions_by_id = {question["id"]: question for question in questionnaire["questions"]}

    assert response.version == "v4"
    assert len(response.questions) == 14
    assert questions_by_id["portfolio_value"]["used_for_scoring"] is False
    assert questions_by_id["emergency_fund_months"]["used_for_scoring"] is False
    assert "current_emergency_fund_months" in questions_by_id
    assert "dependents_obligations" in questions_by_id
    assert "hypothetical_30_loss_reaction" in questions_by_id

    q10_options = {
        option["id"] for option in questions_by_id["market_drop_response"]["options"]
    }
    assert "stay_invested" in q10_options


def test_scoring_v5_policy_weights_and_cap_rule_are_configured() -> None:
    scoring = load_scoring("v5")

    assert scoring["method"] == "weighted_normalized_sections"
    assert sum(scoring["sections"]["risk_capacity"]["questions"].values()) == pytest.approx(1.35)
    assert sum(scoring["sections"]["risk_tolerance"]["questions"].values()) == pytest.approx(1.10)
    assert scoring["section_weights"] == {"risk_capacity": 0.60, "risk_tolerance": 0.40}
    assert scoring["cap_rules"][0]["max_profile_band"] == "balanced"
    assert scoring["cap_rules"][0]["option_ids"] == ["sell_everything"]


def test_weighted_scoring_maps_conservative_answers_to_very_conservative(db_session) -> None:
    questionnaire = load_questionnaire("v4")
    scoring = load_scoring("v5")
    session = _answer_v4_session(db_session, _base_answers())

    profile = score_session(session, questionnaire, scoring)

    assert profile.profile_band == "very_conservative"
    assert profile.profile_score == pytest.approx(0.0)
    assert profile.dimension_scores["risk_capacity"] == pytest.approx(0.0)
    assert profile.dimension_scores["risk_tolerance"] == pytest.approx(0.0)


def test_weighted_scoring_maps_aggressive_answers_to_aggressive(db_session) -> None:
    questionnaire = load_questionnaire("v4")
    scoring = load_scoring("v5")
    session = _answer_v4_session(db_session, _aggressive_answers())

    profile = score_session(session, questionnaire, scoring)

    assert profile.profile_band == "aggressive"
    assert profile.profile_score == pytest.approx(1.0)
    assert profile.dimension_scores["risk_capacity"] == pytest.approx(1.0)
    assert profile.dimension_scores["risk_tolerance"] == pytest.approx(1.0)


def test_sell_everything_caps_aggressive_score_at_balanced(db_session) -> None:
    questionnaire = load_questionnaire("v4")
    scoring = load_scoring("v5")
    answers = _aggressive_answers()
    answers["market_drop_response"] = "sell_everything"
    session = _answer_v4_session(db_session, answers)

    profile = score_session(session, questionnaire, scoring)

    assert profile.profile_band == "balanced"
    assert profile.dimension_scores["final_score_before_caps"] > 0.8
    assert profile.profile_score == pytest.approx(0.599999999)
    assert any("caps" in reason.lower() for reason in profile.reasons)

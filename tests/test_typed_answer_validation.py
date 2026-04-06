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
    load_questionnaire,
    load_scoring,
    score_session,
    upsert_answer,
)
from soc_advisor.typed_answers import parse_and_normalize_currency_amount_text  # noqa: E402


def _build_answered_v3_session(db_session, *, portfolio_value: float) -> object:
    questionnaire = load_questionnaire("v3")
    session = create_assessment_session(
        db_session,
        questionnaire_version="v3",
        scoring_version="v4",
    )

    answers = {
        "portfolio_value": {"numeric_value": portfolio_value},
        "major_expense_withdrawal_amount": {"numeric_value": 10000.0},
        "essential_monthly_expenses": {"numeric_value": 2500.0},
        "emergency_fund_months": {"option_id": "months_4_6"},
        "non_investment_income_stability": {"option_id": "very_stable"},
        "time_horizon": {"option_id": "years_10_plus"},
        "investment_phase": {"option_id": "accumulation"},
        "market_drop_response": {"option_id": "invest_more"},
        "short_term_loss_willingness": {"option_id": "willing"},
        "financial_knowledge": {"option_id": "competent"},
        "investing_experience_length": {"option_id": "years_4_10"},
        "past_loss_action": {"option_id": "did_nothing"},
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


def test_currency_amount_text_parser_accepts_dollar_signs_and_commas() -> None:
    normalized, numeric_value, display = parse_and_normalize_currency_amount_text(
        "$25,000",
        question_id="portfolio_value",
        validation={"min_value": 25000},
    )

    assert normalized == "25000.00"
    assert numeric_value == pytest.approx(25000.0)
    assert display == "$25,000.00"


@pytest.mark.parametrize("raw_text", ["-10", "ten thousand", "25k", "about 25000"])
def test_currency_amount_text_parser_rejects_invalid_text(raw_text: str) -> None:
    with pytest.raises(ValueError):
        parse_and_normalize_currency_amount_text(
            raw_text,
            question_id="portfolio_value",
            validation={"min_value": 25000},
        )


def test_upsert_answer_accepts_currency_amount_for_portfolio_value(db_session) -> None:
    questionnaire = load_questionnaire("v3")
    session = create_assessment_session(db_session, questionnaire_version="v3", scoring_version="v4")

    session = upsert_answer(
        db_session,
        session=session,
        questionnaire=questionnaire,
        question_id="portfolio_value",
        numeric_value=25000.0,
    )

    saved_answer = next(answer for answer in session.answers if answer.question_id == "portfolio_value")
    assert saved_answer.normalized_value == "25000.00"
    assert saved_answer.answer_label_snapshot == "$25,000.00"


def test_portfolio_value_rejects_values_below_minimum(db_session) -> None:
    questionnaire = load_questionnaire("v3")
    session = create_assessment_session(db_session, questionnaire_version="v3", scoring_version="v4")

    with pytest.raises(HTTPException) as exc_info:
        upsert_answer(
            db_session,
            session=session,
            questionnaire=questionnaire,
            question_id="portfolio_value",
            numeric_value=24999.99,
        )

    assert exc_info.value.status_code == 400
    assert "$25,000" in str(exc_info.value.detail)


def test_currency_amount_rejects_option_id_payload(db_session) -> None:
    questionnaire = load_questionnaire("v3")
    session = create_assessment_session(db_session, questionnaire_version="v3", scoring_version="v4")

    with pytest.raises(HTTPException) as exc_info:
        upsert_answer(
            db_session,
            session=session,
            questionnaire=questionnaire,
            question_id="portfolio_value",
            option_id="not_allowed",
        )

    assert exc_info.value.status_code == 400
    assert "numeric_value" in str(exc_info.value.detail)


def test_single_choice_rejects_numeric_payload(db_session) -> None:
    questionnaire = load_questionnaire("v3")
    session = create_assessment_session(db_session, questionnaire_version="v3", scoring_version="v4")

    with pytest.raises(HTTPException) as exc_info:
        upsert_answer(
            db_session,
            session=session,
            questionnaire=questionnaire,
            question_id="financial_knowledge",
            numeric_value=123.0,
        )

    assert exc_info.value.status_code == 400
    assert "option_id" in str(exc_info.value.detail)


def test_scored_fallback_skips_currency_amount_questions(db_session) -> None:
    questionnaire = load_questionnaire("v3")
    scoring = load_scoring("v4")

    low_amount_session = _build_answered_v3_session(db_session, portfolio_value=25000.0)
    low_amount_profile = score_session(low_amount_session, questionnaire, scoring)

    another_session = _build_answered_v3_session(db_session, portfolio_value=2500000.0)
    another_profile = score_session(another_session, questionnaire, scoring)

    assert low_amount_profile.profile_score == another_profile.profile_score
    assert low_amount_profile.profile_band == another_profile.profile_band

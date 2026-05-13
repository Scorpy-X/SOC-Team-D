from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.liquidity_policy import (  # noqa: E402
    EMERGENCY_MONTHS_BY_OPTION_ID,
    build_liquidity_policy_check,
    nearest_liquidity_compatible_profile,
)
from soc_advisor.portfolio import load_portfolio_config  # noqa: E402
from soc_advisor.schemas import AnswerSummary  # noqa: E402


def _answer(question_id: str, value: str, *, option_id: str | None = None) -> AnswerSummary:
    return AnswerSummary(
        question_id=question_id,
        question_text=question_id,
        dimension=question_id,
        answer_type="single_choice" if option_id is not None else "currency_amount",
        option_id=option_id,
        answer_label=value,
    )


def _liquidity_answers(
    *,
    portfolio_value: str = "$100,000.00",
    major_expense: str = "$10,000.00",
    monthly_expenses: str = "$2,000.00",
    emergency_option_id: str = "months_4_6",
) -> list[AnswerSummary]:
    return [
        _answer("portfolio_value", portfolio_value),
        _answer("major_expense_withdrawal_amount", major_expense),
        _answer("essential_monthly_expenses", monthly_expenses),
        _answer(
            "emergency_fund_months",
            emergency_option_id,
            option_id=emergency_option_id,
        ),
    ]


def test_emergency_month_mapping_matches_policy() -> None:
    assert EMERGENCY_MONTHS_BY_OPTION_ID == {
        "months_0": 0.0,
        "months_1_3": 2.0,
        "months_4_6": 5.0,
        "months_6_plus": 9.0,
    }


def test_liquidity_amount_and_floor_are_calculated_from_answers() -> None:
    portfolio_config = load_portfolio_config("v3")

    check = build_liquidity_policy_check(
        answers=_liquidity_answers(),
        selected_profile_band="growth",
        portfolio_config=portfolio_config,
        user_action="checked_selected_profile",
    )

    assert check.required_liquidity_amount == 20000.0
    assert check.liquidity_floor == pytest.approx(0.20)
    assert check.emergency_months_used == 5.0


def test_growth_with_22_percent_liquidity_floor_suggests_conservative() -> None:
    portfolio_config = load_portfolio_config("v3")

    check = build_liquidity_policy_check(
        answers=_liquidity_answers(monthly_expenses="$2,400.00"),
        selected_profile_band="growth",
        portfolio_config=portfolio_config,
        user_action="checked_selected_profile",
    )

    assert check.required_liquidity_amount == 22000.0
    assert check.liquidity_floor == pytest.approx(0.22)
    assert check.selected_profile_compatible is False
    assert check.effective_profile_band == "conservative"
    assert check.profile_adjusted is True


def test_compatible_selected_profile_stays_unchanged() -> None:
    portfolio_config = load_portfolio_config("v3")

    check = build_liquidity_policy_check(
        answers=_liquidity_answers(major_expense="$2,000.00", monthly_expenses="$500.00"),
        selected_profile_band="growth",
        portfolio_config=portfolio_config,
        user_action="checked_selected_profile",
    )

    assert check.liquidity_floor == pytest.approx(0.045)
    assert check.selected_profile_compatible is True
    assert check.effective_profile_band == "growth"
    assert check.profile_adjusted is False


def test_no_profile_fits_if_liquidity_floor_exceeds_safest_cash_ceiling() -> None:
    portfolio_config = load_portfolio_config("v3")

    assert (
        nearest_liquidity_compatible_profile(
            selected_profile_band="aggressive",
            liquidity_floor=0.50,
            portfolio_config=portfolio_config,
        )
        is None
    )


def test_missing_liquidity_answer_fails_clearly() -> None:
    portfolio_config = load_portfolio_config("v3")

    with pytest.raises(ValueError, match="major_expense_withdrawal_amount"):
        build_liquidity_policy_check(
            answers=[
                _answer("portfolio_value", "$100,000.00"),
                _answer("essential_monthly_expenses", "$2,000.00"),
                _answer("emergency_fund_months", "months_4_6", option_id="months_4_6"),
            ],
            selected_profile_band="growth",
            portfolio_config=portfolio_config,
            user_action="checked_selected_profile",
        )

"""Liquidity compatibility policy for the advisor profile flow.

This module owns the rule that liquidity need is checked before the optimizer
builds a portfolio. It does not run PyPortfolioOpt and it does not score the
questionnaire.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from .schemas import LiquidityPolicyCheckTrace


LIQUIDITY_BUCKET = "Cash"
LIQUIDITY_QUESTION_IDS = {
    "portfolio_value",
    "major_expense_withdrawal_amount",
    "essential_monthly_expenses",
    "emergency_fund_months",
}
EMERGENCY_MONTHS_BY_OPTION_ID = {
    "months_0": 0.0,
    "months_1_3": 2.0,
    "months_4_6": 5.0,
    "months_6_plus": 9.0,
}


def _profile_label(portfolio_config: Mapping[str, Any], profile_band: str) -> str:
    band = portfolio_config["bands"][profile_band]
    return str(band.get("label", profile_band.replace("_", " ").title()))


def _cash_ceiling(portfolio_config: Mapping[str, Any], profile_band: str) -> float:
    band = portfolio_config["bands"][profile_band]
    return float(band.get("max_super_class", {}).get(LIQUIDITY_BUCKET, 1.0))


def _get_answer_field(answer: Any, field_name: str) -> Any:
    if isinstance(answer, Mapping):
        return answer.get(field_name)
    return getattr(answer, field_name, None)


def _answers_by_question(answers: Iterable[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for answer in answers:
        question_id = _get_answer_field(answer, "question_id")
        if isinstance(question_id, str):
            result[question_id] = answer
    return result


def _parse_money_value(raw_value: Any, *, question_id: str) -> float:
    if raw_value is None:
        raise ValueError(f"Missing liquidity answer '{question_id}'.")
    normalized = str(raw_value).strip()
    if normalized.startswith("$"):
        normalized = normalized[1:].strip()
    normalized = normalized.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        raise ValueError(f"Liquidity answer '{question_id}' is not a valid saved money amount.")
    return float(normalized)


def _money_answer(answers_lookup: Mapping[str, Any], question_id: str) -> float:
    answer = answers_lookup.get(question_id)
    normalized_value = _get_answer_field(answer, "normalized_value")
    answer_label = _get_answer_field(answer, "answer_label")
    if answer_label is None:
        answer_label = _get_answer_field(answer, "answer_label_snapshot")
    return _parse_money_value(
        normalized_value if normalized_value is not None else answer_label,
        question_id=question_id,
    )


def _option_answer(answers_lookup: Mapping[str, Any], question_id: str) -> str:
    answer = answers_lookup.get(question_id)
    option_id = _get_answer_field(answer, "option_id")
    if option_id is None:
        option_id = _get_answer_field(answer, "normalized_value")
    if not isinstance(option_id, str) or not option_id.strip():
        raise ValueError(f"Missing liquidity answer '{question_id}'.")
    return option_id


def nearest_liquidity_compatible_profile(
    *,
    selected_profile_band: str,
    liquidity_floor: float,
    portfolio_config: Mapping[str, Any],
) -> str | None:
    """Return the selected or nearest safer profile that can hold the Cash floor."""

    band_order = list(portfolio_config.get("band_order", []))
    if selected_profile_band not in band_order:
        raise ValueError(f"Unknown profile band '{selected_profile_band}'.")

    selected_index = band_order.index(selected_profile_band)
    for candidate in reversed(band_order[: selected_index + 1]):
        if liquidity_floor <= _cash_ceiling(portfolio_config, candidate) + 1e-9:
            return candidate
    return None


def build_liquidity_policy_check(
    *,
    answers: Iterable[Any],
    selected_profile_band: str,
    portfolio_config: Mapping[str, Any],
    user_action: str,
) -> LiquidityPolicyCheckTrace:
    """Build the trace object for one profile/liquidity compatibility check."""

    answers_lookup = _answers_by_question(answers)
    portfolio_value = _money_answer(answers_lookup, "portfolio_value")
    if portfolio_value <= 0:
        raise ValueError("Portfolio value must be greater than zero for the liquidity check.")

    major_expense = _money_answer(answers_lookup, "major_expense_withdrawal_amount")
    monthly_expenses = _money_answer(answers_lookup, "essential_monthly_expenses")
    emergency_option_id = _option_answer(answers_lookup, "emergency_fund_months")
    try:
        emergency_months = EMERGENCY_MONTHS_BY_OPTION_ID[emergency_option_id]
    except KeyError as exc:
        raise ValueError(
            f"Emergency reserve answer '{emergency_option_id}' is not mapped for liquidity policy."
        ) from exc

    required_liquidity = major_expense + (monthly_expenses * emergency_months)
    liquidity_floor = required_liquidity / portfolio_value
    selected_cash_ceiling = _cash_ceiling(portfolio_config, selected_profile_band)
    selected_compatible = liquidity_floor <= selected_cash_ceiling + 1e-9
    effective_band = nearest_liquidity_compatible_profile(
        selected_profile_band=selected_profile_band,
        liquidity_floor=liquidity_floor,
        portfolio_config=portfolio_config,
    )

    return LiquidityPolicyCheckTrace(
        portfolio_value=portfolio_value,
        major_expense_withdrawal_amount=major_expense,
        essential_monthly_expenses=monthly_expenses,
        emergency_fund_option_id=emergency_option_id,
        emergency_months_used=emergency_months,
        required_liquidity_amount=required_liquidity,
        liquidity_floor=liquidity_floor,
        selected_profile_band=selected_profile_band,
        selected_profile_label=_profile_label(portfolio_config, selected_profile_band),
        selected_cash_ceiling=selected_cash_ceiling,
        selected_profile_compatible=selected_compatible,
        effective_profile_band=effective_band,
        effective_profile_label=(
            _profile_label(portfolio_config, effective_band)
            if effective_band is not None
            else None
        ),
        effective_cash_ceiling=(
            _cash_ceiling(portfolio_config, effective_band)
            if effective_band is not None
            else None
        ),
        profile_adjusted=effective_band is not None and effective_band != selected_profile_band,
        user_action=user_action,
    )


def with_liquidity_user_action(
    check: LiquidityPolicyCheckTrace,
    *,
    user_action: str,
) -> LiquidityPolicyCheckTrace:
    """Return a copy of a trace with the final user action recorded."""

    return check.model_copy(update={"user_action": user_action})

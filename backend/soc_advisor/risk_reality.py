"""Risk reality check helpers for the Chainlit advisor flow.

This module turns an already-built recommendation into a simple client-facing
stress illustration. It does not choose a profile, score answers, or change the
portfolio.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import RecommendationSummary, RiskRealityCheckTrace, SessionStateResponse


RISK_REALITY_MULTIPLIER = 2.0


@dataclass(frozen=True)
class RiskRealityEstimate:
    profile_label: str
    annual_volatility: float
    multiplier: float
    stress_percent: float
    portfolio_value: float | None
    stress_amount: float | None


def _format_percent(value: float) -> str:
    return f"{value:.1%}"


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


def _parse_money_label(label: str) -> float | None:
    normalized = label.strip()
    if normalized.startswith("$"):
        normalized = normalized[1:].strip()
    normalized = normalized.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return None
    return float(normalized)


def portfolio_value_from_state(state: SessionStateResponse) -> float | None:
    """Read the saved portfolio value used for display-only dollar estimates."""

    for answer in state.answers:
        if answer.question_id != "portfolio_value":
            continue
        return _parse_money_label(answer.answer_label)
    return None


def build_risk_reality_estimate(
    *,
    state: SessionStateResponse,
    recommendation: RecommendationSummary,
    multiplier: float = RISK_REALITY_MULTIPLIER,
) -> RiskRealityEstimate:
    """Build the simple two-standard-deviation style stress illustration."""

    annual_volatility = recommendation.metrics.volatility
    stress_percent = annual_volatility * multiplier
    portfolio_value = portfolio_value_from_state(state)
    stress_amount = (
        round(portfolio_value * stress_percent, 2)
        if portfolio_value is not None
        else None
    )
    return RiskRealityEstimate(
        profile_label=recommendation.profile_label,
        annual_volatility=annual_volatility,
        multiplier=multiplier,
        stress_percent=stress_percent,
        portfolio_value=portfolio_value,
        stress_amount=stress_amount,
    )


def render_risk_reality_prompt(estimate: RiskRealityEstimate) -> str:
    """Render the pre-report risk check in plain client-facing language."""

    amount_text = (
        f", or about **{_format_money(estimate.stress_amount)}**"
        if estimate.stress_amount is not None
        else ""
    )
    return (
        f"**Risk reality check for {estimate.profile_label}**\n\n"
        f"This profile has an estimated annual volatility of **{_format_percent(estimate.annual_volatility)}**.\n\n"
        f"Under that stress estimate, the portfolio could face a potential loss "
        f"of about **{_format_percent(estimate.stress_percent)}**{amount_text}.\n\n"
        "This is not a prediction and not a formal risk model. It is a simple stress estimate "
        "based on two times the portfolio's estimated annual volatility.\n\n"
        "**Type `yes` to generate the report.**"
    )


def is_continue_input(message_text: str) -> bool:
    """Return whether the user affirmed the informational risk notice."""

    return message_text.strip().casefold() == "yes"


def build_risk_reality_trace(
    estimate: RiskRealityEstimate,
    *,
    user_action: str,
    revised_question_ids: list[str] | None = None,
) -> RiskRealityCheckTrace:
    """Convert the displayed estimate into the persisted audit trace model."""

    return RiskRealityCheckTrace(
        multiplier=estimate.multiplier,
        annual_volatility=estimate.annual_volatility,
        stress_percent=estimate.stress_percent,
        portfolio_value=estimate.portfolio_value,
        stress_amount=estimate.stress_amount,
        user_action=user_action,
        revised_question_ids=list(revised_question_ids or []),
    )

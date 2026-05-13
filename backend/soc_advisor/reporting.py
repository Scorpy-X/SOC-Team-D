"""Static HTML report generation for the advisor prototype.

Reports are generated from already-computed recommendation facts. This module
does not score a user, choose a band, run PyPortfolioOpt, or alter holdings.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .decision_explanations import (
    build_liquidity_explanation_lines,
    build_profile_explanation_lines,
    format_profile_basis_label,
)
from .report_llm import ReportProse, build_report_prose
from .risk_score_display import format_risk_score_10
from .schemas import (
    AnswerSummary,
    DecisionTrace,
    PortfolioHolding,
    ProfileSummary,
    RecommendationSummary,
    SessionStateResponse,
)
from .settings import get_settings


SUPER_CLASS_ORDER = ("Cash", "Fixed Income", "Equity", "Fund")
TEMPLATE_DIR = Path(__file__).resolve().parent / "report_templates"


@dataclass(frozen=True)
class GeneratedReportPaths:
    user_report_path: Path
    audit_report_path: Path


@dataclass(frozen=True)
class ReportContext:
    session_id: str
    generated_at_label: str
    portfolio_value: float | None
    portfolio_value_label: str | None
    profile: ProfileSummary
    recommendation_basis_label: str
    recommendation: RecommendationSummary
    decision_trace: DecisionTrace
    answers: list[AnswerSummary]
    metrics: list[dict[str, Any]]
    sensitivity_metrics: list[dict[str, Any]]
    class_allocations: list[dict[str, Any]]
    currency_allocations: list[dict[str, Any]]
    grouped_holdings: list[dict[str, Any]]
    all_holdings: list[dict[str, Any]]
    largest_holding: dict[str, Any] | None
    top_three_weight_label: str
    top_three_amount_label: str | None
    top_five_weight_label: str
    top_five_amount_label: str | None
    liquidity_policy_check: dict[str, Any] | None
    risk_reality_check: dict[str, Any] | None
    scoring_policy_trace: dict[str, Any] | None
    profile_explanation_lines: list[str]
    liquidity_explanation_lines: list[str]
    user_limitation_notes: list[str]
    prose: ReportProse
    calculation_trail: list[dict[str, Any]]
    trace_rows: list[dict[str, str]]
    trace_json: str


def _format_percent(value: float, *, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def _format_decimal(value: float, *, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}"


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


def _format_data_source(source: str) -> str:
    if source == "live_soc_api":
        return "Live SOC API"
    if source == "csv_snapshot":
        return "Saved CSV snapshot"
    return source.replace("_", " ")


def _format_profile_source(source: str) -> str:
    return format_profile_basis_label(source)


def _format_user_limitation_notes(limitations: list[str]) -> list[str]:
    replacements = {
        "The live Chainlit demo still uses manual mock-band selection as the primary path.": (
            "Advisor review can still adjust the calculated profile during this prototype."
        ),
        "The questionnaire now calculates the draft investor profile, while advisor review can still override it during the demo.": (
            "The questionnaire calculates a proposed investor profile, and advisor review can still adjust it during the prototype."
        ),
        "The questionnaire now calculates the proposed investor profile, while advisor review can still override it during the prototype.": (
            "The questionnaire calculates a proposed investor profile, and advisor review can still adjust it during the prototype."
        ),
        "Questionnaire-to-band scoring is retained as a backend fallback, not as the final approved suitability model.": (
            "The questionnaire scoring path is still a backup method, not the final approved suitability model."
        ),
        "Numeric liquidity inputs are captured and reviewable but do not yet drive profile selection or portfolio construction.": (
            "Money amount answers are saved and shown, but they do not yet change the profile or portfolio mix."
        ),
        "Numeric liquidity inputs are used for the Cash-floor compatibility check, while the full suitability model is still under development.": (
            "The money amount answers are used to check the minimum Cash reserve before the portfolio is built."
        ),
        "Expected returns are model inputs and estimates, not guarantees.": (
            "Expected returns are estimates, not guarantees."
        ),
        "Covariance PSD repair is a numerical stability step applied before optimization, not a change to the investment policy.": (
            "The system checks the input data for numerical stability before building the portfolio; "
            "this does not change the investment policy."
        ),
    }
    return [replacements.get(limitation, limitation) for limitation in limitations]


def _safe_report_folder_name(session_id: str) -> str:
    """Keep report output inside a predictable per-session folder."""

    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", session_id).strip("._") or "session"


def _parse_money_label(label: str) -> float | None:
    """Parse saved display labels like ``$50,000.00`` for report-only math."""

    normalized = label.strip()
    if normalized.startswith("$"):
        normalized = normalized[1:].strip()
    normalized = normalized.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return None
    return float(normalized)


def _extract_portfolio_value(answers: list[AnswerSummary]) -> tuple[float | None, str | None]:
    """Return the saved portfolio value used for display-only dollar estimates."""

    for answer in answers:
        if answer.question_id != "portfolio_value":
            continue
        parsed = _parse_money_label(answer.answer_label)
        if parsed is None:
            return None, None
        return parsed, _format_money(parsed)
    return None, None


def _class_sort_key(label: str) -> tuple[int, str]:
    try:
        return SUPER_CLASS_ORDER.index(label), label
    except ValueError:
        return len(SUPER_CLASS_ORDER), label


def _holding_to_row(
    holding: PortfolioHolding,
    *,
    portfolio_value: float | None,
) -> dict[str, Any]:
    return {
        "asset_code": holding.ticker,
        "ticker": holding.ticker,
        "weight": holding.weight,
        "weight_label": _format_percent(holding.weight),
        "amount_label": (
            _format_money(portfolio_value * holding.weight)
            if portfolio_value is not None
            else None
        ),
        "bar_width": max(holding.weight * 100, 1.0),
        "super_class": holding.super_class,
        "asset_class": holding.asset_class,
        "currency": holding.currency,
        "expected_return_label": _format_percent(holding.expected_return),
        "income_yield_label": _format_percent(holding.income_yield_ann),
        "volatility_label": _format_percent(holding.volatility_ann),
    }


def _build_class_allocations(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for holding in recommendation.holdings:
        totals[holding.super_class] += holding.weight

    return [
        {
            "label": label,
            "weight": weight,
            "weight_label": _format_percent(weight),
            "amount_label": (
                _format_money(portfolio_value * weight)
                if portfolio_value is not None
                else None
            ),
            "bar_width": max(weight * 100, 0.0),
            "slug": re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-"),
        }
        for label, weight in sorted(totals.items(), key=lambda item: _class_sort_key(item[0]))
        if weight > 0
    ]


def _build_currency_allocations(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for holding in recommendation.holdings:
        totals[holding.currency] += holding.weight

    return [
        {
            "label": label,
            "weight": weight,
            "weight_label": _format_percent(weight),
            "amount_label": (
                _format_money(portfolio_value * weight)
                if portfolio_value is not None
                else None
            ),
            "bar_width": max(weight * 100, 0.0),
        }
        for label, weight in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        if weight > 0
    ]


def _build_grouped_holdings(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = [
        _holding_to_row(holding, portfolio_value=portfolio_value)
        for holding in recommendation.holdings
    ]
    rows.sort(key=lambda row: (_class_sort_key(row["super_class"]), -row["weight"], row["ticker"]))

    grouped: list[dict[str, Any]] = []
    for super_class in sorted({row["super_class"] for row in rows}, key=_class_sort_key):
        class_rows = [row for row in rows if row["super_class"] == super_class]
        total_weight = sum(row["weight"] for row in class_rows)
        grouped.append(
            {
                "super_class": super_class,
                "weight": total_weight,
                "weight_label": _format_percent(total_weight),
                "holdings": class_rows,
            }
        )
    return grouped, rows


def _build_metric_rows(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metrics = recommendation.metrics
    headline_metrics = [
        {
            "label": "Expected annual return",
            "value": _format_percent(metrics.expected_return),
            "amount": (
                _format_money(portfolio_value * metrics.expected_return)
                if portfolio_value is not None
                else None
            ),
            "note": "A model estimate of possible yearly growth. This is not guaranteed.",
        },
        {
            "label": "Annual volatility",
            "value": _format_percent(metrics.volatility),
            "amount": (
                _format_money(portfolio_value * metrics.volatility)
                if portfolio_value is not None
                else None
            ),
            "note": "A risk scale estimate for year-to-year portfolio movement, not a worst-case loss.",
        },
        {
            "label": "Income yield",
            "value": _format_percent(metrics.income_yield_ann),
            "amount": (
                _format_money(portfolio_value * metrics.income_yield_ann)
                if portfolio_value is not None
                else None
            ),
            "note": "Estimated interest or dividend income before price changes.",
        },
        {
            "label": "Estimated fund costs",
            "value": _format_percent(metrics.expense_ratio_ann, decimals=2),
            "amount": (
                _format_money(portfolio_value * metrics.expense_ratio_ann)
                if portfolio_value is not None
                else None
            ),
            "note": (
                "Approximate yearly fund fees reflected in the selected assets."
                if metrics.expense_ratio_ann > 0
                else "No meaningful fund fee estimate was found in the selected assets."
            ),
        },
        {
            "label": "Interest-rate exposure",
            "value": _format_decimal(metrics.modified_duration),
            "amount": None,
            "note": "Mainly matters for bond-like holdings; higher values mean more rate sensitivity.",
        },
    ]
    sensitivity_metrics = [
        {
            "label": "Rate beta",
            "value": _format_decimal(metrics.rate_beta),
            "amount": None,
            "note": "Estimated sensitivity to interest-rate moves.",
        },
        {
            "label": "Inflation beta",
            "value": _format_decimal(metrics.inflation_beta),
            "amount": None,
            "note": "Estimated sensitivity to inflation changes.",
        },
        {
            "label": "FX beta",
            "value": _format_decimal(metrics.fx_beta),
            "amount": None,
            "note": "Estimated foreign-exchange sensitivity.",
        },
    ]
    return headline_metrics, sensitivity_metrics


def _format_risk_reality_check(trace: DecisionTrace) -> dict[str, Any] | None:
    risk_check = trace.risk_reality_check
    if risk_check is None:
        return None
    return {
        "method": risk_check.method,
        "multiplier": f"{risk_check.multiplier:.1f}",
        "annual_volatility": _format_percent(risk_check.annual_volatility),
        "stress_percent": _format_percent(risk_check.stress_percent),
        "portfolio_value": (
            _format_money(risk_check.portfolio_value)
            if risk_check.portfolio_value is not None
            else None
        ),
        "stress_amount": (
            _format_money(risk_check.stress_amount)
            if risk_check.stress_amount is not None
            else None
        ),
        "user_action": risk_check.user_action,
        "revised_question_ids": risk_check.revised_question_ids,
    }


def _format_liquidity_policy_check(trace: DecisionTrace) -> dict[str, Any] | None:
    liquidity_check = trace.liquidity_policy_check
    if liquidity_check is None:
        return None
    return {
        "method": liquidity_check.method,
        "liquidity_bucket": liquidity_check.liquidity_bucket,
        "portfolio_value": _format_money(liquidity_check.portfolio_value),
        "major_expense_withdrawal_amount": _format_money(
            liquidity_check.major_expense_withdrawal_amount
        ),
        "essential_monthly_expenses": _format_money(
            liquidity_check.essential_monthly_expenses
        ),
        "emergency_fund_option_id": liquidity_check.emergency_fund_option_id,
        "emergency_months_used": _format_decimal(
            liquidity_check.emergency_months_used,
            decimals=1,
        ),
        "required_liquidity_amount": _format_money(
            liquidity_check.required_liquidity_amount
        ),
        "liquidity_floor": _format_percent(liquidity_check.liquidity_floor),
        "selected_profile": (
            f"{liquidity_check.selected_profile_label} "
            f"({liquidity_check.selected_profile_band})"
        ),
        "selected_cash_ceiling": _format_percent(
            liquidity_check.selected_cash_ceiling
        ),
        "selected_profile_compatible": (
            "Yes" if liquidity_check.selected_profile_compatible else "No"
        ),
        "effective_profile": (
            f"{liquidity_check.effective_profile_label} "
            f"({liquidity_check.effective_profile_band})"
            if liquidity_check.effective_profile_band is not None
            else "No compatible profile"
        ),
        "effective_cash_ceiling": (
            _format_percent(liquidity_check.effective_cash_ceiling)
            if liquidity_check.effective_cash_ceiling is not None
            else "N/A"
        ),
        "profile_adjusted": "Yes" if liquidity_check.profile_adjusted else "No",
        "user_action": liquidity_check.user_action,
    }


def _format_scoring_policy_trace(trace: DecisionTrace) -> dict[str, Any] | None:
    scoring_trace = trace.scoring_policy_trace
    if scoring_trace is None:
        return None
    return {
        "method": scoring_trace.method,
        "capacity_score": (
            _format_percent(scoring_trace.capacity_score)
            if scoring_trace.capacity_score is not None
            else "N/A"
        ),
        "tolerance_score": (
            _format_percent(scoring_trace.tolerance_score)
            if scoring_trace.tolerance_score is not None
            else "N/A"
        ),
        "final_score_before_caps": _format_percent(
            scoring_trace.final_score_before_caps
        ),
        "final_score_after_caps": _format_percent(
            scoring_trace.final_score_after_caps
        ),
        "displayed_risk_score": format_risk_score_10(
            scoring_trace.final_score_after_caps
        ),
        "displayed_investor_type": scoring_trace.final_profile_label,
        "draft_profile": (
            f"{scoring_trace.draft_profile_label} "
            f"({scoring_trace.draft_profile_band})"
        ),
        "final_profile": (
            f"{scoring_trace.final_profile_label} "
            f"({scoring_trace.final_profile_band})"
        ),
        "applied_caps": scoring_trace.applied_caps,
        "manual_override_used": "Yes" if scoring_trace.manual_override_used else "No",
        "manual_override": (
            f"{scoring_trace.manual_override_label} "
            f"({scoring_trace.manual_override_band})"
            if scoring_trace.manual_override_band is not None
            else "None"
        ),
        "section_scores": {
            label: _format_percent(value)
            for label, value in scoring_trace.section_scores.items()
        },
        "question_scores": {
            label: _format_percent(value)
            for label, value in scoring_trace.question_scores.items()
        },
    }


def _build_trace_rows(trace: DecisionTrace, prose: ReportProse) -> list[dict[str, str]]:
    rows = [
        {"label": "Questionnaire", "value": trace.questionnaire_version},
        {"label": "Scoring policy", "value": trace.scoring_version},
        {"label": "Portfolio policy", "value": trace.portfolio_version},
        {"label": "Profile source", "value": trace.profile_source},
        {"label": "Final profile", "value": f"{trace.profile_label} ({trace.profile_band})"},
        {"label": "Data source", "value": _format_data_source(trace.data_source)},
        {"label": "Optimizer objective", "value": trace.optimizer_objective},
        {"label": "Risk-free rate", "value": _format_percent(trace.risk_free_rate)},
        {
            "label": "Weight bounds",
            "value": (
                f"{_format_percent(trace.weight_bounds[0])} to "
                f"{_format_percent(trace.weight_bounds[1])}"
            ),
        },
        {"label": "Single asset cap", "value": _format_percent(trace.single_asset_cap)},
        {
            "label": "Covariance PSD repair",
            "value": "Enabled" if trace.covariance_psd_repair_enabled else "Disabled",
        },
        {
            "label": "Applied overlays",
            "value": "; ".join(trace.applied_overlays) if trace.applied_overlays else "None",
        },
        {"label": "Report prose", "value": prose.status},
    ]
    if trace.scoring_policy_trace is not None:
        rows.extend(
            [
                {
                    "label": "Scoring method",
                    "value": trace.scoring_policy_trace.method,
                },
                {
                    "label": "Capacity score",
                    "value": (
                        _format_percent(trace.scoring_policy_trace.capacity_score)
                        if trace.scoring_policy_trace.capacity_score is not None
                        else "N/A"
                    ),
                },
                {
                    "label": "Tolerance score",
                    "value": (
                        _format_percent(trace.scoring_policy_trace.tolerance_score)
                        if trace.scoring_policy_trace.tolerance_score is not None
                        else "N/A"
                    ),
                },
                {
                    "label": "Score before caps",
                    "value": _format_percent(
                        trace.scoring_policy_trace.final_score_before_caps
                    ),
                },
                {
                    "label": "Score after caps",
                    "value": _format_percent(
                        trace.scoring_policy_trace.final_score_after_caps
                    ),
                },
                {
                    "label": "Displayed risk score",
                    "value": format_risk_score_10(
                        trace.scoring_policy_trace.final_score_after_caps
                    ),
                },
                {
                    "label": "Scoring cap applied",
                    "value": (
                        "; ".join(trace.scoring_policy_trace.applied_caps)
                        if trace.scoring_policy_trace.applied_caps
                        else "None"
                    ),
                },
            ]
        )
    if trace.liquidity_policy_check is not None:
        rows.extend(
            [
                {
                    "label": "Liquidity required",
                    "value": _format_money(
                        trace.liquidity_policy_check.required_liquidity_amount
                    ),
                },
                {
                    "label": "Liquidity floor",
                    "value": _format_percent(
                        trace.liquidity_policy_check.liquidity_floor
                    ),
                },
                {
                    "label": "Liquidity profile action",
                    "value": trace.liquidity_policy_check.user_action,
                },
            ]
        )
    if trace.risk_reality_check is not None:
        rows.extend(
            [
                {
                    "label": "Risk reality method",
                    "value": trace.risk_reality_check.method,
                },
                {
                    "label": "Risk reality multiplier",
                    "value": f"{trace.risk_reality_check.multiplier:.1f}",
                },
                {
                    "label": "Risk reality user action",
                    "value": trace.risk_reality_check.user_action,
                },
            ]
        )
    return rows


def _build_calculation_trail(
    trace: DecisionTrace,
    recommendation: RecommendationSummary,
) -> list[dict[str, Any]]:
    """Build audit-only formula cards in the order the advisor applies them."""

    cards: list[dict[str, Any]] = []
    liquidity = trace.liquidity_policy_check
    if liquidity is not None:
        cards.append(
            {
                "title": "1. Liquidity need",
                "formula": "required liquidity = major expense withdrawal + monthly expenses × emergency months",
                "values": (
                    f"{_format_money(liquidity.major_expense_withdrawal_amount)} + "
                    f"{_format_money(liquidity.essential_monthly_expenses)} × "
                    f"{_format_decimal(liquidity.emergency_months_used, decimals=1)} = "
                    f"{_format_money(liquidity.required_liquidity_amount)}"
                ),
                "result": f"Required liquidity: {_format_money(liquidity.required_liquidity_amount)}",
            }
        )
        cards.append(
            {
                "title": "2. Liquidity floor",
                "formula": "liquidity floor = required liquidity / portfolio value",
                "values": (
                    f"{_format_money(liquidity.required_liquidity_amount)} / "
                    f"{_format_money(liquidity.portfolio_value)} = "
                    f"{_format_percent(liquidity.liquidity_floor)}"
                ),
                "result": f"Minimum Cash need: {_format_percent(liquidity.liquidity_floor)}",
            }
        )

    scoring = trace.scoring_policy_trace
    if scoring is not None:
        cards.append(
            {
                "title": "3. Risk capacity score",
                "formula": "capacity score = weighted average of Q5-Q9",
                "values": "Question weights and normalized answer scores are shown in the scoring policy table below.",
                "result": (
                    _format_percent(scoring.capacity_score)
                    if scoring.capacity_score is not None
                    else "N/A"
                ),
            }
        )
        cards.append(
            {
                "title": "4. Risk tolerance score",
                "formula": "tolerance score = weighted average of Q10-Q14",
                "values": "Question weights and normalized answer scores are shown in the scoring policy table below.",
                "result": (
                    _format_percent(scoring.tolerance_score)
                    if scoring.tolerance_score is not None
                    else "N/A"
                ),
            }
        )
        cards.append(
            {
                "title": "5. Final questionnaire score",
                "formula": "final score = 60% × capacity score + 40% × tolerance score",
                "values": (
                    f"60% × {_format_percent(scoring.capacity_score) if scoring.capacity_score is not None else 'N/A'} + "
                    f"40% × {_format_percent(scoring.tolerance_score) if scoring.tolerance_score is not None else 'N/A'} = "
                    f"{_format_percent(scoring.final_score_before_caps)}"
                ),
                "result": f"Draft profile: {scoring.draft_profile_label}",
            }
        )
        cap_result = (
            "; ".join(scoring.applied_caps)
            if scoring.applied_caps
            else "No scoring cap applied."
        )
        cards.append(
            {
                "title": "6. Profile bucket and cap rule",
                "formula": "score range maps to investor profile; if Q10 = sell everything, max profile = Balanced",
                "values": (
                    "0.00-0.20 Very Conservative; 0.20-0.40 Conservative; "
                    "0.40-0.60 Balanced; 0.60-0.80 Growth; 0.80-1.00 Aggressive"
                ),
                "result": (
                    f"Final scoring profile: {scoring.final_profile_label}; "
                    f"displayed risk score {format_risk_score_10(scoring.final_score_after_caps)}. "
                    f"{cap_result}"
                ),
            }
        )

    if liquidity is not None:
        compatibility = (
            "selected profile compatible"
            if liquidity.selected_profile_compatible
            else f"adjusted to {liquidity.effective_profile_label or 'no compatible profile'}"
        )
        cards.append(
            {
                "title": "7. Liquidity compatibility",
                "formula": "if liquidity floor > selected profile Cash max, use nearest safer compatible profile",
                "values": (
                    f"{_format_percent(liquidity.liquidity_floor)} compared with selected Cash ceiling "
                    f"{_format_percent(liquidity.selected_cash_ceiling)}"
                ),
                "result": compatibility,
            }
        )
        cards.append(
            {
                "title": "8. Cash floor overlay",
                "formula": "effective Cash minimum = max(configured Cash minimum, liquidity floor)",
                "values": (
                    f"Configured minima: {', '.join(f'{key} {_format_percent(value)}' for key, value in trace.super_class_minima.items())}; "
                    f"liquidity floor {_format_percent(liquidity.liquidity_floor)}"
                ),
                "result": (
                    "; ".join(trace.applied_overlays)
                    if trace.applied_overlays
                    else "No overlay applied."
                ),
            }
        )

    cards.append(
        {
            "title": "9. Optimizer objective",
            "formula": "maximize Sharpe ratio",
            "values": (
                f"objective={trace.optimizer_objective}; "
                f"risk-free rate={_format_percent(trace.risk_free_rate)}"
            ),
            "result": "PyPortfolioOpt solves inside the approved constraints.",
        }
    )
    cards.append(
        {
            "title": "10. Optimizer inputs",
            "formula": "mu = expected returns; S = covariance matrix",
            "values": (
                f"{len(recommendation.holdings)} selected nonzero holdings; "
                f"data source={_format_data_source(trace.data_source)}; "
                f"PSD repair={'enabled' if trace.covariance_psd_repair_enabled else 'disabled'}"
            ),
            "result": "Inputs are aligned to the asset universe before solving.",
        }
    )
    cards.append(
        {
            "title": "11. Optimizer constraints",
            "formula": "sum(weights) = 100%; weight bounds apply; superclass minima/maxima apply",
            "values": (
                f"weight bounds {_format_percent(trace.weight_bounds[0])} to {_format_percent(trace.weight_bounds[1])}; "
                f"single asset weight ≤ {_format_percent(trace.single_asset_cap)}"
            ),
            "result": (
                "Superclass ranges: "
                + ", ".join(
                    f"{label} {_format_percent(trace.super_class_minima.get(label, 0.0))}-"
                    f"{_format_percent(trace.super_class_maxima.get(label, 1.0))}"
                    for label in SUPER_CLASS_ORDER
                    if label in trace.super_class_minima or label in trace.super_class_maxima
                )
            ),
        }
    )

    risk = trace.risk_reality_check
    if risk is not None:
        cards.append(
            {
                "title": "12. Risk reality check",
                "formula": "stress estimate = 2 × annual volatility; potential loss = portfolio value × stress estimate",
                "values": (
                    f"2 × {_format_percent(risk.annual_volatility)} = {_format_percent(risk.stress_percent)}"
                    + (
                        f"; {_format_money(risk.portfolio_value)} × {_format_percent(risk.stress_percent)} = {_format_money(risk.stress_amount)}"
                        if risk.portfolio_value is not None and risk.stress_amount is not None
                        else ""
                    )
                ),
                "result": "Shown before report generation as a simplified stress estimate, not a guarantee.",
            }
        )

    return cards


def build_report_facts(
    *,
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    decision_trace: DecisionTrace,
) -> dict[str, Any]:
    """Build the structured fact payload used by both reports and optional LLM prose."""

    portfolio_value, portfolio_value_label = _extract_portfolio_value(list(state.answers))
    class_allocations = _build_class_allocations(
        recommendation,
        portfolio_value=portfolio_value,
    )
    currency_allocations = _build_currency_allocations(
        recommendation,
        portfolio_value=portfolio_value,
    )
    _, all_holdings = _build_grouped_holdings(
        recommendation,
        portfolio_value=portfolio_value,
    )
    sorted_holdings = sorted(all_holdings, key=lambda row: row["weight"], reverse=True)
    largest_holding = sorted_holdings[0] if sorted_holdings else None

    return {
        "session_id": state.session_id,
        "portfolio_value": portfolio_value_label,
        "profile": {
            "profile_band": profile.profile_band,
            "profile_label": profile.profile_label,
            "profile_source_label": _format_profile_source(profile.profile_source),
            "profile_description": profile.profile_description,
        },
        "metrics": {
            "expected_return": _format_percent(recommendation.metrics.expected_return),
            "volatility": _format_percent(recommendation.metrics.volatility),
            "income_yield": _format_percent(recommendation.metrics.income_yield_ann),
            "expense_ratio": _format_percent(
                recommendation.metrics.expense_ratio_ann,
                decimals=2,
            ),
            "modified_duration": _format_decimal(
                recommendation.metrics.modified_duration
            ),
        },
        "class_allocations": class_allocations,
        "currency_allocations": currency_allocations,
        "largest_holding": largest_holding,
        "top_three_weight": _format_percent(
            sum(row["weight"] for row in sorted_holdings[:3])
        ),
        "top_three_amount": (
            _format_money(portfolio_value * sum(row["weight"] for row in sorted_holdings[:3]))
            if portfolio_value is not None
            else None
        ),
        "top_five_weight": _format_percent(
            sum(row["weight"] for row in sorted_holdings[:5])
        ),
        "top_five_amount": (
            _format_money(portfolio_value * sum(row["weight"] for row in sorted_holdings[:5]))
            if portfolio_value is not None
            else None
        ),
        "data_source": _format_data_source(decision_trace.data_source),
        "limitations": decision_trace.limitations,
        "liquidity_policy_check": _format_liquidity_policy_check(decision_trace),
        "risk_reality_check": _format_risk_reality_check(decision_trace),
        "scoring_policy_trace": _format_scoring_policy_trace(decision_trace),
    }


def build_report_context(
    *,
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    decision_trace: DecisionTrace,
) -> ReportContext:
    """Build one immutable context object for both user and audit reports."""

    portfolio_value, portfolio_value_label = _extract_portfolio_value(list(state.answers))
    class_allocations = _build_class_allocations(
        recommendation,
        portfolio_value=portfolio_value,
    )
    currency_allocations = _build_currency_allocations(
        recommendation,
        portfolio_value=portfolio_value,
    )
    grouped_holdings, all_holdings = _build_grouped_holdings(
        recommendation,
        portfolio_value=portfolio_value,
    )
    metrics, sensitivity_metrics = _build_metric_rows(
        recommendation,
        portfolio_value=portfolio_value,
    )
    sorted_holdings = sorted(all_holdings, key=lambda row: row["weight"], reverse=True)
    largest_holding = sorted_holdings[0] if sorted_holdings else None
    facts = build_report_facts(
        state=state,
        profile=profile,
        recommendation=recommendation,
        decision_trace=decision_trace,
    )
    prose = build_report_prose(facts)

    return ReportContext(
        session_id=state.session_id,
        generated_at_label=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        portfolio_value=portfolio_value,
        portfolio_value_label=portfolio_value_label,
        profile=profile,
        recommendation_basis_label=_format_profile_source(profile.profile_source),
        recommendation=recommendation,
        decision_trace=decision_trace,
        answers=list(state.answers),
        metrics=metrics,
        sensitivity_metrics=sensitivity_metrics,
        class_allocations=class_allocations,
        currency_allocations=currency_allocations,
        grouped_holdings=grouped_holdings,
        all_holdings=all_holdings,
        largest_holding=largest_holding,
        top_three_weight_label=_format_percent(
            sum(row["weight"] for row in sorted_holdings[:3])
        ),
        top_three_amount_label=(
            _format_money(portfolio_value * sum(row["weight"] for row in sorted_holdings[:3]))
            if portfolio_value is not None
            else None
        ),
        top_five_weight_label=_format_percent(
            sum(row["weight"] for row in sorted_holdings[:5])
        ),
        top_five_amount_label=(
            _format_money(portfolio_value * sum(row["weight"] for row in sorted_holdings[:5]))
            if portfolio_value is not None
            else None
        ),
        liquidity_policy_check=_format_liquidity_policy_check(decision_trace),
        risk_reality_check=_format_risk_reality_check(decision_trace),
        scoring_policy_trace=_format_scoring_policy_trace(decision_trace),
        profile_explanation_lines=build_profile_explanation_lines(
            decision_trace,
            profile=profile,
        ),
        liquidity_explanation_lines=build_liquidity_explanation_lines(
            decision_trace,
        ),
        user_limitation_notes=_format_user_limitation_notes(decision_trace.limitations),
        prose=prose,
        calculation_trail=_build_calculation_trail(decision_trace, recommendation),
        trace_rows=_build_trace_rows(decision_trace, prose),
        trace_json=json.dumps(decision_trace.model_dump(), indent=2),
    )


def _render_template(template_name: str, context: ReportContext) -> str:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml", "j2")),
    )
    template = environment.get_template(template_name)
    return template.render(report=context)


def generate_portfolio_reports(
    *,
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    decision_trace: DecisionTrace,
) -> GeneratedReportPaths:
    """Write the user and audit HTML reports for one submitted session."""

    settings = get_settings()
    report_dir = settings.advisor_reports_dir / _safe_report_folder_name(state.session_id)
    report_dir.mkdir(parents=True, exist_ok=True)

    context = build_report_context(
        state=state,
        profile=profile,
        recommendation=recommendation,
        decision_trace=decision_trace,
    )

    user_report_path = report_dir / "portfolio-report.html"
    audit_report_path = report_dir / "portfolio-audit-report.html"
    user_report_path.write_text(
        _render_template("user_report.html.j2", context),
        encoding="utf-8",
    )
    audit_report_path.write_text(
        _render_template("audit_report.html.j2", context),
        encoding="utf-8",
    )
    return GeneratedReportPaths(
        user_report_path=user_report_path,
        audit_report_path=audit_report_path,
    )

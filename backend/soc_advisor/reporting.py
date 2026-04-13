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

from .report_llm import ReportProse, build_report_prose
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
    user_limitation_notes: list[str]
    prose: ReportProse
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
    if source == "manual_mock_band":
        return "Draft profile selected during the demo"
    if source == "scored_questionnaire":
        return "Profile estimated from questionnaire answers"
    return source.replace("_", " ").capitalize()


def _format_user_limitation_notes(limitations: list[str]) -> list[str]:
    replacements = {
        "The live Chainlit demo still uses manual mock-band selection as the primary path.": (
            "The investor profile is selected during the demo; the team has not finalized "
            "the approved profile-scoring model."
        ),
        "Questionnaire-to-band scoring is retained as a backend fallback, not as the final approved suitability model.": (
            "The questionnaire scoring path is still a backup method, not the final approved suitability model."
        ),
        "Numeric liquidity inputs are captured and reviewable but do not yet drive profile selection or portfolio construction.": (
            "Money amount answers are saved and shown, but they do not yet change the profile or portfolio mix."
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
            "label": "Estimated yearly return",
            "value": _format_percent(metrics.expected_return),
            "amount": (
                _format_money(portfolio_value * metrics.expected_return)
                if portfolio_value is not None
                else None
            ),
            "note": "A model estimate of possible yearly growth. This is not guaranteed.",
        },
        {
            "label": "Expected yearly movement",
            "value": _format_percent(metrics.volatility),
            "amount": (
                _format_money(portfolio_value * metrics.volatility)
                if portfolio_value is not None
                else None
            ),
            "note": "A rough guide to year-to-year ups and downs, not a worst-case loss.",
        },
        {
            "label": "Estimated income",
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


def _build_trace_rows(trace: DecisionTrace, prose: ReportProse) -> list[dict[str, str]]:
    return [
        {"label": "Questionnaire", "value": trace.questionnaire_version},
        {"label": "Scoring fallback", "value": trace.scoring_version},
        {"label": "Portfolio policy", "value": trace.portfolio_version},
        {"label": "Profile source", "value": trace.profile_source},
        {"label": "Selected band", "value": f"{trace.profile_label} ({trace.profile_band})"},
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
        {"label": "Report prose", "value": prose.status},
    ]


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
        user_limitation_notes=_format_user_limitation_notes(decision_trace.limitations),
        prose=prose,
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

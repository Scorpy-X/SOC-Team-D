"""Pure formatting helpers for the Chainlit experiment copy.

This module has one job: turn already-computed state into readable text.

Keeping this separate from the chat controller makes the flow easier to read:

- `chat_app.py` decides *when* to show something
- this file decides *how* the text should look
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .decision_explanations import build_concise_profile_reason
from .risk_score_display import format_risk_score_10
from .schemas import (
    DecisionTrace,
    ProfileSummary,
    RecommendationSummary,
    SessionStateResponse,
)


DISPLAY_SUPER_CLASS_ORDER = ("Cash", "Fixed Income", "Equity", "Fund")


#
# Small reusable text helpers
#


def get_question_label(
    question_id: str,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
) -> str:
    """Return a short label for one question."""

    return question_labels.get(question_id, questions_by_id[question_id]["text"])


def _format_percentage(value: float) -> str:
    return f"{value:.0%}"


def format_percentage_precise(value: float) -> str:
    return f"{value:.1%}"


def format_money(value: float) -> str:
    return f"${value:,.2f}"


def format_profile_score(value: float | None) -> str:
    """Render legacy point totals and normalized risk scores clearly."""

    if value is None:
        return "score not used for this run"
    if 0.0 <= value <= 1.0:
        return f"Risk score {format_risk_score_10(value)}"
    return f"Score {value:.1f}"


def _parse_money_label(label: str) -> float | None:
    """Parse saved display labels like ``$50,000.00`` for chat-only summaries."""

    normalized = label.strip()
    if normalized.startswith("$"):
        normalized = normalized[1:].strip()
    normalized = normalized.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return None
    return float(normalized)


def portfolio_value_from_answers(state: SessionStateResponse) -> float | None:
    """Find the saved portfolio value for report cards and HTML reports."""

    for answer in state.answers:
        if answer.question_id != "portfolio_value":
            continue
        return _parse_money_label(answer.answer_label)
    return None


def _currency_help_text(question: dict[str, Any]) -> str:
    """Build the short input-format guidance for currency questions."""

    help_text = str(question.get("help_text") or "").strip()
    example = (question.get("validation") or {}).get("example")
    if help_text and example and example in help_text:
        return help_text
    if example:
        return (
            f"{help_text}\n\n" if help_text else ""
        ) + f"Enter a dollar amount such as `{example}`. Dollar signs and commas are okay."
    if help_text:
        return (
            f"{help_text}\n\n"
            "Enter a dollar amount. Dollar signs and commas are okay."
        )
    return "Enter a dollar amount. Dollar signs and commas are okay."


def build_answer_summary_lines(
    state: SessionStateResponse,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
    numbered: bool,
    use_full_question_text: bool,
) -> list[str]:
    """Return numbered or bulleted answer summary lines."""

    lines: list[str] = []
    for index, answer in enumerate(state.answers, start=1):
        label = (
            answer.question_text
            if use_full_question_text
            else get_question_label(
                answer.question_id,
                questions_by_id=questions_by_id,
                question_labels=question_labels,
            )
        )
        prefix = f"{index}. " if numbered else "- "
        lines.append(f"{prefix}**{label}:** {answer.answer_label}")
    return lines


def format_super_class_ranges(
    minima: dict[str, float],
    maxima: dict[str, float],
) -> list[str]:
    """Render the active class ranges in a human-readable order."""

    lines: list[str] = []
    for super_class in DISPLAY_SUPER_CLASS_ORDER:
        lower = float(minima.get(super_class, 0.0))
        upper = float(maxima.get(super_class, 1.0))
        if super_class == "Fund" and lower == 0.0 and upper == 0.0:
            continue
        if lower == 0.0 and upper == 1.0:
            continue
        lines.append(
            f"**{super_class}:** {_format_percentage(lower)}-{_format_percentage(upper)}"
        )
    return lines


def format_band_choice_lines(profile_bands: list[dict[str, Any]]) -> list[str]:
    """Render the numbered mock-band choices for review mode."""

    lines: list[str] = []
    for choice in profile_bands:
        range_text = ", ".join(
            format_super_class_ranges(
                choice["super_class_minima"],
                choice["super_class_maxima"],
            )
        )
        lines.append(
            f"{choice['order']}. **{choice['label']}**"
            + (f" - {range_text}" if range_text else "")
        )
    return lines


def format_super_class_mix_from_holdings(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None = None,
) -> list[str]:
    """Render the final superclass mix without listing every holding in chat."""

    totals: dict[str, float] = {}
    for holding in recommendation.holdings:
        totals[holding.super_class] = totals.get(holding.super_class, 0.0) + holding.weight

    lines: list[str] = []
    ordered_labels = list(DISPLAY_SUPER_CLASS_ORDER) + sorted(
        label for label in totals if label not in DISPLAY_SUPER_CLASS_ORDER
    )
    for label in ordered_labels:
        weight = totals.get(label, 0.0)
        if weight <= 0:
            continue
        amount_text = (
            f" / about {format_money(portfolio_value * weight)}"
            if portfolio_value is not None
            else ""
        )
        lines.append(f"- **{label}:** {_format_percentage(weight)}{amount_text}")
    return lines


def format_compact_holding_lines(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None = None,
) -> list[str]:
    """Render selected investments in a compact, user-facing grouped format."""

    grouped: dict[str, list[tuple[str, str, float, str]]] = {}
    for holding in recommendation.holdings:
        if holding.weight <= 0:
            continue
        amount_text = (
            f" / about {format_money(portfolio_value * holding.weight)}"
            if portfolio_value is not None
            else ""
        )
        primary_line = (
            f"- **{holding.ticker}** - "
            f"{format_percentage_precise(holding.weight)}{amount_text}"
        )
        detail_line = f"  {holding.super_class} | {holding.asset_class} | {holding.currency}"
        grouped.setdefault(holding.super_class, []).append(
            (primary_line, detail_line, holding.weight, holding.ticker)
        )

    if not grouped:
        return []

    lines: list[str] = []
    ordered_labels = sorted(
        grouped,
        key=lambda label: (
            -sum(item[2] for item in grouped[label]),
            label,
        ),
    )
    for label in ordered_labels:
        holdings = grouped.get(label)
        if not holdings:
            continue
        if lines:
            lines.append("")
        lines.append(f"**{label}**")
        for primary_line, detail_line, _weight, _ticker in sorted(
            holdings,
            key=lambda item: (-item[2], item[3]),
        ):
            lines.append(primary_line)
            lines.append(detail_line)
    return lines


def format_metric_snapshot_lines(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> list[str]:
    """Return a compact metrics block for the final chat response."""

    metrics = recommendation.metrics
    rows = [
        ("Expected annual return", metrics.expected_return),
        ("Annual volatility", metrics.volatility),
        ("Income yield", metrics.income_yield_ann),
    ]
    lines: list[str] = []
    for label, value in rows:
        amount_text = (
            f" / about {format_money(portfolio_value * value)}"
            if portfolio_value is not None
            else ""
        )
        lines.append(f"- **{label}:** {format_percentage_precise(value)}{amount_text}")
    lines.append("- **Note:** volatility is a risk scale estimate, not a maximum loss.")
    return lines


#
# Major rendered blocks used by the chat controller
#


def format_question(
    question: dict[str, Any],
    *,
    total_questions: int,
    question_label: str,
) -> str:
    """Format one questionnaire prompt for the chat window."""

    if question.get("type") == "currency_amount":
        return (
            f"**Question {question['order']} of {total_questions} - {question_label}**\n\n"
            f"{question['text']}"
            f"\n\n{_currency_help_text(question)}"
        )

    option_lines = [
        f"{index}. {option['label']}"
        for index, option in enumerate(question["options"], start=1)
    ]
    help_text = f"\n\n{question['help_text']}" if question.get("help_text") else ""
    return (
        f"**Question {question['order']} of {total_questions} - {question_label}**\n\n"
        f"{question['text']}"
        f"{help_text}\n\n"
        "Reply with the answer number or type the answer in full.\n\n"
        + "\n".join(option_lines)
    )


def format_edit_prompt(
    question: dict[str, Any],
    *,
    total_questions: int,
    question_label: str,
    current_label: str,
) -> str:
    """Format the prompt used when the user edits an existing answer."""

    if question.get("type") == "currency_amount":
        return (
            f"**Update question {question['order']} of {total_questions} - {question_label}**\n\n"
            "Let's revise this amount.\n\n"
            f"Currently recorded: **{current_label}**\n\n"
            f"{question['text']}\n\n"
            f"{_currency_help_text(question)}"
        )

    return (
        f"**Update question {question['order']} of {total_questions} - {question_label}**\n\n"
        "Let's revise this answer.\n\n"
        f"Currently recorded: **{current_label}**\n\n"
        f"{question['text']}\n\n"
        "Reply with the new answer number or type the answer in full.\n\n"
        + "\n".join(
            f"{index}. {option['label']}"
            for index, option in enumerate(question["options"], start=1)
        )
    )


def render_review_message(
    state: SessionStateResponse,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
    profile_bands: list[dict[str, Any]],
    selected_band_id: str | None,
) -> str:
    """Build the review message shown before final confirmation."""

    answer_lines = build_answer_summary_lines(
        state,
        questions_by_id=questions_by_id,
        question_labels=question_labels,
        numbered=True,
        use_full_question_text=False,
    )
    band_lines = format_band_choice_lines(profile_bands)
    selected_band = next(
        (choice for choice in profile_bands if choice["id"] == selected_band_id),
        None,
    )
    if selected_band is None:
        selected_band_line = (
            "**Selected profile:** Calculated from questionnaire unless you choose an override below."
        )
    else:
        selected_band_line = (
            f"**Selected profile:** {selected_band['order']}. {selected_band['label']}"
        )

    return (
        "**Review your answers**\n\n"
        "Here is what I have recorded:\n\n"
        + "\n".join(answer_lines)
        + "\n\n**Calculated profile and optional advisor override**\n"
        + "\n".join(band_lines)
        + "\n\n"
        + selected_band_line
        + "\n\n**If you prefer typing**\n"
        + "- `change <question number>`\n"
        + "- `band <band number>` to override the calculated profile\n"
        + "- `yes` to continue to the risk check"
    )


def render_profile_summary(
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    *,
    user_report_path: Path | None = None,
    decision_trace: DecisionTrace | None = None,
) -> str:
    """Build the final chat summary after submission.

    The chat gives a compact snapshot. The detailed explanations and audit
    trace stay in the generated HTML report.
    """

    risk_score_line = (
        f"- **Risk score:** {format_risk_score_10(profile.profile_score)}"
        if profile.profile_score is not None and 0.0 <= profile.profile_score <= 1.0
        else ""
    )
    mix_lines = format_super_class_mix_from_holdings(recommendation)
    holding_lines = format_compact_holding_lines(recommendation, portfolio_value=None)
    metric_lines = format_metric_snapshot_lines(
        recommendation,
        portfolio_value=None,
    )
    key_metric_lines = [f"- **Investor type:** {profile.profile_label}"]
    if risk_score_line:
        key_metric_lines.append(risk_score_line)
    key_metric_lines.extend(metric_lines)
    reason_lines = build_concise_profile_reason(
        decision_trace,
        profile=profile,
    )
    report_line = (
        "\n\nI attached the detailed portfolio report below. Open it for dollar allocations, full holdings, and the explanation notes."
        if user_report_path is not None
        else ""
    )
    profile_path_caveat = (
        "- This result uses the profile selected during review."
        if profile.profile_source == "manual_mock_band"
        else "- This result uses a profile adjusted after the liquidity check."
        if profile.profile_source in {
            "liquidity_adjusted_questionnaire",
            "liquidity_adjusted_manual_profile",
        }
        else "- This result uses the profile calculated from the questionnaire."
    )
    caveat_lines = [
        profile_path_caveat,
        "- Dollar allocation details are kept in the HTML report so the chat stays readable.",
        "- Expected returns are estimates, not guarantees.",
    ]

    sections = [
        f"**Portfolio generated: {profile.profile_label}**",
        "**Key metrics**\n" + "\n".join(key_metric_lines),
        "**Why this profile?**\n" + "\n".join(f"- {line}" for line in reason_lines),
    ]
    if report_line:
        sections.append(report_line.strip())
    sections.append("**Portfolio mix**\n" + "\n".join(mix_lines))
    if holding_lines:
        sections.append(
            "**Investments selected**\n"
            "Asset codes are short market identifiers for each investment.\n\n"
            + "\n".join(holding_lines)
        )
    sections.extend(
        [
            "**Important caveats**\n" + "\n".join(caveat_lines),
            "Type `/restart` to run the questionnaire again.",
        ]
    )
    return "\n\n".join(sections)

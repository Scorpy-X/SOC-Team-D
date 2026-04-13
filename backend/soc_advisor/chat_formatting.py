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

from .schemas import ProfileSummary, RecommendationSummary, SessionStateResponse


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


def _format_percentage_precise(value: float) -> str:
    return f"{value:.1%}"


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


def _parse_money_label(label: str) -> float | None:
    """Parse saved display labels like ``$50,000.00`` for chat-only summaries."""

    normalized = label.strip()
    if normalized.startswith("$"):
        normalized = normalized[1:].strip()
    normalized = normalized.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return None
    return float(normalized)


def _portfolio_value_from_answers(state: SessionStateResponse) -> float | None:
    """Find the saved portfolio value so the final chat can show estimates."""

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
            f" / about {_format_money(portfolio_value * weight)}"
            if portfolio_value is not None
            else ""
        )
        lines.append(f"- **{label}:** {_format_percentage(weight)}{amount_text}")
    return lines


def format_metric_snapshot_lines(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> list[str]:
    """Return a compact metrics block for the final chat response."""

    metrics = recommendation.metrics
    rows = [
        ("Estimated annual return", metrics.expected_return),
        ("Annual volatility equivalent", metrics.volatility),
        ("Estimated annual income yield", metrics.income_yield_ann),
    ]
    lines: list[str] = []
    for label, value in rows:
        amount_text = (
            f" / about {_format_money(portfolio_value * value)}"
            if portfolio_value is not None
            else ""
        )
        lines.append(f"- **{label}:** {_format_percentage_precise(value)}{amount_text}")
    lines.append(
        "- **Note:** the volatility dollar figure is a scale estimate, not a maximum loss."
    )
    return lines


#
# Major rendered blocks used by the chat controller
#


def render_sidebar_content(
    state: SessionStateResponse,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
    stage: str,
    current_question: dict[str, Any] | None = None,
    profile_text: str | None = None,
    selected_band_text: str | None = None,
) -> str:
    """Render the right-hand summary panel from persisted session state."""

    answer_lines = build_answer_summary_lines(
        state,
        questions_by_id=questions_by_id,
        question_labels=question_labels,
        numbered=True,
        use_full_question_text=False,
    )
    answers_block = "\n".join(answer_lines) if answer_lines else "- No answers recorded yet."

    stage_map = {
        "questionnaire": "In progress",
        "review": "Review",
        "editing": "Updating answer",
        "numeric_confirm": "Confirm amount",
        "submitted": "Profile ready",
    }
    parts = [
        f"**{stage_map.get(stage, 'Assessment in progress')}**",
        "",
        "Recorded so far",
        answers_block,
    ]

    if current_question is not None:
        parts.extend(
            [
                "",
                (
                    f"**Now:** Question {current_question['order']} - "
                    f"{get_question_label(current_question['id'], questions_by_id=questions_by_id, question_labels=question_labels)}"
                ),
            ]
        )

    if selected_band_text:
        parts.extend(["", f"**Draft band:** {selected_band_text}"])

    if stage == "review":
        parts.extend(
            [
                "",
                "**Next:** `change <question number>`, `band <band number>`, then `confirm`",
            ]
        )

    if profile_text:
        parts.extend(["", f"**Result:** {profile_text}"])

    return "\n".join(parts)


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
        "Reply with the option number, the option id, or the full option text.\n\n"
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
        "Reply with the new option number, the option id, or the full option text.\n\n"
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
            "**Selected draft band:** None yet. Choose one with `band <band number>` before `confirm`."
        )
    else:
        selected_band_line = (
            f"**Selected draft band:** {selected_band['order']}. {selected_band['label']}"
        )

    return (
        "**Review your answers**\n\n"
        "Here is what I have recorded:\n\n"
        + "\n".join(answer_lines)
        + "\n\n**Choose a draft investor band**\n"
        + "\n".join(band_lines)
        + "\n\n"
        + selected_band_line
        + "\n\n**Commands**\n"
        + "- `change <question number>`\n"
        + "- `band <band number>`\n"
        + "- `confirm`"
    )


def render_profile_summary(
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    *,
    user_report_path: Path | None = None,
) -> str:
    """Build the final chat summary after submission.

    The detailed holdings now live in the generated HTML report. Keeping the
    chat answer short makes the final screen easier to read.
    """

    source_label = (
        "Manual mock band selection"
        if profile.profile_source == "manual_mock_band"
        else "Scored questionnaire"
    )
    score_text = (
        f"Score {profile.profile_score:.1f}"
        if profile.profile_score is not None
        else "score not used in this mock-band run"
    )
    portfolio_value = _portfolio_value_from_answers(state)
    portfolio_value_line = (
        f"**Portfolio value used for display:** {_format_money(portfolio_value)}  \n"
        if portfolio_value is not None
        else ""
    )
    mix_lines = format_super_class_mix_from_holdings(
        recommendation,
        portfolio_value=portfolio_value,
    )
    metric_lines = format_metric_snapshot_lines(
        recommendation,
        portfolio_value=portfolio_value,
    )
    report_line = (
        "\n\nI attached the detailed HTML portfolio report with holdings, tables, and audit-friendly context."
        if user_report_path is not None
        else ""
    )
    profile_path_caveat = (
        "- This is still the manual mock-band demo path."
        if profile.profile_source == "manual_mock_band"
        else "- This used the scored-questionnaire fallback path."
    )
    caveat_lines = [
        profile_path_caveat,
        "- Dollar figures are estimates based on the portfolio value you entered; they do not change the allocation.",
        "- Expected returns are estimates, not guarantees.",
    ]

    return (
        f"**Draft portfolio snapshot: {profile.profile_label}**\n\n"
        f"**Profile source:** {source_label} ({score_text})  \n"
        f"**Band id:** `{profile.profile_band}`  \n"
        f"{portfolio_value_line}"
        f"{profile.profile_description}"
        f"{report_line}\n\n"
        + "\n\n**Portfolio mix**\n"
        + "\n".join(mix_lines)
        + "\n\n**Key estimates**\n"
        + "\n".join(metric_lines)
        + "\n\n**Important caveats**\n"
        + "\n".join(caveat_lines)
        + "\n\nType `/restart` to run the questionnaire again."
    )

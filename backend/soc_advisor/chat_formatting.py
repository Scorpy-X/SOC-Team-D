"""Pure formatting helpers for the Chainlit experiment copy."""

from __future__ import annotations

from typing import Any

from .schemas import ProfileSummary, RecommendationSummary, SessionStateResponse


DISPLAY_SUPER_CLASS_ORDER = ("Cash", "Fixed Income", "Equity", "Fund")


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
) -> str:
    """Build the final chat summary after submission."""

    answer_lines = build_answer_summary_lines(
        state,
        questions_by_id={answer.question_id: {"text": answer.question_text} for answer in state.answers},
        question_labels={},
        numbered=True,
        use_full_question_text=True,
    )
    reason_lines = [f"- {reason}" for reason in profile.reasons]
    portfolio_lines = [
        (
            f"- **{holding.ticker}** ({holding.super_class} / {holding.asset_class}): "
            f"{holding.weight:.1%}"
        )
        for holding in recommendation.holdings
    ]
    constraint_lines = [
        f"- **Objective:** {recommendation.objective}",
        f"- **Single asset cap:** {recommendation.constraints.single_asset_cap:.0%}",
    ] + [
        f"- {line}"
        for line in format_super_class_ranges(
            recommendation.constraints.super_class_minima,
            recommendation.constraints.super_class_maxima,
        )
    ]
    note_lines = [f"- {note}" for note in recommendation.notes]
    source_label = (
        "Manual mock band selection"
        if profile.profile_source == "manual_mock_band"
        else "Scored questionnaire"
    )
    score_line = (
        f"**Score:** {profile.profile_score:.1f}\n"
        if profile.profile_score is not None
        else "**Score:** Not used in this mock-band run.\n"
    )

    return (
        f"**Draft profile: {profile.profile_label}**\n\n"
        "Thanks for working through the questionnaire. Here is the current "
        "experimental result from the active Variant B demo path.\n\n"
        f"**Profile source:** {source_label}  \n"
        f"**Band id:** `{profile.profile_band}`  \n"
        f"{score_line}\n"
        f"{profile.profile_description}\n\n"
        "**Why this band fits**\n"
        + "\n".join(reason_lines)
        + "\n\n**Answers captured**\n"
        + "\n".join(answer_lines)
        + "\n\n**Portfolio recommendation**\n"
        + "\n".join(portfolio_lines)
        + "\n\n**Portfolio summary**\n"
        + f"**Expected return:** {recommendation.metrics.expected_return:.1%}  \n"
        + f"**Volatility:** {recommendation.metrics.volatility:.1%}  \n"
        + f"**Income yield:** {recommendation.metrics.income_yield_ann:.1%}  \n"
        + f"**Duration:** {recommendation.metrics.modified_duration:.2f}  \n"
        + f"**Expense ratio:** {recommendation.metrics.expense_ratio_ann:.2%}\n"
        + "\n\n**Band policy used**\n"
        + "\n".join(constraint_lines)
        + "\n\n**Recommendation notes**\n"
        + "\n".join(note_lines)
        + "\n\nType `/restart` to run the questionnaire again."
    )

"""Chainlit view-model builders for the exploratory advisor.

This module owns the small dictionaries and markdown blocks passed into
Chainlit custom elements and sidebars. It does not decide questionnaire flow,
score clients, or build portfolios; it only reshapes already-computed state for
the chat UI.
"""

from __future__ import annotations

from typing import Any

from .chat_formatting import (
    DISPLAY_SUPER_CLASS_ORDER,
    build_answer_summary_lines,
    format_metric_snapshot_lines,
    format_percentage_precise,
    format_super_class_mix_from_holdings,
    get_question_label,
    portfolio_value_from_answers,
)
from .schemas import ProfileSummary, RecommendationSummary, SessionStateResponse


def _format_percentage_no_decimals(value: float) -> str:
    """Render a ratio as an integer percentage without markdown."""

    return f"{value * 100:.0f}%"


def _format_super_class_range_summary(
    minima: dict[str, float],
    maxima: dict[str, float],
) -> str:
    """Return a plain-text class-range summary for profile cards."""

    parts: list[str] = []
    for super_class in DISPLAY_SUPER_CLASS_ORDER:
        lower = float(minima.get(super_class, 0.0))
        upper = float(maxima.get(super_class, 1.0))
        if super_class == "Fund" and lower == 0.0 and upper == 0.0:
            continue
        if lower == 0.0 and upper == 1.0:
            continue
        parts.append(
            f"{super_class} {_format_percentage_no_decimals(lower)}-{_format_percentage_no_decimals(upper)}"
        )
    return " | ".join(parts)


def build_selected_investment_groups(
    recommendation: RecommendationSummary,
    *,
    portfolio_value: float | None,
) -> list[dict[str, Any]]:
    """Build sorted investment groups for the report-ready Chainlit card."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for holding in recommendation.holdings:
        if holding.weight <= 0:
            continue
        grouped.setdefault(holding.super_class, []).append(
            {
                "asset_code": holding.ticker,
                "weight": holding.weight,
                "weight_label": format_percentage_precise(holding.weight),
                "detail": (
                    f"{holding.super_class} | {holding.asset_class} | {holding.currency}"
                ),
            }
        )

    groups: list[dict[str, Any]] = []
    for label, holdings in grouped.items():
        sorted_holdings = sorted(
            holdings,
            key=lambda item: (-float(item["weight"]), str(item["asset_code"])),
        )
        groups.append(
            {
                "label": label,
                "total_weight": sum(float(item["weight"]) for item in sorted_holdings),
                "total_weight_label": format_percentage_precise(
                    sum(float(item["weight"]) for item in sorted_holdings)
                ),
                "holdings": sorted_holdings,
            }
        )

    return sorted(
        groups,
        key=lambda group: (-float(group["total_weight"]), str(group["label"])),
    )


def build_review_element_props(
    state: SessionStateResponse,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
    profile_bands: list[dict[str, Any]],
    selected_band_id: str | None,
    selected_band_source: str | None = None,
    intro: str | None = None,
) -> dict[str, Any]:
    """Build serializable props for the interactive Chainlit review element."""

    answers = [
        {
            "order": index,
            "question_id": answer.question_id,
            "label": get_question_label(
                answer.question_id,
                questions_by_id=questions_by_id,
                question_labels=question_labels,
            ),
            "value": answer.answer_label,
        }
        for index, answer in enumerate(state.answers, start=1)
    ]

    bands = [
        {
            "order": choice["order"],
            "id": choice["id"],
            "label": choice["label"],
            "description": choice["description"],
            "range_summary": _format_super_class_range_summary(
                choice["super_class_minima"],
                choice["super_class_maxima"],
            ),
            "is_selected": choice["id"] == selected_band_id,
        }
        for choice in profile_bands
    ]

    selected_band = next(
        (choice for choice in profile_bands if choice["id"] == selected_band_id),
        None,
    )
    selected_label = (
        f"{selected_band['order']}. {selected_band['label']}"
        if selected_band is not None
        else None
    )
    selected_help = (
        "Choose a profile before generating the report."
        if selected_band is None
        else selected_band_source
        or "You can still change answers or choose a different profile before the risk check."
    )

    return {
        "title": "Review your answers",
        "intro": intro
        or "I have what I need for now. Review the answers below and check the calculated profile before generating the report.",
        "answers": answers,
        "bands": bands,
        "selected_band_id": selected_band_id,
        "selected_band_label": selected_label,
        "selected_band_help": selected_help,
        "can_confirm": selected_band_id is not None,
        "fallback_hint": "If you prefer typing, you can still use: change <question number>, band <band number> to override, yes to continue to the risk check.",
    }


def build_report_ready_props(
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    *,
    report_name: str,
) -> dict[str, Any]:
    """Build serializable props for the post-submit report handoff card."""

    metrics = recommendation.metrics
    investment_groups = build_selected_investment_groups(
        recommendation,
        portfolio_value=None,
    )
    highlights = [
        {
            "label": "Suggested profile",
            "value": profile.profile_label,
            "detail": (
                "Adjusted after liquidity check"
                if profile.profile_source in {
                    "liquidity_adjusted_questionnaire",
                    "liquidity_adjusted_manual_profile",
                }
                else
                "Chosen during review"
                if profile.profile_source == "manual_mock_band"
                else "Calculated from questionnaire"
            ),
        },
        {
            "label": "Expected annual return",
            "value": format_percentage_precise(metrics.expected_return),
            "detail": "Model estimate, not a guarantee",
        },
        {
            "label": "Annual volatility",
            "value": format_percentage_precise(metrics.volatility),
            "detail": "Risk scale estimate, not a guaranteed loss range",
        },
    ]

    return {
        "title": "Report ready",
        "eyebrow": "Report ready",
        "summary": (
            "The detailed portfolio report is attached below. It includes the grouped holdings view, key estimates, concentration checks, and the limitations section."
        ),
        "report_name": report_name,
        "highlights": highlights,
        "investment_note": "Asset codes are short market identifiers for each investment.",
        "investment_groups": investment_groups,
        "next_steps": [
            "See a quick report summary in the panel on the right.",
            "Open or download the attached report for the full details.",
            "Use Start over when you want to run the assessment again.",
        ],
    }


def build_sidebar_sections(
    state: SessionStateResponse,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
    stage: str,
    current_question: dict[str, Any] | None = None,
    profile_text: str | None = None,
    selected_band_text: str | None = None,
    pending_amount_text: str | None = None,
    report_preview_markdown: str | None = None,
) -> list[dict[str, str]]:
    """Build structured sidebar sections for the assessment summary."""

    status_map = {
        "questionnaire": "In progress",
        "review": "Ready for review",
        "editing": "Updating answer",
        "numeric_confirm": "Review amount",
        "submitted": "Portfolio ready",
        "risk_reality_check": "Checking risk comfort",
    }
    total_questions = len(questions_by_id)
    captured_lines = build_answer_summary_lines(
        state,
        questions_by_id=questions_by_id,
        question_labels=question_labels,
        numbered=False,
        use_full_question_text=False,
    )
    captured_block = (
        "\n".join(captured_lines)
        if captured_lines
        else "- No answers recorded yet."
    )

    status_lines = [f"**{status_map.get(stage, 'Assessment in progress')}**"]
    if current_question is not None:
        question_label = get_question_label(
            current_question["id"],
            questions_by_id=questions_by_id,
            question_labels=question_labels,
        )
        status_lines.extend(
            [
                "",
                f"**Question {current_question['order']} of {total_questions}**",
                question_label,
            ]
        )
    elif stage == "review":
        status_lines.extend(
            ["", "**Questionnaire complete**", "Choose the profile that fits best."]
        )
    elif stage == "submitted":
        status_lines.extend(
            ["", "**Portfolio generated**", "Use the summary to track your result and report status."]
        )

    next_step_lines = {
        "questionnaire": [
            "**What happens now**",
            "",
            "Reply with the answer number or type the answer in full.",
        ],
        "editing": [
            "**What happens now**",
            "",
            "Send the replacement answer in chat. Your saved answer will update right away.",
        ],
        "numeric_confirm": [
            "**What happens now**",
            "",
            (
                f"Pending amount: **{pending_amount_text}**  \nType `yes` to save it, or send a different amount."
                if pending_amount_text is not None
                else "Type `yes` to save the parsed amount, or send a different amount."
            ),
        ],
        "review": [
            "**What happens now**",
            "",
            (
                "Choose a profile, then type yes to continue to the risk check."
                if selected_band_text is None
                else "You can still change answers or type yes to continue with the selected profile."
            ),
        ],
        "submitted": [
            "**What happens now**",
            "",
            "Open the detailed report from the chat card, or use the summary button for a quick overview.",
        ],
    }.get(stage, ["**What happens now**", "", "Continue in the current chat flow."])

    sections = [
        {"key": "status", "content": "\n".join(status_lines)},
        {"key": "next", "content": "\n".join(next_step_lines)},
        {"key": "captured", "content": f"**Answers saved**\n\n{captured_block}"},
    ]

    if selected_band_text is not None or stage == "review":
        sections.append(
            {
                "key": "band",
                "content": (
                    "**Selected profile**\n\n"
                    + (
                        selected_band_text
                        if selected_band_text is not None
                        else "Not selected yet."
                    )
                ),
            }
        )

    if profile_text is not None:
        sections.append({"key": "result", "content": f"**Profile result**\n\n{profile_text}"})

    if stage == "submitted":
        report_content = (
            report_preview_markdown
            if report_preview_markdown is not None
            else (
                "**Report status**\n\n"
                "Report ready. Open the attached report from the chat, or use the summary button for a quick overview."
            )
        )
        sections.append({"key": "report", "content": report_content})

    return sections


def render_sidebar_content(
    state: SessionStateResponse,
    *,
    questions_by_id: dict[str, dict[str, Any]],
    question_labels: dict[str, str],
    stage: str,
    current_question: dict[str, Any] | None = None,
    profile_text: str | None = None,
    selected_band_text: str | None = None,
    pending_amount_text: str | None = None,
    report_preview_markdown: str | None = None,
) -> str:
    """Render the structured assessment summary as one markdown block."""

    sections = build_sidebar_sections(
        state,
        questions_by_id=questions_by_id,
        question_labels=question_labels,
        stage=stage,
        current_question=current_question,
        profile_text=profile_text,
        selected_band_text=selected_band_text,
        pending_amount_text=pending_amount_text,
        report_preview_markdown=report_preview_markdown,
    )
    return "\n\n---\n\n".join(section["content"] for section in sections)


def render_report_preview(
    state: SessionStateResponse,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    *,
    report_name: str,
) -> str:
    """Render the sidebar preview used by the report handoff action."""

    portfolio_value = portfolio_value_from_answers(state)
    mix_lines = format_super_class_mix_from_holdings(
        recommendation,
        portfolio_value=portfolio_value,
    )
    metric_lines = format_metric_snapshot_lines(
        recommendation,
        portfolio_value=portfolio_value,
    )
    return (
        f"**{report_name}**\n\n"
        "This is the full portfolio report for this assessment.\n\n"
        f"**Suggested profile:** {profile.profile_label}\n\n"
        "**Portfolio mix preview**\n"
        + "\n".join(mix_lines)
        + "\n\n**Key estimates preview**\n"
        + "\n".join(metric_lines)
        + "\n\nUse the attachment in the chat to open or download the full report."
    )

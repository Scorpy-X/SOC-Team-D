"""Chainlit entrypoint for the exploratory SOC chat advisor.

This file is the conversation controller for the active advisor prototype.

High-level flow:

1. create a new assessment session in SQLite
2. ask one configured question at a time
3. save each answer immediately through the backend service layer
4. keep the sidebar synced with the saved session state
5. let the user review or edit answers
6. calculate an investor profile and allow advisor review/override
7. submit once complete, which triggers the Variant B allocation engine

Important separation of responsibilities:

- this file handles chat flow and UI behavior
- `soc_advisor.services` handles questionnaire/session logic
- `soc_advisor.portfolio` handles the actual allocation math
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

import chainlit as cl


def find_project_root(start: Path) -> Path:
    """Find the repo root so this file can import backend modules reliably."""

    for candidate in (start, *start.parents):
        if (candidate / "backend" / "soc_advisor" / "__init__.py").exists():
            return candidate
    raise RuntimeError("Could not find the project root.")


PROJECT_ROOT = find_project_root(Path(__file__).resolve())
BACKEND_DIR = PROJECT_ROOT / "backend"
FILES_DIR = PROJECT_ROOT / ".files"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.chat_formatting import (  # noqa: E402
    format_edit_prompt,
    format_profile_score,
    format_question,
    get_question_label,
    render_profile_summary,
)
from soc_advisor.chat_view_models import (  # noqa: E402
    build_report_ready_props,
    build_review_element_props,
    render_report_preview,
    render_sidebar_content,
)
from soc_advisor.database import Base, SessionLocal, engine  # noqa: E402
from soc_advisor.liquidity_policy import (  # noqa: E402
    build_liquidity_policy_check,
    with_liquidity_user_action,
)
from soc_advisor.portfolio import list_profile_bands  # noqa: E402
from soc_advisor.portfolio import load_portfolio_config  # noqa: E402
from soc_advisor.reporting import generate_portfolio_reports  # noqa: E402
from soc_advisor.risk_reality import (  # noqa: E402
    RiskRealityEstimate,
    build_risk_reality_estimate,
    build_risk_reality_trace,
    is_continue_input,
    render_risk_reality_prompt,
)
from soc_advisor.schemas import (  # noqa: E402
    AnswerSummary,
    DecisionTrace,
    LiquidityPolicyCheckTrace,
    ProfileSummary,
    RecommendationSummary,
    RiskRealityCheckTrace,
    SessionStateResponse,
)
from soc_advisor.services import (  # noqa: E402
    build_session_state,
    create_assessment_session,
    get_saved_decision_trace,
    get_session_or_404,
    is_question_active,
    load_questionnaire,
    load_scoring,
    preview_assessment_recommendation,
    score_session,
    submit_assessment,
    upsert_answer,
)
from soc_advisor.settings import get_settings  # noqa: E402
from soc_advisor.typed_answers import parse_and_normalize_currency_amount_text  # noqa: E402


# Chainlit owns browser-chat state and message routing only. The questionnaire
# logic lives in `soc_advisor.services`, and the actual allocation math lives
# in `soc_advisor.portfolio`.
FILES_DIR.mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)
settings = get_settings()
QUESTIONNAIRE = load_questionnaire(settings.questionnaire_version)
ORDERED_QUESTIONS = sorted(QUESTIONNAIRE["questions"], key=lambda item: item["order"])
QUESTIONS_BY_ID = {question["id"]: question for question in ORDERED_QUESTIONS}
PROFILE_BAND_CHOICES = list_profile_bands(settings.portfolio_version)
PROFILE_BANDS_BY_ID = {choice["id"]: choice for choice in PROFILE_BAND_CHOICES}
PORTFOLIO_CONFIG = load_portfolio_config(settings.portfolio_version)
QuestionDict = dict[str, Any]
OptionDict = dict[str, Any]
REVIEW_ELEMENT_SESSION_KEY = "review_workspace_element"
REPORT_PREVIEW_SESSION_KEY = "report_preview_markdown"
REPORT_PREVIEW_ACTIVE_SESSION_KEY = "report_preview_active"
SUBMITTED_PROFILE_TEXT_SESSION_KEY = "submitted_profile_text"
RISK_REALITY_ESTIMATE_SESSION_KEY = "risk_reality_estimate"
LIQUIDITY_POLICY_CHECK_SESSION_KEY = "liquidity_policy_check"


# ---------------------------------------------------------------------------
# Compact display labels and compatibility aliases
# ---------------------------------------------------------------------------


# Compact human labels used in the sidebar and confirmation copy.
QUESTION_LABELS = {
    "portfolio_value": "Portfolio value",
    "major_expense_withdrawal_amount": "Major expense need",
    "essential_monthly_expenses": "Monthly expenses",
    "emergency_fund_months": "Desired emergency reserve",
    "current_emergency_fund_months": "Current emergency reserve",
    "non_investment_income_stability": "Income stability",
    "dependents_obligations": "Dependents",
    "time_horizon": "Horizon",
    "investment_phase": "Investment phase",
    "market_drop_response": "Market drop response",
    "short_term_loss_willingness": "Loss willingness",
    "financial_knowledge": "Knowledge",
    "investing_experience_length": "Experience",
    "hypothetical_30_loss_reaction": "30% loss reaction",
}

# The live review prompt teaches "change <question number>" only, but these
# aliases are kept as a compatibility path for older habits during internal use.
CHANGE_TARGET_ALIASES = {
    "portfolio value": "portfolio_value",
    "value": "portfolio_value",
    "major expense": "major_expense_withdrawal_amount",
    "withdrawal": "major_expense_withdrawal_amount",
    "monthly expenses": "essential_monthly_expenses",
    "expenses": "essential_monthly_expenses",
    "emergency fund": "emergency_fund_months",
    "emergency reserve": "emergency_fund_months",
    "current emergency fund": "current_emergency_fund_months",
    "current emergency reserve": "current_emergency_fund_months",
    "income": "non_investment_income_stability",
    "income stability": "non_investment_income_stability",
    "non-investment income": "non_investment_income_stability",
    "dependents": "dependents_obligations",
    "obligations": "dependents_obligations",
    "horizon": "time_horizon",
    "phase": "investment_phase",
    "investment phase": "investment_phase",
    "market drop": "market_drop_response",
    "drop response": "market_drop_response",
    "loss willingness": "short_term_loss_willingness",
    "risk willingness": "short_term_loss_willingness",
    "knowledge": "financial_knowledge",
    "experience": "investing_experience_length",
    "loss": "hypothetical_30_loss_reaction",
    "loss reaction": "hypothetical_30_loss_reaction",
    "30% loss": "hypothetical_30_loss_reaction",
}


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------


def get_session_id() -> str | None:
    """Fetch the active assessment session id from Chainlit's user session."""

    return cast(str | None, cl.user_session.get("assessment_session_id"))


def get_selected_band_choice() -> dict[str, Any] | None:
    """Return the currently selected manual override band from chat session state."""

    selected_band_id = cast(str | None, cl.user_session.get("selected_mock_profile_band"))
    if not selected_band_id:
        return None
    return PROFILE_BANDS_BY_ID.get(selected_band_id)


def active_profile_for_review(session_id: str) -> tuple[ProfileSummary, bool]:
    """Return the profile currently driving review, plus override status."""

    manual_choice = get_selected_band_choice()
    if manual_choice is not None:
        return (
            ProfileSummary(
                profile_band=manual_choice["id"],
                profile_label=manual_choice["label"],
                profile_score=None,
                profile_source="manual_mock_band",
                profile_description=manual_choice["description"],
                dimension_scores={},
                reasons=["Advisor review selected this profile manually."],
            ),
            True,
        )
    return score_chat_profile(session_id), False


def get_pending_numeric_answer() -> dict[str, Any] | None:
    """Return the current unsaved numeric answer awaiting confirmation."""

    pending = cast(dict[str, Any] | None, cl.user_session.get("pending_numeric_answer"))
    return pending if pending else None


def get_review_element() -> cl.CustomElement | None:
    """Return the stored interactive review element if it exists."""

    return cast(cl.CustomElement | None, cl.user_session.get(REVIEW_ELEMENT_SESSION_KEY))


def set_review_element(element: cl.CustomElement | None) -> None:
    """Store or clear the current interactive review element."""

    cl.user_session.set(REVIEW_ELEMENT_SESSION_KEY, element)


def get_risk_reality_estimate() -> RiskRealityEstimate | None:
    """Return the pending pre-report risk check estimate if one exists."""

    return cast(
        RiskRealityEstimate | None,
        cl.user_session.get(RISK_REALITY_ESTIMATE_SESSION_KEY),
    )


def set_risk_reality_estimate(estimate: RiskRealityEstimate | None) -> None:
    """Store or clear the current pre-report risk check estimate."""

    cl.user_session.set(RISK_REALITY_ESTIMATE_SESSION_KEY, estimate)


def get_liquidity_policy_check() -> LiquidityPolicyCheckTrace | None:
    """Return the pending/submitted liquidity compatibility trace."""

    return cast(
        LiquidityPolicyCheckTrace | None,
        cl.user_session.get(LIQUIDITY_POLICY_CHECK_SESSION_KEY),
    )


def set_liquidity_policy_check(check: LiquidityPolicyCheckTrace | None) -> None:
    """Store or clear the current liquidity compatibility trace."""

    cl.user_session.set(LIQUIDITY_POLICY_CHECK_SESSION_KEY, check)


def set_pending_numeric_answer(
    *,
    question_id: str,
    numeric_value: float,
    display_value: str,
) -> None:
    """Store one parsed numeric answer until the user confirms it."""

    cl.user_session.set(
        "pending_numeric_answer",
        {
            "question_id": question_id,
            "numeric_value": numeric_value,
            "display_value": display_value,
        },
    )


def clear_pending_numeric_answer() -> None:
    """Clear any unsaved numeric answer from chat session state."""

    cl.user_session.set("pending_numeric_answer", None)


def answer_lookup_for_state(state: SessionStateResponse) -> dict[str, str | None]:
    """Build the minimal answer lookup used for dependency-aware question flow."""

    return {answer.question_id: answer.option_id for answer in state.answers}


def get_current_question(state: SessionStateResponse) -> QuestionDict | None:
    """Return the next unanswered active question for the current saved state."""

    saved_answers = answer_lookup_for_state(state)
    for question in ORDERED_QUESTIONS:
        if not is_question_active(question, saved_answers):
            continue
        if question["id"] not in saved_answers:
            return question
    return None


def current_answer_for_question(
    state: SessionStateResponse,
    question_id: str,
) -> AnswerSummary | None:
    """Return the currently saved answer for one question if it exists."""

    return next((answer for answer in state.answers if answer.question_id == question_id), None)


def question_for_active_stage(
    state: SessionStateResponse,
    *,
    edit_target_question_id: str | None,
) -> QuestionDict | None:
    """Return the question that should currently be answered in the chat."""

    if edit_target_question_id is not None:
        return QUESTIONS_BY_ID[edit_target_question_id]
    return get_current_question(state)


# ---------------------------------------------------------------------------
# Persistence wrappers
# ---------------------------------------------------------------------------


def create_chat_session() -> SessionStateResponse:
    """Create a brand-new draft assessment session in the backend database."""

    with SessionLocal() as db:
        session = create_assessment_session(db)
        questionnaire = load_questionnaire(session.questionnaire_version)
        return build_session_state(session, questionnaire)


def load_chat_state(session_id: str) -> SessionStateResponse:
    """Load the latest saved state for one chat session."""

    with SessionLocal() as db:
        session = get_session_or_404(db, session_id)
        questionnaire = load_questionnaire(session.questionnaire_version)
        return build_session_state(session, questionnaire)


def save_chat_answer(
    *,
    session_id: str,
    question_id: str,
    option_id: str | None = None,
    numeric_value: float | None = None,
) -> SessionStateResponse:
    """Persist one answer and return the refreshed session state."""

    with SessionLocal() as db:
        session = get_session_or_404(db, session_id)
        questionnaire = load_questionnaire(session.questionnaire_version)
        updated_session = upsert_answer(
            db,
            session=session,
            questionnaire=questionnaire,
            question_id=question_id,
            option_id=option_id,
            numeric_value=numeric_value,
        )
        return build_session_state(updated_session, questionnaire)


def submit_chat_session(
    session_id: str,
    *,
    mock_profile_band: str | None,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
    risk_reality_check: RiskRealityCheckTrace | None = None,
) -> tuple[SessionStateResponse, ProfileSummary, RecommendationSummary, DecisionTrace]:
    """Submit the session, which triggers the portfolio generation flow."""

    with SessionLocal() as db:
        session = get_session_or_404(db, session_id)
        submitted_session, profile, recommendation = submit_assessment(
            db,
            session=session,
            mock_profile_band=mock_profile_band,
            liquidity_policy_check=liquidity_policy_check,
            risk_reality_check=risk_reality_check,
        )
        decision_trace = get_saved_decision_trace(submitted_session)
        questionnaire = load_questionnaire(submitted_session.questionnaire_version)
        return (
            build_session_state(submitted_session, questionnaire),
            profile,
            recommendation,
            decision_trace,
        )


def preview_chat_recommendation(
    session_id: str,
    *,
    mock_profile_band: str | None,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
) -> tuple[ProfileSummary, RecommendationSummary]:
    """Build a recommendation preview without saving the session as submitted."""

    with SessionLocal() as db:
        session = get_session_or_404(db, session_id)
        return preview_assessment_recommendation(
            db,
            session=session,
            mock_profile_band=mock_profile_band,
            liquidity_policy_check=liquidity_policy_check,
        )


def score_chat_profile(session_id: str) -> ProfileSummary:
    """Calculate the profile from saved questionnaire answers for review mode."""

    with SessionLocal() as db:
        session = get_session_or_404(db, session_id)
        questionnaire = load_questionnaire(session.questionnaire_version)
        scoring = load_scoring(session.scoring_version)
        return score_session(session, questionnaire, scoring)


def build_chat_liquidity_policy_check(
    state: SessionStateResponse,
    *,
    selected_profile_band: str,
    user_action: str,
) -> LiquidityPolicyCheckTrace:
    """Calculate the pre-submit liquidity/profile compatibility check."""

    return build_liquidity_policy_check(
        answers=state.answers,
        selected_profile_band=selected_profile_band,
        portfolio_config=PORTFOLIO_CONFIG,
        user_action=user_action,
    )


def render_liquidity_auto_adjustment_notice(check: LiquidityPolicyCheckTrace) -> str:
    """Explain an automatic profile adjustment without adding a choice menu."""

    return (
        "**Liquidity adjustment applied**\n\n"
        f"Your liquidity answers require at least **{check.liquidity_floor:.1%} Cash** "
        f"(${check.required_liquidity_amount:,.2f} in near-term Cash reserve). "
        f"{check.selected_profile_label} allows up to **{check.selected_cash_ceiling:.1%} Cash**, "
        f"so the report will use **{check.effective_profile_label}**, which allows up to "
        f"**{(check.effective_cash_ceiling or 0.0):.1%} Cash**."
    )


def render_liquidity_blocked_notice(check: LiquidityPolicyCheckTrace) -> str:
    """Explain why the report cannot be generated under the active policy."""

    return (
        "**Report blocked by liquidity policy**\n\n"
        f"Your liquidity answers require at least **{check.liquidity_floor:.1%} Cash** "
        f"(${check.required_liquidity_amount:,.2f} in near-term Cash reserve). "
        "That is higher than every configured investor profile currently allows. "
        "Please revise the portfolio value, major expense need, monthly expenses, "
        "or emergency reserve answer before generating the report."
    )


# ---------------------------------------------------------------------------
# Sidebar and prompt rendering
# ---------------------------------------------------------------------------


async def update_sidebar(
    state: SessionStateResponse,
    *,
    stage: str,
    current_question: QuestionDict | None = None,
    profile_text: str | None = None,
) -> None:
    """Push a fresh sidebar summary whenever the workflow state changes."""

    manual_band_choice = get_selected_band_choice()
    active_profile: ProfileSummary | None = None
    if state.can_submit and stage in {"review", "risk_reality_check"}:
        try:
            active_profile, _manual_override = active_profile_for_review(state.session_id)
        except Exception:
            active_profile = None
    pending_numeric = get_pending_numeric_answer()
    liquidity_check = get_liquidity_policy_check()
    report_preview_markdown = (
        cast(str | None, cl.user_session.get(REPORT_PREVIEW_SESSION_KEY))
        if cast(bool | None, cl.user_session.get(REPORT_PREVIEW_ACTIVE_SESSION_KEY))
        else None
    )
    key_parts = [
        state.session_id,
        stage,
        current_question["id"] if current_question is not None else "none",
        (
            active_profile.profile_band
            if active_profile is not None
            else manual_band_choice["id"]
            if manual_band_choice is not None
            else "no-band"
        ),
        pending_numeric["question_id"] if pending_numeric is not None else "no-pending",
        pending_numeric["display_value"] if pending_numeric is not None else "no-value",
        (
            liquidity_check.effective_profile_band
            if liquidity_check is not None
            else "no-liquidity-check"
        ),
        "preview-on" if report_preview_markdown is not None else "preview-off",
        state.updated_at.isoformat(),
    ]
    await cl.ElementSidebar.set_title("Assessment summary")
    await cl.ElementSidebar.set_elements(
        [
            cl.Text(
                name="Assessment summary",
                content=render_sidebar_content(
                    state,
                    questions_by_id=QUESTIONS_BY_ID,
                    question_labels=QUESTION_LABELS,
                    stage=stage,
                    current_question=current_question,
                    profile_text=profile_text,
                    selected_band_text=(
                        active_profile.profile_label
                        if active_profile is not None
                        else manual_band_choice["label"]
                        if manual_band_choice is not None
                        else None
                    ),
                    pending_amount_text=(
                        cast(str, pending_numeric["display_value"])
                        if pending_numeric is not None
                        else None
                    ),
                    report_preview_markdown=report_preview_markdown,
                ),
            )
        ],
        key="|".join(key_parts),
    )


def build_profile_sidebar_text(profile: ProfileSummary) -> str:
    """Format the short profile result shown in the sidebar after submit."""

    if profile.profile_source == "manual_mock_band":
        detail_text = "Chosen during review"
    elif profile.profile_source in {
        "liquidity_adjusted_questionnaire",
        "liquidity_adjusted_manual_profile",
    }:
        detail_text = f"Adjusted after liquidity check; {format_profile_score(profile.profile_score)}"
    else:
        detail_text = format_profile_score(profile.profile_score)
    return f"**{profile.profile_label}**  \n{detail_text}"


async def send_missing_session_message() -> None:
    """Tell the user to restart if the chat-side session state is gone."""

    await cl.Message(
        content="The saved chat session is missing. Type `/restart` to begin again.",
    ).send()


async def send_edit_prompt_for_question(
    state: SessionStateResponse,
    question: QuestionDict,
) -> None:
    """Show the edit prompt for one already-answered question."""

    current_answer = current_answer_for_question(state, question["id"])
    current_label = (
        current_answer.answer_label
        if current_answer is not None
        else "No answer recorded yet"
    )
    cl.user_session.set("workflow_stage", "editing")
    await update_sidebar(state, stage="editing", current_question=question)
    await cl.Message(
        content=format_edit_prompt(
            question,
            total_questions=len(ORDERED_QUESTIONS),
            question_label=get_question_label(
                question["id"],
                questions_by_id=QUESTIONS_BY_ID,
                question_labels=QUESTION_LABELS,
            ),
            current_label=current_label,
        )
    ).send()


async def send_numeric_confirmation_prompt(
    state: SessionStateResponse,
    question: QuestionDict,
    *,
    display_value: str,
    edit_target_question_id: str | None,
) -> None:
    """Ask the user to confirm one parsed numeric amount before saving it."""

    cl.user_session.set("workflow_stage", "numeric_confirm")
    await update_sidebar(state, stage="numeric_confirm", current_question=question)
    await cl.Message(
        content=(
            f"I read that as **{display_value}** for question **{question['order']}** "
            f"(**{get_question_label(question['id'], questions_by_id=QUESTIONS_BY_ID, question_labels=QUESTION_LABELS)}**).\n\n"
            "Type `yes` to save it, or enter a different amount."
            + (
                "\n\nThis will update the existing answer once you type yes."
                if edit_target_question_id is not None
                else ""
            )
        ),
    ).send()


async def send_question_prompt(
    state: SessionStateResponse,
    question: QuestionDict,
) -> None:
    """Show the next active questionnaire prompt."""

    cl.user_session.set("workflow_stage", "questionnaire")
    cl.user_session.set("current_question_id", question["id"])
    await update_sidebar(state, stage="questionnaire", current_question=question)
    await cl.Message(
        content=format_question(
            question,
            total_questions=len(ORDERED_QUESTIONS),
            question_label=get_question_label(
                question["id"],
                questions_by_id=QUESTIONS_BY_ID,
                question_labels=QUESTION_LABELS,
            ),
        )
    ).send()


async def upsert_review_workspace(
    state: SessionStateResponse,
    *,
    intro: str | None,
) -> None:
    """Create or update the interactive review workspace element."""

    session_id = get_session_id()
    if session_id is None:
        await send_missing_session_message()
        return

    active_profile, manual_override = active_profile_for_review(session_id)
    selected_source = (
        "Advisor override selected during review. You can still change answers or choose a different profile before generating the report."
        if manual_override
        else "Calculated from your questionnaire answers. You can still choose a different profile as an advisor/demo override."
    )
    review_props = build_review_element_props(
        state,
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        profile_bands=PROFILE_BAND_CHOICES,
        selected_band_id=active_profile.profile_band,
        selected_band_source=selected_source,
        intro=intro,
    )
    review_element = get_review_element()
    if review_element is None:
        review_element = cl.CustomElement(
            name="ReviewWorkspace",
            props=review_props,
            display="inline",
        )
        set_review_element(review_element)
        await cl.Message(
            content=(
                "Review the current draft below. Use the controls first; typed commands still work if you prefer."
            ),
            elements=[review_element],
        ).send()
        return

    review_element.props = review_props
    await review_element.update()


async def send_review_message(*, intro: str | None = None) -> None:
    """Show the review screen once all active questions are answered."""

    session_id = get_session_id()
    if session_id is None:
        await send_missing_session_message()
        return

    state = load_chat_state(session_id)
    clear_pending_numeric_answer()
    set_liquidity_policy_check(None)
    cl.user_session.set("workflow_stage", "review")
    cl.user_session.set("edit_target_question_id", None)
    await update_sidebar(state, stage="review")
    await upsert_review_workspace(
        state,
        intro=(
            intro
            or "I have what I need for now. I calculated a draft profile from the questionnaire. Review the saved answers, adjust the profile only if needed, then generate the report when you are ready."
        ),
    )


async def send_fresh_review_message_after_edit(*, intro: str) -> None:
    """Send a new review workspace at the bottom after an edited answer is saved."""

    # Updating the old custom element in place can make the chat look stalled
    # because the refreshed review card may be far above the user's current
    # scroll position. Clearing it forces Chainlit to render a fresh card after
    # the "recorded answer" message.
    set_review_element(None)
    await send_review_message(intro=intro)


async def send_next_question() -> None:
    """Advance the chat to the next question, edit prompt, or review screen."""

    session_id = get_session_id()
    if session_id is None:
        await send_missing_session_message()
        return

    state = load_chat_state(session_id)
    edit_target_question_id = cast(str | None, cl.user_session.get("edit_target_question_id"))
    question = question_for_active_stage(
        state,
        edit_target_question_id=edit_target_question_id,
    )

    if question is None:
        await send_review_message()
        return

    if edit_target_question_id is not None:
        await send_edit_prompt_for_question(state, question)
        return

    await send_question_prompt(state, question)


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------


def find_option(question: QuestionDict, message_text: str) -> OptionDict | None:
    """Resolve typed user input into one of the configured answer options."""

    normalized = message_text.strip()
    if not normalized:
        return None

    if normalized.isdigit():
        index = int(normalized) - 1
        if 0 <= index < len(question["options"]):
            return question["options"][index]

    lowered = normalized.casefold()
    for option in question["options"]:
        if lowered == option["id"].casefold():
            return option
        if lowered == option["label"].casefold():
            return option

    return None


def parse_currency_amount_for_question(
    question: QuestionDict,
    message_text: str,
) -> tuple[str, float, str]:
    """Parse one currency question from raw chat text."""

    return parse_and_normalize_currency_amount_text(
        message_text,
        question_id=question["id"],
        validation=question.get("validation"),
    )


def parse_change_target(message_text: str) -> QuestionDict | None:
    """Resolve review-mode commands such as 'change 2'."""

    normalized = message_text.strip()
    if not normalized:
        return None

    lowered = normalized.casefold()
    if lowered.startswith("change "):
        normalized = normalized[7:].strip()
        lowered = normalized.casefold()

    if normalized.isdigit():
        order = int(normalized)
        return next((q for q in ORDERED_QUESTIONS if q["order"] == order), None)

    alias_target = CHANGE_TARGET_ALIASES.get(lowered)
    if alias_target:
        return QUESTIONS_BY_ID[alias_target]

    return QUESTIONS_BY_ID.get(lowered)


def parse_band_target(message_text: str) -> dict[str, Any] | None:
    """Resolve review-mode commands such as 'band 4'."""

    normalized = message_text.strip()
    if not normalized:
        return None

    lowered = normalized.casefold()
    if lowered.startswith("band "):
        normalized = normalized[5:].strip()
        lowered = normalized.casefold()

    if normalized.isdigit():
        order = int(normalized)
        return next((choice for choice in PROFILE_BAND_CHOICES if choice["order"] == order), None)

    for choice in PROFILE_BAND_CHOICES:
        if lowered == choice["id"].casefold():
            return choice
        if lowered == choice["label"].casefold():
            return choice

    return None


# ---------------------------------------------------------------------------
# Message handling helpers
# ---------------------------------------------------------------------------


async def send_invalid_answer_feedback(
    question: QuestionDict,
    state: SessionStateResponse,
    *,
    edit_target_question_id: str | None,
) -> None:
    """Explain the valid answer formats and re-show the relevant prompt."""

    await cl.Message(
        content=(
            "I could not match that answer yet. Reply with the answer number "
            "or type the answer exactly as shown."
        ),
    ).send()

    if edit_target_question_id is not None:
        await send_edit_prompt_for_question(state, question)
        return

    await send_question_prompt(state, question)


async def send_recorded_answer_feedback(
    question: QuestionDict,
    recorded_label: str,
    updated_state: SessionStateResponse,
    *,
    edit_target_question_id: str | None,
) -> None:
    """Confirm that an answer was saved and refresh the sidebar."""

    await update_sidebar(
        updated_state,
        stage="editing" if edit_target_question_id is not None else "questionnaire",
        current_question=question,
    )
    await cl.Message(
        content=(
            f"Got it. I recorded question **{question['order']}** "
            f"(**{get_question_label(question['id'], questions_by_id=QUESTIONS_BY_ID, question_labels=QUESTION_LABELS)}**) as "
            f"**{recorded_label}**.\n\n"
            "The summary on the right has been updated."
        ),
    ).send()


async def send_invalid_numeric_feedback(
    question: QuestionDict,
    state: SessionStateResponse,
    *,
    error_message: str,
    edit_target_question_id: str | None,
) -> None:
    """Explain a numeric parsing error and re-show the relevant amount prompt."""

    await cl.Message(content=error_message).send()
    if edit_target_question_id is not None:
        await send_edit_prompt_for_question(state, question)
        return
    await send_question_prompt(state, question)


async def handle_currency_question_entry(
    question: QuestionDict,
    state: SessionStateResponse,
    *,
    content: str,
    edit_target_question_id: str | None,
) -> None:
    """Parse a currency amount and stage it for explicit confirmation."""

    try:
        _, numeric_value, display_value = parse_currency_amount_for_question(question, content)
    except ValueError as exc:
        await send_invalid_numeric_feedback(
            question,
            state,
            error_message=str(exc),
            edit_target_question_id=edit_target_question_id,
        )
        return

    set_pending_numeric_answer(
        question_id=question["id"],
        numeric_value=numeric_value,
        display_value=display_value,
    )
    await send_numeric_confirmation_prompt(
        state,
        question,
        display_value=display_value,
        edit_target_question_id=edit_target_question_id,
    )


async def handle_numeric_confirmation_stage(session_id: str, content: str) -> None:
    """Confirm or replace the current pending numeric amount."""

    pending = get_pending_numeric_answer()
    if pending is None:
        cl.user_session.set("workflow_stage", "questionnaire")
        await send_next_question()
        return

    state = load_chat_state(session_id)
    question = QUESTIONS_BY_ID[pending["question_id"]]
    edit_target_question_id = cast(str | None, cl.user_session.get("edit_target_question_id"))

    if content.strip().casefold() == "yes":
        updated_state = save_chat_answer(
            session_id=session_id,
            question_id=question["id"],
            numeric_value=float(pending["numeric_value"]),
        )
        clear_pending_numeric_answer()
        await send_recorded_answer_feedback(
            question,
            pending["display_value"],
            updated_state,
            edit_target_question_id=edit_target_question_id,
        )
        if edit_target_question_id is not None:
            cl.user_session.set("edit_target_question_id", None)
            await send_fresh_review_message_after_edit(
                intro="Updated. Here is the latest summary."
            )
            return
        await send_next_question()
        return

    try:
        _, numeric_value, display_value = parse_currency_amount_for_question(question, content)
    except ValueError as exc:
        await cl.Message(
            content=(
                f"{exc}\n\n"
                f"I still have **{pending['display_value']}** pending for this question. "
                "Type `yes` to save it, or enter a different valid amount."
            )
        ).send()
        return

    set_pending_numeric_answer(
        question_id=question["id"],
        numeric_value=numeric_value,
        display_value=display_value,
    )
    await send_numeric_confirmation_prompt(
        state,
        question,
        display_value=display_value,
        edit_target_question_id=edit_target_question_id,
    )


async def finalize_review_submission(
    session_id: str,
    *,
    selected_band_id: str | None,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None,
    risk_reality_check: RiskRealityCheckTrace | None,
) -> None:
    """Submit the reviewed session and generate reports after the volatility notice."""

    state, profile, recommendation, decision_trace = submit_chat_session(
        session_id,
        mock_profile_band=selected_band_id,
        liquidity_policy_check=liquidity_policy_check,
        risk_reality_check=risk_reality_check,
    )
    set_review_element(None)
    set_risk_reality_estimate(None)
    set_liquidity_policy_check(None)
    report_paths = generate_portfolio_reports(
        state=state,
        profile=profile,
        recommendation=recommendation,
        decision_trace=decision_trace,
    )
    report_preview = render_report_preview(
        state,
        profile,
        recommendation,
        report_name="SOC portfolio report.html",
    )
    cl.user_session.set(REPORT_PREVIEW_SESSION_KEY, report_preview)
    cl.user_session.set(REPORT_PREVIEW_ACTIVE_SESSION_KEY, False)
    cl.user_session.set(
        SUBMITTED_PROFILE_TEXT_SESSION_KEY,
        build_profile_sidebar_text(profile),
    )
    await update_sidebar(
        state,
        stage="submitted",
        profile_text=build_profile_sidebar_text(profile),
    )
    report_ready_element = cl.CustomElement(
        name="ReportReadyCard",
        props=build_report_ready_props(
            state,
            profile,
            recommendation,
            report_name="SOC portfolio report.html",
        ),
        display="inline",
    )
    await cl.Message(
        content=render_profile_summary(
            state,
            profile,
            recommendation,
            user_report_path=report_paths.user_report_path,
            decision_trace=decision_trace,
        ),
        elements=[
            report_ready_element,
            cl.File(
                name="SOC portfolio report.html",
                path=str(report_paths.user_report_path),
                display="inline",
                mime="text/html",
            )
        ],
    ).send()


async def handle_review_submission(session_id: str) -> None:
    """Apply liquidity policy automatically, then start the risk reality check."""

    state = load_chat_state(session_id)
    active_profile, manual_override = active_profile_for_review(session_id)
    mock_profile_band = active_profile.profile_band if manual_override else None
    try:
        liquidity_check = build_chat_liquidity_policy_check(
            state,
            selected_profile_band=active_profile.profile_band,
            user_action="submitted_compatible_profile",
        )
    except ValueError as exc:
        await cl.Message(
            content=(
                f"I could not run the liquidity check yet: {exc}\n\n"
                "Please review the liquidity answers before generating the report."
            )
        ).send()
        return

    adjustment_notice = ""
    if (
        not liquidity_check.selected_profile_compatible
        and liquidity_check.effective_profile_band is None
    ):
        blocked_check = with_liquidity_user_action(
            liquidity_check,
            user_action="blocked_no_compatible_profile",
        )
        set_liquidity_policy_check(None)
        await send_review_message(intro=render_liquidity_blocked_notice(blocked_check))
        return

    if not liquidity_check.selected_profile_compatible:
        liquidity_check = with_liquidity_user_action(
            liquidity_check,
            user_action="auto_adjusted_to_safer_profile",
        )
        adjustment_notice = render_liquidity_auto_adjustment_notice(liquidity_check) + "\n\n"
    set_liquidity_policy_check(liquidity_check)

    await cl.Message(
        content="Checking liquidity and portfolio volatility before generating the report..."
    ).send()
    try:
        _profile, recommendation = preview_chat_recommendation(
            session_id,
            mock_profile_band=mock_profile_band,
            liquidity_policy_check=liquidity_check,
        )
    except Exception as exc:  # noqa: BLE001 - surface Chainlit preview failures to the user.
        await cl.Message(
            content=(
                "I could not build the risk check for this profile. "
                "Please try again, choose another profile, or type `/restart`.\n\n"
                f"Technical detail: {type(exc).__name__}: {exc}"
            )
        ).send()
        return

    estimate = build_risk_reality_estimate(
        state=state,
        recommendation=recommendation,
    )
    set_risk_reality_estimate(estimate)
    cl.user_session.set("workflow_stage", "risk_reality_check")
    await update_sidebar(state, stage="risk_reality_check")
    await cl.Message(
        content=adjustment_notice + render_risk_reality_prompt(estimate)
    ).send()


@cl.action_callback("review_continue_to_risk_check")
async def on_review_continue_to_risk_check(_action: cl.Action) -> None:
    """Continue from the review card without relying on synthetic chat text."""

    if cast(str | None, cl.user_session.get("workflow_stage")) != "review":
        await cl.Message(
            content="That review card is no longer the active step. Continue with the current prompt or type `/restart` to begin again.",
        ).send()
        return

    session_id = get_session_id()
    if session_id is None:
        await send_missing_session_message()
        return

    await handle_review_submission(session_id)


async def handle_risk_reality_check_stage(session_id: str, content: str) -> None:
    """Wait for the user to acknowledge the informational volatility notice."""

    estimate = get_risk_reality_estimate()
    if estimate is None:
        await send_review_message(
            intro="The risk check needs a selected profile first. Please review the profile choice again."
        )
        return
    manual_band_choice = get_selected_band_choice()

    if is_continue_input(content):
        risk_trace = build_risk_reality_trace(
            estimate,
            user_action="continued_current_profile",
            revised_question_ids=[],
        )
        await finalize_review_submission(
            session_id,
            selected_band_id=(
                manual_band_choice["id"] if manual_band_choice is not None else None
            ),
            liquidity_policy_check=get_liquidity_policy_check(),
            risk_reality_check=risk_trace,
        )
        return

    await cl.Message(
        content=(
            "Type `yes` to generate the report after reviewing the volatility notice.\n\n"
            + render_risk_reality_prompt(estimate)
        )
    ).send()


async def handle_review_stage(session_id: str, content: str) -> None:
    """Handle commands while the chat is in review mode."""

    if content.strip().casefold() == "yes":
        await handle_review_submission(session_id)
        return

    band_choice = parse_band_target(content)
    if band_choice is not None:
        cl.user_session.set("selected_mock_profile_band", band_choice["id"])
        await send_review_message(
            intro=(
                f"Selected profile **{band_choice['order']}. {band_choice['label']}**. "
                "You can still change answers or choose a different profile before typing `yes`."
            )
        )
        return

    target_question = parse_change_target(content)
    if target_question is None:
        await cl.Message(
            content=(
                "I am in review mode right now.\n\n"
                "- Type `change <question number>` to update an answer.\n"
                "- Type `band <band number>` to choose a profile.\n"
                "- Type `yes` after a profile is selected."
            ),
        ).send()
        return

    cl.user_session.set("edit_target_question_id", target_question["id"])
    await send_next_question()


@cl.action_callback("review_select_band")
async def on_review_select_band(action: cl.Action) -> None:
    """Handle band selection from the interactive review element."""

    if cast(str | None, cl.user_session.get("workflow_stage")) != "review":
        await cl.Message(
            content="That review card is no longer the active step. Continue with the current prompt or type `/restart` to begin again.",
        ).send()
        return

    band_id = cast(str | None, action.payload.get("bandId"))
    if band_id is None:
        await cl.Message(content="I could not identify that profile option.").send()
        return

    band_choice = next((choice for choice in PROFILE_BAND_CHOICES if choice["id"] == band_id), None)
    if band_choice is None:
        await cl.Message(content="That profile option is not available right now.").send()
        return

    cl.user_session.set("selected_mock_profile_band", band_choice["id"])
    await send_review_message(
        intro=(
            f"Selected profile **{band_choice['order']}. {band_choice['label']}**. You can still change answers or choose a different profile before typing `yes`."
        )
    )


@cl.action_callback("review_edit_answer")
async def on_review_edit_answer(action: cl.Action) -> None:
    """Jump back to a specific question from the interactive review element."""

    if cast(str | None, cl.user_session.get("workflow_stage")) != "review":
        await cl.Message(
            content="The review controls are inactive right now. Finish the current question or type `/restart` to begin again.",
        ).send()
        return

    question_id = cast(str | None, action.payload.get("questionId"))
    if question_id not in QUESTIONS_BY_ID:
        await cl.Message(content="I could not find that question in the current questionnaire.").send()
        return

    cl.user_session.set("edit_target_question_id", question_id)
    await send_next_question()


@cl.action_callback("report_show_preview")
async def on_report_show_preview(_action: cl.Action) -> None:
    """Open a short report preview in the sidebar."""

    preview_markdown = cast(str | None, cl.user_session.get(REPORT_PREVIEW_SESSION_KEY))
    if not preview_markdown:
        await cl.Message(
            content="The report preview is not available yet. Generate a result first, then try again.",
        ).send()
        return

    session_id = get_session_id()
    if session_id is None:
        await send_missing_session_message()
        return

    cl.user_session.set(REPORT_PREVIEW_ACTIVE_SESSION_KEY, True)
    state = load_chat_state(session_id)
    await update_sidebar(
        state,
        stage="submitted",
        profile_text=cast(str | None, cl.user_session.get(SUBMITTED_PROFILE_TEXT_SESSION_KEY)),
    )


@cl.action_callback("restart_chat")
async def on_restart_chat(_action: cl.Action) -> None:
    """Start a fresh assessment from a custom element button."""

    await start_new_chat()


async def handle_questionnaire_stage(session_id: str, content: str) -> None:
    """Handle normal questionnaire answers and answer edits."""

    state = load_chat_state(session_id)
    if state.status == "submitted":
        await cl.Message(
            content="This run is already complete. Type `/restart` to begin a new one.",
        ).send()
        return

    edit_target_question_id = cast(str | None, cl.user_session.get("edit_target_question_id"))
    question = question_for_active_stage(
        state,
        edit_target_question_id=edit_target_question_id,
    )
    if question is None:
        await send_review_message()
        return

    if question.get("type") == "currency_amount":
        await handle_currency_question_entry(
            question,
            state,
            content=content,
            edit_target_question_id=edit_target_question_id,
        )
        return

    option = find_option(question, content)
    if option is None:
        await send_invalid_answer_feedback(
            question,
            state,
            edit_target_question_id=edit_target_question_id,
        )
        return

    updated_state = save_chat_answer(
        session_id=session_id,
        question_id=question["id"],
        option_id=option["id"],
    )
    await send_recorded_answer_feedback(
        question,
        option["label"],
        updated_state,
        edit_target_question_id=edit_target_question_id,
    )

    if edit_target_question_id is not None:
        cl.user_session.set("edit_target_question_id", None)
        await send_fresh_review_message_after_edit(
            intro="Updated. Here is the latest summary."
        )
        return

    await send_next_question()


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------


async def start_new_chat() -> None:
    """Reset the chat-side state and begin a fresh assessment run."""

    state = create_chat_session()
    reset_chat_runtime_state(state.session_id)
    await cl.Message(
        content=(
            "Welcome. I will guide you through a short investor profile assessment, "
            "keep a running summary on the right, and let you review everything "
            "before I generate your draft portfolio result.\n\n"
            "For multiple-choice questions, reply with the number or type the answer in full. "
            "For money amounts, I will ask you to review and type yes before saving. "
            "Type `/restart` any time to start over."
        ),
    ).send()
    await send_next_question()


def reset_chat_runtime_state(session_id: str) -> None:
    """Clear Chainlit runtime state that should not survive a new assessment."""

    cl.user_session.set("assessment_session_id", session_id)
    cl.user_session.set("current_question_id", None)
    cl.user_session.set("edit_target_question_id", None)
    cl.user_session.set("selected_mock_profile_band", None)
    cl.user_session.set(REPORT_PREVIEW_SESSION_KEY, None)
    cl.user_session.set(REPORT_PREVIEW_ACTIVE_SESSION_KEY, False)
    cl.user_session.set(SUBMITTED_PROFILE_TEXT_SESSION_KEY, None)
    set_risk_reality_estimate(None)
    set_liquidity_policy_check(None)
    set_review_element(None)
    clear_pending_numeric_answer()
    cl.user_session.set("workflow_stage", "questionnaire")


@cl.on_chat_start
async def on_chat_start() -> None:
    """Chainlit lifecycle hook fired when a new browser chat starts."""

    await start_new_chat()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Main conversation router for questionnaire, review, edit, and submit."""

    content = (message.content or "").strip()
    if not content:
        await cl.Message(content="Please send an answer or type `/restart`.").send()
        return

    if content.casefold() == "/restart":
        await start_new_chat()
        return

    session_id = get_session_id()
    if session_id is None:
        await start_new_chat()
        return

    workflow_stage = cast(str | None, cl.user_session.get("workflow_stage")) or "questionnaire"
    if workflow_stage == "review":
        await handle_review_stage(session_id, content)
        return
    if workflow_stage == "numeric_confirm":
        await handle_numeric_confirmation_stage(session_id, content)
        return
    if workflow_stage == "risk_reality_check":
        await handle_risk_reality_check_stage(session_id, content)
        return

    await handle_questionnaire_stage(session_id, content)

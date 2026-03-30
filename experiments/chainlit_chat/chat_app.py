"""Chainlit entrypoint for the exploratory SOC chat advisor.

This file is the conversation controller for the whole experiment.

High-level flow:

1. create a new assessment session in SQLite
2. ask one configured question at a time
3. save each answer immediately through the backend service layer
4. keep the sidebar synced with the saved session state
5. let the user review or edit answers
6. let the user choose a draft investor band
7. submit once complete, which triggers the Variant B allocation engine

Important separation of responsibilities:

- this file handles chat flow and UI behavior
- `soc_advisor.services` handles questionnaire/session logic
- `soc_advisor.portfolio` handles the actual allocation math
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import chainlit as cl


def find_project_root(start: Path) -> Path:
    """Find the repo root so this file can import backend modules reliably."""

    for candidate in (start, *start.parents):
        if (candidate / "backend" / "soc_advisor" / "__init__.py").exists():
            return candidate
    raise RuntimeError("Could not find the Team D project root.")


PROJECT_ROOT = find_project_root(Path(__file__).resolve())
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.chat_formatting import (  # noqa: E402
    format_edit_prompt,
    format_question,
    get_question_label,
    render_profile_summary,
    render_review_message,
    render_sidebar_content,
)
from soc_advisor.database import Base, SessionLocal, engine  # noqa: E402
from soc_advisor.portfolio import list_profile_bands  # noqa: E402
from soc_advisor.schemas import (  # noqa: E402
    AnswerSummary,
    ProfileSummary,
    RecommendationSummary,
    SessionStateResponse,
)
from soc_advisor.services import (  # noqa: E402
    build_session_state,
    create_assessment_session,
    get_session_or_404,
    is_question_active,
    load_questionnaire,
    submit_assessment,
    upsert_answer,
)
from soc_advisor.settings import get_settings  # noqa: E402


Base.metadata.create_all(bind=engine)
settings = get_settings()
QUESTIONNAIRE = load_questionnaire(settings.questionnaire_version)
ORDERED_QUESTIONS = sorted(QUESTIONNAIRE["questions"], key=lambda item: item["order"])
QUESTIONS_BY_ID = {question["id"]: question for question in ORDERED_QUESTIONS}
PROFILE_BAND_CHOICES = list_profile_bands(settings.portfolio_version)
PROFILE_BANDS_BY_ID = {choice["id"]: choice for choice in PROFILE_BAND_CHOICES}
QuestionDict = dict[str, Any]
OptionDict = dict[str, Any]

# Compact human labels used in the sidebar and confirmation copy.
QUESTION_LABELS = {
    "portfolio_purpose": "Purpose",
    "goal_time_horizon": "Horizon",
    "age_band": "Age",
    "income_stability": "Income stability",
    "investment_phase": "Investment phase",
    "major_expense_withdrawal": "Major expense need",
    "emergency_fund_months": "Emergency fund",
    "risk_willingness": "Risk willingness",
    "risky_asset_preference": "Risk preference",
    "financial_knowledge": "Knowledge",
    "investment_experience": "Experience",
    "stock_market_view": "Market view",
    "loss_response": "Loss response",
}
CHANGE_TARGET_ALIASES = {
    "purpose": "portfolio_purpose",
    "goal": "portfolio_purpose",
    "horizon": "goal_time_horizon",
    "age": "age_band",
    "income": "income_stability",
    "income stability": "income_stability",
    "phase": "investment_phase",
    "investment phase": "investment_phase",
    "liquidity": "major_expense_withdrawal",
    "major expense": "major_expense_withdrawal",
    "emergency fund": "emergency_fund_months",
    "reserves": "emergency_fund_months",
    "risk": "risk_willingness",
    "risk willingness": "risk_willingness",
    "preference": "risky_asset_preference",
    "risk preference": "risky_asset_preference",
    "knowledge": "financial_knowledge",
    "experience": "investment_experience",
    "market": "stock_market_view",
    "market view": "stock_market_view",
    "loss": "loss_response",
    "loss response": "loss_response",
}


def get_session_id() -> str | None:
    """Fetch the active assessment session id from Chainlit's user session."""

    return cast(str | None, cl.user_session.get("assessment_session_id"))


def get_selected_band_choice() -> dict[str, Any] | None:
    """Return the currently selected mock band from chat session state."""

    selected_band_id = cast(str | None, cl.user_session.get("selected_mock_profile_band"))
    if not selected_band_id:
        return None
    return PROFILE_BANDS_BY_ID.get(selected_band_id)


def answer_lookup_for_state(state: SessionStateResponse) -> dict[str, Any]:
    """Build a simple answer lookup used for dependency-aware question flow."""

    return {
        answer.question_id: SimpleNamespace(normalized_value=answer.option_id)
        for answer in state.answers
    }


def get_current_question(state: SessionStateResponse) -> QuestionDict | None:
    """Return the next unanswered active question for the current saved state."""

    saved_answers = answer_lookup_for_state(state)
    for question in ORDERED_QUESTIONS:
        if not is_question_active(question, saved_answers):
            continue
        if question["id"] not in saved_answers:
            return question
    return None


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
    option_id: str,
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
        )
        return build_session_state(updated_session, questionnaire)


def submit_chat_session(
    session_id: str,
    *,
    mock_profile_band: str | None,
) -> tuple[SessionStateResponse, ProfileSummary, RecommendationSummary]:
    """Submit the session, which triggers the portfolio generation flow."""

    with SessionLocal() as db:
        session = get_session_or_404(db, session_id)
        submitted_session, profile, recommendation = submit_assessment(
            db,
            session=session,
            mock_profile_band=mock_profile_band,
        )
        questionnaire = load_questionnaire(submitted_session.questionnaire_version)
        return build_session_state(submitted_session, questionnaire), profile, recommendation


async def update_sidebar(
    state: SessionStateResponse,
    *,
    stage: str,
    current_question: QuestionDict | None = None,
    profile_text: str | None = None,
) -> None:
    """Push a fresh sidebar summary whenever the workflow state changes."""

    selected_band_choice = get_selected_band_choice()
    key_parts = [
        state.session_id,
        stage,
        current_question["id"] if current_question is not None else "none",
        selected_band_choice["id"] if selected_band_choice is not None else "no-band",
        state.updated_at.isoformat(),
    ]
    await cl.ElementSidebar.set_title("Your summary")
    await cl.ElementSidebar.set_elements(
        [
            cl.Text(
                name="Your summary",
                content=render_sidebar_content(
                    state,
                    questions_by_id=QUESTIONS_BY_ID,
                    question_labels=QUESTION_LABELS,
                    stage=stage,
                    current_question=current_question,
                    profile_text=profile_text,
                    selected_band_text=(
                        selected_band_choice["label"]
                        if selected_band_choice is not None
                        else None
                    ),
                ),
            )
        ],
        key="|".join(key_parts),
    )


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


def current_answer_for_question(
    state: SessionStateResponse,
    question_id: str,
) -> AnswerSummary | None:
    """Return the currently saved answer for one question if it exists."""

    return next((answer for answer in state.answers if answer.question_id == question_id), None)


async def send_review_message(*, intro: str | None = None) -> None:
    """Show the review screen once all active questions are answered."""

    session_id = get_session_id()
    if session_id is None:
        await cl.Message(
            content="The saved chat session is missing. Type `/restart` to begin again.",
        ).send()
        return

    state = load_chat_state(session_id)
    selected_band_choice = get_selected_band_choice()
    cl.user_session.set("workflow_stage", "review")
    cl.user_session.set("edit_target_question_id", None)
    await update_sidebar(state, stage="review")
    message_intro = intro or "I have what I need for now."
    review_body = render_review_message(
        state,
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        profile_bands=PROFILE_BAND_CHOICES,
        selected_band_id=(
            selected_band_choice["id"] if selected_band_choice is not None else None
        ),
    )
    await cl.Message(
        content=(
            f"{message_intro}\n\n"
            f"{review_body}"
        )
    ).send()


async def send_next_question() -> None:
    """Advance the chat to the next question, edit prompt, or review screen."""

    session_id = get_session_id()
    if session_id is None:
        await cl.Message(
            content="The saved chat session is missing. Type `/restart` to begin again.",
        ).send()
        return

    state = load_chat_state(session_id)
    edit_target_question_id = cast(str | None, cl.user_session.get("edit_target_question_id"))
    if edit_target_question_id:
        question = QUESTIONS_BY_ID[edit_target_question_id]
        current_answer = current_answer_for_question(state, edit_target_question_id)
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
        return

    question = get_current_question(state)
    if question is None:
        await send_review_message()
        return

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


async def start_new_chat() -> None:
    """Reset the chat-side state and begin a fresh assessment run."""

    state = create_chat_session()
    cl.user_session.set("assessment_session_id", state.session_id)
    cl.user_session.set("current_question_id", None)
    cl.user_session.set("edit_target_question_id", None)
    cl.user_session.set("selected_mock_profile_band", None)
    cl.user_session.set("workflow_stage", "questionnaire")
    await cl.Message(
        content=(
            "Welcome. I will guide you through the current investor profile questionnaire, "
            "keep a running summary on the right, and let you review everything "
            "before you choose a draft investor band and I generate a Variant B result.\n\n"
            "You can answer with the option number, the option id, or the full option text. "
            "Type `/restart` any time to begin again."
        )
    ).send()
    await send_next_question()


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
        if content.casefold() == "confirm":
            selected_band_choice = get_selected_band_choice()
            if selected_band_choice is None:
                await cl.Message(
                    content=(
                        "Choose a draft investor band before confirming. "
                        "Type `band 1`, `band 2`, `band 3`, `band 4`, or `band 5`."
                    ),
                ).send()
                return

            state, profile, recommendation = submit_chat_session(
                session_id,
                mock_profile_band=selected_band_choice["id"],
            )
            await update_sidebar(
                state,
                stage="submitted",
                profile_text=(
                    f"**{profile.profile_label}**  \n"
                    + (
                        f"Score: {profile.profile_score:.1f}"
                        if profile.profile_score is not None
                        else "Source: manual mock band"
                    )
                ),
            )
            await cl.Message(content=render_profile_summary(state, profile, recommendation)).send()
            return

        band_choice = parse_band_target(content)
        if band_choice is not None:
            cl.user_session.set("selected_mock_profile_band", band_choice["id"])
            await send_review_message(
                intro=(
                    f"Selected draft band **{band_choice['order']}. {band_choice['label']}**. "
                    "You can still change answers or choose a different band before `confirm`."
                )
            )
            return

        target_question = parse_change_target(content)
        if target_question is None:
            await cl.Message(
                content=(
                    "I am in review mode right now.\n\n"
                    "- Type `change <question number>` to update an answer.\n"
                    "- Type `band <band number>` to choose a draft investor band.\n"
                    "- Type `confirm` after a band is selected."
                ),
            ).send()
            return

        cl.user_session.set("edit_target_question_id", target_question["id"])
        await send_next_question()
        return

    state = load_chat_state(session_id)
    if state.status == "submitted":
        await cl.Message(
            content="This run is already complete. Type `/restart` to begin a new one.",
        ).send()
        return

    edit_target_question_id = cast(str | None, cl.user_session.get("edit_target_question_id"))
    question = (
        QUESTIONS_BY_ID[edit_target_question_id]
        if edit_target_question_id is not None
        else get_current_question(state)
    )
    if question is None:
        await send_review_message()
        return

    option = find_option(question, content)
    if option is None:
        await cl.Message(
            content=(
                "I could not match that answer yet. Reply with the option number, "
                "the option id, or the full option text exactly as shown."
            ),
        ).send()
        if edit_target_question_id is not None:
            current_answer = current_answer_for_question(state, edit_target_question_id)
            current_label = (
                current_answer.answer_label
                if current_answer is not None
                else "No answer recorded yet"
            )
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
        else:
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
        return

    updated_state = save_chat_answer(
        session_id=session_id,
        question_id=question["id"],
        option_id=option["id"],
    )
    await update_sidebar(
        updated_state,
        stage="editing" if edit_target_question_id is not None else "questionnaire",
        current_question=question,
    )
    await cl.Message(
        content=(
            f"Got it. I recorded question **{question['order']}** "
            f"(**{get_question_label(question['id'], questions_by_id=QUESTIONS_BY_ID, question_labels=QUESTION_LABELS)}**) as "
            f"**{option['label']}**.\n\n"
            "The summary on the right has been updated."
        ),
    ).send()

    if edit_target_question_id is not None:
        cl.user_session.set("edit_target_question_id", None)
        await send_review_message(intro="Updated. Here is the latest summary.")
        return

    await send_next_question()

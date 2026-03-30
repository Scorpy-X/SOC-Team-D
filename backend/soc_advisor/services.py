"""Core service helpers for questionnaire loading, validation, and scoring.

Think of this module as the business-logic layer for the assessment flow.

It sits between:

- the UI/API entrypoints
- the database
- the portfolio engine

Responsibilities:

- load questionnaire and scoring configs
- validate submitted answers
- track which questions are still missing
- score completed questionnaires into a profile band
- pass the finished profile to the portfolio engine
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import AssessmentAnswer, AssessmentSession, utc_now
from .portfolio import build_recommendation, load_portfolio_config
from .schemas import (
    AnswerSummary,
    ProfileSummary,
    RecommendationSummary,
    SessionStateResponse,
)
from .settings import get_settings


settings = get_settings()
MANUAL_MOCK_PROFILE_SOURCE = "manual_mock_band"
SCORED_QUESTIONNAIRE_PROFILE_SOURCE = "scored_questionnaire"


@lru_cache(maxsize=8)
def load_questionnaire(version: str) -> dict[str, Any]:
    """Load one questionnaire JSON file by version."""

    path = settings.questionnaire_dir / f"{version}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Questionnaire version '{version}' was not found.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=8)
def load_scoring(version: str) -> dict[str, Any]:
    """Load one scoring JSON file by version."""

    path = settings.scoring_dir / f"{version}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Scoring version '{version}' was not found.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _question_lookup(questionnaire: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index questionnaire entries by question id for quick lookups."""

    return {question["id"]: question for question in questionnaire["questions"]}


def _option_lookup(questionnaire: dict[str, Any], question_id: str) -> dict[str, dict[str, Any]]:
    """Index one question's options by option id."""

    question = _question_lookup(questionnaire).get(question_id)
    if question is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown question_id '{question_id}'.",
        )
    return {option["id"]: option for option in question["options"]}


def ensure_valid_answer(
    questionnaire: dict[str, Any],
    *,
    question_id: str,
    option_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate that a submitted answer matches the questionnaire config."""

    question = _question_lookup(questionnaire).get(question_id)
    if question is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown question_id '{question_id}'.",
        )

    option = _option_lookup(questionnaire, question_id).get(option_id)
    if option is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown option_id '{option_id}' for question '{question_id}'.",
        )

    return question, option


def answers_by_question(session: AssessmentSession) -> dict[str, AssessmentAnswer]:
    """Return ORM answers keyed by question id."""

    return {answer.question_id: answer for answer in session.answers}


def is_question_active(
    question: dict[str, Any],
    answers_lookup: dict[str, AssessmentAnswer],
) -> bool:
    """Evaluate a simple dependency rule if the question has one."""

    depends_on = question.get("depends_on")
    if not depends_on:
        return True

    parent_answer = answers_lookup.get(depends_on["question_id"])
    if parent_answer is None:
        return False

    return parent_answer.normalized_value in depends_on["option_ids"]


def get_missing_question_ids(
    questionnaire: dict[str, Any],
    session: AssessmentSession,
) -> list[str]:
    """Return required questions that are still unanswered."""

    answers_lookup = answers_by_question(session)
    missing_question_ids: list[str] = []

    for question in sorted(questionnaire["questions"], key=lambda item: item["order"]):
        if not is_question_active(question, answers_lookup):
            continue
        if not question.get("required", True):
            continue
        if question["id"] not in answers_lookup:
            missing_question_ids.append(question["id"])

    return missing_question_ids


def build_answer_summaries(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
) -> list[AnswerSummary]:
    """Convert ORM answers into API-friendly summary objects."""

    order_map = {
        question["id"]: question["order"] for question in questionnaire["questions"]
    }

    return [
        AnswerSummary(
            question_id=answer.question_id,
            question_text=answer.question_text_snapshot,
            dimension=answer.dimension_snapshot,
            option_id=answer.normalized_value,
            answer_label=answer.answer_label_snapshot,
        )
        for answer in sorted(
            session.answers,
            key=lambda item: order_map.get(item.question_id, 999),
        )
    ]


def create_assessment_session(
    db: Session,
    *,
    questionnaire_version: str | None = None,
    scoring_version: str | None = None,
) -> AssessmentSession:
    """Create and persist a fresh assessment session."""

    resolved_questionnaire_version = questionnaire_version or settings.questionnaire_version
    resolved_scoring_version = scoring_version or settings.scoring_version

    load_questionnaire(resolved_questionnaire_version)
    load_scoring(resolved_scoring_version)

    session = AssessmentSession(
        id=str(uuid4()),
        questionnaire_version=resolved_questionnaire_version,
        scoring_version=resolved_scoring_version,
        status="draft",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def upsert_answer(
    db: Session,
    *,
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    question_id: str,
    option_id: str,
) -> AssessmentSession:
    """Insert or update one answer inside a session."""

    question, option = ensure_valid_answer(
        questionnaire,
        question_id=question_id,
        option_id=option_id,
    )

    existing_answer = next(
        (answer for answer in session.answers if answer.question_id == question_id),
        None,
    )

    if existing_answer is None:
        session.answers.append(
            AssessmentAnswer(
                question_id=question_id,
                dimension_snapshot=question["dimension"],
                question_text_snapshot=question["text"],
                raw_value=option["label"],
                normalized_value=option["id"],
                answer_label_snapshot=option["label"],
            )
        )
    else:
        existing_answer.dimension_snapshot = question["dimension"]
        existing_answer.question_text_snapshot = question["text"]
        existing_answer.raw_value = option["label"]
        existing_answer.normalized_value = option["id"]
        existing_answer.answer_label_snapshot = option["label"]
        existing_answer.updated_at = utc_now()

    session.status = "draft"
    session.profile_band = None
    session.profile_score = None
    session.result_json = None
    session.submitted_at = None
    session.updated_at = utc_now()

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_or_404(db: Session, session_id: str) -> AssessmentSession:
    """Fetch one session or fail with a 404."""

    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' was not found.",
        )
    return session


def build_session_state(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
) -> SessionStateResponse:
    """Build the shared session response body."""

    missing_question_ids = get_missing_question_ids(questionnaire, session)

    return SessionStateResponse(
        session_id=session.id,
        questionnaire_version=session.questionnaire_version,
        scoring_version=session.scoring_version,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        submitted_at=session.submitted_at,
        answers=build_answer_summaries(session, questionnaire),
        missing_question_ids=missing_question_ids,
        can_submit=not missing_question_ids,
    )


def _ensure_session_complete(
    questionnaire: dict[str, Any],
    session: AssessmentSession,
) -> None:
    """Fail clearly if the questionnaire is still incomplete."""

    missing_question_ids = get_missing_question_ids(questionnaire, session)
    if missing_question_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Cannot submit the session until all required questions are answered.",
                "missing_question_ids": missing_question_ids,
            },
        )


def _band_for_score(scoring: dict[str, Any], score: float) -> dict[str, Any]:
    """Pick the configured profile band whose score range matches the total."""

    for band in scoring["profile_bands"]:
        if band["min_score"] <= score <= band["max_score"]:
            return band

    raise HTTPException(
        status_code=500,
        detail="No profile band matched the computed score. Check scoring config.",
    )


def _build_reasons(
    scoring: dict[str, Any],
    answers_lookup: dict[str, AssessmentAnswer],
) -> list[str]:
    """Build explanation reasons from the configured reason rules."""

    reasons: list[str] = []

    for rule in scoring.get("reason_rules", []):
        answer = answers_lookup.get(rule["question_id"])
        if answer is None:
            continue
        if answer.normalized_value in rule["option_ids"]:
            reasons.append(rule["text"])

    return reasons


def score_session(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    scoring: dict[str, Any],
) -> ProfileSummary:
    """Compute a provisional profile result from the saved answers.

    Design choice:

    - scoring is config-driven, not hardcoded in the chat layer
    - each active question contributes a score based on the selected option id
    - the total score is then mapped into one configured investor band
    """

    _ensure_session_complete(questionnaire, session)

    answers_lookup = answers_by_question(session)
    dimension_scores: dict[str, float] = {}
    total_score = 0.0

    for question in questionnaire["questions"]:
        if not is_question_active(question, answers_lookup):
            continue

        answer = answers_lookup[question["id"]]
        score_map = scoring["question_scores"].get(question["id"])
        if score_map is None:
            raise HTTPException(
                status_code=500,
                detail=f"Missing score map for question '{question['id']}'.",
            )

        answer_score = score_map.get(answer.normalized_value)
        if answer_score is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Missing score for option '{answer.normalized_value}' "
                    f"on question '{question['id']}'."
                ),
            )

        total_score += float(answer_score)
        # Dimension scores are currently a lightweight record keyed by the
        # question dimension. They are useful for debugging and explanation,
        # even though this is not yet a richer weighted sub-score model.
        dimension_scores[question["dimension"]] = float(answer_score)

    band = _band_for_score(scoring, total_score)
    reasons = _build_reasons(scoring, answers_lookup)

    if not reasons:
        reasons.append(
            "This provisional profile was generated from the structured questionnaire answers."
        )

    return ProfileSummary(
        profile_band=band["id"],
        profile_label=band["label"],
        profile_score=total_score,
        profile_source=SCORED_QUESTIONNAIRE_PROFILE_SOURCE,
        profile_description=band["description"],
        dimension_scores=dimension_scores,
        reasons=reasons,
    )


def build_manual_mock_profile(
    *,
    profile_band: str,
    portfolio_version: str | None = None,
) -> ProfileSummary:
    """Build a mock profile directly from the configured Variant B bands."""

    resolved_version = portfolio_version or settings.portfolio_version
    portfolio_config = load_portfolio_config(resolved_version)

    try:
        band = portfolio_config["bands"][profile_band]
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown mock_profile_band '{profile_band}'. "
                "Use one of the configured Variant B band ids."
            ),
        ) from exc

    label = str(band.get("label", profile_band.replace("_", " ").title()))
    description = str(
        band.get(
            "description",
            "This mock band uses the active Variant B class-range policy.",
        )
    )

    return ProfileSummary(
        profile_band=profile_band,
        profile_label=label,
        profile_score=None,
        profile_source=MANUAL_MOCK_PROFILE_SOURCE,
        profile_description=description,
        dimension_scores={},
        reasons=[
            (
                f"This run used the manually selected {label} band because the "
                "question-to-band pipeline is not final yet."
            ),
            (
                "The questionnaire answers were still captured and reviewable, "
                "but they did not decide the band in this demo path."
            ),
        ],
    )


def save_submission_result(
    db: Session,
    *,
    session: AssessmentSession,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
) -> AssessmentSession:
    """Persist the computed profile and recommendation onto the session.

    The result is stored as JSON so both the API and the Chainlit experiment can
    read back the same saved recommendation after submission.
    """

    session.status = "submitted"
    session.profile_band = profile.profile_band
    session.profile_score = profile.profile_score
    session.result_json = json.dumps(
        {
            "profile": profile.model_dump(),
            "recommendation": recommendation.model_dump(),
        }
    )
    session.submitted_at = utc_now()
    session.updated_at = utc_now()

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_saved_recommendation(session: AssessmentSession) -> RecommendationSummary:
    """Return the persisted recommendation for a submitted session."""

    if not session.result_json:
        raise HTTPException(
            status_code=409,
            detail="This session does not have a saved recommendation yet.",
        )

    payload = json.loads(session.result_json)
    recommendation_payload = payload.get("recommendation")
    if recommendation_payload is None:
        raise HTTPException(
            status_code=500,
            detail="The saved session result is missing the recommendation payload.",
        )
    return RecommendationSummary.model_validate(recommendation_payload)


def get_saved_profile(session: AssessmentSession) -> ProfileSummary:
    """Return the persisted profile for a submitted session."""

    if not session.result_json:
        raise HTTPException(
            status_code=409,
            detail="This session does not have a saved profile yet.",
        )

    payload = json.loads(session.result_json)
    profile_payload = payload.get("profile")
    if profile_payload is None:
        raise HTTPException(
            status_code=500,
            detail="The saved session result is missing the profile payload.",
        )
    return ProfileSummary.model_validate(profile_payload)


def submit_assessment(
    db: Session,
    *,
    session: AssessmentSession,
    mock_profile_band: str | None = None,
) -> tuple[AssessmentSession, ProfileSummary, RecommendationSummary]:
    """Score the saved answers, build a recommendation, and persist both.

    This is the main "finish the assessment" entrypoint used by both:

    - the FastAPI submit route
    - the Chainlit chat review/confirm step
    """

    questionnaire = load_questionnaire(session.questionnaire_version)
    _ensure_session_complete(questionnaire, session)

    if mock_profile_band:
        profile = build_manual_mock_profile(profile_band=mock_profile_band)
    else:
        scoring = load_scoring(session.scoring_version)
        profile = score_session(session, questionnaire, scoring)

    recommendation = build_recommendation(profile=profile)
    saved_session = save_submission_result(
        db,
        session=session,
        profile=profile,
        recommendation=recommendation,
    )
    return saved_session, profile, recommendation

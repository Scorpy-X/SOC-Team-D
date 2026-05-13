"""Core service helpers for questionnaire loading, validation, and scoring.

This module is the business-logic layer for the advisor flow.

It sits between:

- the UI/API entrypoints
- the database models
- the portfolio engine

Responsibilities:

- load questionnaire and scoring configs
- validate submitted answers
- track which questions are still missing
- choose a profile through either the manual-band path or the scored fallback
- pass the finished profile to the portfolio engine
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import AssessmentAnswer, AssessmentSession, utc_now
from .liquidity_policy import (
    LIQUIDITY_QUESTION_IDS,
    build_liquidity_policy_check,
)
from .portfolio import (
    build_recommendation,
    get_active_portfolio_data_source,
    load_portfolio_config,
)
from .schemas import (
    AnswerSummary,
    CapturedAnswerTrace,
    DecisionTrace,
    LiquidityPolicyCheckTrace,
    ProfileSummary,
    RecommendationSummary,
    RiskRealityCheckTrace,
    ScoringPolicyTrace,
    SessionStateResponse,
)
from .settings import get_settings
from .typed_answers import normalize_currency_amount


settings = get_settings()
MANUAL_MOCK_PROFILE_SOURCE = "manual_mock_band"
SCORED_QUESTIONNAIRE_PROFILE_SOURCE = "scored_questionnaire"
LIQUIDITY_ADJUSTED_QUESTIONNAIRE_PROFILE_SOURCE = "liquidity_adjusted_questionnaire"
LIQUIDITY_ADJUSTED_MANUAL_PROFILE_SOURCE = "liquidity_adjusted_manual_profile"


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Questionnaire lookups and validation
# ---------------------------------------------------------------------------


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


def _question_type(question: dict[str, Any]) -> str:
    """Return the configured question type, defaulting old configs safely."""

    return str(question.get("type", "single_choice"))


def _resolve_submitted_answer(
    questionnaire: dict[str, Any],
    *,
    question_id: str,
    option_id: str | None,
    numeric_value: float | None,
) -> tuple[dict[str, Any], str | None, str, str, str]:
    """Validate one submitted answer and return the persisted answer payload.

    Returns:

    - question definition
    - option id if this is a single-choice answer
    - raw value snapshot
    - normalized value snapshot
    - human-readable answer label snapshot
    """

    question = _question_lookup(questionnaire).get(question_id)
    if question is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown question_id '{question_id}'.",
        )

    question_type = _question_type(question)
    if question_type == "single_choice":
        if option_id is None or numeric_value is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Question '{question_id}' expects an option_id and does not accept numeric_value."
                ),
            )

        _, option = ensure_valid_answer(
            questionnaire,
            question_id=question_id,
            option_id=option_id,
        )
        return (
            question,
            option["id"],
            option["label"],
            option["id"],
            option["label"],
        )

    if question_type == "currency_amount":
        if option_id is not None or numeric_value is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Question '{question_id}' expects numeric_value and does not accept option_id."
                ),
            )

        try:
            normalized_value, _, display_value = normalize_currency_amount(
                numeric_value,
                question_id=question_id,
                validation=question.get("validation"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return (
            question,
            None,
            display_value,
            normalized_value,
            display_value,
        )

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported question type '{question_type}' for question '{question_id}'.",
    )


# ---------------------------------------------------------------------------
# Answer lookup helpers
# ---------------------------------------------------------------------------


def _normalized_answer_value(answer: Any) -> str | None:
    """Extract one normalized answer id from several lightweight answer shapes.

    Why this helper exists:

    - the database layer uses ``AssessmentAnswer.normalized_value``
    - API summaries use ``AnswerSummary.option_id``
    - the chat flow only needs plain ``question_id -> option_id`` lookups

    Normalizing those cases here keeps the rest of the dependency logic simple
    and removes the need for placeholder wrapper objects in the chat layer.
    """

    if answer is None:
        return None
    if isinstance(answer, str):
        return answer
    if isinstance(answer, Mapping):
        for key in ("normalized_value", "option_id"):
            value = answer.get(key)
            if isinstance(value, str):
                return value

    for attribute in ("normalized_value", "option_id"):
        value = getattr(answer, attribute, None)
        if isinstance(value, str):
            return value

    return None


def answers_by_question(session: AssessmentSession) -> dict[str, AssessmentAnswer]:
    """Return ORM answers keyed by question id."""

    return {answer.question_id: answer for answer in session.answers}


def is_question_active(
    question: dict[str, Any],
    answers_lookup: Mapping[str, Any],
) -> bool:
    """Evaluate a simple dependency rule if the question has one."""

    depends_on = question.get("depends_on")
    if not depends_on:
        return True

    parent_value = _normalized_answer_value(answers_lookup.get(depends_on["question_id"]))
    if parent_value is None:
        return False

    return parent_value in depends_on["option_ids"]


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
    type_map = {
        question["id"]: _question_type(question) for question in questionnaire["questions"]
    }

    return [
        AnswerSummary(
            question_id=answer.question_id,
            question_text=answer.question_text_snapshot,
            dimension=answer.dimension_snapshot,
            answer_type=type_map.get(answer.question_id, "single_choice"),
            option_id=(
                answer.normalized_value
                if type_map.get(answer.question_id, "single_choice") == "single_choice"
                else None
            ),
            answer_label=answer.answer_label_snapshot,
        )
        for answer in sorted(
            session.answers,
            key=lambda item: order_map.get(item.question_id, 999),
        )
    ]


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


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
    option_id: str | None = None,
    numeric_value: float | None = None,
) -> AssessmentSession:
    """Insert or update one answer inside a session."""

    question, _resolved_option_id, raw_value, normalized_value, answer_label = _resolve_submitted_answer(
        questionnaire,
        question_id=question_id,
        option_id=option_id,
        numeric_value=numeric_value,
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
                raw_value=raw_value,
                normalized_value=normalized_value,
                answer_label_snapshot=answer_label,
            )
        )
    else:
        existing_answer.dimension_snapshot = question["dimension"]
        existing_answer.question_text_snapshot = question["text"]
        existing_answer.raw_value = raw_value
        existing_answer.normalized_value = normalized_value
        existing_answer.answer_label_snapshot = answer_label
        existing_answer.updated_at = utc_now()

    # Any answer change invalidates the previous submitted result so the next
    # submit starts from the refreshed questionnaire state.
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


# ---------------------------------------------------------------------------
# Profile selection and scoring
# ---------------------------------------------------------------------------


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

    profile_bands = scoring["profile_bands"]
    weighted_method = scoring.get("method") == "weighted_normalized_sections"
    for index, band in enumerate(profile_bands):
        min_score = float(band["min_score"])
        max_score = float(band["max_score"])
        is_last_band = index == len(profile_bands) - 1
        if weighted_method:
            if min_score <= score < max_score or (is_last_band and score <= max_score):
                return band
            continue
        if min_score <= score <= max_score:
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


def _profile_band_index(scoring: dict[str, Any], profile_band: str) -> int:
    """Return the configured order index for one profile id."""

    for index, band in enumerate(scoring["profile_bands"]):
        if band["id"] == profile_band:
            return index
    raise HTTPException(
        status_code=500,
        detail=f"Profile band '{profile_band}' is missing from scoring config.",
    )


def _band_by_id(scoring: dict[str, Any], profile_band: str) -> dict[str, Any]:
    """Return one configured scoring band by id."""

    for band in scoring["profile_bands"]:
        if band["id"] == profile_band:
            return band
    raise HTTPException(
        status_code=500,
        detail=f"Profile band '{profile_band}' is missing from scoring config.",
    )


def _build_weighted_scoring_trace(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    scoring: dict[str, Any],
) -> ScoringPolicyTrace:
    """Calculate the DOCX-style weighted normalized profile trace."""

    _ensure_session_complete(questionnaire, session)
    answers_lookup = answers_by_question(session)
    question_scores: dict[str, float] = {}
    section_scores: dict[str, float] = {}

    for section_id, section_config in scoring["sections"].items():
        weighted_sum = 0.0
        total_weight = 0.0
        for question_id, raw_weight in section_config["questions"].items():
            question = _question_lookup(questionnaire).get(question_id)
            answer = answers_lookup.get(question_id)
            if question is None or answer is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Scoring section '{section_id}' references unanswered or unknown question '{question_id}'.",
                )
            if not is_question_active(question, answers_lookup):
                continue

            score_map = scoring["question_scores"].get(question_id)
            if score_map is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Missing score map for question '{question_id}'.",
                )
            answer_score = score_map.get(answer.normalized_value)
            if answer_score is None:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Missing score for option '{answer.normalized_value}' "
                        f"on question '{question_id}'."
                    ),
                )

            weight = float(raw_weight)
            normalized_score = float(answer_score)
            question_scores[question_id] = normalized_score
            weighted_sum += normalized_score * weight
            total_weight += weight

        if total_weight <= 0:
            raise HTTPException(
                status_code=500,
                detail=f"Scoring section '{section_id}' has no positive question weights.",
            )
        section_scores[section_id] = weighted_sum / total_weight

    section_weights = scoring["section_weights"]
    final_score_before_caps = 0.0
    total_section_weight = 0.0
    for section_id, raw_weight in section_weights.items():
        if section_id not in section_scores:
            raise HTTPException(
                status_code=500,
                detail=f"Missing section score for '{section_id}'.",
            )
        weight = float(raw_weight)
        final_score_before_caps += section_scores[section_id] * weight
        total_section_weight += weight

    if total_section_weight <= 0:
        raise HTTPException(
            status_code=500,
            detail="Weighted scoring config has no positive section weights.",
        )
    final_score_before_caps = final_score_before_caps / total_section_weight
    draft_band = _band_for_score(scoring, final_score_before_caps)
    final_band = draft_band
    final_score_after_caps = final_score_before_caps
    applied_caps: list[str] = []

    for rule in scoring.get("cap_rules", []):
        answer = answers_lookup.get(rule["question_id"])
        if answer is None or answer.normalized_value not in rule["option_ids"]:
            continue

        max_band = _band_by_id(scoring, rule["max_profile_band"])
        if _profile_band_index(scoring, final_band["id"]) > _profile_band_index(
            scoring,
            max_band["id"],
        ):
            final_band = max_band
            # Keep the public score consistent with the capped profile while
            # preserving the uncapped value in final_score_before_caps.
            final_score_after_caps = min(
                final_score_after_caps,
                float(max_band["max_score"]) - 1e-9,
            )
            applied_caps.append(str(rule.get("text", rule["id"])))

    return ScoringPolicyTrace(
        method=str(scoring.get("method", "weighted_normalized_sections")),
        capacity_score=section_scores.get("risk_capacity"),
        tolerance_score=section_scores.get("risk_tolerance"),
        final_score_before_caps=final_score_before_caps,
        final_score_after_caps=final_score_after_caps,
        draft_profile_band=draft_band["id"],
        draft_profile_label=draft_band["label"],
        final_profile_band=final_band["id"],
        final_profile_label=final_band["label"],
        applied_caps=applied_caps,
        section_scores=section_scores,
        question_scores=question_scores,
    )


def build_scoring_policy_trace(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    scoring: dict[str, Any],
    *,
    profile: ProfileSummary | None = None,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
) -> ScoringPolicyTrace | None:
    """Return the internal scoring trace when the scoring config supports it."""

    if scoring.get("method") != "weighted_normalized_sections":
        return None

    trace = _build_weighted_scoring_trace(session, questionnaire, scoring)
    if profile is None:
        return trace

    manual_override_used = profile.profile_source in {
        MANUAL_MOCK_PROFILE_SOURCE,
        LIQUIDITY_ADJUSTED_MANUAL_PROFILE_SOURCE,
    }
    manual_override_band = profile.profile_band if manual_override_used else None
    manual_override_label = profile.profile_label if manual_override_used else None

    # If liquidity later downgrades a manual override, keep the originally
    # chosen profile in the scoring trace so the explanation chain stays true.
    if (
        manual_override_used
        and profile.profile_source == LIQUIDITY_ADJUSTED_MANUAL_PROFILE_SOURCE
        and liquidity_policy_check is not None
    ):
        manual_override_band = liquidity_policy_check.selected_profile_band
        manual_override_label = liquidity_policy_check.selected_profile_label

    return trace.model_copy(
        update={
            "manual_override_used": manual_override_used,
            "manual_override_band": manual_override_band,
            "manual_override_label": manual_override_label,
        }
    )


def _score_session_additive(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    scoring: dict[str, Any],
) -> ProfileSummary:
    """Compute the legacy additive score used by older scoring configs."""

    _ensure_session_complete(questionnaire, session)

    answers_lookup = answers_by_question(session)
    dimension_scores: dict[str, float] = {}
    total_score = 0.0

    for question in questionnaire["questions"]:
        if not is_question_active(question, answers_lookup):
            continue
        if not question.get("used_for_scoring", True):
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
        # This is still a lightweight dimension record rather than a richer
        # weighted sub-score model. It remains useful for debugging and future
        # explanation work, so the compatibility path keeps it.
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


def _score_session_weighted(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    scoring: dict[str, Any],
) -> ProfileSummary:
    """Compute the DOCX-aligned weighted normalized profile."""

    trace = _build_weighted_scoring_trace(session, questionnaire, scoring)
    band = _band_by_id(scoring, trace.final_profile_band)
    reasons = _build_reasons(scoring, answers_by_question(session))
    if trace.applied_caps:
        reasons.extend(trace.applied_caps)
    if not reasons:
        reasons.append(
            "This profile was calculated from the weighted risk-capacity and risk-tolerance questionnaire scores."
        )

    return ProfileSummary(
        profile_band=band["id"],
        profile_label=band["label"],
        profile_score=trace.final_score_after_caps,
        profile_source=SCORED_QUESTIONNAIRE_PROFILE_SOURCE,
        profile_description=band["description"],
        dimension_scores={
            "risk_capacity": trace.capacity_score or 0.0,
            "risk_tolerance": trace.tolerance_score or 0.0,
            "final_score_before_caps": trace.final_score_before_caps,
            "final_score_after_caps": trace.final_score_after_caps,
        },
        reasons=reasons,
    )


def score_session(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    scoring: dict[str, Any],
) -> ProfileSummary:
    """Compute a provisional profile result from the saved answers."""

    if scoring.get("method") == "weighted_normalized_sections":
        return _score_session_weighted(session, questionnaire, scoring)
    return _score_session_additive(session, questionnaire, scoring)


def build_manual_mock_profile(
    *,
    profile_band: str,
    portfolio_version: str | None = None,
) -> ProfileSummary:
    """Build a mock profile directly from the configured Variant B bands."""

    return _build_profile_from_portfolio_band(
        profile_band=profile_band,
        profile_source=MANUAL_MOCK_PROFILE_SOURCE,
        profile_score=None,
        dimension_scores={},
        reasons=None,
        portfolio_version=portfolio_version,
    )


def _build_profile_from_portfolio_band(
    *,
    profile_band: str,
    profile_source: str,
    profile_score: float | None,
    dimension_scores: dict[str, float],
    reasons: list[str] | None,
    portfolio_version: str | None = None,
) -> ProfileSummary:
    """Build a profile summary from the active portfolio band config."""

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
        profile_score=profile_score,
        profile_source=profile_source,
        profile_description=description,
        dimension_scores=dimension_scores,
        reasons=reasons
        or [
            f"This run used the {label} profile selected during advisor review.",
        ],
    )


def build_liquidity_adjusted_profile(
    *,
    original_profile: ProfileSummary,
    effective_profile_band: str,
) -> ProfileSummary:
    """Build the final profile after the liquidity policy changes the profile."""

    source = (
        LIQUIDITY_ADJUSTED_MANUAL_PROFILE_SOURCE
        if original_profile.profile_source == MANUAL_MOCK_PROFILE_SOURCE
        else LIQUIDITY_ADJUSTED_QUESTIONNAIRE_PROFILE_SOURCE
    )
    adjusted = _build_profile_from_portfolio_band(
        profile_band=effective_profile_band,
        profile_source=source,
        profile_score=original_profile.profile_score,
        dimension_scores=original_profile.dimension_scores,
        reasons=[
            (
                f"The questionnaire first indicated {original_profile.profile_label}, "
                "but the liquidity check required a safer compatible profile."
            ),
        ],
    )
    return adjusted


def _select_profile_for_submission(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    *,
    mock_profile_band: str | None,
) -> ProfileSummary:
    """Choose the active profile path for one submission.

    Active story:

    - if the advisor/user explicitly overrode the calculated profile, use the
      selected band

    Compatibility story:

    - if no override was supplied, calculate the profile from the questionnaire
    """

    if mock_profile_band:
        return build_manual_mock_profile(profile_band=mock_profile_band)

    scoring = load_scoring(session.scoring_version)
    return score_session(session, questionnaire, scoring)


def build_liquidity_check_for_profile(
    session: AssessmentSession,
    *,
    profile_band: str,
    user_action: str,
    portfolio_version: str | None = None,
) -> LiquidityPolicyCheckTrace:
    """Calculate the liquidity/profile compatibility trace for one session."""

    resolved_version = portfolio_version or settings.portfolio_version
    portfolio_config = load_portfolio_config(resolved_version)
    try:
        return build_liquidity_policy_check(
            answers=session.answers,
            selected_profile_band=profile_band,
            portfolio_config=portfolio_config,
            user_action=user_action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _liquidity_rejection_detail(check: LiquidityPolicyCheckTrace) -> dict[str, Any]:
    """Return a structured 400 detail when no configured profile can fit liquidity."""

    message = (
        "The liquidity need is higher than every configured profile's Cash ceiling. "
        "Revise the liquidity answers or reduce the investable amount before submitting."
    )

    return {
        "message": message,
        "selected_profile_band": check.selected_profile_band,
        "selected_profile_label": check.selected_profile_label,
        "suggested_profile_band": check.effective_profile_band,
        "suggested_profile_label": check.effective_profile_label,
        "required_liquidity_amount": check.required_liquidity_amount,
        "liquidity_floor": check.liquidity_floor,
        "selected_cash_ceiling": check.selected_cash_ceiling,
        "user_action": "blocked_no_compatible_profile",
    }


def _resolve_liquidity_policy_check(
    session: AssessmentSession,
    *,
    profile: ProfileSummary,
    provided_check: LiquidityPolicyCheckTrace | None,
) -> LiquidityPolicyCheckTrace:
    """Return a compatible liquidity trace or fail before optimization."""

    if provided_check is not None:
        profile_matches_selected = provided_check.selected_profile_band == profile.profile_band
        profile_matches_effective = provided_check.effective_profile_band == profile.profile_band
        if not (profile_matches_selected or profile_matches_effective):
            raise HTTPException(
                status_code=400,
                detail=(
                    "The liquidity policy trace does not match the profile being submitted."
                ),
            )
        if (
            not provided_check.selected_profile_compatible
            and provided_check.effective_profile_band is None
        ):
            blocked_check = provided_check.model_copy(
                update={"user_action": "blocked_no_compatible_profile"}
            )
            raise HTTPException(
                status_code=400,
                detail=_liquidity_rejection_detail(blocked_check),
            )
        if (
            not provided_check.selected_profile_compatible
            and provided_check.user_action == "checked_selected_profile"
        ):
            return provided_check.model_copy(
                update={"user_action": "auto_adjusted_to_safer_profile"}
            )
        return provided_check

    check = build_liquidity_check_for_profile(
        session,
        profile_band=profile.profile_band,
        user_action="submitted_compatible_profile",
    )
    if check.selected_profile_compatible:
        return check
    if check.effective_profile_band is None:
        check = check.model_copy(update={"user_action": "blocked_no_compatible_profile"})
        raise HTTPException(status_code=400, detail=_liquidity_rejection_detail(check))
    return check.model_copy(update={"user_action": "auto_adjusted_to_safer_profile"})


# ---------------------------------------------------------------------------
# Result persistence and submit orchestration
# ---------------------------------------------------------------------------


def save_submission_result(
    db: Session,
    *,
    session: AssessmentSession,
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    decision_trace: DecisionTrace,
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
            "decision_trace": decision_trace.model_dump(),
        }
    )
    session.submitted_at = utc_now()
    session.updated_at = utc_now()

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _build_captured_answer_trace(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    *,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
) -> list[CapturedAnswerTrace]:
    """Convert saved answers into trace facts for report/audit use."""

    questions_by_id = _question_lookup(questionnaire)
    answers_lookup = answers_by_question(session)
    answer_traces: list[CapturedAnswerTrace] = []
    allocation_answer_ids = (
        LIQUIDITY_QUESTION_IDS if liquidity_policy_check is not None else set()
    )

    for question in sorted(questionnaire["questions"], key=lambda item: item["order"]):
        if not is_question_active(question, answers_lookup):
            continue
        answer = answers_lookup.get(question["id"])
        if answer is None:
            continue

        question_type = _question_type(question)
        used_for_scoring = bool(question.get("used_for_scoring", True))
        used_for_allocation = question["id"] in allocation_answer_ids
        answer_traces.append(
            CapturedAnswerTrace(
                question_id=question["id"],
                question_text=questions_by_id[question["id"]]["text"],
                answer_type=question_type,
                answer_label=answer.answer_label_snapshot,
                used_for_scoring=used_for_scoring,
                used_for_allocation=used_for_allocation,
            )
        )

    return answer_traces


def build_decision_trace(
    session: AssessmentSession,
    questionnaire: dict[str, Any],
    profile: ProfileSummary,
    recommendation: RecommendationSummary,
    *,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
    risk_reality_check: RiskRealityCheckTrace | None = None,
) -> DecisionTrace:
    """Build the internal explanation facts for one submitted session."""

    portfolio_config = load_portfolio_config(recommendation.version)
    optimizer_config = portfolio_config["optimizer"]
    configured_bounds = optimizer_config.get("weight_bounds", [0.0, 1.0])
    effective_upper_bound = min(
        float(configured_bounds[1]),
        recommendation.constraints.single_asset_cap,
    )
    captured_answers = _build_captured_answer_trace(
        session,
        questionnaire,
        liquidity_policy_check=liquidity_policy_check,
    )
    captured_but_not_used = [
        answer.question_id
        for answer in captured_answers
        if answer.answer_type == "currency_amount" and not answer.used_for_allocation
    ]
    scoring = load_scoring(session.scoring_version)
    scoring_policy_trace = build_scoring_policy_trace(
        session,
        questionnaire,
        scoring,
        profile=profile,
        liquidity_policy_check=liquidity_policy_check,
    )

    limitations = [
        "The questionnaire now calculates the proposed investor profile, while advisor review can still override it during the prototype.",
        "Numeric liquidity inputs are used for the Cash-floor compatibility check, while the full suitability model is still under development.",
        "Expected returns are model inputs and estimates, not guarantees.",
        "Covariance PSD repair is a numerical stability step applied before optimization, not a change to the investment policy.",
    ]

    return DecisionTrace(
        questionnaire_version=session.questionnaire_version,
        scoring_version=session.scoring_version,
        portfolio_version=recommendation.version,
        profile_band=profile.profile_band,
        profile_label=profile.profile_label,
        profile_source=profile.profile_source,
        data_source=get_active_portfolio_data_source(),
        optimizer_objective=str(optimizer_config.get("objective", recommendation.objective)),
        risk_free_rate=float(optimizer_config.get("risk_free_rate", 0.0)),
        weight_bounds=[float(configured_bounds[0]), effective_upper_bound],
        single_asset_cap=recommendation.constraints.single_asset_cap,
        covariance_psd_repair_enabled=bool(
            optimizer_config.get("repair_nonpositive_semidefinite", False)
        ),
        applied_overlays=list(recommendation.constraints.applied_overlays),
        super_class_minima=recommendation.constraints.super_class_minima,
        super_class_maxima=recommendation.constraints.super_class_maxima,
        metric_minima=recommendation.constraints.metric_minima,
        metric_maxima=recommendation.constraints.metric_maxima,
        captured_answers=captured_answers,
        captured_but_not_used=captured_but_not_used,
        limitations=limitations,
        scoring_policy_trace=scoring_policy_trace,
        liquidity_policy_check=liquidity_policy_check,
        risk_reality_check=risk_reality_check,
    )


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


def get_saved_decision_trace(session: AssessmentSession) -> DecisionTrace:
    """Return the persisted decision trace for a submitted session."""

    if not session.result_json:
        raise HTTPException(
            status_code=409,
            detail="This session does not have a saved decision trace yet.",
        )

    payload = json.loads(session.result_json)
    trace_payload = payload.get("decision_trace")
    if trace_payload is None:
        raise HTTPException(
            status_code=500,
            detail="The saved session result is missing the decision trace payload.",
        )
    return DecisionTrace.model_validate(trace_payload)


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
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
    risk_reality_check: RiskRealityCheckTrace | None = None,
) -> tuple[AssessmentSession, ProfileSummary, RecommendationSummary]:
    """Score the saved answers, build a recommendation, and persist both.

    This is the main "finish the assessment" entrypoint used by both:

    - the FastAPI submit route
    - the Chainlit chat review/yes step
    """

    questionnaire = load_questionnaire(session.questionnaire_version)
    _ensure_session_complete(questionnaire, session)

    profile = _select_profile_for_submission(
        session,
        questionnaire,
        mock_profile_band=mock_profile_band,
    )
    resolved_liquidity_check = _resolve_liquidity_policy_check(
        session,
        profile=profile,
        provided_check=liquidity_policy_check,
    )
    if (
        resolved_liquidity_check.effective_profile_band is not None
        and resolved_liquidity_check.effective_profile_band != profile.profile_band
    ):
        profile = build_liquidity_adjusted_profile(
            original_profile=profile,
            effective_profile_band=resolved_liquidity_check.effective_profile_band,
        )
    recommendation = build_recommendation(
        profile=profile,
        cash_floor_override=resolved_liquidity_check.liquidity_floor,
    )
    decision_trace = build_decision_trace(
        session,
        questionnaire,
        profile,
        recommendation,
        liquidity_policy_check=resolved_liquidity_check,
        risk_reality_check=risk_reality_check,
    )
    saved_session = save_submission_result(
        db,
        session=session,
        profile=profile,
        recommendation=recommendation,
        decision_trace=decision_trace,
    )
    return saved_session, profile, recommendation


def preview_assessment_recommendation(
    db: Session,
    *,
    session: AssessmentSession,
    mock_profile_band: str | None = None,
    liquidity_policy_check: LiquidityPolicyCheckTrace | None = None,
) -> tuple[ProfileSummary, RecommendationSummary]:
    """Build a recommendation preview without persisting a submitted result."""

    questionnaire = load_questionnaire(session.questionnaire_version)
    _ensure_session_complete(questionnaire, session)
    profile = _select_profile_for_submission(
        session,
        questionnaire,
        mock_profile_band=mock_profile_band,
    )
    resolved_liquidity_check = _resolve_liquidity_policy_check(
        session,
        profile=profile,
        provided_check=liquidity_policy_check,
    )
    if (
        resolved_liquidity_check.effective_profile_band is not None
        and resolved_liquidity_check.effective_profile_band != profile.profile_band
    ):
        profile = build_liquidity_adjusted_profile(
            original_profile=profile,
            effective_profile_band=resolved_liquidity_check.effective_profile_band,
        )
    recommendation = build_recommendation(
        profile=profile,
        cash_floor_override=resolved_liquidity_check.liquidity_floor,
    )

    # Keep the SQLAlchemy object explicitly unmodified so Chainlit can show the
    # pre-submit risk check before the real submit path writes result_json.
    db.expire(session)
    return profile, recommendation

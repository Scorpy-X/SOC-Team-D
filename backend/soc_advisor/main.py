"""FastAPI entry point for the SOC advisor backend scaffold.

This file is deliberately thin.

It owns:

- app setup
- route definitions
- wiring request payloads to service-layer helpers

It does not own:

- questionnaire logic
- scoring logic
- portfolio allocation logic
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .schemas import (
    AnswerUpsertRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    QuestionnaireResponse,
    RecommendationResponse,
    SessionStateResponse,
    SubmitSessionRequest,
    SubmitSessionResponse,
)
from .services import (
    build_session_state,
    create_assessment_session,
    get_session_or_404,
    get_saved_profile,
    get_saved_recommendation,
    load_questionnaire,
    submit_assessment,
    upsert_answer,
)
from .settings import get_settings


settings = get_settings()
# FastAPI is only the HTTP shell around the service layer. The advisor logic
# still lives in `services.py` and `portfolio.py`.
app = FastAPI(
    title="SOC Advisor Backend",
    version="0.1.0",
    description="Config-driven backend scaffold for the active SOC questionnaire and allocation flow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#
# App lifecycle and simple status routes
#


@app.on_event("startup")
def on_startup() -> None:
    """Create local tables the first time the app starts."""

    Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict[str, str]:
    """Small root payload to confirm the API is running."""

    return {
        "message": "SOC advisor backend is running.",
        "docs": "/docs",
        "questionnaire": "/questionnaire",
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Health endpoint for simple checks."""

    return {
        "status": "ok",
        "questionnaire_version": settings.questionnaire_version,
        "scoring_version": settings.scoring_version,
        "portfolio_version": settings.portfolio_version,
    }


#
# Questionnaire and session routes
#


@app.get("/questionnaire", response_model=QuestionnaireResponse)
def get_current_questionnaire(
    questionnaire_version: str | None = None,
) -> QuestionnaireResponse:
    """Return the current questionnaire config for the frontend."""

    resolved_version = questionnaire_version or settings.questionnaire_version
    questionnaire = load_questionnaire(resolved_version)
    return QuestionnaireResponse.model_validate(questionnaire)


@app.post("/sessions", response_model=CreateSessionResponse)
def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> CreateSessionResponse:
    """Start a new assessment session."""

    session = create_assessment_session(
        db,
        questionnaire_version=payload.questionnaire_version,
        scoring_version=payload.scoring_version,
    )
    return CreateSessionResponse(
        session_id=session.id,
        questionnaire_version=session.questionnaire_version,
        scoring_version=session.scoring_version,
        status=session.status,
    )


@app.get("/sessions/{session_id}", response_model=SessionStateResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Return the current session state, including saved answers."""

    session = get_session_or_404(db, session_id)
    questionnaire = load_questionnaire(session.questionnaire_version)
    return build_session_state(session, questionnaire)


@app.get("/sessions/{session_id}/summary", response_model=SessionStateResponse)
def get_session_summary(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Alias for the current session state."""

    session = get_session_or_404(db, session_id)
    questionnaire = load_questionnaire(session.questionnaire_version)
    return build_session_state(session, questionnaire)


@app.post("/sessions/{session_id}/answers", response_model=SessionStateResponse)
def save_answer(
    session_id: str,
    payload: AnswerUpsertRequest,
    db: Session = Depends(get_db),
):
    """Save or replace one answer in a session."""

    session = get_session_or_404(db, session_id)
    questionnaire = load_questionnaire(session.questionnaire_version)
    updated_session = upsert_answer(
        db,
        session=session,
        questionnaire=questionnaire,
        question_id=payload.question_id,
        option_id=payload.option_id,
        numeric_value=payload.numeric_value,
    )
    return build_session_state(updated_session, questionnaire)


#
# Submit and recommendation routes
#


@app.post("/sessions/{session_id}/submit", response_model=SubmitSessionResponse)
def submit_session(
    session_id: str,
    payload: SubmitSessionRequest | None = None,
    db: Session = Depends(get_db),
) -> SubmitSessionResponse:
    """Validate the session and compute a profile plus recommendation."""

    session = get_session_or_404(db, session_id)
    saved_session, profile, recommendation = submit_assessment(
        db,
        session=session,
        mock_profile_band=payload.mock_profile_band if payload is not None else None,
    )
    questionnaire = load_questionnaire(saved_session.questionnaire_version)
    session_state = build_session_state(saved_session, questionnaire)

    return SubmitSessionResponse(
        **session_state.model_dump(),
        profile=profile,
        recommendation=recommendation,
    )


@app.get(
    "/sessions/{session_id}/recommendation",
    response_model=RecommendationResponse,
)
def get_session_recommendation(
    session_id: str,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Return the saved recommendation for a submitted session."""

    session = get_session_or_404(db, session_id)
    return RecommendationResponse(
        session_id=session.id,
        status=session.status,
        profile=get_saved_profile(session),
        recommendation=get_saved_recommendation(session),
    )

"""Pydantic schemas for the advisor API and Chainlit experiment.

This file defines the wire-format contracts shared between:

- the FastAPI routes
- the service layer
- the Chainlit UI helpers

It does not contain business logic. If you are trying to understand *how* a
profile or recommendation is produced, move next to `services.py` or
`portfolio.py`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


#
# Questionnaire definition models
#


class QuestionOption(BaseModel):
    id: str
    label: str
    description: str | None = None


class QuestionDependency(BaseModel):
    question_id: str
    option_ids: list[str]


class QuestionValidation(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    example: str | None = None


class QuestionDefinition(BaseModel):
    id: str
    order: int
    text: str
    help_text: str | None = None
    type: str
    dimension: str
    required: bool = True
    used_for_scoring: bool = True
    depends_on: QuestionDependency | None = None
    validation: QuestionValidation | None = None
    options: list[QuestionOption] = Field(default_factory=list)


class QuestionnaireResponse(BaseModel):
    version: str
    title: str
    description: str
    questions: list[QuestionDefinition]


#
# Session and answer models
#


class CreateSessionRequest(BaseModel):
    questionnaire_version: str | None = None
    scoring_version: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    questionnaire_version: str
    scoring_version: str
    status: str


class AnswerUpsertRequest(BaseModel):
    question_id: str = Field(..., examples=["financial_knowledge"])
    option_id: str | None = Field(default=None, examples=["wealth_building"])
    numeric_value: float | None = Field(default=None, examples=[25000])


class AnswerSummary(BaseModel):
    question_id: str
    question_text: str
    dimension: str
    answer_type: str
    option_id: str | None = None
    answer_label: str


class SessionStateResponse(BaseModel):
    session_id: str
    questionnaire_version: str
    scoring_version: str
    status: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    answers: list[AnswerSummary]
    missing_question_ids: list[str]
    can_submit: bool


#
# Profile and recommendation models
#


class ProfileSummary(BaseModel):
    profile_band: str
    profile_label: str
    profile_score: float | None = None
    profile_source: str = "scored_questionnaire"
    profile_description: str
    dimension_scores: dict[str, float]
    reasons: list[str]


class PortfolioHolding(BaseModel):
    ticker: str
    weight: float
    super_class: str
    asset_class: str
    currency: str
    expected_return: float
    income_yield_ann: float
    volatility_ann: float


class PortfolioMetrics(BaseModel):
    expected_return: float
    volatility: float
    income_yield_ann: float
    modified_duration: float
    expense_ratio_ann: float
    rate_beta: float
    inflation_beta: float
    fx_beta: float


class ConstraintSummary(BaseModel):
    version: str
    objective: str
    single_asset_cap: float
    super_class_minima: dict[str, float]
    super_class_maxima: dict[str, float]
    metric_minima: dict[str, float]
    metric_maxima: dict[str, float]
    applied_overlays: list[str]
    fallback_note: str | None = None


class RecommendationSummary(BaseModel):
    version: str
    profile_band: str
    profile_label: str
    objective: str
    holdings: list[PortfolioHolding]
    metrics: PortfolioMetrics
    constraints: ConstraintSummary
    notes: list[str]


#
# Submit/result wrapper models
#


class SubmitSessionRequest(BaseModel):
    mock_profile_band: str | None = Field(
        default=None,
        examples=["growth"],
    )


class SubmitSessionResponse(SessionStateResponse):
    profile: ProfileSummary
    recommendation: RecommendationSummary


class RecommendationResponse(BaseModel):
    session_id: str
    status: str
    profile: ProfileSummary
    recommendation: RecommendationSummary

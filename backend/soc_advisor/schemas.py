"""Pydantic schemas for request and response payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    id: str
    label: str
    description: str | None = None


class QuestionDependency(BaseModel):
    question_id: str
    option_ids: list[str]


class QuestionDefinition(BaseModel):
    id: str
    order: int
    text: str
    help_text: str | None = None
    type: str
    dimension: str
    required: bool = True
    depends_on: QuestionDependency | None = None
    options: list[QuestionOption]


class QuestionnaireResponse(BaseModel):
    version: str
    title: str
    description: str
    questions: list[QuestionDefinition]


class CreateSessionRequest(BaseModel):
    questionnaire_version: str | None = None
    scoring_version: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    questionnaire_version: str
    scoring_version: str
    status: str


class AnswerUpsertRequest(BaseModel):
    question_id: str = Field(..., examples=["portfolio_purpose"])
    option_id: str = Field(..., examples=["wealth_building"])


class AnswerSummary(BaseModel):
    question_id: str
    question_text: str
    dimension: str
    option_id: str
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

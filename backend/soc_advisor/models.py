"""Database models for questionnaire sessions and answers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class AssessmentSession(Base):
    """One questionnaire run for one user session."""

    __tablename__ = "assessment_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    questionnaire_version: Mapped[str] = mapped_column(String(32))
    scoring_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    profile_band: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class AssessmentAnswer(Base):
    """Saved answer for a single question inside one session."""

    __tablename__ = "assessment_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_sessions.id"),
        index=True,
    )
    question_id: Mapped[str] = mapped_column(String(100))
    dimension_snapshot: Mapped[str] = mapped_column(String(100))
    question_text_snapshot: Mapped[str] = mapped_column(Text)
    raw_value: Mapped[str] = mapped_column(String(100))
    normalized_value: Mapped[str] = mapped_column(String(100))
    answer_label_snapshot: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    session: Mapped[AssessmentSession] = relationship(back_populates="answers")

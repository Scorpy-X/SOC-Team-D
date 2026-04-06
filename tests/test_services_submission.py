from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.services import (  # noqa: E402
    get_saved_profile,
    submit_assessment,
)


@pytest.mark.parametrize(
    "mock_profile_band",
    [
        "very_conservative",
        "conservative",
        "balanced",
        "growth",
        "aggressive",
    ],
)
def test_submit_assessment_accepts_manual_mock_bands(
    db_session,
    answered_session,
    mock_profile_band: str,
) -> None:
    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=answered_session,
        mock_profile_band=mock_profile_band,
    )

    assert profile.profile_band == mock_profile_band
    assert profile.profile_source == "manual_mock_band"
    assert profile.profile_score is None
    assert recommendation.profile_band == mock_profile_band
    assert any("manual" in note.lower() for note in recommendation.notes)
    assert any("liquidity inputs" in note.lower() for note in recommendation.notes)

    saved_profile = get_saved_profile(saved_session)
    assert saved_profile.profile_source == "manual_mock_band"
    assert saved_profile.profile_score is None


def test_submit_assessment_preserves_scored_fallback(db_session, answered_session) -> None:
    saved_session, profile, recommendation = submit_assessment(
        db_session,
        session=answered_session,
        mock_profile_band=None,
    )

    assert profile.profile_source == "scored_questionnaire"
    assert profile.profile_score is not None
    assert recommendation.profile_band == profile.profile_band
    assert get_saved_profile(saved_session).profile_source == "scored_questionnaire"


def test_submit_assessment_rejects_unknown_mock_band(db_session, answered_session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        submit_assessment(
            db_session,
            session=answered_session,
            mock_profile_band="not_a_real_band",
        )

    assert exc_info.value.status_code == 400
    assert "mock_profile_band" in str(exc_info.value.detail)

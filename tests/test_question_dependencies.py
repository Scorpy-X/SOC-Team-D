from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.schemas import AnswerSummary  # noqa: E402
from soc_advisor.services import (  # noqa: E402
    create_assessment_session,
    get_missing_question_ids,
    is_question_active,
    upsert_answer,
)


def _dependency_questionnaire() -> dict:
    """Small synthetic questionnaire used to exercise dependency helpers.

    The live `v2` questionnaire does not currently use `depends_on`, so these
    tests lock in the helper behavior directly instead of relying on config.
    """

    return {
        "version": "dependency-test",
        "title": "Dependency Test",
        "description": "Synthetic questionnaire for helper-level tests.",
        "questions": [
            {
                "id": "needs_follow_up",
                "order": 1,
                "text": "Should the follow-up question appear?",
                "type": "single_choice",
                "dimension": "branching",
                "required": True,
                "options": [
                    {"id": "yes", "label": "Yes"},
                    {"id": "no", "label": "No"},
                ],
            },
            {
                "id": "follow_up_reason",
                "order": 2,
                "text": "Why is the follow-up question needed?",
                "type": "single_choice",
                "dimension": "branching",
                "required": True,
                "depends_on": {
                    "question_id": "needs_follow_up",
                    "option_ids": ["yes"],
                },
                "options": [
                    {"id": "reason_a", "label": "Reason A"},
                    {"id": "reason_b", "label": "Reason B"},
                ],
            },
        ],
    }


def test_is_question_active_accepts_plain_option_lookup() -> None:
    questionnaire = _dependency_questionnaire()
    follow_up = questionnaire["questions"][1]

    assert is_question_active(follow_up, {"needs_follow_up": "yes"}) is True
    assert is_question_active(follow_up, {"needs_follow_up": "no"}) is False


def test_is_question_active_accepts_answer_summary_lookup() -> None:
    questionnaire = _dependency_questionnaire()
    follow_up = questionnaire["questions"][1]
    answer_summary = AnswerSummary(
        question_id="needs_follow_up",
        question_text=questionnaire["questions"][0]["text"],
        dimension="branching",
        answer_type="single_choice",
        option_id="yes",
        answer_label="Yes",
    )

    assert is_question_active(follow_up, {"needs_follow_up": answer_summary}) is True


def test_get_missing_question_ids_skips_inactive_follow_up(db_session) -> None:
    questionnaire = _dependency_questionnaire()
    session = create_assessment_session(db_session)

    session = upsert_answer(
        db_session,
        session=session,
        questionnaire=questionnaire,
        question_id="needs_follow_up",
        option_id="no",
    )

    assert get_missing_question_ids(questionnaire, session) == []


def test_get_missing_question_ids_marks_active_follow_up_as_missing(db_session) -> None:
    questionnaire = _dependency_questionnaire()
    session = create_assessment_session(db_session)

    session = upsert_answer(
        db_session,
        session=session,
        questionnaire=questionnaire,
        question_id="needs_follow_up",
        option_id="yes",
    )

    assert get_missing_question_ids(questionnaire, session) == ["follow_up_reason"]

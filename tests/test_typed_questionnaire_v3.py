from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.schemas import QuestionnaireResponse  # noqa: E402
from soc_advisor.services import load_questionnaire  # noqa: E402


def test_questionnaire_v3_validates_against_schema() -> None:
    questionnaire = load_questionnaire("v3")
    response = QuestionnaireResponse.model_validate(questionnaire)

    assert response.version == "v3"
    assert len(response.questions) == 12


def test_questionnaire_v3_currency_questions_define_validation_and_scoring_flags() -> None:
    questionnaire = load_questionnaire("v3")
    questions_by_id = {question["id"]: question for question in questionnaire["questions"]}

    assert questions_by_id["portfolio_value"]["type"] == "currency_amount"
    assert questions_by_id["portfolio_value"]["validation"]["min_value"] == 25000
    assert questions_by_id["portfolio_value"]["used_for_scoring"] is False

    assert questions_by_id["major_expense_withdrawal_amount"]["used_for_scoring"] is False
    assert questions_by_id["essential_monthly_expenses"]["used_for_scoring"] is False

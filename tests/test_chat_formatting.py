from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.chat_formatting import (  # noqa: E402
    render_profile_summary,
    render_review_message,
)
from soc_advisor.portfolio import list_profile_bands  # noqa: E402
from soc_advisor.schemas import (  # noqa: E402
    AnswerSummary,
    ConstraintSummary,
    PortfolioHolding,
    PortfolioMetrics,
    ProfileSummary,
    RecommendationSummary,
    SessionStateResponse,
)


QUESTION_LABELS = {
    "portfolio_purpose": "Purpose",
    "financial_knowledge": "Knowledge",
}
QUESTIONS_BY_ID = {
    "portfolio_purpose": {"text": "What is the main purpose of this portfolio?"},
    "financial_knowledge": {"text": "How knowledgeable are you about financial and investment concepts?"},
}


def _sample_state() -> SessionStateResponse:
    now = datetime.now(timezone.utc)
    return SessionStateResponse(
        session_id="session-1",
        questionnaire_version="v2",
        scoring_version="v3",
        status="draft",
        created_at=now,
        updated_at=now,
        submitted_at=None,
        answers=[
            AnswerSummary(
                question_id="portfolio_purpose",
                question_text=QUESTIONS_BY_ID["portfolio_purpose"]["text"],
                dimension="portfolio_purpose",
                option_id="wealth_building",
                answer_label="To build long-term wealth",
            ),
            AnswerSummary(
                question_id="financial_knowledge",
                question_text=QUESTIONS_BY_ID["financial_knowledge"]["text"],
                dimension="financial_knowledge",
                option_id="very_knowledgeable",
                answer_label="Very knowledgeable",
            ),
        ],
        missing_question_ids=[],
        can_submit=True,
    )


def _sample_profile() -> ProfileSummary:
    return ProfileSummary(
        profile_band="growth",
        profile_label="Growth",
        profile_score=None,
        profile_source="manual_mock_band",
        profile_description="Growth-oriented profile with a clear equity majority.",
        dimension_scores={},
        reasons=["Manual mock band was selected for this draft run."],
    )


def _sample_recommendation() -> RecommendationSummary:
    return RecommendationSummary(
        version="v2",
        profile_band="growth",
        profile_label="Growth",
        objective="max_sharpe",
        holdings=[
            PortfolioHolding(
                ticker="BQB",
                weight=0.60,
                super_class="Equity",
                asset_class="Emerging Market Equity",
                currency="USD",
                expected_return=0.15,
                income_yield_ann=0.01,
                volatility_ann=0.20,
            ),
            PortfolioHolding(
                ticker="QPESE",
                weight=0.30,
                super_class="Fixed Income",
                asset_class="Long Government Bonds",
                currency="JMD",
                expected_return=0.08,
                income_yield_ann=0.05,
                volatility_ann=0.07,
            ),
            PortfolioHolding(
                ticker="TBILLJMD",
                weight=0.10,
                super_class="Cash",
                asset_class="JMD T-Bill",
                currency="JMD",
                expected_return=0.04,
                income_yield_ann=0.04,
                volatility_ann=0.01,
            ),
        ],
        metrics=PortfolioMetrics(
            expected_return=0.10,
            volatility=0.07,
            income_yield_ann=0.03,
            modified_duration=2.1,
            expense_ratio_ann=0.01,
            rate_beta=0.3,
            inflation_beta=0.2,
            fx_beta=0.1,
        ),
        constraints=ConstraintSummary(
            version="v2",
            objective="max_sharpe",
            single_asset_cap=0.4,
            super_class_minima={"Cash": 0.0, "Fixed Income": 0.1, "Equity": 0.6, "Fund": 0.0},
            super_class_maxima={"Cash": 0.1, "Fixed Income": 0.3, "Equity": 0.8, "Fund": 0.0},
            metric_minima={},
            metric_maxima={},
            applied_overlays=[],
            fallback_note=None,
        ),
        notes=[
            "Variant B uses band-only class ranges.",
            "This run used a manually selected mock investor band.",
        ],
    )


def test_render_review_message_numbers_answers_and_teaches_commands() -> None:
    text = render_review_message(
        _sample_state(),
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        profile_bands=list_profile_bands(),
        selected_band_id="growth",
    )

    assert "1. **Purpose:** To build long-term wealth" in text
    assert "2. **Knowledge:** Very knowledgeable" in text
    assert "`change <question number>`" in text
    assert "`band <band number>`" in text
    assert "Selected draft band:" in text


def test_render_profile_summary_numbers_answers_in_final_output() -> None:
    text = render_profile_summary(
        _sample_state(),
        _sample_profile(),
        _sample_recommendation(),
    )

    assert "1. **What is the main purpose of this portfolio?:** To build long-term wealth" in text
    assert "2. **How knowledgeable are you about financial and investment concepts?:** Very knowledgeable" in text
    assert "Score:** Not used in this mock-band run." in text
    assert "Band policy used" in text

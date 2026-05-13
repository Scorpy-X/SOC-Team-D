from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.risk_reality import (  # noqa: E402
    build_risk_reality_estimate,
    build_risk_reality_trace,
    is_continue_input,
    render_risk_reality_prompt,
)
from soc_advisor.schemas import (  # noqa: E402
    AnswerSummary,
    ConstraintSummary,
    PortfolioMetrics,
    RecommendationSummary,
    SessionStateResponse,
)


def _sample_state(*, include_portfolio_value: bool = True) -> SessionStateResponse:
    now = datetime.now(timezone.utc)
    answers = []
    if include_portfolio_value:
        answers.append(
            AnswerSummary(
                question_id="portfolio_value",
                question_text="What is your portfolio value?",
                dimension="liquidity",
                answer_type="currency_amount",
                option_id=None,
                answer_label="$100,000.00",
            )
        )
    return SessionStateResponse(
        session_id="risk-session",
        questionnaire_version="v3",
        scoring_version="v4",
        status="draft",
        created_at=now,
        updated_at=now,
        submitted_at=None,
        answers=answers,
        missing_question_ids=[],
        can_submit=True,
    )


def _sample_recommendation() -> RecommendationSummary:
    return RecommendationSummary(
        version="v2",
        profile_band="growth",
        profile_label="Growth",
        objective="max_sharpe",
        holdings=[],
        metrics=PortfolioMetrics(
            expected_return=0.10,
            volatility=0.072,
            income_yield_ann=0.03,
            modified_duration=2.1,
            expense_ratio_ann=0.002,
            rate_beta=0.1,
            inflation_beta=0.2,
            fx_beta=0.3,
        ),
        constraints=ConstraintSummary(
            version="v2",
            objective="max_sharpe",
            single_asset_cap=0.4,
            super_class_minima={},
            super_class_maxima={},
            metric_minima={},
            metric_maxima={},
            applied_overlays=[],
            fallback_note=None,
        ),
        notes=[],
    )


def test_risk_reality_estimate_uses_two_times_annual_volatility() -> None:
    estimate = build_risk_reality_estimate(
        state=_sample_state(),
        recommendation=_sample_recommendation(),
    )

    assert estimate.annual_volatility == 0.072
    assert estimate.multiplier == 2.0
    assert estimate.stress_percent == 0.144
    assert estimate.portfolio_value == 100000.0
    assert estimate.stress_amount == 14400.0


def test_risk_reality_estimate_handles_missing_portfolio_value() -> None:
    estimate = build_risk_reality_estimate(
        state=_sample_state(include_portfolio_value=False),
        recommendation=_sample_recommendation(),
    )

    assert estimate.stress_percent == 0.144
    assert estimate.portfolio_value is None
    assert estimate.stress_amount is None


def test_risk_reality_prompt_is_informational_and_requires_yes() -> None:
    prompt = render_risk_reality_prompt(
        build_risk_reality_estimate(
            state=_sample_state(),
            recommendation=_sample_recommendation(),
        )
    )

    assert "estimated annual volatility of **7.2%**" in prompt
    assert "potential loss of about **14.4%**, or about **$14,400.00**" in prompt
    assert "This is not a prediction" in prompt
    assert "stress illustration" not in prompt
    assert "Type `yes` to generate the report" in prompt
    assert "Edit short-term loss willingness" not in prompt
    assert "Return to profile review" not in prompt
    assert "Continue with the current profile" not in prompt
    assert "guaranteed loss" not in prompt.casefold()
    assert "maximum loss" not in prompt.casefold()
    assert "worst case" not in prompt.casefold()


def test_risk_reality_continue_requires_yes() -> None:
    assert is_continue_input("6") is False
    assert is_continue_input("yes") is True
    assert is_continue_input("continue") is False
    assert is_continue_input("confirm") is False
    assert is_continue_input("no") is False
    assert is_continue_input("no, continue") is False


def test_risk_reality_trace_records_user_action_and_revisions() -> None:
    trace = build_risk_reality_trace(
        build_risk_reality_estimate(
            state=_sample_state(),
            recommendation=_sample_recommendation(),
        ),
        user_action="continued_current_profile",
        revised_question_ids=["market_drop_response"],
    )

    assert trace.method == "two_standard_deviation_volatility_proxy"
    assert trace.multiplier == 2.0
    assert trace.annual_volatility == 0.072
    assert trace.stress_percent == 0.144
    assert trace.portfolio_value == 100000.0
    assert trace.stress_amount == 14400.0
    assert trace.user_action == "continued_current_profile"
    assert trace.revised_question_ids == ["market_drop_response"]

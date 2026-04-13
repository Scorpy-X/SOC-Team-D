from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor import reporting  # noqa: E402
from soc_advisor.report_llm import ReportProse  # noqa: E402
from soc_advisor.schemas import (  # noqa: E402
    AnswerSummary,
    CapturedAnswerTrace,
    ConstraintSummary,
    DecisionTrace,
    PortfolioHolding,
    PortfolioMetrics,
    ProfileSummary,
    RecommendationSummary,
    SessionStateResponse,
)


def _sample_state() -> SessionStateResponse:
    now = datetime.now(timezone.utc)
    return SessionStateResponse(
        session_id="session-report-test",
        questionnaire_version="v3",
        scoring_version="v4",
        status="submitted",
        created_at=now,
        updated_at=now,
        submitted_at=now,
        answers=[
            AnswerSummary(
                question_id="portfolio_value",
                question_text="What is your portfolio value?",
                dimension="liquidity",
                answer_type="currency_amount",
                option_id=None,
                answer_label="$50,000.00",
            )
        ],
        missing_question_ids=[],
        can_submit=True,
    )


def _sample_state_without_portfolio_value() -> SessionStateResponse:
    now = datetime.now(timezone.utc)
    return SessionStateResponse(
        session_id="session-report-test-no-value",
        questionnaire_version="v3",
        scoring_version="v4",
        status="submitted",
        created_at=now,
        updated_at=now,
        submitted_at=now,
        answers=[],
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
                ticker="AAA",
                weight=0.50,
                super_class="Equity",
                asset_class="Local Equity",
                currency="JMD",
                expected_return=0.12,
                income_yield_ann=0.02,
                volatility_ann=0.18,
            ),
            PortfolioHolding(
                ticker="BBB",
                weight=0.30,
                super_class="Fixed Income",
                asset_class="Government Bond",
                currency="JMD",
                expected_return=0.07,
                income_yield_ann=0.05,
                volatility_ann=0.04,
            ),
            PortfolioHolding(
                ticker="CCC",
                weight=0.20,
                super_class="Equity",
                asset_class="US Equity",
                currency="USD",
                expected_return=0.10,
                income_yield_ann=0.01,
                volatility_ann=0.16,
            ),
        ],
        metrics=PortfolioMetrics(
            expected_return=0.10,
            volatility=0.08,
            income_yield_ann=0.03,
            modified_duration=1.8,
            expense_ratio_ann=0.005,
            rate_beta=0.2,
            inflation_beta=0.1,
            fx_beta=0.3,
        ),
        constraints=ConstraintSummary(
            version="v2",
            objective="max_sharpe",
            single_asset_cap=0.5,
            super_class_minima={"Cash": 0.0, "Fixed Income": 0.1, "Equity": 0.6},
            super_class_maxima={"Cash": 0.1, "Fixed Income": 0.3, "Equity": 0.8},
            metric_minima={},
            metric_maxima={},
            applied_overlays=[],
            fallback_note=None,
        ),
        notes=["Variant B uses band-only class ranges."],
    )


def _sample_trace() -> DecisionTrace:
    return DecisionTrace(
        questionnaire_version="v3",
        scoring_version="v4",
        portfolio_version="v2",
        profile_band="growth",
        profile_label="Growth",
        profile_source="manual_mock_band",
        data_source="csv_snapshot",
        optimizer_objective="max_sharpe",
        risk_free_rate=0.0,
        weight_bounds=[0.0, 0.5],
        single_asset_cap=0.5,
        covariance_psd_repair_enabled=True,
        super_class_minima={"Cash": 0.0, "Fixed Income": 0.1, "Equity": 0.6},
        super_class_maxima={"Cash": 0.1, "Fixed Income": 0.3, "Equity": 0.8},
        metric_minima={},
        metric_maxima={},
        captured_answers=[
            CapturedAnswerTrace(
                question_id="portfolio_value",
                question_text="What is your portfolio value?",
                answer_type="currency_amount",
                answer_label="$50,000.00",
                used_for_scoring=False,
                used_for_allocation=False,
            )
        ],
        captured_but_not_used=["portfolio_value"],
        limitations=[
            "The live Chainlit demo still uses manual mock-band selection as the primary path.",
            "Questionnaire-to-band scoring is retained as a backend fallback, not as the final approved suitability model.",
            "Numeric liquidity inputs are captured and reviewable but do not yet drive profile selection or portfolio construction.",
            "Expected returns are model inputs and estimates, not guarantees.",
            "Covariance PSD repair is a numerical stability step applied before optimization, not a change to the investment policy.",
        ],
    )


def _deterministic_prose(_facts):
    return ReportProse(
        executive_summary="This is the executive summary.",
        allocation_explanation="This is the allocation explanation.",
        limitation_note="This is the limitation note.",
        status="deterministic",
    )


def test_report_context_groups_allocations_and_concentration(monkeypatch) -> None:
    monkeypatch.setattr(reporting, "build_report_prose", _deterministic_prose)

    context = reporting.build_report_context(
        state=_sample_state(),
        profile=_sample_profile(),
        recommendation=_sample_recommendation(),
        decision_trace=_sample_trace(),
    )

    class_totals = {
        allocation["label"]: allocation["weight"]
        for allocation in context.class_allocations
    }
    currency_totals = {
        allocation["label"]: allocation["weight"]
        for allocation in context.currency_allocations
    }

    assert class_totals["Equity"] == 0.70
    assert class_totals["Fixed Income"] == 0.30
    assert currency_totals["JMD"] == 0.80
    assert currency_totals["USD"] == 0.20
    assert context.portfolio_value == 50000.0
    assert context.portfolio_value_label == "$50,000.00"
    assert context.class_allocations[0]["amount_label"] == "$15,000.00"
    assert context.largest_holding["ticker"] == "AAA"
    assert context.largest_holding["amount_label"] == "$25,000.00"
    assert context.top_three_weight_label == "100.0%"
    assert context.top_three_amount_label == "$50,000.00"
    assert context.grouped_holdings[0]["super_class"] == "Fixed Income"
    assert context.grouped_holdings[1]["super_class"] == "Equity"


def test_report_context_falls_back_when_portfolio_value_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(reporting, "build_report_prose", _deterministic_prose)

    context = reporting.build_report_context(
        state=_sample_state_without_portfolio_value(),
        profile=_sample_profile(),
        recommendation=_sample_recommendation(),
        decision_trace=_sample_trace(),
    )

    assert context.portfolio_value is None
    assert context.portfolio_value_label is None
    assert context.class_allocations[0]["amount_label"] is None
    assert context.all_holdings[0]["amount_label"] is None
    assert context.top_three_amount_label is None


def test_generate_portfolio_reports_writes_user_and_audit_html(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(reporting, "build_report_prose", _deterministic_prose)
    monkeypatch.setattr(
        reporting,
        "get_settings",
        lambda: SimpleNamespace(advisor_reports_dir=tmp_path),
    )

    report_paths = reporting.generate_portfolio_reports(
        state=_sample_state(),
        profile=_sample_profile(),
        recommendation=_sample_recommendation(),
        decision_trace=_sample_trace(),
    )

    user_html = report_paths.user_report_path.read_text(encoding="utf-8")
    audit_html = report_paths.audit_report_path.read_text(encoding="utf-8")

    assert report_paths.user_report_path.exists()
    assert report_paths.audit_report_path.exists()
    assert "Full investment list" in user_html
    assert "AAA" in user_html
    assert "$25,000.00" in user_html
    assert "Asset code" in user_html
    assert "Investment type" in user_html
    assert "Estimated amount" in user_html
    assert "Asset codes are the short market identifiers" in user_html
    assert "Key estimates in plain language." in user_html
    assert "A rough guide to year-to-year ups and downs" in user_html
    assert "cost drag" not in user_html
    assert "proxy" not in user_html
    assert "Ticker" not in user_html
    assert "Superclass" not in user_html
    assert "optimizer" not in user_html.casefold()
    assert "profile source" not in user_html.casefold()
    assert "mock-band" not in user_html.casefold()
    assert "Rate beta" not in user_html
    assert "Inflation beta" not in user_html
    assert "FX beta" not in user_html
    assert "Raw Trace JSON" not in user_html
    assert "Decision Trace" in audit_html
    assert "Technical Risk Signals" in audit_html
    assert "Rate beta" in audit_html
    assert "Inflation beta" in audit_html
    assert "FX beta" in audit_html
    assert "manual mock-band" in audit_html
    assert "csv_snapshot" in audit_html

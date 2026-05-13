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
    LiquidityPolicyCheckTrace,
    PortfolioHolding,
    PortfolioMetrics,
    ProfileSummary,
    RecommendationSummary,
    RiskRealityCheckTrace,
    ScoringPolicyTrace,
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
        version="v3",
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
            version="v3",
            objective="max_sharpe",
            single_asset_cap=0.5,
            super_class_minima={"Cash": 0.20, "Fixed Income": 0.1, "Equity": 0.6},
            super_class_maxima={"Cash": 0.20, "Fixed Income": 0.3, "Equity": 0.8},
            metric_minima={},
            metric_maxima={},
            applied_overlays=["liquidity_cash_floor:0.200000"],
            fallback_note=None,
        ),
        notes=["Variant B uses band-only class ranges."],
    )


def _sample_trace() -> DecisionTrace:
    return DecisionTrace(
        questionnaire_version="v3",
        scoring_version="v4",
        portfolio_version="v3",
        profile_band="growth",
        profile_label="Growth",
        profile_source="manual_mock_band",
        data_source="csv_snapshot",
        optimizer_objective="max_sharpe",
        risk_free_rate=0.0,
        weight_bounds=[0.0, 0.5],
        single_asset_cap=0.5,
        covariance_psd_repair_enabled=True,
        applied_overlays=["liquidity_cash_floor:0.200000"],
        super_class_minima={"Cash": 0.20, "Fixed Income": 0.1, "Equity": 0.6},
        super_class_maxima={"Cash": 0.20, "Fixed Income": 0.3, "Equity": 0.8},
        metric_minima={},
        metric_maxima={},
        captured_answers=[
            CapturedAnswerTrace(
                question_id="portfolio_value",
                question_text="What is your portfolio value?",
                answer_type="currency_amount",
                answer_label="$50,000.00",
                used_for_scoring=False,
                used_for_allocation=True,
            )
        ],
        captured_but_not_used=[],
        limitations=[
            "The live Chainlit demo still uses manual mock-band selection as the primary path.",
            "Questionnaire-to-band scoring is retained as a backend fallback, not as the final approved suitability model.",
            "Numeric liquidity inputs are used for the Cash-floor compatibility check, while the full suitability model is still under development.",
            "Expected returns are model inputs and estimates, not guarantees.",
            "Covariance PSD repair is a numerical stability step applied before optimization, not a change to the investment policy.",
        ],
        liquidity_policy_check=LiquidityPolicyCheckTrace(
            portfolio_value=50000.0,
            major_expense_withdrawal_amount=10000.0,
            essential_monthly_expenses=2500.0,
            emergency_fund_option_id="months_0",
            emergency_months_used=0.0,
            required_liquidity_amount=10000.0,
            liquidity_floor=0.20,
            selected_profile_band="growth",
            selected_profile_label="Growth",
            selected_cash_ceiling=0.15,
            selected_profile_compatible=False,
            effective_profile_band="balanced",
            effective_profile_label="Balanced",
            effective_cash_ceiling=0.20,
            profile_adjusted=True,
            user_action="auto_adjusted_to_safer_profile",
        ),
    )


def _sample_trace_with_scoring_policy() -> DecisionTrace:
    trace = _sample_trace()
    return trace.model_copy(
        update={
            "scoring_policy_trace": ScoringPolicyTrace(
                method="weighted_normalized_sections",
                capacity_score=0.58,
                tolerance_score=0.61,
                final_score_before_caps=0.592,
                final_score_after_caps=0.592,
                draft_profile_band="balanced",
                draft_profile_label="Balanced",
                final_profile_band="balanced",
                final_profile_label="Balanced",
                section_scores={"capacity": 0.58, "tolerance": 0.61},
                question_scores={"time_horizon": 1.0},
            )
        }
    )


def _sample_trace_with_risk_check() -> DecisionTrace:
    trace = _sample_trace()
    return trace.model_copy(
        update={
            "risk_reality_check": RiskRealityCheckTrace(
                annual_volatility=0.08,
                stress_percent=0.16,
                portfolio_value=50000.0,
                stress_amount=8000.0,
                user_action="continued_current_profile",
                revised_question_ids=["market_drop_response"],
            )
        }
    )


def _deterministic_prose(_facts):
    return ReportProse(
        executive_summary="This report presents a proposed Growth allocation for review.",
        allocation_explanation="This is the allocation explanation.",
        limitation_note="This SOC advisor prototype report is prepared for review and is not final regulated financial advice.",
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
    assert "<title>Portfolio Report</title>" in user_html
    assert "Prepared for review" in user_html
    assert "Draft Portfolio Report" not in user_html
    assert "draft demo report" not in user_html.casefold()
    assert "Full investment list" in user_html
    assert "All investments included in this proposed portfolio." in user_html
    assert "AAA" in user_html
    assert "$25,000.00" in user_html
    assert "Asset code" in user_html
    assert "Investment type" in user_html
    assert "Estimated amount" in user_html
    assert "Asset codes are the short market identifiers" in user_html
    assert "Key portfolio metrics." in user_html
    assert "Why this investor profile was used." in user_html
    assert "Recommendation basis" in user_html
    assert "required Cash reserve" in user_html
    assert "Liquidity check" in user_html
    assert "Cash needs were checked before the report." in user_html
    assert "$10,000.00" in user_html
    assert "20.0%" in user_html
    assert "Annual volatility" in user_html
    assert "risk scale estimate for year-to-year portfolio movement" in user_html
    assert user_html.count("not final regulated financial advice") == 1
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
    assert "Chronological Calculation Trail" in audit_html
    assert "1. Liquidity need" in audit_html
    assert "required liquidity = major expense withdrawal + monthly expenses × emergency months" in audit_html
    assert "$10,000.00 + $2,500.00 × 0.0 = $10,000.00" in audit_html
    assert "liquidity floor = required liquidity / portfolio value" in audit_html
    assert "$10,000.00 / $50,000.00 = 20.0%" in audit_html
    assert "Cash floor overlay" in audit_html
    assert "effective Cash minimum = max(configured Cash minimum, liquidity floor)" in audit_html
    assert "Optimizer constraints" in audit_html
    assert "sum(weights) = 100%" in audit_html
    assert "single asset weight ≤ 50.0%" in audit_html
    assert "Chronological Calculation Trail" not in user_html
    assert "Scoring policy" in audit_html
    assert "Final profile" in audit_html
    assert "Profile policy applied before solving." in audit_html
    assert "Applied overlays" in audit_html
    assert "liquidity_cash_floor:0.200000" in audit_html
    assert "Liquidity Policy Check" in audit_html
    assert "cash_floor_from_liquidity_need" in audit_html
    assert "auto_adjusted_to_safer_profile" in audit_html
    assert "Technical Risk Signals" in audit_html
    assert "Rate beta" in audit_html
    assert "Inflation beta" in audit_html
    assert "FX beta" in audit_html
    assert "manual mock-band" in audit_html
    assert "csv_snapshot" in audit_html


def test_reports_show_display_risk_score_when_scoring_trace_is_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(reporting, "build_report_prose", _deterministic_prose)
    monkeypatch.setattr(
        reporting,
        "get_settings",
        lambda: SimpleNamespace(advisor_reports_dir=tmp_path),
    )

    profile = ProfileSummary(
        profile_band="balanced",
        profile_label="Balanced",
        profile_score=0.592,
        profile_source="scored_questionnaire",
        profile_description="Middle-ground profile balancing stability and growth.",
        dimension_scores={},
        reasons=["Calculated from questionnaire answers."],
    )

    report_paths = reporting.generate_portfolio_reports(
        state=_sample_state(),
        profile=profile,
        recommendation=_sample_recommendation(),
        decision_trace=_sample_trace_with_scoring_policy(),
    )

    user_html = report_paths.user_report_path.read_text(encoding="utf-8")
    audit_html = report_paths.audit_report_path.read_text(encoding="utf-8")

    assert "Risk score" in user_html
    assert "6 / 10" in user_html
    assert "Investor type" in user_html
    assert "Balanced" in user_html
    assert "Balanced means the portfolio keeps a mix of stability and growth exposure." in user_html
    assert "Risk capacity: medium." in user_html
    assert "Risk tolerance: medium." in user_html
    assert "Decision: the system selected Balanced because the capacity and tolerance answers together support a middle profile." in user_html
    assert "Liquidity need: high." in user_html
    assert "Technical note: capacity 58.0%, tolerance 61.0%, displayed risk score 6 / 10." in user_html
    assert "The questionnaire estimated Balanced from risk capacity" not in user_html
    assert "The combined result is shown as" not in user_html
    assert "Chronological Calculation Trail" in audit_html
    assert "Risk capacity score" in audit_html
    assert "capacity score = weighted average of Q5-Q9" in audit_html
    assert "Risk tolerance score" in audit_html
    assert "tolerance score = weighted average of Q10-Q14" in audit_html
    assert "final score = 60% × capacity score + 40% × tolerance score" in audit_html
    assert "60% × 58.0% + 40% × 61.0% = 59.2%" in audit_html
    assert "Profile bucket and cap rule" in audit_html
    assert "Displayed risk score" in audit_html
    assert "6 / 10" in audit_html


def test_reports_show_risk_reality_check_at_user_and_audit_levels(
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
        decision_trace=_sample_trace_with_risk_check(),
    )

    user_html = report_paths.user_report_path.read_text(encoding="utf-8")
    audit_html = report_paths.audit_report_path.read_text(encoding="utf-8")

    assert "Risk reality check" in user_html
    assert "rough volatility stress estimate" in user_html
    assert "16.0%" in user_html
    assert "$8,000.00" in user_html
    assert "maximum loss" not in user_html.casefold()
    assert "worst case" not in user_html.casefold()
    assert "Risk Reality Check" in audit_html
    assert "two_standard_deviation_volatility_proxy" in audit_html
    assert "2.0" in audit_html
    assert "continued_current_profile" in audit_html
    assert "market_drop_response" in audit_html

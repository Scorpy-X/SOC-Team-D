from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.chat_formatting import (  # noqa: E402
    format_edit_prompt,
    format_question,
    render_profile_summary,
    render_review_message,
)
from soc_advisor.chat_view_models import (  # noqa: E402
    build_report_ready_props,
    build_review_element_props,
    build_sidebar_sections,
    render_report_preview,
)
from soc_advisor.portfolio import list_profile_bands  # noqa: E402
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
    ScoringPolicyTrace,
    SessionStateResponse,
)


QUESTION_LABELS = {
    "portfolio_value": "Portfolio value",
    "financial_knowledge": "Knowledge",
}
QUESTIONS_BY_ID = {
    "portfolio_value": {"text": "How much are you investing in this portfolio today? The minimum portfolio value for this questionnaire is $25,000."},
    "financial_knowledge": {"text": "How knowledgeable are you about financial and investment concepts?"},
}


def _sample_state() -> SessionStateResponse:
    now = datetime.now(timezone.utc)
    return SessionStateResponse(
        session_id="session-1",
        questionnaire_version="v3",
        scoring_version="v4",
        status="draft",
        created_at=now,
        updated_at=now,
        submitted_at=None,
        answers=[
            AnswerSummary(
                question_id="portfolio_value",
                question_text=QUESTIONS_BY_ID["portfolio_value"]["text"],
                dimension="portfolio_value",
                answer_type="currency_amount",
                option_id=None,
                answer_label="$50,000.00",
            ),
            AnswerSummary(
                question_id="financial_knowledge",
                question_text=QUESTIONS_BY_ID["financial_knowledge"]["text"],
                dimension="financial_knowledge",
                answer_type="single_choice",
                option_id="very_knowledgeable",
                answer_label="Very knowledgeable",
            ),
        ],
        missing_question_ids=[],
        can_submit=True,
    )


def _sample_state_without_portfolio_value() -> SessionStateResponse:
    now = datetime.now(timezone.utc)
    return SessionStateResponse(
        session_id="session-2",
        questionnaire_version="v3",
        scoring_version="v4",
        status="draft",
        created_at=now,
        updated_at=now,
        submitted_at=None,
        answers=[
            AnswerSummary(
                question_id="financial_knowledge",
                question_text=QUESTIONS_BY_ID["financial_knowledge"]["text"],
                dimension="financial_knowledge",
                answer_type="single_choice",
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
        reasons=["The Growth profile was chosen during review for this draft run."],
    )


def _sample_calculated_profile() -> ProfileSummary:
    return ProfileSummary(
        profile_band="balanced",
        profile_label="Balanced",
        profile_score=0.59,
        profile_source="scored_questionnaire",
        profile_description="Middle-ground profile balancing stability and growth.",
        dimension_scores={},
        reasons=["Calculated from questionnaire answers."],
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

    assert "1. **Portfolio value:** $50,000.00" in text
    assert "2. **Knowledge:** Very knowledgeable" in text
    assert "`change <question number>`" in text
    assert "`band <band number>`" in text
    assert "Selected profile:" in text


def test_build_review_element_props_marks_selected_band_and_answer_rows() -> None:
    props = build_review_element_props(
        _sample_state(),
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        profile_bands=list_profile_bands(),
        selected_band_id="growth",
        intro="Updated. Here is the latest summary.",
    )

    assert props["title"] == "Review your answers"
    assert props["intro"] == "Updated. Here is the latest summary."
    assert props["answers"][0]["label"] == "Portfolio value"
    assert props["answers"][1]["value"] == "Very knowledgeable"
    assert props["selected_band_label"] == "4. Growth"
    assert any(band["is_selected"] for band in props["bands"])
    assert props["can_confirm"] is True
    assert "risk check" in props["selected_band_help"]
    assert "yes to continue to the risk check" in props["fallback_hint"]


def _sample_decision_trace() -> DecisionTrace:
    return DecisionTrace(
        questionnaire_version="v4",
        scoring_version="v5",
        portfolio_version="v3",
        profile_band="balanced",
        profile_label="Balanced",
        profile_source="liquidity_adjusted_questionnaire",
        data_source="csv_snapshot",
        optimizer_objective="max_sharpe",
        risk_free_rate=0.0,
        weight_bounds=[0.0, 0.4],
        single_asset_cap=0.4,
        covariance_psd_repair_enabled=True,
        applied_overlays=["liquidity_cash_floor:0.200000"],
        super_class_minima={"Cash": 0.2, "Fixed Income": 0.25, "Equity": 0.35},
        super_class_maxima={"Cash": 0.2, "Fixed Income": 0.55, "Equity": 0.65},
        metric_minima={},
        metric_maxima={},
        captured_answers=[
            CapturedAnswerTrace(
                question_id="portfolio_value",
                question_text=QUESTIONS_BY_ID["portfolio_value"]["text"],
                answer_type="currency_amount",
                answer_label="$50,000.00",
                used_for_scoring=False,
                used_for_allocation=True,
            )
        ],
        captured_but_not_used=[],
        limitations=[],
        scoring_policy_trace=ScoringPolicyTrace(
            method="weighted_normalized_sections",
            capacity_score=0.58,
            tolerance_score=0.61,
            final_score_before_caps=0.592,
            final_score_after_caps=0.592,
            draft_profile_band="balanced",
            draft_profile_label="Balanced",
            final_profile_band="balanced",
            final_profile_label="Balanced",
            applied_caps=[],
            section_scores={"risk_capacity": 0.58, "risk_tolerance": 0.61},
            question_scores={"time_horizon": 1.0},
        ),
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


def test_currency_amount_prompts_use_amount_specific_copy() -> None:
    question = {
        "id": "portfolio_value",
        "order": 1,
        "text": QUESTIONS_BY_ID["portfolio_value"]["text"],
        "type": "currency_amount",
        "help_text": "Enter a dollar amount at or above $25,000.",
        "validation": {"example": "$50,000"},
        "options": [],
    }

    prompt = format_question(question, total_questions=12, question_label="Portfolio value")
    edit_prompt = format_edit_prompt(
        question,
        total_questions=12,
        question_label="Portfolio value",
        current_label="$50,000.00",
    )

    assert "Enter a dollar amount at or above $25,000." in prompt
    assert prompt.count("$50,000") == 1
    assert "Let's revise this amount." in edit_prompt
    assert "option id" not in prompt
    assert "option id" not in edit_prompt


def test_render_profile_summary_numbers_answers_in_final_output() -> None:
    text = render_profile_summary(
        _sample_state(),
        _sample_profile(),
        _sample_recommendation(),
    )

    assert "Portfolio generated: Growth" in text
    assert "Draft portfolio snapshot" not in text
    assert "draft demo" not in text.casefold()
    assert "Portfolio value used for display" not in text
    assert "Recommendation basis" not in text
    assert "**Key metrics**" in text
    assert text.index("**Key metrics**") < text.index("**Portfolio mix**")
    assert "Portfolio mix" in text
    assert "**Equity:** 60%" in text
    assert "about $30,000.00" not in text
    assert "**Investments selected**" in text
    assert "Asset codes are short market identifiers" in text
    assert text.index("**Portfolio mix**") < text.index("**Investments selected**")
    assert text.index("**Equity**") < text.index("**Fixed Income**") < text.index("**Cash**")
    assert "\n\n**Fixed Income**\n" in text
    assert "\n\n**Cash**\n" in text
    assert "- **BQB** - 60.0%" in text
    assert "  Equity | Emerging Market Equity | USD" in text
    assert "USD **Fixed Income**" not in text
    assert "JMD **Cash**" not in text
    assert "- **QPESE** - 30.0%" in text
    assert "  Fixed Income | Long Government Bonds | JMD" in text
    assert "- **TBILLJMD** - 10.0%" in text
    assert "Asset code **BQB" not in text
    assert "Expected annual return:** 10.0%" in text
    assert "Annual volatility:** 7.0%" in text
    assert "Income yield:** 3.0%" in text
    assert "about $5,000.00" not in text
    assert "about $3,500.00" not in text
    assert "about $1,500.00" not in text
    assert "Answers captured" not in text
    assert "Band policy used" not in text
    assert "ticker" not in text.casefold()
    assert "optimizer" not in text.casefold()
    assert "manual mock band" not in text.casefold()
    assert "option id" not in text.casefold()


def test_render_profile_summary_holdings_fall_back_to_percentages_without_portfolio_value() -> None:
    text = render_profile_summary(
        _sample_state_without_portfolio_value(),
        _sample_profile(),
        _sample_recommendation(),
    )

    assert "**Investments selected**" in text
    assert "- **BQB** - 60.0%" in text
    assert "Asset code **BQB" not in text
    assert "about $30,000.00" not in text


def test_render_profile_summary_shows_user_facing_risk_score_for_calculated_profile() -> None:
    profile = _sample_calculated_profile().model_copy(
        update={"profile_source": "liquidity_adjusted_questionnaire"}
    )
    text = render_profile_summary(
        _sample_state(),
        profile,
        _sample_recommendation(),
        decision_trace=_sample_decision_trace(),
    )

    assert "Risk score:** 6 / 10" in text
    assert "Investor type:** Balanced" in text
    assert "Recommendation basis" not in text
    assert "**Why this profile?**" in text
    assert "medium risk capacity" in text
    assert "medium risk tolerance" in text
    assert "liquidity need is high" in text
    assert "adjusted from Growth to Balanced" in text
    assert "risk capacity 58.0%" not in text
    assert "risk tolerance 61.0%" not in text
    assert "Score 0.59 / 1.00" not in text
    assert "Profile source" not in text


def test_render_profile_summary_says_review_kept_draft_before_liquidity_adjustment() -> None:
    trace = _sample_decision_trace().model_copy(
        update={
            "profile_label": "Conservative",
            "profile_source": "liquidity_adjusted_manual_profile",
            "scoring_policy_trace": ScoringPolicyTrace(
                method="weighted_normalized_sections",
                capacity_score=0.88,
                tolerance_score=0.92,
                final_score_before_caps=0.896,
                final_score_after_caps=0.896,
                draft_profile_band="aggressive",
                draft_profile_label="Aggressive",
                final_profile_band="aggressive",
                final_profile_label="Aggressive",
                manual_override_used=True,
                manual_override_band="aggressive",
                manual_override_label="Aggressive",
                applied_caps=[],
                section_scores={"risk_capacity": 0.88, "risk_tolerance": 0.92},
                question_scores={},
            ),
            "liquidity_policy_check": LiquidityPolicyCheckTrace(
                portfolio_value=50000.0,
                major_expense_withdrawal_amount=10000.0,
                essential_monthly_expenses=0.0,
                emergency_fund_option_id="months_0",
                emergency_months_used=0.0,
                required_liquidity_amount=10000.0,
                liquidity_floor=0.20,
                selected_profile_band="aggressive",
                selected_profile_label="Aggressive",
                selected_cash_ceiling=0.10,
                selected_profile_compatible=False,
                effective_profile_band="conservative",
                effective_profile_label="Conservative",
                effective_cash_ceiling=0.30,
                profile_adjusted=True,
                user_action="auto_adjusted_to_safer_profile",
            ),
        }
    )

    text = render_profile_summary(
        _sample_state(),
        ProfileSummary(
            profile_band="conservative",
            profile_label="Conservative",
            profile_score=0.90,
            profile_source="liquidity_adjusted_manual_profile",
            profile_description="Conservative profile after liquidity adjustment.",
            dimension_scores={},
            reasons=[],
        ),
        _sample_recommendation().model_copy(
            update={"profile_band": "conservative", "profile_label": "Conservative"}
        ),
        decision_trace=trace,
    )

    assert "instead of the questionnaire draft profile, which was Aggressive" not in text
    assert "questionnaire draft profile" not in text


def test_render_profile_summary_mentions_html_report_when_attached(tmp_path: Path) -> None:
    text = render_profile_summary(
        _sample_state(),
        _sample_profile(),
        _sample_recommendation(),
        user_report_path=tmp_path / "portfolio-report.html",
    )

    assert "attached the detailed portfolio report below" in text
    assert "Open it for dollar allocations, full holdings, and the explanation notes" in text


def test_render_report_preview_and_ready_props_are_handoff_focused() -> None:
    preview = render_report_preview(
        _sample_state(),
        _sample_profile(),
        _sample_recommendation(),
        report_name="SOC portfolio report.html",
    )
    props = build_report_ready_props(
        _sample_state(),
        _sample_profile(),
        _sample_recommendation(),
        report_name="SOC portfolio report.html",
    )

    assert "**SOC portfolio report.html**" in preview
    assert "Suggested profile" in preview
    assert props["title"] == "Report ready"
    assert props["eyebrow"] == "Report ready"
    assert props["report_name"] == "SOC portfolio report.html"
    assert props["highlights"][0]["value"] == "Growth"
    assert props["highlights"][0]["detail"] == "Chosen during review"
    assert props["highlights"][2]["label"] == "Annual volatility"
    assert props["investment_note"] == "Asset codes are short market identifiers for each investment."
    assert [group["label"] for group in props["investment_groups"]] == [
        "Equity",
        "Fixed Income",
        "Cash",
    ]
    equity_holdings = props["investment_groups"][0]["holdings"]
    assert equity_holdings[0]["asset_code"] == "BQB"
    assert equity_holdings[0]["weight_label"] == "60.0%"
    assert "amount_label" not in equity_holdings[0]
    assert equity_holdings[0]["detail"] == "Equity | Emerging Market Equity | USD"


def test_build_sidebar_sections_prioritizes_progress_and_captured_facts() -> None:
    sections = build_sidebar_sections(
        _sample_state(),
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        stage="questionnaire",
        current_question={"id": "financial_knowledge", "order": 2},
    )

    assert sections[0]["key"] == "status"
    assert "Question 2 of 2" in sections[0]["content"]
    assert "Knowledge" in sections[0]["content"]
    assert sections[1]["key"] == "next"
    assert "Reply with the answer number" in sections[1]["content"]
    assert sections[2]["key"] == "captured"
    assert "Answers saved" in sections[2]["content"]
    assert "- **Portfolio value:** $50,000.00" in sections[2]["content"]


def test_build_sidebar_sections_review_and_submitted_add_decision_sections() -> None:
    review_sections = build_sidebar_sections(
        _sample_state(),
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        stage="review",
        selected_band_text="Growth",
    )
    submitted_sections = build_sidebar_sections(
        _sample_state(),
        questions_by_id=QUESTIONS_BY_ID,
        question_labels=QUESTION_LABELS,
        stage="submitted",
        profile_text="**Growth**  \nChosen during review",
        report_preview_markdown="**SOC portfolio report.html**\n\nPortfolio mix preview",
    )

    assert any(section["key"] == "band" for section in review_sections)
    assert any("Growth" in section["content"] for section in review_sections)
    assert any("yes" in section["content"].casefold() for section in review_sections)
    assert any(section["key"] == "result" for section in submitted_sections)
    assert any(section["key"] == "report" for section in submitted_sections)
    assert any("SOC portfolio report.html" in section["content"] for section in submitted_sections)


def test_custom_elements_do_not_use_removed_confirm_callback() -> None:
    element_dir = PROJECT_ROOT / "public" / "elements"
    jsx_source = "\n".join(path.read_text(encoding="utf-8") for path in element_dir.glob("*.jsx"))

    assert "review_confirm_submission" not in jsx_source
    assert "review_continue_to_risk_check" in jsx_source
    assert 'sendUserMessage("yes")' not in jsx_source
    assert 'sendUserMessage("confirm")' not in jsx_source

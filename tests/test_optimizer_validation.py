from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor import optimizer_validation, portfolio  # noqa: E402
from soc_advisor.optimizer_validation import (  # noqa: E402
    PortfolioSnapshot,
    render_validation_report,
    run_optimizer_validation,
)
from soc_advisor.portfolio import list_profile_bands  # noqa: E402
from soc_advisor.schemas import PortfolioMetrics  # noqa: E402


@pytest.fixture(scope="module")
def validation_report():
    original_loader = optimizer_validation.load_portfolio_frames
    original_portfolio_loader = portfolio.load_portfolio_frames
    original_snapshot_loader = portfolio.load_snapshot_frames
    original_portfolio_loader.cache_clear()
    original_snapshot_loader.cache_clear()
    snapshot_assets, snapshot_covariance = original_snapshot_loader()

    def snapshot_loader():
        return snapshot_assets.copy(), snapshot_covariance.copy(), "test_snapshot"

    optimizer_validation.load_portfolio_frames = snapshot_loader
    try:
        yield run_optimizer_validation(portfolio_version="v2")
    finally:
        optimizer_validation.load_portfolio_frames = original_loader
        original_portfolio_loader.cache_clear()
        original_snapshot_loader.cache_clear()


def test_validation_uses_configured_profile_order_and_labels(validation_report) -> None:
    configured = list_profile_bands("v2")

    assert [profile.profile_id for profile in validation_report.profiles] == [
        band["id"] for band in configured
    ]
    assert [profile.label for profile in validation_report.profiles] == [
        band["label"] for band in configured
    ]
    assert [profile.order for profile in validation_report.profiles] == [
        band["order"] for band in configured
    ]


def test_rendered_report_contains_audit_trace(validation_report) -> None:
    text = render_validation_report(validation_report)

    assert "SOC Advisor Optimizer Validation" in text
    assert "Portfolio config version: v2" in text
    assert "Data source used: test_snapshot" in text
    assert "Optimizer objective: max_sharpe" in text
    assert "Profile 1: Very Conservative" in text
    assert "Internal id: very_conservative" in text


def test_optimized_portfolios_pass_required_constraints(validation_report) -> None:
    assert validation_report.passed is True
    for profile in validation_report.profiles:
        assert profile.optimized.constraint_valid is True
        assert all(check.passed for check in profile.optimized.checks)


def test_scipy_cross_checks_are_structured_and_close_to_optimized_result(
    validation_report,
) -> None:
    for profile in validation_report.profiles:
        cross_check = profile.independent_solver
        assert cross_check.name == "SciPy SLSQP cross-check"
        assert cross_check.constraint_valid is True
        assert cross_check.objective_gap is not None
        assert cross_check.max_weight_difference is not None
        assert cross_check.objective_gap <= 1e-3
        assert cross_check.max_weight_difference <= 2e-2


def test_baseline_summaries_remain_available_as_internal_appendix_data(validation_report) -> None:
    expected_fields = set(PortfolioMetrics.model_fields)

    for profile in validation_report.profiles:
        snapshots: list[PortfolioSnapshot] = [
            profile.optimized,
            profile.independent_solver,
            *profile.baselines,
        ]
        for snapshot in snapshots:
            assert set(snapshot.metrics.model_dump()) == expected_fields
            assert snapshot.weights.sum() > 0


def test_equal_weight_baseline_can_be_constraint_invalid_without_failing_run(
    validation_report,
) -> None:
    equal_weight_baselines = [
        baseline
        for profile in validation_report.profiles
        for baseline in profile.baselines
        if baseline.name == "Equal-weight baseline"
    ]

    assert equal_weight_baselines
    assert any(not baseline.constraint_valid for baseline in equal_weight_baselines)
    assert validation_report.passed is True


def test_stress_checks_are_structured_and_explained(validation_report) -> None:
    for profile in validation_report.profiles:
        assert [result.name for result in profile.stress_results][:2] == [
            "Expected-return haircut",
            "Covariance risk shock",
        ]
        assert len(profile.stress_results) == 3
        assert all(isinstance(result.passed, bool) for result in profile.stress_results)
        assert all(result.detail for result in profile.stress_results)


def test_rendered_report_includes_holdings_and_baseline_comparison(
    validation_report,
) -> None:
    text = render_validation_report(validation_report)

    assert "Optimized holdings and weights" in text
    assert "Independent solver cross-check" in text
    assert "SciPy SLSQP cross-check" in text
    assert "Objective gap" in text
    assert "Baseline comparison" not in text
    assert "Equal-weight baseline" not in text
    assert "Profile-policy midpoint baseline" not in text
    assert "TBILLJMD" in text

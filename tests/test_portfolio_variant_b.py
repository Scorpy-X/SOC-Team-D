from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.portfolio import (  # noqa: E402
    build_constraint_summary,
    build_recommendation,
    load_portfolio_config,
)
from soc_advisor.services import build_manual_mock_profile  # noqa: E402


BAND_RANGES = {
    "very_conservative": {
        "Cash": (0.15, 0.35),
        "Fixed Income": (0.55, 0.80),
        "Equity": (0.00, 0.20),
        "Fund": (0.00, 0.10),
    },
    "conservative": {
        "Cash": (0.10, 0.30),
        "Fixed Income": (0.45, 0.70),
        "Equity": (0.15, 0.35),
        "Fund": (0.00, 0.10),
    },
    "balanced": {
        "Cash": (0.05, 0.20),
        "Fixed Income": (0.25, 0.55),
        "Equity": (0.35, 0.65),
        "Fund": (0.00, 0.15),
    },
    "growth": {
        "Cash": (0.00, 0.15),
        "Fixed Income": (0.10, 0.40),
        "Equity": (0.50, 0.85),
        "Fund": (0.00, 0.15),
    },
    "aggressive": {
        "Cash": (0.00, 0.10),
        "Fixed Income": (0.00, 0.25),
        "Equity": (0.70, 1.00),
        "Fund": (0.00, 0.20),
    },
}


@pytest.mark.parametrize("profile_band", list(BAND_RANGES))
def test_variant_b_band_ranges_are_feasible(profile_band: str) -> None:
    profile = build_manual_mock_profile(profile_band=profile_band)
    recommendation = build_recommendation(profile=profile)

    totals: dict[str, float] = defaultdict(float)
    for holding in recommendation.holdings:
        totals[holding.super_class] += holding.weight

    assert recommendation.holdings
    for super_class, (lower, upper) in BAND_RANGES[profile_band].items():
        actual = totals.get(super_class, 0.0)
        assert lower - 1e-4 <= actual
        assert actual <= upper + 1e-4


def test_portfolio_v3_config_has_optional_fund_and_single_asset_cap() -> None:
    portfolio_config = load_portfolio_config("v3")

    assert portfolio_config["version"] == "v3"
    for band_id, band in portfolio_config["bands"].items():
        assert band["single_asset_cap"] == pytest.approx(0.4)
        assert "Fund" in band["min_super_class"]
        assert "Fund" in band["max_super_class"]
        assert band["min_super_class"]["Fund"] == pytest.approx(0.0)
        assert band["max_super_class"]["Fund"] <= 0.20
        assert band_id in BAND_RANGES


def test_cash_floor_overlay_raises_configured_cash_minimum() -> None:
    portfolio_config = load_portfolio_config("v3")

    constraints = build_constraint_summary(
        profile_band="conservative",
        portfolio_config=portfolio_config,
        cash_floor_override=0.22,
    )

    assert constraints.super_class_minima["Cash"] == pytest.approx(0.22)
    assert constraints.super_class_maxima["Cash"] == pytest.approx(0.30)
    assert constraints.applied_overlays == ["liquidity_cash_floor:0.220000"]

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.portfolio import build_recommendation  # noqa: E402
from soc_advisor.services import build_manual_mock_profile  # noqa: E402


BAND_RANGES = {
    "very_conservative": {
        "Cash": (0.20, 0.30),
        "Fixed Income": (0.60, 0.70),
        "Equity": (0.00, 0.10),
        "Fund": (0.00, 0.00),
    },
    "conservative": {
        "Cash": (0.10, 0.20),
        "Fixed Income": (0.50, 0.60),
        "Equity": (0.20, 0.30),
        "Fund": (0.00, 0.00),
    },
    "balanced": {
        "Cash": (0.05, 0.10),
        "Fixed Income": (0.35, 0.50),
        "Equity": (0.40, 0.60),
        "Fund": (0.00, 0.00),
    },
    "growth": {
        "Cash": (0.00, 0.10),
        "Fixed Income": (0.10, 0.30),
        "Equity": (0.60, 0.80),
        "Fund": (0.00, 0.00),
    },
    "aggressive": {
        "Cash": (0.00, 0.05),
        "Fixed Income": (0.00, 0.15),
        "Equity": (0.85, 1.00),
        "Fund": (0.00, 0.00),
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

    assert totals.get("Fund", 0.0) == pytest.approx(0.0, abs=1e-8)

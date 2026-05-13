from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.risk_score_display import risk_score_10_from_normalized  # noqa: E402


def test_risk_score_10_maps_normalized_score_to_user_scale() -> None:
    assert risk_score_10_from_normalized(0.0) == 1
    assert risk_score_10_from_normalized(0.19) == 2
    assert risk_score_10_from_normalized(0.20) == 3
    assert risk_score_10_from_normalized(0.59) == 6
    assert risk_score_10_from_normalized(0.60) == 7
    assert risk_score_10_from_normalized(0.80) == 9
    assert risk_score_10_from_normalized(1.0) == 10


def test_risk_score_10_clamps_out_of_range_values() -> None:
    assert risk_score_10_from_normalized(-0.5) == 1
    assert risk_score_10_from_normalized(1.5) == 10

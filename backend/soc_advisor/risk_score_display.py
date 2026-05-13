"""Display helpers for translating normalized risk scores for users."""

from __future__ import annotations

import math


def risk_score_10_from_normalized(score: float) -> int:
    """Translate a normalized ``0.0`` to ``1.0`` score into a 1-10 display score."""

    clamped = min(max(float(score), 0.0), 1.0)
    if clamped >= 1.0:
        return 10
    return min(max(math.floor(clamped * 10) + 1, 1), 10)


def format_risk_score_10(score: float) -> str:
    """Render a normalized score as a user-facing risk score label."""

    return f"{risk_score_10_from_normalized(score)} / 10"

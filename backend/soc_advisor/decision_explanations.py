"""Plain-language explanation helpers for advisor decisions.

These helpers translate internal trace fields into client-readable explanation
lines. They do not calculate scores, change profiles, or alter allocations.
"""

from __future__ import annotations

from .risk_score_display import format_risk_score_10
from .schemas import DecisionTrace, ProfileSummary


def format_profile_basis_label(source: str) -> str:
    """Return a short user-facing label for how the profile was chosen."""

    if source == "manual_mock_band":
        return "Chosen during review"
    if source == "scored_questionnaire":
        return "Calculated from questionnaire"
    if source == "liquidity_adjusted_questionnaire":
        return "Questionnaire profile adjusted for liquidity"
    if source == "liquidity_adjusted_manual_profile":
        return "Review choice adjusted for liquidity"
    return source.replace("_", " ").capitalize()


def build_profile_explanation_lines(
    trace: DecisionTrace | None,
    *,
    profile: ProfileSummary | None = None,
) -> list[str]:
    """Explain why the final profile was used in plain language."""

    if trace is None:
        if profile is None:
            return []
        return [
            f"The report uses the {profile.profile_label} investor profile.",
        ]

    lines: list[str] = []
    scoring = trace.scoring_policy_trace
    if scoring is not None:
        if scoring.manual_override_used:
            manual_label = scoring.manual_override_label or trace.profile_label
            if manual_label == scoring.draft_profile_label:
                lines.append(
                    f"The questionnaire estimated {scoring.draft_profile_label}, "
                    "and advisor review kept that profile before the liquidity check."
                )
            else:
                lines.append(
                    f"Advisor review used the {manual_label} profile instead of the "
                    f"questionnaire draft profile, which was {scoring.draft_profile_label}."
                )
        else:
            capacity_label = _score_bucket(scoring.capacity_score)
            tolerance_label = _score_bucket(scoring.tolerance_score)
            lines.append(
                _profile_meaning_line(scoring.final_profile_label)
            )
            lines.append(
                f"Risk capacity: {capacity_label}. "
                + _capacity_meaning(capacity_label)
            )
            lines.append(
                f"Risk tolerance: {tolerance_label}. "
                + _tolerance_meaning(tolerance_label)
            )
            lines.append(
                _profile_decision_line(
                    profile_label=scoring.final_profile_label,
                    capacity_label=capacity_label,
                    tolerance_label=tolerance_label,
                )
            )
            lines.append(
                "Technical note: "
                f"capacity {_format_optional_percent(scoring.capacity_score)}, "
                f"tolerance {_format_optional_percent(scoring.tolerance_score)}, "
                f"displayed risk score {format_risk_score_10(scoring.final_score_after_caps)}."
            )

        if scoring.applied_caps:
            lines.append(
                "A cap rule limited the maximum profile because the market-drop "
                "answer showed the investor may fully exit after a severe decline."
            )
    elif profile is not None:
        lines.append(
            f"The report uses the {profile.profile_label} investor profile selected during review."
        )

    liquidity = trace.liquidity_policy_check
    if liquidity is not None:
        liquidity_label = _liquidity_need_bucket(liquidity.liquidity_floor)
        if liquidity.profile_adjusted:
            lines.append(
                f"Liquidity need: {liquidity_label}. The liquidity check adjusted the profile "
                f"from {liquidity.selected_profile_label} to {liquidity.effective_profile_label} "
                "so the portfolio could support the required Cash reserve."
            )
        else:
            lines.append(
                f"Liquidity need: {liquidity_label}. The selected profile could support the "
                "required Cash reserve without adjustment."
            )

    return lines


def build_concise_profile_reason(
    trace: DecisionTrace | None,
    *,
    profile: ProfileSummary,
) -> list[str]:
    """Return short chat-ready reasons for the final investor profile."""

    if trace is None:
        return [f"The questionnaire supports a {profile.profile_label} investor profile."]

    lines: list[str] = []
    scoring = trace.scoring_policy_trace
    if scoring is not None and scoring.manual_override_used:
        manual_label = scoring.manual_override_label or profile.profile_label
        draft_label = scoring.draft_profile_label or profile.profile_label
        if manual_label == draft_label:
            lines.append(
                f"The questionnaire pointed to {draft_label}, and that profile was kept during review."
            )
        else:
            lines.append(
                f"The questionnaire pointed to {draft_label}; review selected {manual_label} before the liquidity check."
            )
    elif scoring is not None:
        capacity_label = _score_bucket(scoring.capacity_score)
        tolerance_label = _score_bucket(scoring.tolerance_score)
        lines.append(
            f"Your answers point to {capacity_label} risk capacity and {tolerance_label} risk tolerance."
        )
        if scoring.applied_caps:
            lines.append(
                "The market-drop answer limited the maximum profile to keep the recommendation more conservative."
            )
    else:
        lines.append(f"The questionnaire supports a {profile.profile_label} investor profile.")

    liquidity = trace.liquidity_policy_check
    if liquidity is not None:
        liquidity_label = _liquidity_need_bucket(liquidity.liquidity_floor)
        if liquidity.profile_adjusted:
            lines.append(
                f"Your liquidity need is {liquidity_label}, so the profile was adjusted "
                f"from {liquidity.selected_profile_label} to {liquidity.effective_profile_label}."
            )
        else:
            lines.append(
                f"Your liquidity need is {liquidity_label} and fits the selected profile."
            )

    return lines


def build_liquidity_explanation_lines(trace: DecisionTrace | None) -> list[str]:
    """Explain the current liquidity check without exposing internal trace names."""

    if trace is None or trace.liquidity_policy_check is None:
        return []
    liquidity = trace.liquidity_policy_check
    lines = [
        (
            "Required liquidity was calculated as expected major withdrawals plus "
            "essential monthly expenses multiplied by the selected emergency reserve."
        ),
        (
            f"The required Cash reserve was {_format_money(liquidity.required_liquidity_amount)}, "
            f"or {_format_percent(liquidity.liquidity_floor)} of the portfolio value entered."
        ),
    ]
    if liquidity.profile_adjusted:
        lines.append(
            f"The original {liquidity.selected_profile_label} profile could not support that Cash level, "
            f"so the compatible profile used was {liquidity.effective_profile_label}."
        )
    return lines


def _format_optional_percent(value: float | None) -> str:
    if value is None:
        return "not available"
    return _format_percent(value)


def _score_bucket(value: float | None) -> str:
    if value is None:
        return "available"
    if value < 0.40:
        return "low"
    if value < 0.70:
        return "medium"
    return "high"


def _liquidity_need_bucket(liquidity_floor: float) -> str:
    if liquidity_floor < 0.10:
        return "low"
    if liquidity_floor < 0.20:
        return "medium"
    return "high"


def _profile_meaning_line(profile_label: str) -> str:
    meanings = {
        "Very Conservative": (
            "Very Conservative means the portfolio is focused mainly on capital preservation "
            "and liquidity."
        ),
        "Conservative": (
            "Conservative means the portfolio prioritizes stability and income, with limited "
            "growth exposure."
        ),
        "Balanced": (
            "Balanced means the portfolio keeps a mix of stability and growth exposure."
        ),
        "Growth": (
            "Growth means the portfolio targets higher long-term growth and accepts more "
            "short-term movement."
        ),
        "Aggressive": (
            "Aggressive means the portfolio prioritizes long-term growth and assumes the "
            "investor can tolerate large short-term losses."
        ),
    }
    return meanings.get(profile_label, f"{profile_label} is the investor profile used for this report.")


def _capacity_meaning(label: str) -> str:
    if label == "high":
        return "The financial situation and time horizon answers support a stronger ability to take investment risk."
    if label == "medium":
        return "The financial situation and time horizon answers support a moderate ability to take investment risk."
    if label == "low":
        return "The financial situation and time horizon answers suggest limited ability to take investment risk."
    return "The available answers did not provide a clear capacity signal."


def _tolerance_meaning(label: str) -> str:
    if label == "high":
        return "The market-decline and loss-comfort answers suggest stronger comfort with short-term portfolio movement."
    if label == "medium":
        return "The market-decline and loss-comfort answers suggest moderate comfort with short-term portfolio movement."
    if label == "low":
        return "The market-decline and loss-comfort answers suggest low comfort with short-term losses."
    return "The available answers did not provide a clear tolerance signal."


def _profile_decision_line(
    *,
    profile_label: str,
    capacity_label: str,
    tolerance_label: str,
) -> str:
    if capacity_label == "high" and tolerance_label == "low":
        return (
            f"Decision: the system selected {profile_label} because capacity supports growth, "
            "but tolerance argues against a more aggressive portfolio."
        )
    if capacity_label == "low" and tolerance_label == "high":
        return (
            f"Decision: the system selected {profile_label} because lower capacity keeps the "
            "portfolio more cautious even though tolerance is higher."
        )
    if capacity_label == "high" and tolerance_label == "high":
        return (
            f"Decision: the system selected {profile_label} because both capacity and tolerance "
            "support a growth-oriented portfolio."
        )
    if capacity_label == "low" and tolerance_label == "low":
        return (
            f"Decision: the system selected {profile_label} because both capacity and tolerance "
            "point toward a more defensive portfolio."
        )
    return (
        f"Decision: the system selected {profile_label} because the capacity and tolerance "
        "answers together support a middle profile."
    )


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_money(value: float) -> str:
    return f"${value:,.2f}"

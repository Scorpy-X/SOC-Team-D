"""Human-readable optimizer validation for the SOC advisor.

This module does not change the recommendation engine. It runs the current
portfolio path for every configured profile and produces an audit-style text
report that is useful for demos, reviews, and defense.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .portfolio import (
    _prepare_covariance_input,
    _optimize_portfolio,
    _resolve_weight_bounds,
    build_constraint_summary,
    list_profile_bands,
    load_portfolio_config,
    load_portfolio_frames,
)
from .schemas import ConstraintSummary, PortfolioMetrics
from .settings import get_settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
DEFAULT_TOP_HOLDINGS = 25
WEIGHT_TOLERANCE = 1e-4


@dataclass(frozen=True)
class ValidationCheck:
    """One pass/fail line in the audit report."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Summary values for one optimized or baseline portfolio."""

    name: str
    weights: pd.Series
    metrics: PortfolioMetrics
    checks: list[ValidationCheck]
    objective_value: float | None = None
    objective_gap: float | None = None
    max_weight_difference: float | None = None

    @property
    def constraint_valid(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass(frozen=True)
class StressResult:
    """Result of one sensitivity run."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ProfileValidation:
    """All validation evidence for one configured profile."""

    order: int
    profile_id: str
    label: str
    description: str
    constraints: ConstraintSummary
    optimized: PortfolioSnapshot
    independent_solver: PortfolioSnapshot
    baselines: list[PortfolioSnapshot]
    stress_results: list[StressResult]

    @property
    def required_checks_passed(self) -> bool:
        return self.optimized.constraint_valid


@dataclass(frozen=True)
class OptimizerValidationReport:
    """Top-level validation result."""

    generated_at: datetime
    portfolio_version: str
    portfolio_name: str
    data_source: str
    assets: pd.DataFrame
    asset_count: int
    covariance_shape: tuple[int, int]
    optimizer_config: dict[str, Any]
    profiles: list[ProfileValidation]

    @property
    def passed(self) -> bool:
        return all(profile.required_checks_passed for profile in self.profiles)


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_float(value: float) -> str:
    return f"{value:.4f}"


def _metrics_from_weights(
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    weights: pd.Series,
) -> PortfolioMetrics:
    """Calculate summary metrics for baselines without invoking the optimizer."""

    aligned_weights = weights.reindex(assets.index, fill_value=0.0).astype(float)
    covariance_input = covariance.loc[assets.index, assets.index].astype(float)
    variance = float(aligned_weights.to_numpy() @ covariance_input.to_numpy() @ aligned_weights.to_numpy())
    volatility = float(np.sqrt(max(variance, 0.0)))
    return PortfolioMetrics(
        expected_return=float(aligned_weights @ assets["total_expected_return"].astype(float)),
        volatility=volatility,
        income_yield_ann=float(aligned_weights @ assets["income_yield_ann"].astype(float)),
        modified_duration=float(aligned_weights @ assets["modified_duration"].astype(float)),
        expense_ratio_ann=float(aligned_weights @ assets["expense_ratio_ann"].astype(float)),
        rate_beta=float(aligned_weights @ assets["rate_beta"].astype(float)),
        inflation_beta=float(aligned_weights @ assets["inflation_beta"].astype(float)),
        fx_beta=float(aligned_weights @ assets["fx_beta"].astype(float)),
    )


def _sharpe_ratio(metrics: PortfolioMetrics, *, risk_free_rate: float) -> float:
    if metrics.volatility <= 0:
        return float("-inf")
    return (metrics.expected_return - risk_free_rate) / metrics.volatility


def _super_class_totals(assets: pd.DataFrame, weights: pd.Series) -> dict[str, float]:
    weighted_assets = assets.loc[weights.index].copy()
    weighted_assets["weight"] = weights
    return weighted_assets.groupby("super_class")["weight"].sum().to_dict()


def _largest_holding_weight(weights: pd.Series) -> float:
    if weights.empty:
        return 0.0
    return float(weights.max())


def validate_weights(
    assets: pd.DataFrame,
    weights: pd.Series,
    constraints: ConstraintSummary,
) -> list[ValidationCheck]:
    """Check whether one weight vector obeys the active portfolio constraints."""

    total_weight = float(weights.sum())
    checks = [
        ValidationCheck(
            name="Weights sum to 100%",
            passed=abs(total_weight - 1.0) <= WEIGHT_TOLERANCE,
            detail=f"Observed total: {_format_percent(total_weight)}",
        ),
        ValidationCheck(
            name="Single-asset cap",
            passed=_largest_holding_weight(weights) <= constraints.single_asset_cap + WEIGHT_TOLERANCE,
            detail=(
                f"Largest holding: {_format_percent(_largest_holding_weight(weights))}; "
                f"cap: {_format_percent(constraints.single_asset_cap)}"
            ),
        ),
    ]

    totals = _super_class_totals(assets, weights)
    for super_class in sorted(set(constraints.super_class_minima) | set(constraints.super_class_maxima)):
        lower = constraints.super_class_minima.get(super_class, 0.0)
        upper = constraints.super_class_maxima.get(super_class, 1.0)
        actual = totals.get(super_class, 0.0)
        checks.append(
            ValidationCheck(
                name=f"{super_class} range",
                passed=lower - WEIGHT_TOLERANCE <= actual <= upper + WEIGHT_TOLERANCE,
                detail=(
                    f"Observed: {_format_percent(actual)}; "
                    f"allowed: {_format_percent(lower)}-{_format_percent(upper)}"
                ),
            )
        )
    return checks


def _build_equal_weight_baseline(
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
) -> PortfolioSnapshot:
    weights = pd.Series(1.0 / len(assets), index=assets.index, dtype=float)
    return PortfolioSnapshot(
        name="Equal-weight baseline",
        weights=weights,
        metrics=_metrics_from_weights(assets, covariance, weights),
        checks=validate_weights(assets, weights, constraints),
    )


def _target_super_class_weights(constraints: ConstraintSummary) -> dict[str, float]:
    """Use profile midpoint ranges, then adjust to a full 100% target mix."""

    classes = sorted(set(constraints.super_class_minima) | set(constraints.super_class_maxima))
    targets = {
        super_class: (
            constraints.super_class_minima.get(super_class, 0.0)
            + constraints.super_class_maxima.get(super_class, 1.0)
        )
        / 2.0
        for super_class in classes
    }

    total = sum(targets.values())
    if total < 1.0:
        remaining = 1.0 - total
        for super_class in classes:
            spare = constraints.super_class_maxima.get(super_class, 1.0) - targets[super_class]
            addition = min(spare, remaining)
            targets[super_class] += addition
            remaining -= addition
            if remaining <= WEIGHT_TOLERANCE:
                break
    elif total > 1.0:
        excess = total - 1.0
        for super_class in reversed(classes):
            reducible = targets[super_class] - constraints.super_class_minima.get(super_class, 0.0)
            reduction = min(reducible, excess)
            targets[super_class] -= reduction
            excess -= reduction
            if excess <= WEIGHT_TOLERANCE:
                break
    return {key: value for key, value in targets.items() if value > WEIGHT_TOLERANCE}


def _allocate_class_weight_equally(
    tickers: list[str],
    target_weight: float,
    single_asset_cap: float,
) -> pd.Series:
    if not tickers or target_weight <= 0:
        return pd.Series(dtype=float)

    remaining = target_weight
    open_tickers = list(tickers)
    allocations: dict[str, float] = {}
    while open_tickers and remaining > WEIGHT_TOLERANCE:
        equal_share = remaining / len(open_tickers)
        if equal_share <= single_asset_cap + WEIGHT_TOLERANCE:
            for ticker in open_tickers:
                allocations[ticker] = allocations.get(ticker, 0.0) + equal_share
            remaining = 0.0
            break

        ticker = open_tickers.pop(0)
        allocations[ticker] = allocations.get(ticker, 0.0) + single_asset_cap
        remaining -= single_asset_cap

    return pd.Series(allocations, dtype=float)


def _build_profile_policy_baseline(
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
) -> PortfolioSnapshot:
    """Build a simple rules-only portfolio from profile midpoint targets."""

    weights = pd.Series(dtype=float)
    targets = _target_super_class_weights(constraints)
    for super_class, target_weight in targets.items():
        tickers = assets.index[assets["super_class"] == super_class].astype(str).tolist()
        class_weights = _allocate_class_weight_equally(
            tickers,
            target_weight,
            constraints.single_asset_cap,
        )
        weights = pd.concat([weights, class_weights])

    weights = weights.groupby(level=0).sum().astype(float)
    return PortfolioSnapshot(
        name="Profile-policy midpoint baseline",
        weights=weights,
        metrics=_metrics_from_weights(assets, covariance, weights),
        checks=validate_weights(assets, weights, constraints),
    )


def _clean_scipy_weights(raw_weights: np.ndarray, index: pd.Index) -> pd.Series:
    cleaned = pd.Series(raw_weights, index=index, dtype=float)
    cleaned[cleaned.abs() < WEIGHT_TOLERANCE] = 0.0
    cleaned = cleaned.round(6)
    return cleaned[cleaned > 0].sort_values(ascending=False)


def _scipy_constraints(
    assets: pd.DataFrame,
    constraints: ConstraintSummary,
) -> list[dict[str, Any]]:
    """Build SLSQP constraints matching the active portfolio policy."""

    scipy_constraints: list[dict[str, Any]] = [
        {"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)}
    ]

    for super_class in sorted(set(constraints.super_class_minima) | set(constraints.super_class_maxima)):
        mask = (assets["super_class"] == super_class).astype(float).to_numpy()
        lower = constraints.super_class_minima.get(super_class, 0.0)
        upper = constraints.super_class_maxima.get(super_class, 1.0)
        scipy_constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights, m=mask, floor=lower: float(weights @ m - floor),
            }
        )
        scipy_constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights, m=mask, cap=upper: float(cap - weights @ m),
            }
        )

    for metric_name, minimum in constraints.metric_minima.items():
        vector = assets[metric_name].astype(float).to_numpy()
        scipy_constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights, v=vector, floor=minimum: float(weights @ v - floor),
            }
        )

    for metric_name, maximum in constraints.metric_maxima.items():
        vector = assets[metric_name].astype(float).to_numpy()
        scipy_constraints.append(
            {
                "type": "ineq",
                "fun": lambda weights, v=vector, cap=maximum: float(cap - weights @ v),
            }
        )

    return scipy_constraints


def _feasible_initial_weights(
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
    optimized_weights: pd.Series,
) -> pd.Series:
    """Use the simple policy baseline as the first SLSQP starting point."""

    baseline = _build_profile_policy_baseline(assets, covariance, constraints)
    if baseline.constraint_valid:
        return baseline.weights.reindex(assets.index, fill_value=0.0).astype(float)
    return optimized_weights.reindex(assets.index, fill_value=0.0).astype(float)


def _build_scipy_cross_check(
    *,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
    optimized: PortfolioSnapshot,
) -> PortfolioSnapshot:
    """Replay the same max-Sharpe problem through SciPy SLSQP.

    This is not a second investment model. It is an independent numerical path
    for checking that the configured inputs and constraints lead to a similar
    feasible solution outside PyPortfolioOpt's wrapper.
    """

    covariance_input = _prepare_covariance_input(covariance, optimizer_config)
    ordered_assets = assets.copy()
    mu = ordered_assets["total_expected_return"].astype(float).to_numpy()
    matrix = covariance_input.loc[ordered_assets.index, ordered_assets.index].astype(float).to_numpy()
    risk_free_rate = float(optimizer_config.get("risk_free_rate", 0.0))
    lower_bound, upper_bound = _resolve_weight_bounds(constraints, optimizer_config)
    x0 = _feasible_initial_weights(
        ordered_assets,
        covariance_input,
        constraints,
        optimized.weights,
    ).to_numpy()

    def negative_sharpe(weights: np.ndarray) -> float:
        portfolio_return = float(weights @ mu)
        variance = float(weights @ matrix @ weights)
        volatility = float(np.sqrt(max(variance, 1e-16)))
        return -((portfolio_return - risk_free_rate) / volatility)

    result = minimize(
        negative_sharpe,
        x0=x0,
        method="SLSQP",
        bounds=[(lower_bound, upper_bound)] * len(ordered_assets),
        constraints=_scipy_constraints(ordered_assets, constraints),
        options={"ftol": 1e-9, "maxiter": 1000, "disp": False},
    )

    if not result.success:
        weights = optimized.weights.copy()
        metrics = _metrics_from_weights(ordered_assets, covariance_input, weights)
        checks = validate_weights(ordered_assets, weights, constraints)
        checks.append(
            ValidationCheck(
                name="SciPy solver convergence",
                passed=False,
                detail=str(result.message),
            )
        )
        return PortfolioSnapshot(
            name="SciPy SLSQP cross-check",
            weights=weights,
            metrics=metrics,
            checks=checks,
            objective_value=None,
            objective_gap=None,
            max_weight_difference=None,
        )

    weights = _clean_scipy_weights(result.x, ordered_assets.index)
    metrics = _metrics_from_weights(ordered_assets, covariance_input, weights)
    checks = validate_weights(ordered_assets, weights, constraints)
    checks.append(
        ValidationCheck(
            name="SciPy solver convergence",
            passed=True,
            detail=str(result.message),
        )
    )
    scipy_sharpe = _sharpe_ratio(metrics, risk_free_rate=risk_free_rate)
    optimized_sharpe = _sharpe_ratio(optimized.metrics, risk_free_rate=risk_free_rate)
    aligned_scipy = weights.reindex(ordered_assets.index, fill_value=0.0)
    aligned_optimized = optimized.weights.reindex(ordered_assets.index, fill_value=0.0)
    return PortfolioSnapshot(
        name="SciPy SLSQP cross-check",
        weights=weights,
        metrics=metrics,
        checks=checks,
        objective_value=scipy_sharpe,
        objective_gap=abs(scipy_sharpe - optimized_sharpe),
        max_weight_difference=float((aligned_scipy - aligned_optimized).abs().max()),
    )


def _optimize_snapshot(
    *,
    name: str,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
) -> PortfolioSnapshot:
    weights, metrics = _optimize_portfolio(
        assets=assets,
        covariance=covariance,
        constraints=constraints,
        optimizer_config=optimizer_config,
    )
    return PortfolioSnapshot(
        name=name,
        weights=weights,
        metrics=metrics,
        checks=validate_weights(assets, weights, constraints),
        objective_value=_sharpe_ratio(
            metrics,
            risk_free_rate=float(optimizer_config.get("risk_free_rate", 0.0)),
        ),
    )


def _run_stress_checks(
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
    optimized_weights: pd.Series,
) -> list[StressResult]:
    """Run small sensitivity checks and record failures as audit evidence."""

    scenarios: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []

    return_haircut_assets = assets.copy()
    return_haircut_assets["total_expected_return"] = (
        return_haircut_assets["total_expected_return"].astype(float) * 0.9
    )
    scenarios.append(("Expected-return haircut", return_haircut_assets, covariance.copy()))

    scenarios.append(("Covariance risk shock", assets.copy(), covariance.astype(float) * 1.1))

    if optimized_weights.empty:
        scenarios.append(("Largest holding removed", assets.iloc[0:0].copy(), covariance.iloc[0:0, 0:0].copy()))
    else:
        largest_ticker = str(optimized_weights.idxmax())
        reduced_assets = assets.drop(index=largest_ticker)
        reduced_covariance = covariance.drop(index=largest_ticker, columns=largest_ticker)
        scenarios.append((f"Largest holding removed ({largest_ticker})", reduced_assets, reduced_covariance))

    results: list[StressResult] = []
    for name, scenario_assets, scenario_covariance in scenarios:
        try:
            scenario_snapshot = _optimize_snapshot(
                name=name,
                assets=scenario_assets,
                covariance=scenario_covariance,
                constraints=constraints,
                optimizer_config=optimizer_config,
            )
        except Exception as exc:
            results.append(StressResult(name=name, passed=False, detail=str(exc)))
            continue

        if scenario_snapshot.constraint_valid:
            results.append(
                StressResult(
                    name=name,
                    passed=True,
                    detail=(
                        f"Feasible. Return {_format_percent(scenario_snapshot.metrics.expected_return)}, "
                        f"movement {_format_percent(scenario_snapshot.metrics.volatility)}."
                    ),
                )
            )
        else:
            failed = "; ".join(
                f"{check.name}: {check.detail}"
                for check in scenario_snapshot.checks
                if not check.passed
            )
            results.append(StressResult(name=name, passed=False, detail=failed))
    return results


def run_optimizer_validation(
    *,
    portfolio_version: str | None = None,
) -> OptimizerValidationReport:
    """Run the full validation evidence pack for every configured profile."""

    settings = get_settings()
    resolved_version = portfolio_version or settings.portfolio_version
    portfolio_config = load_portfolio_config(resolved_version)
    assets, covariance, data_source = load_portfolio_frames()
    optimizer_config = portfolio_config["optimizer"]

    profiles: list[ProfileValidation] = []
    for band in list_profile_bands(resolved_version):
        constraints = build_constraint_summary(
            profile_band=band["id"],
            portfolio_config=portfolio_config,
        )
        optimized = _optimize_snapshot(
            name="Optimized portfolio",
            assets=assets,
            covariance=covariance,
            constraints=constraints,
            optimizer_config=optimizer_config,
        )
        independent_solver = _build_scipy_cross_check(
            assets=assets,
            covariance=covariance,
            constraints=constraints,
            optimizer_config=optimizer_config,
            optimized=optimized,
        )
        baselines = [
            _build_equal_weight_baseline(assets, covariance, constraints),
            _build_profile_policy_baseline(assets, covariance, constraints),
        ]
        stress_results = _run_stress_checks(
            assets,
            covariance,
            constraints,
            optimizer_config,
            optimized.weights,
        )
        profiles.append(
            ProfileValidation(
                order=int(band["order"]),
                profile_id=str(band["id"]),
                label=str(band["label"]),
                description=str(band["description"]),
                constraints=constraints,
                optimized=optimized,
                independent_solver=independent_solver,
                baselines=baselines,
                stress_results=stress_results,
            )
        )

    return OptimizerValidationReport(
        generated_at=datetime.now().astimezone(),
        portfolio_version=str(portfolio_config["version"]),
        portfolio_name=str(portfolio_config.get("name", "")),
        data_source=data_source,
        assets=assets,
        asset_count=len(assets),
        covariance_shape=tuple(covariance.shape),
        optimizer_config=optimizer_config,
        profiles=profiles,
    )


def _render_check(check: ValidationCheck) -> str:
    status = "PASS" if check.passed else "FAIL"
    return f"{status} - {check.name}: {check.detail}"


def _render_metrics(snapshot: PortfolioSnapshot) -> list[str]:
    metrics = snapshot.metrics
    return [
        f"- Expected yearly return: {_format_percent(metrics.expected_return)}",
        f"- Expected yearly movement: {_format_percent(metrics.volatility)}",
        f"- Estimated income: {_format_percent(metrics.income_yield_ann)}",
        f"- Expense ratio: {_format_percent(metrics.expense_ratio_ann)}",
        f"- Modified duration: {_format_float(metrics.modified_duration)}",
        f"- Largest holding: {_format_percent(_largest_holding_weight(snapshot.weights))}",
        f"- Constraint valid: {'PASS' if snapshot.constraint_valid else 'FAIL'}",
    ]


def _render_holdings(assets: pd.DataFrame, weights: pd.Series) -> list[str]:
    lines: list[str] = []
    for ticker, weight in weights.sort_values(ascending=False).items():
        row = assets.loc[ticker]
        lines.append(
            f"- {ticker}: {_format_percent(float(weight))} | "
            f"{row['super_class']} | {row['asset_class']} | {row['currency']}"
        )
    return lines


def _render_super_class_mix(assets: pd.DataFrame, weights: pd.Series) -> list[str]:
    totals = _super_class_totals(assets, weights)
    return [
        f"- {super_class}: {_format_percent(weight)}"
        for super_class, weight in sorted(totals.items())
        if weight > WEIGHT_TOLERANCE
    ]


def _render_baseline_table(baselines: list[PortfolioSnapshot], optimized: PortfolioSnapshot) -> list[str]:
    rows = [optimized, *baselines]
    lines = [
        "Method | Return | Movement | Income | Expense | Duration | Largest Holding | Constraints",
        "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---",
    ]
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.name,
                    _format_percent(row.metrics.expected_return),
                    _format_percent(row.metrics.volatility),
                    _format_percent(row.metrics.income_yield_ann),
                    _format_percent(row.metrics.expense_ratio_ann),
                    _format_float(row.metrics.modified_duration),
                    _format_percent(_largest_holding_weight(row.weights)),
                    "PASS" if row.constraint_valid else "FAIL",
                ]
            )
        )
    return lines


def _render_independent_solver_cross_check(
    optimized: PortfolioSnapshot,
    independent_solver: PortfolioSnapshot,
) -> list[str]:
    lines = [
        f"- Cross-check path: {independent_solver.name}",
        f"- PyPortfolioOpt Sharpe objective: {_format_float(optimized.objective_value or 0.0)}",
        f"- SciPy Sharpe objective: {_format_float(independent_solver.objective_value or 0.0)}",
        f"- Objective gap: {_format_float(independent_solver.objective_gap or 0.0)}",
        f"- Largest weight difference: {_format_percent(independent_solver.max_weight_difference or 0.0)}",
        f"- SciPy constraints valid: {'PASS' if independent_solver.constraint_valid else 'FAIL'}",
        "",
        "SciPy constraint checks",
    ]
    lines.extend(_render_check(check) for check in independent_solver.checks)
    return lines


def render_validation_report(report: OptimizerValidationReport) -> str:
    """Render the full validation report as plain text/markdown."""

    lines = [
        "SOC Advisor Optimizer Validation",
        f"Generated: {report.generated_at.isoformat(timespec='seconds')}",
        "",
        "Overall result: " + ("PASS" if report.passed else "FAIL"),
        "",
        "Audit trace",
        f"- Portfolio config version: {report.portfolio_version}",
        f"- Portfolio config name: {report.portfolio_name}",
        f"- Data source used: {report.data_source}",
        f"- Asset count: {report.asset_count}",
        f"- Covariance shape: {report.covariance_shape[0]} x {report.covariance_shape[1]}",
        f"- Optimizer objective: {report.optimizer_config.get('objective')}",
        f"- Risk-free rate: {report.optimizer_config.get('risk_free_rate')}",
        f"- Weight bounds: {report.optimizer_config.get('weight_bounds')}",
        f"- PSD repair enabled: {report.optimizer_config.get('repair_nonpositive_semidefinite')}",
        "",
        "Validation claim",
        "This report checks whether the optimizer integration obeys configured constraints and can be replayed through an independent SciPy SLSQP solver path. It does not prove that the output is suitable financial advice.",
        "",
    ]

    for profile in report.profiles:
        lines.extend(
            [
                "=" * 72,
                f"Profile {profile.order}: {profile.label}",
                f"Internal id: {profile.profile_id}",
                f"Description: {profile.description}",
                "",
                "Profile audit trace",
                f"- Objective: {profile.constraints.objective}",
                f"- Single-asset cap: {_format_percent(profile.constraints.single_asset_cap)}",
                f"- Superclass minima: {profile.constraints.super_class_minima}",
                f"- Superclass maxima: {profile.constraints.super_class_maxima}",
                "",
                "Optimized portfolio summary",
                *(_render_metrics(profile.optimized)),
                "",
                "Optimized superclass mix",
                *(_render_super_class_mix(report.assets, profile.optimized.weights)),
                "",
                "Optimized holdings and weights",
                *(_render_holdings(report.assets, profile.optimized.weights)),
                "",
                "Constraint checks",
                *(_render_check(check) for check in profile.optimized.checks),
                "",
                "Independent solver cross-check",
                *_render_independent_solver_cross_check(
                    profile.optimized,
                    profile.independent_solver,
                ),
            ]
        )
        lines.extend(["", "Stress checks"])
        for stress in profile.stress_results:
            status = "PASS" if stress.passed else "REVIEW"
            lines.append(f"{status} - {stress.name}: {stress.detail}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_validation_logs(
    report_text: str,
    *,
    output_dir: Path = VALIDATION_DIR,
    generated_at: datetime | None = None,
) -> tuple[Path, Path]:
    """Write latest and timestamped validation logs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_generated_at = generated_at or datetime.now().astimezone()
    timestamp = resolved_generated_at.strftime("%Y-%m-%d-%H%M%S")
    timestamped_path = output_dir / f"optimizer-validation-{timestamp}.txt"
    latest_path = output_dir / "optimizer-validation-latest.txt"
    timestamped_path.write_text(report_text, encoding="utf-8")
    latest_path.write_text(report_text, encoding="utf-8")
    return latest_path, timestamped_path

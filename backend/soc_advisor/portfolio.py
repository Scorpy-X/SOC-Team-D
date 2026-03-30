"""Portfolio recommendation helpers built on PyPortfolioOpt.

This module is the allocation engine.

It starts only after a profile band is already known, whether that band came
from questionnaire scoring or from the current manual mock-band demo flow.

Inputs:

- a profile band such as ``balanced`` or ``growth``
- the portfolio config
- the asset and covariance snapshots

Outputs:

- ticker weights
- portfolio summary metrics
- the exact constraints that were applied
- notes explaining the active allocation path
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from pypfopt import EfficientFrontier, risk_models
from pypfopt.exceptions import OptimizationError

from .schemas import (
    ConstraintSummary,
    PortfolioHolding,
    PortfolioMetrics,
    ProfileSummary,
    RecommendationSummary,
)
from .settings import get_settings


settings = get_settings()
DEFAULT_PROFILE_BAND_ORDER = (
    "very_conservative",
    "conservative",
    "balanced",
    "growth",
    "aggressive",
)
ASSET_FIELDS = [
    "super_class",
    "asset_class",
    "currency",
    "total_expected_return",
    "income_yield_ann",
    "volatility_ann",
    "modified_duration",
    "expense_ratio_ann",
    "rate_beta",
    "inflation_beta",
    "fx_beta",
]
METRIC_COLUMNS = (
    "income_yield_ann",
    "modified_duration",
    "expense_ratio_ann",
    "rate_beta",
    "inflation_beta",
    "fx_beta",
)


@lru_cache(maxsize=8)
def load_portfolio_config(version: str) -> dict[str, Any]:
    """Load one portfolio config JSON file by version."""

    path = settings.portfolio_dir / f"{version}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio config version '{version}' was not found.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _label_from_band_id(profile_band: str) -> str:
    """Convert a band id into a readable label."""

    return profile_band.replace("_", " ").title()


def _get_band_definition(
    portfolio_config: dict[str, Any],
    profile_band: str,
) -> dict[str, Any]:
    """Fetch one configured portfolio band or fail clearly."""

    try:
        return portfolio_config["bands"][profile_band]
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown portfolio profile band '{profile_band}'.",
        ) from exc


def list_profile_bands(
    portfolio_version: str | None = None,
) -> list[dict[str, Any]]:
    """Return the configured portfolio bands in display order."""

    resolved_version = portfolio_version or settings.portfolio_version
    portfolio_config = load_portfolio_config(resolved_version)
    ordered_band_ids = portfolio_config.get("band_order", list(DEFAULT_PROFILE_BAND_ORDER))

    bands: list[dict[str, Any]] = []
    for order, band_id in enumerate(ordered_band_ids, start=1):
        band = _get_band_definition(portfolio_config, band_id)
        bands.append(
            {
                "order": order,
                "id": band_id,
                "label": str(band.get("label", _label_from_band_id(band_id))),
                "description": str(band.get("description", "")),
                "single_asset_cap": float(band["single_asset_cap"]),
                "super_class_minima": {
                    key: float(value)
                    for key, value in band.get("min_super_class", {}).items()
                },
                "super_class_maxima": {
                    key: float(value)
                    for key, value in band.get("max_super_class", {}).items()
                },
            }
        )
    return bands


def _load_assets_snapshot(path: Path) -> pd.DataFrame:
    """Load the asset snapshot and verify the columns the optimizer expects."""

    frame = pd.read_csv(path)
    if "ticker" not in frame.columns:
        raise HTTPException(
            status_code=500,
            detail=f"Snapshot '{path.name}' is missing the 'ticker' column.",
        )
    frame = frame.set_index("ticker")
    for column in ASSET_FIELDS:
        if column not in frame.columns:
            raise HTTPException(
                status_code=500,
                detail=f"Snapshot '{path.name}' is missing required field '{column}'.",
            )
    return frame


def _load_square_matrix_snapshot(path: Path) -> pd.DataFrame:
    """Load a CSV snapshot that is meant to behave like a square matrix."""

    frame = pd.read_csv(path)
    if frame.shape[0] != frame.shape[1]:
        raise HTTPException(
            status_code=500,
            detail=f"Snapshot '{path.name}' is not square and cannot be used as a matrix.",
        )
    frame.index = frame.columns
    return frame.apply(pd.to_numeric, errors="coerce")


@lru_cache(maxsize=1)
def load_snapshot_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and align the portfolio snapshot data once per process.

    Alignment matters because the expected-return vector and covariance matrix
    must refer to the same tickers in the same order before optimization.
    """

    assets = _load_assets_snapshot(settings.snapshot_dir / "full_assets_df.csv")
    covariance = _load_square_matrix_snapshot(
        settings.snapshot_dir / "full_asset_covariance_df.csv"
    )

    common_tickers = [
        ticker
        for ticker in assets.index
        if ticker in covariance.index and ticker in covariance.columns
    ]
    if not common_tickers:
        raise HTTPException(
            status_code=500,
            detail="No overlapping tickers were found between the asset table and covariance matrix.",
        )

    assets = assets.loc[common_tickers, ASSET_FIELDS].copy()
    covariance = covariance.loc[common_tickers, common_tickers].copy()

    for column in ASSET_FIELDS:
        if column in ("super_class", "asset_class", "currency"):
            assets[column] = assets[column].fillna("").astype(str)
        else:
            assets[column] = pd.to_numeric(assets[column], errors="coerce").fillna(0.0)

    return assets, covariance


def build_constraint_summary(
    *,
    profile_band: str,
    portfolio_config: dict[str, Any],
    fallback_note: str | None = None,
) -> ConstraintSummary:
    """Translate one profile band into a Variant B constraint set."""

    base = _get_band_definition(portfolio_config, profile_band)

    super_minima = {
        key: float(value) for key, value in base.get("min_super_class", {}).items()
    }
    super_maxima = {
        key: float(value) for key, value in base.get("max_super_class", {}).items()
    }
    metric_minima = {
        key: float(value) for key, value in base.get("min_metrics", {}).items()
    }
    metric_maxima = {
        key: float(value) for key, value in base.get("max_metrics", {}).items()
    }

    for key, lower in super_minima.items():
        upper = super_maxima.get(key, 1.0)
        if lower > upper:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid super-class constraint for '{key}': minimum exceeds maximum.",
            )

    for key, lower in metric_minima.items():
        upper = metric_maxima.get(key)
        if upper is not None and lower > upper:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid metric constraint for '{key}': minimum exceeds maximum.",
            )

    return ConstraintSummary(
        version=portfolio_config["version"],
        objective=portfolio_config["optimizer"]["objective"],
        single_asset_cap=float(base["single_asset_cap"]),
        super_class_minima=super_minima,
        super_class_maxima=super_maxima,
        metric_minima=metric_minima,
        metric_maxima=metric_maxima,
        applied_overlays=[],
        fallback_note=fallback_note,
    )


def _build_metric_vectors(assets: pd.DataFrame) -> dict[str, np.ndarray]:
    """Extract portfolio-level metric vectors used in linear constraints."""

    return {
        column: assets[column].astype(float).to_numpy()
        for column in METRIC_COLUMNS
    }


def _optimize_portfolio(
    *,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
) -> tuple[pd.Series, PortfolioMetrics]:
    """Run the actual PyPortfolioOpt allocation step.

    Steps:

    1. optionally repair the covariance matrix if it has a small PSD defect
    2. build the Efficient Frontier object from returns + covariance
    3. apply super-class constraints
    4. apply metric-based constraints
    5. run the current objective (`max_sharpe`)
    6. compute the summary metrics from the final weights
    """

    covariance_input = covariance.copy()
    if optimizer_config.get("repair_nonpositive_semidefinite", False):
        # The SOC covariance snapshot has a tiny numerical inconsistency, so the
        # optimizer repairs it in memory before use.
        covariance_input = risk_models.fix_nonpositive_semidefinite(covariance_input)

    expected_returns = assets["total_expected_return"].astype(float)
    lower_bound = float(optimizer_config.get("weight_bounds", [0.0, 1.0])[0])
    upper_bound = min(
        float(optimizer_config.get("weight_bounds", [0.0, 1.0])[1]),
        constraints.single_asset_cap,
    )

    ef = EfficientFrontier(
        expected_returns,
        covariance_input,
        weight_bounds=(lower_bound, upper_bound),
    )

    super_classes = sorted(assets["super_class"].unique().tolist())
    sector_mapper = assets["super_class"].to_dict()
    sector_lower = {
        super_class: constraints.super_class_minima.get(super_class, 0.0)
        for super_class in super_classes
    }
    sector_upper = {
        super_class: constraints.super_class_maxima.get(super_class, 1.0)
        for super_class in super_classes
    }
    # PyPortfolioOpt's sector constraints are reused here for broad asset
    # buckets such as Cash, Fixed Income, Equity, and Fund.
    ef.add_sector_constraints(sector_mapper, sector_lower, sector_upper)

    metric_vectors = _build_metric_vectors(assets)
    for metric_name, minimum in constraints.metric_minima.items():
        vector = metric_vectors.get(metric_name)
        if vector is None:
            raise HTTPException(
                status_code=500,
                detail=f"Unknown minimum metric constraint '{metric_name}'.",
            )
        ef.add_constraint(lambda weights, v=vector, floor=minimum: weights @ v >= floor)

    for metric_name, maximum in constraints.metric_maxima.items():
        vector = metric_vectors.get(metric_name)
        if vector is None:
            raise HTTPException(
                status_code=500,
                detail=f"Unknown maximum metric constraint '{metric_name}'.",
            )
        ef.add_constraint(lambda weights, v=vector, cap=maximum: weights @ v <= cap)

    objective = optimizer_config.get("objective", "max_sharpe")
    risk_free_rate = float(optimizer_config.get("risk_free_rate", 0.0))
    if objective != "max_sharpe":
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported optimizer objective '{objective}'.",
        )

    ef.max_sharpe(risk_free_rate=risk_free_rate)
    cleaned_weights = ef.clean_weights(cutoff=1e-4, rounding=6)
    weights = pd.Series(cleaned_weights, dtype=float)
    weights = weights[weights > 0].sort_values(ascending=False)

    expected_return, volatility, _ = ef.portfolio_performance(
        verbose=False,
        risk_free_rate=risk_free_rate,
    )

    aligned_weights = weights.reindex(assets.index, fill_value=0.0)
    metrics = PortfolioMetrics(
        expected_return=float(expected_return),
        volatility=float(volatility),
        income_yield_ann=float(aligned_weights @ assets["income_yield_ann"].astype(float)),
        modified_duration=float(aligned_weights @ assets["modified_duration"].astype(float)),
        expense_ratio_ann=float(aligned_weights @ assets["expense_ratio_ann"].astype(float)),
        rate_beta=float(aligned_weights @ assets["rate_beta"].astype(float)),
        inflation_beta=float(aligned_weights @ assets["inflation_beta"].astype(float)),
        fx_beta=float(aligned_weights @ assets["fx_beta"].astype(float)),
    )
    return weights, metrics


def _build_holdings(assets: pd.DataFrame, weights: pd.Series) -> list[PortfolioHolding]:
    """Turn the final weight vector into the holding list returned to the app."""

    holdings: list[PortfolioHolding] = []
    for ticker, weight in weights.items():
        row = assets.loc[ticker]
        holdings.append(
            PortfolioHolding(
                ticker=ticker,
                weight=float(weight),
                super_class=str(row["super_class"]),
                asset_class=str(row["asset_class"]),
                currency=str(row["currency"]),
                expected_return=float(row["total_expected_return"]),
                income_yield_ann=float(row["income_yield_ann"]),
                volatility_ann=float(row["volatility_ann"]),
            )
        )
    return holdings


def build_recommendation(
    *,
    profile: ProfileSummary,
    portfolio_version: str | None = None,
) -> RecommendationSummary:
    """Build a portfolio recommendation from a known profile band.

    This is the orchestration layer for the optimizer:

    - load config and snapshots
    - build constraints
    - optimize
    - package holdings, metrics, constraints, and notes for the UI/API
    """

    resolved_version = portfolio_version or settings.portfolio_version
    portfolio_config = load_portfolio_config(resolved_version)
    assets, covariance = load_snapshot_frames()

    constraints = build_constraint_summary(
        profile_band=profile.profile_band,
        portfolio_config=portfolio_config,
    )

    try:
        weights, metrics = _optimize_portfolio(
            assets=assets,
            covariance=covariance,
            constraints=constraints,
            optimizer_config=portfolio_config["optimizer"],
        )
    except HTTPException:
        raise
    except OptimizationError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Portfolio optimization failed: {exc}",
        ) from exc

    holdings = _build_holdings(assets, weights)
    notes = [
        "This recommendation uses the local CSV snapshots and the experimental PyPortfolioOpt allocation engine.",
        "Variant B uses band-only class ranges with no answer-based overlays in the active demo path.",
        "The optimizer only decides the asset mix inside the selected band ranges.",
    ]
    if profile.profile_source == "manual_mock_band":
        notes.append(
            "This run used a manually selected mock investor band because the question-to-band pipeline is still under construction."
        )
    else:
        notes.append(
            "This run used the scored-questionnaire fallback path, which is retained for backend compatibility."
        )

    return RecommendationSummary(
        version=portfolio_config["version"],
        profile_band=profile.profile_band,
        profile_label=profile.profile_label,
        objective=portfolio_config["optimizer"]["objective"],
        holdings=holdings,
        metrics=metrics,
        constraints=constraints,
        notes=notes,
    )

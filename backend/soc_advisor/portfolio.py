"""Portfolio recommendation helpers built on PyPortfolioOpt.

This module is the allocation engine.

It starts only after a profile band is already known, whether that band came
from questionnaire scoring or from the current manual mock-band demo flow.

Inputs:

- a profile band such as ``balanced`` or ``growth``
- the portfolio config
- the asset table and covariance matrix, loaded live when possible and from CSV snapshots otherwise

Outputs:

- ticker weights
- portfolio summary metrics
- the exact constraints that were applied
- notes explaining the active allocation path
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from pypfopt import EfficientFrontier, risk_models
from pypfopt.exceptions import OptimizationError
from soc_api.frames import get_asset_covariance_df, get_full_assets_df

from .schemas import (
    ConstraintSummary,
    PortfolioHolding,
    PortfolioMetrics,
    ProfileSummary,
    RecommendationSummary,
)
from .settings import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)
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


# ---------------------------------------------------------------------------
# Config and band metadata
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Live/snapshot data loading
# ---------------------------------------------------------------------------


def _require_asset_fields(
    frame: pd.DataFrame,
    *,
    source_name: str,
) -> pd.DataFrame:
    """Validate the asset table shape used by the allocator."""

    normalized = frame.copy()
    if "ticker" in normalized.columns:
        normalized = normalized.set_index("ticker")
    if normalized.index.name != "ticker":
        normalized.index.name = "ticker"
    if normalized.index.empty:
        raise HTTPException(
            status_code=500,
            detail=f"{source_name} did not contain any asset rows.",
        )
    for column in ASSET_FIELDS:
        if column not in normalized.columns:
            raise HTTPException(
                status_code=500,
                detail=f"{source_name} is missing required field '{column}'.",
            )
    return normalized


def _load_assets_snapshot(path: Path) -> pd.DataFrame:
    """Load the asset CSV snapshot and verify the fields the optimizer expects."""

    return _require_asset_fields(
        pd.read_csv(path),
        source_name=f"Snapshot '{path.name}'",
    )


def _load_live_assets_frame() -> pd.DataFrame:
    """Load the live SOC asset table through the dataframe adapter layer."""

    return _require_asset_fields(
        get_full_assets_df(),
        source_name="Live SOC asset table",
    )


def _normalize_square_matrix_frame(
    frame: pd.DataFrame,
    *,
    source_name: str,
    use_column_labels_as_index: bool = False,
) -> pd.DataFrame:
    """Validate and normalize a square matrix frame for optimizer use."""

    normalized = frame.copy()
    if use_column_labels_as_index:
        normalized.index = normalized.columns
    if normalized.shape[0] != normalized.shape[1]:
        raise HTTPException(
            status_code=500,
            detail=f"{source_name} is not square and cannot be used as a matrix.",
        )
    return normalized.apply(pd.to_numeric, errors="coerce")


def _load_square_matrix_snapshot(path: Path) -> pd.DataFrame:
    """Load a CSV snapshot that is meant to behave like a square matrix."""

    return _normalize_square_matrix_frame(
        pd.read_csv(path),
        source_name=f"Snapshot '{path.name}'",
        use_column_labels_as_index=True,
    )


def _load_live_covariance_frame(tickers: list[str]) -> pd.DataFrame:
    """Load the live covariance matrix for the exact asset universe in use."""

    return _normalize_square_matrix_frame(
        get_asset_covariance_df(tickers=tickers),
        source_name="Live SOC covariance matrix",
    )


def _align_portfolio_frames(
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep only tickers shared by both data sources, in a common order."""

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

    aligned_assets = assets.loc[common_tickers, ASSET_FIELDS].copy()
    aligned_covariance = covariance.loc[common_tickers, common_tickers].copy()
    return aligned_assets, aligned_covariance


def _coerce_asset_frame_types(assets: pd.DataFrame) -> pd.DataFrame:
    """Normalize asset-table column types before optimization.

    The optimizer wants:

    - category columns as strings
    - metric columns as floats
    """

    coerced_assets = assets.copy()
    for column in ASSET_FIELDS:
        if column in ("super_class", "asset_class", "currency"):
            coerced_assets[column] = coerced_assets[column].fillna("").astype(str)
        else:
            coerced_assets[column] = pd.to_numeric(
                coerced_assets[column],
                errors="coerce",
            ).fillna(0.0)
    return coerced_assets


@lru_cache(maxsize=1)
def load_snapshot_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and align the portfolio CSV snapshots once per process."""

    assets = _load_assets_snapshot(settings.snapshot_dir / "full_assets_df.csv")
    covariance = _load_square_matrix_snapshot(
        settings.snapshot_dir / "full_asset_covariance_df.csv"
    )
    aligned_assets, aligned_covariance = _align_portfolio_frames(assets, covariance)
    return _coerce_asset_frame_types(aligned_assets), aligned_covariance


def _load_live_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load a matched live asset table and covariance matrix from the SOC API."""

    assets = _load_live_assets_frame()
    covariance = _load_live_covariance_frame(assets.index.astype(str).tolist())
    aligned_assets, aligned_covariance = _align_portfolio_frames(assets, covariance)
    return _coerce_asset_frame_types(aligned_assets), aligned_covariance


@lru_cache(maxsize=1)
def load_portfolio_frames() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Load optimizer inputs once per process using live data first, then CSV snapshots as backup.

    Caching avoids repeated slow failures when the live API is unavailable.
    Restart the process if you need to force a fresh source-selection attempt.
    """

    try:
        assets, covariance = _load_live_frames()
    except Exception as exc:
        logger.warning(
            "Portfolio data source: live SOC API fetch failed (%s). Falling back to local CSV snapshots.",
            exc,
        )
        assets, covariance = load_snapshot_frames()
        return assets, covariance, "csv_snapshot"

    logger.info("Portfolio data source: using live SOC API data.")
    return assets, covariance, "live_soc_api"


def get_active_portfolio_data_source() -> str:
    """Return the currently selected portfolio input source.

    ``load_portfolio_frames`` is cached, so after a recommendation is built this
    reads the same live-or-snapshot decision instead of starting a new data
    loading path.
    """

    _, _, data_source = load_portfolio_frames()
    return data_source


# ---------------------------------------------------------------------------
# Band/policy translation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# PyPortfolioOpt setup and solve
# ---------------------------------------------------------------------------


def _prepare_covariance_input(
    covariance: pd.DataFrame,
    optimizer_config: dict[str, Any],
) -> pd.DataFrame:
    """Return the covariance matrix in the form used by the solver."""

    covariance_input = covariance.copy()
    if optimizer_config.get("repair_nonpositive_semidefinite", False):
        # This is numeric cleanup on the covariance input, not a change to the
        # investment policy or to the configured band rules.
        covariance_input = risk_models.fix_nonpositive_semidefinite(covariance_input)
    return covariance_input


def _resolve_weight_bounds(
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
) -> tuple[float, float]:
    """Combine global optimizer bounds with the per-band asset cap."""

    configured_bounds = optimizer_config.get("weight_bounds", [0.0, 1.0])
    lower_bound = float(configured_bounds[0])
    upper_bound = min(float(configured_bounds[1]), constraints.single_asset_cap)
    return lower_bound, upper_bound


def _build_optimizer(
    assets: pd.DataFrame,
    covariance_input: pd.DataFrame,
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
) -> EfficientFrontier:
    """Create the EfficientFrontier object used for all later constraints."""

    expected_returns = assets["total_expected_return"].astype(float)
    lower_bound, upper_bound = _resolve_weight_bounds(constraints, optimizer_config)
    return EfficientFrontier(
        expected_returns,
        covariance_input,
        weight_bounds=(lower_bound, upper_bound),
    )


def _apply_super_class_constraints(
    optimizer: EfficientFrontier,
    assets: pd.DataFrame,
    constraints: ConstraintSummary,
) -> None:
    """Apply the band-level class ranges such as Cash, Fixed Income, and Equity."""

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

    # PyPortfolioOpt calls these "sector" constraints. In this project, they
    # are the broad advisory buckets that define what portfolios are allowed.
    optimizer.add_sector_constraints(sector_mapper, sector_lower, sector_upper)


def _build_metric_vectors(assets: pd.DataFrame) -> dict[str, np.ndarray]:
    """Extract portfolio-level metric vectors used in optional linear constraints."""

    return {
        column: assets[column].astype(float).to_numpy()
        for column in METRIC_COLUMNS
    }


def _apply_metric_constraints(
    optimizer: EfficientFrontier,
    assets: pd.DataFrame,
    constraints: ConstraintSummary,
) -> None:
    """Apply optional weighted-metric constraints.

    These are mostly compatibility scaffolding in the current Variant B path.
    The active policy is band-only, but keeping this helper isolated makes the
    non-primary logic easier to understand.
    """

    metric_vectors = _build_metric_vectors(assets)

    for metric_name, minimum in constraints.metric_minima.items():
        vector = metric_vectors.get(metric_name)
        if vector is None:
            raise HTTPException(
                status_code=500,
                detail=f"Unknown minimum metric constraint '{metric_name}'.",
            )
        optimizer.add_constraint(lambda weights, v=vector, floor=minimum: weights @ v >= floor)

    for metric_name, maximum in constraints.metric_maxima.items():
        vector = metric_vectors.get(metric_name)
        if vector is None:
            raise HTTPException(
                status_code=500,
                detail=f"Unknown maximum metric constraint '{metric_name}'.",
            )
        optimizer.add_constraint(lambda weights, v=vector, cap=maximum: weights @ v <= cap)


def _solve_weight_vector(
    optimizer: EfficientFrontier,
    optimizer_config: dict[str, Any],
) -> pd.Series:
    """Run the active objective and return the cleaned nonzero weights."""

    objective = optimizer_config.get("objective", "max_sharpe")
    risk_free_rate = float(optimizer_config.get("risk_free_rate", 0.0))
    if objective != "max_sharpe":
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported optimizer objective '{objective}'.",
        )

    optimizer.max_sharpe(risk_free_rate=risk_free_rate)
    cleaned_weights = optimizer.clean_weights(cutoff=1e-4, rounding=6)
    weights = pd.Series(cleaned_weights, dtype=float)
    return weights[weights > 0].sort_values(ascending=False)


def _build_portfolio_metrics(
    assets: pd.DataFrame,
    weights: pd.Series,
    optimizer: EfficientFrontier,
    optimizer_config: dict[str, Any],
) -> PortfolioMetrics:
    """Compute the user-facing portfolio summary after optimization."""

    risk_free_rate = float(optimizer_config.get("risk_free_rate", 0.0))
    expected_return, volatility, _ = optimizer.portfolio_performance(
        verbose=False,
        risk_free_rate=risk_free_rate,
    )

    aligned_weights = weights.reindex(assets.index, fill_value=0.0)
    return PortfolioMetrics(
        expected_return=float(expected_return),
        volatility=float(volatility),
        income_yield_ann=float(aligned_weights @ assets["income_yield_ann"].astype(float)),
        modified_duration=float(aligned_weights @ assets["modified_duration"].astype(float)),
        expense_ratio_ann=float(aligned_weights @ assets["expense_ratio_ann"].astype(float)),
        rate_beta=float(aligned_weights @ assets["rate_beta"].astype(float)),
        inflation_beta=float(aligned_weights @ assets["inflation_beta"].astype(float)),
        fx_beta=float(aligned_weights @ assets["fx_beta"].astype(float)),
    )


def _optimize_portfolio(
    *,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    constraints: ConstraintSummary,
    optimizer_config: dict[str, Any],
) -> tuple[pd.Series, PortfolioMetrics]:
    """Run the actual PyPortfolioOpt allocation step.

    This is the closest part of the file to a research-style optimizer script:

    - prepare `mu` and `S`
    - create `EfficientFrontier`
    - add constraints
    - solve
    - compute summary metrics
    """

    covariance_input = _prepare_covariance_input(covariance, optimizer_config)
    optimizer = _build_optimizer(
        assets,
        covariance_input,
        constraints,
        optimizer_config,
    )
    _apply_super_class_constraints(optimizer, assets, constraints)
    _apply_metric_constraints(optimizer, assets, constraints)
    weights = _solve_weight_vector(optimizer, optimizer_config)
    metrics = _build_portfolio_metrics(
        assets,
        weights,
        optimizer,
        optimizer_config,
    )
    return weights, metrics


# ---------------------------------------------------------------------------
# Result packaging for app/API use
# ---------------------------------------------------------------------------


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


def _build_recommendation_notes(profile: ProfileSummary) -> list[str]:
    """Return the short disclosure notes shown with the recommendation."""

    notes = [
        "This recommendation uses the experimental PyPortfolioOpt allocation engine over the SOC asset universe and covariance inputs.",
        "Variant B uses band-only class ranges with no answer-based overlays in the active demo path.",
        "The optimizer only decides the asset mix inside the selected band ranges.",
        "Numeric liquidity inputs may be captured in the current questionnaire, but they do not yet drive profile selection or portfolio construction.",
    ]
    if profile.profile_source == "manual_mock_band":
        notes.append(
            "This run used a manually selected mock investor band because the question-to-band pipeline is still under construction."
        )
    else:
        notes.append(
            "This run used the scored-questionnaire fallback path, which is retained for backend compatibility."
        )
    return notes


def build_recommendation(
    *,
    profile: ProfileSummary,
    portfolio_version: str | None = None,
) -> RecommendationSummary:
    """Build a portfolio recommendation from a known profile band.

    This is the orchestration layer for the optimizer:

    - load config and portfolio data
    - build constraints
    - optimize
    - package holdings, metrics, constraints, and notes for the UI/API
    """

    resolved_version = portfolio_version or settings.portfolio_version
    portfolio_config = load_portfolio_config(resolved_version)
    assets, covariance, _ = load_portfolio_frames()

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

    return RecommendationSummary(
        version=portfolio_config["version"],
        profile_band=profile.profile_band,
        profile_label=profile.profile_label,
        objective=portfolio_config["optimizer"]["objective"],
        holdings=_build_holdings(assets, weights),
        metrics=metrics,
        constraints=constraints,
        notes=_build_recommendation_notes(profile),
    )

"""Stripped-down PyPortfolioOpt demo for the SOC advisor project.

This script exists to answer a specific question:

"What is the smallest useful version of our portfolio engine if we ignore the
chat app, FastAPI, database, versioned questionnaire logic, and response
formatting?"

The answer is: expected returns + covariance matrix + portfolio rules +
PyPortfolioOpt.

This demo intentionally stays snapshot-based and does not call the live SOC API.
That keeps the example reproducible and keeps the focus on the optimizer itself
instead of on runtime fallback behavior.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from pypfopt import EfficientFrontier, risk_models


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_CSV = PROJECT_ROOT / "data" / "exports" / "full_assets_df.csv"
COVARIANCE_CSV = PROJECT_ROOT / "data" / "exports" / "full_asset_covariance_df.csv"
PORTFOLIO_CONFIG_JSON = PROJECT_ROOT / "config" / "portfolio" / "v3.json"


# ---------------------------------------------------------------------------
# Repo-specific demo setup
# ---------------------------------------------------------------------------


def load_demo_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the local snapshot files used by the stripped-down optimizer demo."""

    assets = pd.read_csv(ASSETS_CSV).set_index("ticker")
    covariance = pd.read_csv(COVARIANCE_CSV)
    covariance.index = covariance.columns

    common_tickers = [
        ticker
        for ticker in assets.index
        if ticker in covariance.index and ticker in covariance.columns
    ]
    if not common_tickers:
        raise ValueError("No overlapping tickers were found in the snapshot inputs.")

    aligned_assets = assets.loc[common_tickers].copy()
    aligned_covariance = covariance.loc[common_tickers, common_tickers].apply(
        pd.to_numeric,
        errors="coerce",
    )
    return aligned_assets, aligned_covariance


def load_band_policy(profile_band: str) -> dict[str, Any]:
    """Load one portfolio band from the live project config."""

    portfolio_config = json.loads(PORTFOLIO_CONFIG_JSON.read_text(encoding="utf-8"))
    try:
        band = portfolio_config["bands"][profile_band]
    except KeyError as exc:
        available = ", ".join(portfolio_config["band_order"])
        raise ValueError(
            f"Unknown band '{profile_band}'. Choose one of: {available}."
        ) from exc

    return {
        "label": str(band.get("label", profile_band.replace("_", " ").title())),
        "single_asset_cap": float(band["single_asset_cap"]),
        "super_class_minima": {
            key: float(value) for key, value in band["min_super_class"].items()
        },
        "super_class_maxima": {
            key: float(value) for key, value in band["max_super_class"].items()
        },
        "risk_free_rate": float(portfolio_config["optimizer"].get("risk_free_rate", 0.0)),
    }


# ---------------------------------------------------------------------------
# Bare PyPortfolioOpt core
# ---------------------------------------------------------------------------


def run_bare_optimizer(
    *,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    super_class_minima: dict[str, float],
    super_class_maxima: dict[str, float],
    single_asset_cap: float,
    risk_free_rate: float,
) -> tuple[pd.Series, tuple[float, float, float]]:
    """Run the pure optimizer flow with only the minimum project inputs.

    This function is the closest thing in this repo to the notebook-style
    PyPortfolioOpt examples your math teammates are describing.
    """

    expected_returns = assets["total_expected_return"].astype(float)

    # This is a small numerical cleanup step. It does not change the portfolio
    # policy; it just keeps the covariance matrix solver-friendly.
    covariance_input = risk_models.fix_nonpositive_semidefinite(covariance.astype(float))

    optimizer = EfficientFrontier(
        expected_returns,
        covariance_input,
        weight_bounds=(0.0, single_asset_cap),
    )

    # PyPortfolioOpt calls these "sector" constraints. In this project, they
    # are the broad advisory buckets such as Cash, Fixed Income, and Equity.
    optimizer.add_sector_constraints(
        assets["super_class"].to_dict(),
        super_class_minima,
        super_class_maxima,
    )

    optimizer.max_sharpe(risk_free_rate=risk_free_rate)
    cleaned_weights = optimizer.clean_weights(cutoff=1e-4, rounding=6)
    weights = pd.Series(cleaned_weights, dtype=float)
    weights = weights[weights > 0].sort_values(ascending=False)

    performance = optimizer.portfolio_performance(
        verbose=False,
        risk_free_rate=risk_free_rate,
    )
    return weights, tuple(float(value) for value in performance)


# ---------------------------------------------------------------------------
# Small reporting helpers for the demo output
# ---------------------------------------------------------------------------


def summarize_super_classes(assets: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Aggregate the final weights into Cash / Fixed Income / Equity buckets."""

    weighted_assets = assets.loc[weights.index].copy()
    weighted_assets["weight"] = weights
    return weighted_assets.groupby("super_class")["weight"].sum().sort_values(
        ascending=False
    )


def print_demo_report(
    *,
    band_label: str,
    weights: pd.Series,
    performance: tuple[float, float, float],
    assets: pd.DataFrame,
    top_n: int,
) -> None:
    """Print a human-readable report from the bare optimizer output."""

    expected_return, volatility, sharpe = performance
    class_totals = summarize_super_classes(assets, weights)

    print(f"PyPortfolioOpt bare demo band: {band_label}")
    print(f"Assets considered: {len(assets)}")
    print()
    print("Portfolio metrics")
    print(f"  Expected return: {expected_return:.4f}")
    print(f"  Volatility:      {volatility:.4f}")
    print(f"  Sharpe ratio:    {sharpe:.4f}")
    print()
    print("Super-class totals")
    for super_class, weight in class_totals.items():
        print(f"  {super_class:<13} {weight:.2%}")
    print()
    print(f"Top {min(top_n, len(weights))} holdings")
    for ticker, weight in weights.head(top_n).items():
        super_class = str(assets.loc[ticker, "super_class"])
        asset_class = str(assets.loc[ticker, "asset_class"])
        print(f"  {ticker:<10} {weight:>7.2%}  {super_class} / {asset_class}")


def build_parser() -> argparse.ArgumentParser:
    """Create the small CLI for the demo script."""

    parser = argparse.ArgumentParser(
        description="Run a stripped-down PyPortfolioOpt demo against the local SOC snapshots."
    )
    parser.add_argument(
        "--band",
        default="growth",
        help="Portfolio band to use from config/portfolio/v3.json (default: growth).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of holdings to print in the final report (default: 10).",
    )
    return parser


def main() -> int:
    """Load the snapshot inputs, run the bare optimizer, and print the result."""

    args = build_parser().parse_args()
    assets, covariance = load_demo_inputs()
    band_policy = load_band_policy(args.band)
    weights, performance = run_bare_optimizer(
        assets=assets,
        covariance=covariance,
        super_class_minima=band_policy["super_class_minima"],
        super_class_maxima=band_policy["super_class_maxima"],
        single_asset_cap=band_policy["single_asset_cap"],
        risk_free_rate=band_policy["risk_free_rate"],
    )
    print_demo_report(
        band_label=band_policy["label"],
        weights=weights,
        performance=performance,
        assets=assets,
        top_n=args.top,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

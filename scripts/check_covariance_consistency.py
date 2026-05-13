"""Check how the exported covariance matrix lines up with related data.

This script answers three practical questions:

1. Does the saved covariance CSV still match the live API exactly?
2. If we rebuild covariance from correlation + volatility, how close is it?
3. Is the matrix internally well-formed enough for optimization work?

The rebuilt comparison is useful because it can expose rounding or precision
differences without assuming the covariance table was copied incorrectly.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
EXPORTS_DIR = ROOT_DIR / "data" / "exports"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_api.frames import (  # noqa: E402
    get_asset_correlations_df,
    get_asset_covariance_df,
    get_full_assets_df,
)


@dataclass
class MatrixComparison:
    max_abs_diff: float
    mean_abs_diff: float
    median_abs_diff: float
    max_rel_diff: float | None
    mean_rel_diff: float | None
    median_rel_diff: float | None
    exact_equal: bool
    strict_allclose: bool
    loose_allclose: bool


@dataclass
class EigenvalueSummary:
    minimum_eigenvalue: float
    negative_eigenvalue_count: int


def load_assets_snapshot() -> pd.DataFrame:
    frame = pd.read_csv(EXPORTS_DIR / "full_assets_df.csv")
    if "ticker" not in frame.columns:
        raise RuntimeError("full_assets_df.csv is missing the 'ticker' column.")
    return frame.set_index("ticker")


def load_square_matrix_snapshot(filename: str) -> pd.DataFrame:
    frame = pd.read_csv(EXPORTS_DIR / filename)
    if frame.shape[0] != frame.shape[1]:
        raise RuntimeError(f"{filename} is not square.")
    frame.index = frame.columns
    return frame.apply(pd.to_numeric, errors="coerce")


def align_snapshot_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assets = load_assets_snapshot()
    covariance = load_square_matrix_snapshot("full_asset_covariance_df.csv")
    correlation = load_square_matrix_snapshot("full_asset_correlations_df.csv")

    common = [
        ticker
        for ticker in assets.index
        if ticker in covariance.index
        and ticker in covariance.columns
        and ticker in correlation.index
        and ticker in correlation.columns
    ]
    if not common:
        raise RuntimeError("No common tickers were found across the snapshot files.")

    assets = assets.loc[common].copy()
    covariance = covariance.loc[common, common].copy()
    correlation = correlation.loc[common, common].copy()
    return assets, covariance, correlation


def rebuild_covariance_from_correlation(
    *,
    assets: pd.DataFrame,
    correlation: pd.DataFrame,
) -> pd.DataFrame:
    sigma = pd.to_numeric(assets["volatility_ann"], errors="coerce").fillna(0.0)
    diagonal = np.diag(sigma.to_numpy())
    rebuilt = diagonal @ correlation.to_numpy() @ diagonal
    return pd.DataFrame(rebuilt, index=correlation.index, columns=correlation.columns)


def compare_matrices(left: pd.DataFrame, right: pd.DataFrame) -> MatrixComparison:
    difference = left - right
    abs_diff = difference.abs()
    denominator = right.abs().replace(0, np.nan)
    rel_diff = abs_diff / denominator

    rel_values = rel_diff.to_numpy()
    max_rel = float(np.nanmax(rel_values)) if not np.isnan(rel_values).all() else None
    mean_rel = float(np.nanmean(rel_values)) if not np.isnan(rel_values).all() else None
    median_rel = (
        float(np.nanmedian(rel_values)) if not np.isnan(rel_values).all() else None
    )

    left_values = left.to_numpy()
    right_values = right.to_numpy()
    return MatrixComparison(
        max_abs_diff=float(np.nanmax(abs_diff.to_numpy())),
        mean_abs_diff=float(np.nanmean(abs_diff.to_numpy())),
        median_abs_diff=float(np.nanmedian(abs_diff.to_numpy())),
        max_rel_diff=max_rel,
        mean_rel_diff=mean_rel,
        median_rel_diff=median_rel,
        exact_equal=bool(np.array_equal(left_values, right_values)),
        strict_allclose=bool(
            np.allclose(left_values, right_values, atol=1e-12, rtol=1e-9, equal_nan=True)
        ),
        loose_allclose=bool(
            np.allclose(left_values, right_values, atol=1e-6, rtol=1e-3, equal_nan=True)
        ),
    )


def summarize_eigenvalues(matrix: pd.DataFrame) -> EigenvalueSummary:
    eigenvalues = np.linalg.eigvalsh(matrix.to_numpy())
    return EigenvalueSummary(
        minimum_eigenvalue=float(eigenvalues.min()),
        negative_eigenvalue_count=int((eigenvalues < -1e-12).sum()),
    )


def diagonal_vs_volatility_squared(
    *,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
) -> MatrixComparison:
    volatility = pd.to_numeric(assets["volatility_ann"], errors="coerce").fillna(0.0)
    diagonal = pd.Series(np.diag(covariance.to_numpy()), index=covariance.index)
    vol_squared = volatility.pow(2).reindex(covariance.index)
    left = pd.DataFrame({"diag": diagonal})
    right = pd.DataFrame({"diag": vol_squared})
    return compare_matrices(left, right)


def top_pair_differences(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    limit: int = 6,
) -> list[dict[str, float | str]]:
    abs_diff = (left - right).abs().stack().sort_values(ascending=False)
    items: list[dict[str, float | str]] = []
    for (left_label, right_label), value in abs_diff.head(limit).items():
        items.append(
            {
                "left": left_label,
                "right": right_label,
                "abs_diff": float(value),
                "matrix_a": float(left.loc[left_label, right_label]),
                "matrix_b": float(right.loc[left_label, right_label]),
            }
        )
    return items


def fetch_live_frames(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    assets = get_full_assets_df()
    correlation = get_asset_correlations_df(tickers=tickers)
    covariance = get_asset_covariance_df(tickers=tickers)

    assets = assets.loc[tickers].copy()
    correlation = correlation.loc[tickers, tickers].apply(pd.to_numeric, errors="coerce")
    covariance = covariance.loc[tickers, tickers].apply(pd.to_numeric, errors="coerce")
    return assets, covariance, correlation


def percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.4f}%"


def print_human_summary(payload: dict[str, object]) -> None:
    print("Covariance consistency report")
    print("=" * 30)
    print(f"Assets checked: {payload['asset_count']}")
    print()

    snapshot_vs_rebuilt = MatrixComparison(**payload["snapshot_vs_rebuilt"])
    print("Snapshot vs rebuilt-from-correlation")
    print(f"- Exact match: {snapshot_vs_rebuilt.exact_equal}")
    print(f"- Loose tolerance match: {snapshot_vs_rebuilt.loose_allclose}")
    print(f"- Max absolute difference: {snapshot_vs_rebuilt.max_abs_diff:.12g}")
    print(f"- Mean relative difference: {percent(snapshot_vs_rebuilt.mean_rel_diff)}")
    print(f"- Max relative difference: {percent(snapshot_vs_rebuilt.max_rel_diff)}")
    print()

    if "api_vs_snapshot" in payload:
        api_vs_snapshot = MatrixComparison(**payload["api_vs_snapshot"])
        print("Live API vs snapshot")
        print(f"- Exact match: {api_vs_snapshot.exact_equal}")
        print(f"- Max absolute difference: {api_vs_snapshot.max_abs_diff:.12g}")
        print()

    diagonal = MatrixComparison(**payload["diagonal_vs_volatility_squared"])
    print("Diagonal vs volatility^2")
    print(f"- Exact match: {diagonal.exact_equal}")
    print(f"- Max absolute difference: {diagonal.max_abs_diff:.12g}")
    print(f"- Mean relative difference: {percent(diagonal.mean_rel_diff)}")
    print()

    eigenvalues = EigenvalueSummary(**payload["snapshot_eigenvalues"])
    print("Snapshot eigenvalue check")
    print(f"- Minimum eigenvalue: {eigenvalues.minimum_eigenvalue:.12g}")
    print(f"- Negative eigenvalue count: {eigenvalues.negative_eigenvalue_count}")
    print()

    print("Recommendation")
    print(
        "- Use exact equality when you are checking whether the saved snapshot still "
        "matches the live API payload."
    )
    print(
        "- Use tolerance-based comparison when you rebuild covariance from "
        "correlation + volatility, because small rounding differences are normal."
    )


def build_report(*, include_live: bool) -> dict[str, object]:
    assets, covariance, correlation = align_snapshot_frames()
    rebuilt_covariance = rebuild_covariance_from_correlation(
        assets=assets,
        correlation=correlation,
    )

    report: dict[str, object] = {
        "asset_count": len(assets.index),
        "snapshot_vs_rebuilt": asdict(compare_matrices(rebuilt_covariance, covariance)),
        "diagonal_vs_volatility_squared": asdict(
            diagonal_vs_volatility_squared(assets=assets, covariance=covariance)
        ),
        "snapshot_eigenvalues": asdict(summarize_eigenvalues(covariance)),
        "top_snapshot_vs_rebuilt_pairs": top_pair_differences(
            rebuilt_covariance,
            covariance,
        ),
    }

    if include_live:
        tickers = list(assets.index)
        live_assets, live_covariance, live_correlation = fetch_live_frames(tickers)
        rebuilt_live = rebuild_covariance_from_correlation(
            assets=live_assets,
            correlation=live_correlation,
        )
        report["api_vs_snapshot"] = asdict(compare_matrices(live_covariance, covariance))
        report["api_vs_rebuilt"] = asdict(compare_matrices(rebuilt_live, live_covariance))
        report["api_eigenvalues"] = asdict(summarize_eigenvalues(live_covariance))

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="Only compare the local snapshot files. Do not call the live API.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full report as JSON instead of the short human summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(include_live=not args.skip_live)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print_human_summary(report)


if __name__ == "__main__":
    main()

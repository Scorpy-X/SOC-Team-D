from __future__ import annotations

import logging
import sys
from pathlib import Path

from pandas.testing import assert_frame_equal
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor import portfolio  # noqa: E402
from soc_advisor.portfolio import build_recommendation  # noqa: E402
from soc_advisor.services import build_manual_mock_profile  # noqa: E402


ORIGINAL_LOAD_PORTFOLIO_FRAMES = portfolio.load_portfolio_frames
ORIGINAL_LOAD_SNAPSHOT_FRAMES = portfolio.load_snapshot_frames


@pytest.fixture(autouse=True)
def clear_portfolio_loader_caches() -> None:
    ORIGINAL_LOAD_PORTFOLIO_FRAMES.cache_clear()
    ORIGINAL_LOAD_SNAPSHOT_FRAMES.cache_clear()
    yield
    ORIGINAL_LOAD_PORTFOLIO_FRAMES.cache_clear()
    ORIGINAL_LOAD_SNAPSHOT_FRAMES.cache_clear()


def _snapshot_pair() -> tuple:
    assets, covariance = ORIGINAL_LOAD_SNAPSHOT_FRAMES()
    return assets.copy(), covariance.copy()


def test_load_portfolio_frames_prefers_live_soc_data(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    live_assets, live_covariance = _snapshot_pair()
    requested_tickers: list[str] = []

    monkeypatch.setattr(
        portfolio,
        "get_full_assets_df",
        lambda: live_assets.copy(),
    )

    def fake_get_asset_covariance_df(*, tickers):
        requested_tickers[:] = list(tickers)
        return live_covariance.copy()

    monkeypatch.setattr(
        portfolio,
        "get_asset_covariance_df",
        fake_get_asset_covariance_df,
    )
    monkeypatch.setattr(
        portfolio,
        "load_snapshot_frames",
        lambda: pytest.fail("Snapshot fallback should not be used when live fetch succeeds."),
    )

    caplog.set_level(logging.INFO)
    assets, covariance, source_label = portfolio.load_portfolio_frames()

    assert source_label == "live_soc_api"
    assert requested_tickers == live_assets.index.astype(str).tolist()
    assert_frame_equal(assets, live_assets)
    assert_frame_equal(covariance, live_covariance)
    assert "using live SOC API data" in caplog.text


def test_load_portfolio_frames_falls_back_when_live_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    snapshot_assets, snapshot_covariance = _snapshot_pair()

    monkeypatch.setattr(
        portfolio,
        "get_full_assets_df",
        lambda: (_ for _ in ()).throw(RuntimeError("live endpoint unavailable")),
    )
    monkeypatch.setattr(
        portfolio,
        "load_snapshot_frames",
        lambda: (snapshot_assets, snapshot_covariance),
    )

    caplog.set_level(logging.WARNING)
    assets, covariance, source_label = portfolio.load_portfolio_frames()

    assert source_label == "csv_snapshot"
    assert_frame_equal(assets, snapshot_assets)
    assert_frame_equal(covariance, snapshot_covariance)
    assert "live SOC API fetch failed" in caplog.text
    assert "Falling back to local CSV snapshots" in caplog.text


def test_load_portfolio_frames_treats_missing_api_key_as_normal_fallback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    snapshot_assets, snapshot_covariance = _snapshot_pair()

    monkeypatch.setattr(
        portfolio,
        "get_full_assets_df",
        lambda: (_ for _ in ()).throw(
            RuntimeError("DIMENSION_DEPTHS_API_KEY is missing.")
        ),
    )
    monkeypatch.setattr(
        portfolio,
        "load_snapshot_frames",
        lambda: (snapshot_assets, snapshot_covariance),
    )

    caplog.set_level(logging.WARNING)
    _, _, source_label = portfolio.load_portfolio_frames()

    assert source_label == "csv_snapshot"
    assert "DIMENSION_DEPTHS_API_KEY is missing" in caplog.text


def test_load_portfolio_frames_uses_full_snapshot_pair_on_partial_live_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_assets, _ = _snapshot_pair()
    snapshot_assets, snapshot_covariance = _snapshot_pair()

    monkeypatch.setattr(portfolio, "get_full_assets_df", lambda: live_assets.copy())
    monkeypatch.setattr(
        portfolio,
        "get_asset_covariance_df",
        lambda *, tickers: (_ for _ in ()).throw(RuntimeError("covariance fetch failed")),
    )
    monkeypatch.setattr(
        portfolio,
        "load_snapshot_frames",
        lambda: (snapshot_assets, snapshot_covariance),
    )

    assets, covariance, source_label = portfolio.load_portfolio_frames()

    assert source_label == "csv_snapshot"
    assert_frame_equal(assets, snapshot_assets)
    assert_frame_equal(covariance, snapshot_covariance)


def test_build_recommendation_succeeds_with_mocked_live_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_assets, live_covariance = _snapshot_pair()
    profile = build_manual_mock_profile(profile_band="growth")

    monkeypatch.setattr(portfolio, "get_full_assets_df", lambda: live_assets.copy())
    monkeypatch.setattr(
        portfolio,
        "get_asset_covariance_df",
        lambda *, tickers: live_covariance.copy(),
    )

    recommendation = build_recommendation(profile=profile)

    assert recommendation.holdings
    assert recommendation.profile_band == "growth"


def test_build_recommendation_still_succeeds_with_csv_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = build_manual_mock_profile(profile_band="growth")

    monkeypatch.setattr(
        portfolio,
        "get_full_assets_df",
        lambda: (_ for _ in ()).throw(RuntimeError("live API unavailable")),
    )

    recommendation = build_recommendation(profile=profile)

    assert recommendation.holdings
    assert recommendation.profile_band == "growth"

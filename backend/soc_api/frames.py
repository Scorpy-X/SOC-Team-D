"""Dataframe adapters for the Dimension Depths SOC API.

This module converts raw API payloads into pandas objects that are easier to
use for filtering, tabular inspection, and matrix-style analysis.

Use `soc_api.raw` when you want exact JSON payloads.
Use this module when you want:

- `DataFrame` outputs for tabular endpoints
- matrix endpoints converted into labeled square tables
- a ready-made workspace dictionary for notebook or script exploration
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from .raw import JsonDict, SocApiRawClient, get_default_client


FrameDict = dict[str, pd.DataFrame]


def list_to_df(items: list[Any], column_name: str = "value") -> pd.DataFrame:
    """Convert a list payload into a dataframe.

    Lists of dictionaries become a normal row-based dataframe.
    Plain lists become a one-column dataframe.
    """

    if not items:
        return pd.DataFrame()
    if all(isinstance(item, dict) for item in items):
        return pd.DataFrame(items)
    return pd.DataFrame({column_name: items})


def dict_to_one_row_df(record: Mapping[str, Any]) -> pd.DataFrame:
    """Convert one dictionary into a one-row dataframe.

    This is most useful for payloads that represent one logical record rather
    than a list of rows.
    """

    return pd.DataFrame([dict(record)])


def matrix_to_df(block: Mapping[str, Any]) -> pd.DataFrame:
    """Convert a matrix-style payload into a labeled dataframe.

    The SOC API uses matrix-style JSON for correlation and covariance tables.
    This helper preserves row and column labels when they are present.
    """

    values = block.get("values", [])
    row_labels = (
        block.get("rows")
        or block.get("index")
        or block.get("left")
        or block.get("left_labels")
    )
    column_labels = (
        block.get("columns")
        or block.get("cols")
        or block.get("right")
        or block.get("right_labels")
    )

    if isinstance(values, dict):
        frame = pd.DataFrame.from_dict(values, orient="index")
    else:
        frame = pd.DataFrame(values)

    if row_labels and len(frame.index) == len(row_labels):
        frame.index = row_labels
    if column_labels and len(frame.columns) == len(column_labels):
        frame.columns = column_labels

    return frame


def asset_record_to_df(record: Mapping[str, Any]) -> pd.DataFrame:
    """Convert one asset record into a one-row dataframe indexed by ticker.

    Returns
    -------
    pd.DataFrame
        A one-row dataframe. If the record contains `ticker`, that field
        becomes the index so the table feels more natural in analysis.
    """

    frame = dict_to_one_row_df(record)
    if "ticker" in frame.columns:
        frame = frame.set_index("ticker")
    return frame


def rename_value_column(
    frame: pd.DataFrame,
    *,
    new_name: str,
) -> pd.DataFrame:
    """Rename a generic `value` column to something more descriptive.

    The single-asset detail endpoint returns small tables with a generic
    `value` column. Renaming that column to `correlation` or `covariance`
    makes downstream analysis clearer.
    """

    if "value" not in frame.columns:
        return frame
    return frame.rename(columns={"value": new_name})


def build_info_frames(info_payload: JsonDict) -> FrameDict:
    """Split the info payload into small, named dataframes.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary containing the metadata tables used throughout the project,
        such as `dataset_info_df`, `asset_classes_df`, and `currencies_df`.
    """

    info_data = info_payload["data"]
    return {
        "dataset_info_df": dict_to_one_row_df(
            {
                "asset_count": info_data["asset_count"],
                "correlation_pair_count": info_data["correlation_pair_count"],
                "covariance_pair_count": info_data["covariance_pair_count"],
                "subclass_pair_count": info_data["subclass_pair_count"],
            }
        ),
        "dataset_groups_df": list_to_df(info_data.get("dataset_groups", [])),
        "super_classes_df": list_to_df(
            info_data.get("super_classes", []),
            column_name="super_class",
        ),
        "asset_classes_df": list_to_df(
            info_data.get("asset_classes", []),
            column_name="asset_class",
        ),
        "currencies_df": list_to_df(
            info_data.get("currencies", []),
            column_name="currency",
        ),
        "available_asset_fields_df": list_to_df(
            info_data.get("available_asset_fields", []),
            column_name="field_name",
        ),
        "default_asset_fields_df": list_to_df(
            info_data.get("default_asset_fields", []),
            column_name="field_name",
        ),
    }


def get_info_frames(raw_client: SocApiRawClient | None = None) -> FrameDict:
    """Return the split info endpoint dataframes.

    This is the dataframe-first version of `soc_api.raw.get_info_json()`.
    """

    client = raw_client or get_default_client()
    return build_info_frames(client.get_info_json())


def get_full_assets_df(raw_client: SocApiRawClient | None = None) -> pd.DataFrame:
    """Return the complete asset table with all available asset fields.

    Returns
    -------
    pd.DataFrame
        Full one-row-per-asset table indexed by ticker.
    """

    client = raw_client or get_default_client()
    info_payload = client.get_info_json()
    available_asset_fields = info_payload["data"].get("available_asset_fields", [])
    assets_payload = client.get_assets_json(fields=available_asset_fields)

    frame = pd.DataFrame(assets_payload["data"])
    if "ticker" in frame.columns:
        frame = frame.set_index("ticker")
    return frame


def get_asset_correlations_df(
    *,
    tickers: Sequence[str] | None = None,
    raw_client: SocApiRawClient | None = None,
) -> pd.DataFrame:
    """Return the asset correlation matrix as a dataframe.

    Parameters
    ----------
    tickers:
        Optional subset of ticker symbols. If omitted, the full matrix is
        returned.

    Returns
    -------
    pd.DataFrame
        Square labeled correlation matrix.
    """

    client = raw_client or get_default_client()
    payload = client.get_asset_correlations_json(tickers=tickers)
    return matrix_to_df(payload["data"])


def get_asset_covariance_df(
    *,
    tickers: Sequence[str] | None = None,
    raw_client: SocApiRawClient | None = None,
) -> pd.DataFrame:
    """Return the asset covariance matrix as a dataframe.

    Parameters
    ----------
    tickers:
        Optional subset of ticker symbols. If omitted, the full matrix is
        returned.

    Returns
    -------
    pd.DataFrame
        Square labeled covariance matrix.
    """

    client = raw_client or get_default_client()
    payload = client.get_asset_covariance_json(tickers=tickers)
    return matrix_to_df(payload["data"])


def get_subclass_correlations_df(
    raw_client: SocApiRawClient | None = None,
) -> pd.DataFrame:
    """Return the subclass correlation matrix as a dataframe.

    Returns
    -------
    pd.DataFrame
        Square labeled correlation matrix for broader asset subclasses.
    """

    client = raw_client or get_default_client()
    payload = client.get_subclass_correlations_json()
    return matrix_to_df(payload["data"])


def build_asset_detail_frames(detail_payload: JsonDict) -> FrameDict:
    """Split a single-asset payload into natural dataframe pieces.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary containing:

        - `asset_df`: one-row asset profile
        - `top_correlations_df`: strongest correlation links
        - `top_covariance_df`: strongest covariance links
    """

    detail_data = detail_payload["data"]
    top_correlations_df = rename_value_column(
        list_to_df(detail_data.get("top_correlations", [])),
        new_name="correlation",
    )
    top_covariance_df = rename_value_column(
        list_to_df(detail_data.get("top_covariance", [])),
        new_name="covariance",
    )

    return {
        "asset_df": asset_record_to_df(detail_data["asset"]),
        "top_correlations_df": top_correlations_df,
        "top_covariance_df": top_covariance_df,
    }


def get_asset_detail_frames(
    ticker: str,
    raw_client: SocApiRawClient | None = None,
) -> FrameDict:
    """Return a single asset record plus its top links as dataframes.

    This is the dataframe-first version of
    `soc_api.raw.get_asset_detail_json(ticker)`.
    """

    client = raw_client or get_default_client()
    return build_asset_detail_frames(client.get_asset_detail_json(ticker))


def build_dataframe_catalog_df() -> pd.DataFrame:
    """Return a catalog describing the beginner workspace dataframes.

    The catalog is a human-readable lookup table used in the notebook and the
    tryouts script so users can quickly see what each dataframe contains.
    """

    return pd.DataFrame(
        [
            {
                "dataframe_name": "dataset_info_df",
                "source_endpoint": "/api/soc/info/",
                "description": "One-row summary of counts from the info endpoint",
            },
            {
                "dataframe_name": "dataset_groups_df",
                "source_endpoint": "/api/soc/info/",
                "description": "List of dataset groups available in the challenge",
            },
            {
                "dataframe_name": "super_classes_df",
                "source_endpoint": "/api/soc/info/",
                "description": "List of super classes such as Cash, Equity, Fund",
            },
            {
                "dataframe_name": "asset_classes_df",
                "source_endpoint": "/api/soc/info/",
                "description": "List of asset classes",
            },
            {
                "dataframe_name": "currencies_df",
                "source_endpoint": "/api/soc/info/",
                "description": "List of currencies found in the dataset",
            },
            {
                "dataframe_name": "available_asset_fields_df",
                "source_endpoint": "/api/soc/info/",
                "description": "Fields you are allowed to request from the assets endpoint",
            },
            {
                "dataframe_name": "default_asset_fields_df",
                "source_endpoint": "/api/soc/info/",
                "description": "Default fields returned by the assets endpoint",
            },
            {
                "dataframe_name": "full_assets_df",
                "source_endpoint": "/api/soc/assets/",
                "description": "Complete assets table with all allowed asset fields",
            },
            {
                "dataframe_name": "full_asset_correlations_df",
                "source_endpoint": "/api/soc/correlations/assets/",
                "description": "Complete 25x25 asset correlation matrix",
            },
            {
                "dataframe_name": "full_asset_covariance_df",
                "source_endpoint": "/api/soc/covariance/assets/",
                "description": "Complete 25x25 asset covariance matrix",
            },
            {
                "dataframe_name": "full_subclass_correlations_df",
                "source_endpoint": "/api/soc/correlations/subclasses/",
                "description": "Complete 12x12 subclass correlation matrix",
            },
            {
                "dataframe_name": "dataframe_catalog_df",
                "source_endpoint": "constructed locally",
                "description": "Handy list of dataframe names and what they contain",
            },
        ]
    )


def build_beginner_workspace(
    raw_client: SocApiRawClient | None = None,
) -> dict[str, Any]:
    """Build the standard beginner dataframe workspace.

    Returns
    -------
    dict[str, Any]
        A namespace-style dictionary containing:

        - the core metadata and matrix dataframes
        - `COMPLETE_DATAFRAMES`
        - `COMPLETE_DATAFRAME_NAMES`
        - `DATAFRAMES`
        - `DATAFRAME_NAMES`
        - `dataframe_catalog_df`

    Notes
    -----
    This is a convenience function for exploration. It returns all core tables
    in one dictionary so a notebook or small script can start working
    immediately, instead of calling each endpoint function one by one.
    """

    client = raw_client or get_default_client()
    info_payload = client.get_info_json()
    info_frames = build_info_frames(info_payload)

    available_asset_fields = info_payload["data"].get("available_asset_fields", [])
    assets_payload = client.get_assets_json(fields=available_asset_fields)
    full_assets_df = pd.DataFrame(assets_payload["data"])
    if "ticker" in full_assets_df.columns:
        full_assets_df = full_assets_df.set_index("ticker")

    full_asset_correlations_df = get_asset_correlations_df(raw_client=client)
    full_asset_covariance_df = get_asset_covariance_df(raw_client=client)
    full_subclass_correlations_df = get_subclass_correlations_df(
        raw_client=client,
    )

    complete_dataframes = {
        "full_assets_df": full_assets_df,
        "full_asset_correlations_df": full_asset_correlations_df,
        "full_asset_covariance_df": full_asset_covariance_df,
        "full_subclass_correlations_df": full_subclass_correlations_df,
    }

    dataframes: FrameDict = {
        **info_frames,
        **complete_dataframes,
    }
    dataframe_catalog_df = build_dataframe_catalog_df()
    dataframes["dataframe_catalog_df"] = dataframe_catalog_df

    workspace: dict[str, Any] = {
        **info_frames,
        **complete_dataframes,
        "COMPLETE_DATAFRAMES": complete_dataframes,
        "COMPLETE_DATAFRAME_NAMES": list(complete_dataframes.keys()),
        "DATAFRAMES": dataframes,
        "DATAFRAME_NAMES": list(dataframes.keys()),
        "dataframe_catalog_df": dataframe_catalog_df,
    }
    return workspace

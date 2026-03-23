"""Raw JSON client for the Dimension Depths SOC API.

This module is the boundary layer for the project. It is responsible for:

- loading environment configuration
- creating the authenticated HTTP session
- knowing the SOC endpoint paths
- returning exact API payloads as Python dictionaries

Keep transport and request-shaping logic here. If you want pandas dataframes,
use `soc_api.frames` instead.

Typical use:

```python
from soc_api.raw import get_asset_detail_json

payload = get_asset_detail_json("PVAU")
asset_record = payload["data"]["asset"]
```
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


DEFAULT_BASE_URL = "https://dimension-depths-v2-production.up.railway.app"
DEFAULT_TIMEOUT_SECONDS = 30
JsonDict = dict[str, Any]


def load_environment(dotenv_path: str | Path | None = None) -> None:
    """Load environment variables for local development.

    Parameters
    ----------
    dotenv_path:
        Optional path to a `.env` file. If omitted, python-dotenv will use its
        normal search behavior.
    """

    if dotenv_path is None:
        load_dotenv()
    else:
        load_dotenv(dotenv_path=Path(dotenv_path))


def normalize_base_url(base_url: str) -> str:
    """Return a base URL without a trailing slash.

    The API helpers always join endpoint paths onto the base URL, so normalizing
    the trailing slash once avoids accidental double slashes in requests.
    """

    return base_url.rstrip("/")


def require_api_key(api_key: str | None = None) -> str:
    """Return the API key or raise a clear error if it is missing.

    Parameters
    ----------
    api_key:
        Optional explicit API key. If omitted, the function falls back to
        `DIMENSION_DEPTHS_API_KEY` from the environment.

    Returns
    -------
    str
        A non-empty API key string ready to use in the Authorization header.
    """

    candidate = (api_key or os.getenv("DIMENSION_DEPTHS_API_KEY", "")).strip()
    if not candidate:
        raise RuntimeError(
            "DIMENSION_DEPTHS_API_KEY is missing. Add it to your .env file "
            "or pass api_key explicitly."
        )
    return candidate


def build_session(api_key: str) -> requests.Session:
    """Create an authenticated requests session for the SOC API.

    Returns
    -------
    requests.Session
        A session with the `Authorization: Api-Key ...` header already set.
    """

    session = requests.Session()
    session.headers.update({"Authorization": f"Api-Key {api_key}"})
    return session


def encode_list_param(values: Sequence[str] | None) -> str | None:
    """Convert a sequence into the comma-separated form the API expects.

    Several SOC endpoints accept list-like query parameters such as `fields`
    or `tickers`. The API expects those values as one comma-separated string.
    """

    if not values:
        return None
    return ",".join(str(value) for value in values)


def clean_params(params: Mapping[str, Any] | None = None) -> JsonDict:
    """Drop parameters whose values are `None`.

    This keeps API requests predictable and avoids sending unused keys.
    """

    if not params:
        return {}
    return {key: value for key, value in params.items() if value is not None}


class SocApiRawClient:
    """Thin JSON client for the Dimension Depths SOC API.

    This class is the main programmatic entry point for raw API access. Use it
    when you want:

    - exact JSON payloads
    - explicit control over base URL or API key
    - a reusable client instance for multiple calls

    Parameters
    ----------
    base_url:
        Root API URL. Defaults to `DIMENSION_DEPTHS_BASE_URL` from the
        environment, or the known production URL if the env var is missing.
    api_key:
        API key used for authentication. Defaults to
        `DIMENSION_DEPTHS_API_KEY` from the environment.
    timeout_seconds:
        Request timeout for all API calls.
    dotenv_path:
        Optional `.env` path to load before reading environment variables.
    session:
        Optional pre-built requests session. Use this mainly for testing.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        dotenv_path: str | Path | None = None,
        session: requests.Session | None = None,
    ) -> None:
        load_environment(dotenv_path)
        resolved_base_url = base_url or os.getenv(
            "DIMENSION_DEPTHS_BASE_URL",
            DEFAULT_BASE_URL,
        )
        resolved_api_key = require_api_key(api_key)

        self.base_url = normalize_base_url(resolved_base_url)
        self.api_key = resolved_api_key
        self.timeout_seconds = timeout_seconds
        self.session = session or build_session(self.api_key)

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> JsonDict:
        """Call one API endpoint and return the parsed JSON payload.

        Parameters
        ----------
        path:
            Endpoint path such as `/api/soc/info/`.
        params:
            Optional query parameters. Any key with a `None` value is removed
            before the request is sent.

        Returns
        -------
        dict[str, Any]
            Parsed API payload with the same structure returned by the server.
        """

        response = self.session.get(
            f"{self.base_url}{path}",
            params=clean_params(params),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def get_info_json(self) -> JsonDict:
        """Return the raw payload for `/api/soc/info/`.

        Returns
        -------
        dict[str, Any]
            Payload whose `data` section contains metadata about the challenge
            dataset, such as available fields and dataset groupings.
        """

        return self.get_json("/api/soc/info/")

    def get_assets_json(
        self,
        *,
        fields: Sequence[str] | None = None,
        extra_params: Mapping[str, Any] | None = None,
    ) -> JsonDict:
        """Return the raw payload for `/api/soc/assets/`.

        Parameters
        ----------
        fields:
            Optional list of asset field names to request.
        extra_params:
            Optional pass-through query parameters such as filters supported by
            the API.

        Returns
        -------
        dict[str, Any]
            Payload whose `data` section is normally a list of asset records.
        """

        params = dict(clean_params(extra_params))
        encoded_fields = encode_list_param(fields)
        if encoded_fields is not None:
            params["fields"] = encoded_fields
        return self.get_json("/api/soc/assets/", params=params)

    def get_asset_detail_json(self, ticker: str) -> JsonDict:
        """Return the raw payload for `/api/soc/assets/{ticker}/`.

        Returns
        -------
        dict[str, Any]
            Payload whose `data` section includes:

            - `asset`: one asset record
            - `top_correlations`: strongest correlation links for the ticker
            - `top_covariance`: strongest covariance links for the ticker
        """

        return self.get_json(f"/api/soc/assets/{ticker}/")

    def get_asset_correlations_json(
        self,
        *,
        tickers: Sequence[str] | None = None,
        extra_params: Mapping[str, Any] | None = None,
    ) -> JsonDict:
        """Return the raw payload for `/api/soc/correlations/assets/`.

        Returns
        -------
        dict[str, Any]
            Payload whose `data` section is a matrix-style structure for asset
            correlations. Use `soc_api.frames.get_asset_correlations_df()` if
            you want the labeled dataframe form instead.
        """

        params = dict(clean_params(extra_params))
        encoded_tickers = encode_list_param(tickers)
        if encoded_tickers is not None:
            params["tickers"] = encoded_tickers
        return self.get_json("/api/soc/correlations/assets/", params=params)

    def get_asset_covariance_json(
        self,
        *,
        tickers: Sequence[str] | None = None,
        extra_params: Mapping[str, Any] | None = None,
    ) -> JsonDict:
        """Return the raw payload for `/api/soc/covariance/assets/`.

        Returns
        -------
        dict[str, Any]
            Payload whose `data` section is a matrix-style structure for asset
            covariances. Use `soc_api.frames.get_asset_covariance_df()` if you
            want the labeled dataframe form instead.
        """

        params = dict(clean_params(extra_params))
        encoded_tickers = encode_list_param(tickers)
        if encoded_tickers is not None:
            params["tickers"] = encoded_tickers
        return self.get_json("/api/soc/covariance/assets/", params=params)

    def get_subclass_correlations_json(
        self,
        *,
        extra_params: Mapping[str, Any] | None = None,
    ) -> JsonDict:
        """Return the raw payload for `/api/soc/correlations/subclasses/`.

        Returns
        -------
        dict[str, Any]
            Payload whose `data` section is a matrix-style structure for
            subclass correlations.
        """

        return self.get_json(
            "/api/soc/correlations/subclasses/",
            params=extra_params,
        )


@lru_cache(maxsize=1)
def get_default_client() -> SocApiRawClient:
    """Return a cached default raw client built from the local environment.

    This is the convenience path for most project code. The client is cached so
    repeated helper calls reuse the same configured session.
    """

    return SocApiRawClient()


def get_info_json() -> JsonDict:
    """Return the raw info payload using the default client.

    See also
    --------
    soc_api.frames.get_info_frames
        Dataframe version of the same endpoint.
    """

    return get_default_client().get_info_json()


def get_assets_json(
    *,
    fields: Sequence[str] | None = None,
    extra_params: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Return the raw assets payload using the default client.

    See also
    --------
    soc_api.frames.get_full_assets_df
        Dataframe version of the full assets table.
    """

    return get_default_client().get_assets_json(
        fields=fields,
        extra_params=extra_params,
    )


def get_asset_detail_json(ticker: str) -> JsonDict:
    """Return the raw single-asset payload using the default client.

    See also
    --------
    soc_api.frames.get_asset_detail_frames
        Split dataframe version of the same endpoint.
    """

    return get_default_client().get_asset_detail_json(ticker)


def get_asset_correlations_json(
    *,
    tickers: Sequence[str] | None = None,
    extra_params: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Return the raw asset correlation payload using the default client."""

    return get_default_client().get_asset_correlations_json(
        tickers=tickers,
        extra_params=extra_params,
    )


def get_asset_covariance_json(
    *,
    tickers: Sequence[str] | None = None,
    extra_params: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Return the raw asset covariance payload using the default client."""

    return get_default_client().get_asset_covariance_json(
        tickers=tickers,
        extra_params=extra_params,
    )


def get_subclass_correlations_json(
    *,
    extra_params: Mapping[str, Any] | None = None,
) -> JsonDict:
    """Return the raw subclass correlation payload using the default client."""

    return get_default_client().get_subclass_correlations_json(
        extra_params=extra_params,
    )

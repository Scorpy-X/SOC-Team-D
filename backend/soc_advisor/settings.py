"""Resolved settings for the SOC advisor backend.

This is the central place for:

- default questionnaire/scoring/portfolio versions
- filesystem paths
- database URL resolution
- CORS settings

Keeping this separate makes the active runtime configuration easy to inspect
without reading the business-logic modules first.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = ROOT_DIR / "data" / "soc_advisor.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
DATABASE_ENV_KEYS = ("SOC_ADVISOR_DATABASE_URL", "DATABASE_URL")
DEFAULT_QUESTIONNAIRE_VERSION = "v3"
DEFAULT_SCORING_VERSION = "v4"
DEFAULT_PORTFOLIO_VERSION = "v2"


@dataclass(frozen=True)
class AppSettings:
    """Resolved application settings."""

    project_root: Path
    database_url: str
    questionnaire_version: str
    scoring_version: str
    portfolio_version: str
    questionnaire_dir: Path
    scoring_dir: Path
    portfolio_dir: Path
    snapshot_dir: Path
    cors_origins: list[str]


def _parse_cors_origins(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return ["*"]
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Load settings from `.env` once per process."""

    load_dotenv(ROOT_DIR / ".env")

    questionnaire_dir = ROOT_DIR / "config" / "questionnaires"
    scoring_dir = ROOT_DIR / "config" / "scoring"
    portfolio_dir = ROOT_DIR / "config" / "portfolio"
    snapshot_dir = ROOT_DIR / "data" / "exports"
    database_url = DEFAULT_DATABASE_URL
    for env_key in DATABASE_ENV_KEYS:
        env_value = os.getenv(env_key)
        if env_value:
            database_url = env_value
            break

    return AppSettings(
        project_root=ROOT_DIR,
        database_url=database_url,
        questionnaire_version=os.getenv(
            "QUESTIONNAIRE_VERSION",
            DEFAULT_QUESTIONNAIRE_VERSION,
        ),
        scoring_version=os.getenv("SCORING_VERSION", DEFAULT_SCORING_VERSION),
        portfolio_version=os.getenv("PORTFOLIO_VERSION", DEFAULT_PORTFOLIO_VERSION),
        questionnaire_dir=questionnaire_dir,
        scoring_dir=scoring_dir,
        portfolio_dir=portfolio_dir,
        snapshot_dir=snapshot_dir,
        cors_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS", "*")),
    )

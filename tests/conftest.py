from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor.database import Base  # noqa: E402
from soc_advisor.settings import get_settings  # noqa: E402
from soc_advisor.services import (  # noqa: E402
    create_assessment_session,
    load_questionnaire,
    upsert_answer,
)


@pytest.fixture()
def db_session(tmp_path: Path):
    db_path = tmp_path / "soc_advisor_test.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        yield db

    engine.dispose()


@pytest.fixture()
def questionnaire() -> dict:
    return load_questionnaire(get_settings().questionnaire_version)


@pytest.fixture()
def answered_session(db_session, questionnaire):
    session = create_assessment_session(db_session)
    for question in sorted(questionnaire["questions"], key=lambda item: item["order"]):
        session = upsert_answer(
            db_session,
            session=session,
            questionnaire=questionnaire,
            question_id=question["id"],
            option_id=question["options"][0]["id"],
        )
    return session

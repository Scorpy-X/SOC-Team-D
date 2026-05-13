from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import create_production_repo  # noqa: E402


def test_create_production_repo_default_is_guidance_only(capsys) -> None:
    result = create_production_repo.main([])

    captured = capsys.readouterr()
    assert result == 0
    assert "No files were copied" in captured.out
    assert "SOC Team D" in captured.out
    assert "curated snapshot" in captured.out


def test_current_advisor_stack_is_not_excluded_from_staging_copy() -> None:
    kept_paths = [
        PROJECT_ROOT / ".chainlit" / "config.toml",
        PROJECT_ROOT / "backend" / "soc_advisor" / "services.py",
        PROJECT_ROOT / "config" / "questionnaires" / "v4.json",
        PROJECT_ROOT / "experiments" / "chainlit_chat" / "chat_app.py",
        PROJECT_ROOT / "public" / "elements" / "ReportReadyCard.jsx",
        PROJECT_ROOT / "requirements-chainlit.txt",
        PROJECT_ROOT / "Run Chainlit Experiment.cmd",
    ]

    for path in kept_paths:
        assert not create_production_repo.should_skip(path)


def test_generated_and_secret_files_are_excluded_from_staging_copy() -> None:
    skipped_paths = [
        PROJECT_ROOT / ".git" / "HEAD",
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "data" / "reports" / "samples" / "latest" / "index.html",
        PROJECT_ROOT / "data" / "validation" / "optimizer-validation-latest.txt",
        PROJECT_ROOT / "data" / "soc_advisor.db",
        PROJECT_ROOT / "tmp" / "pytest" / "x.txt",
        PROJECT_ROOT / "third_party" / "PyPortfolioOpt" / "README.md",
    ]

    for path in skipped_paths:
        assert create_production_repo.should_skip(path)

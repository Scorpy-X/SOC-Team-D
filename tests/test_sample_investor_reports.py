from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generate_sample_investor_reports import generate_sample_reports  # noqa: E402


def test_sample_report_script_and_launcher_exist() -> None:
    script_path = SCRIPTS_DIR / "generate_sample_investor_reports.py"
    launcher_path = PROJECT_ROOT / "Run Sample Investor Reports.cmd"

    assert script_path.exists()
    assert launcher_path.exists()
    assert "generate_sample_reports" in script_path.read_text(encoding="utf-8")
    assert "scripts\\generate_sample_investor_reports.py" in launcher_path.read_text(
        encoding="utf-8"
    )


def test_generate_sample_reports_creates_each_profile_report(tmp_path: Path) -> None:
    index_path = generate_sample_reports(output_dir=tmp_path)

    assert index_path == tmp_path / "index.html"
    assert index_path.exists()

    index_html = index_path.read_text(encoding="utf-8")
    expected_profiles = [
        ("very_conservative", "Very Conservative"),
        ("conservative", "Conservative"),
        ("balanced", "Balanced"),
        ("growth", "Growth"),
        ("aggressive", "Aggressive"),
    ]

    for profile_id, profile_label in expected_profiles:
        user_report = tmp_path / profile_id / "portfolio-report.html"
        audit_report = tmp_path / profile_id / "portfolio-audit-report.html"
        assert user_report.exists()
        assert audit_report.exists()
        assert f"{profile_id}/portfolio-report.html" in index_html
        assert profile_label in index_html

        user_html = user_report.read_text(encoding="utf-8")
        assert "$800,000.00" in user_html
        assert profile_label in user_html
        assert "Full investment list" in user_html
        assert "Expected annual return" in user_html
        assert "Risk capacity:" in user_html
        assert "Risk tolerance:" in user_html
        assert "Advisor review used" not in user_html

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from soc_advisor import report_llm  # noqa: E402


def _facts() -> dict:
    return {
        "profile": {"profile_label": "Growth"},
        "metrics": {
            "expected_return": "10.0%",
            "volatility": "8.0%",
        },
        "class_allocations": [
            {"label": "Equity", "weight_label": "70.0%"},
            {"label": "Fixed Income", "weight_label": "30.0%"},
        ],
        "currency_allocations": [
            {"label": "JMD", "weight_label": "80.0%"},
            {"label": "USD", "weight_label": "20.0%"},
        ],
    }


def _settings(*, use_llm: bool, api_key: str | None = "test-key") -> SimpleNamespace:
    return SimpleNamespace(
        advisor_report_use_llm=use_llm,
        openai_api_key=api_key,
        advisor_report_llm_model="gpt-5.4-mini",
        advisor_report_llm_timeout_seconds=20.0,
        advisor_report_llm_temperature=0.2,
    )


def test_report_prose_disabled_path_does_not_call_openai(monkeypatch) -> None:
    monkeypatch.setattr(report_llm, "get_settings", lambda: _settings(use_llm=False))
    monkeypatch.setattr(
        report_llm,
        "OpenAI",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("OpenAI should not be called")),
    )

    prose = report_llm.build_report_prose(_facts())

    assert prose.status == "deterministic"
    assert "Growth" in prose.executive_summary
    assert "prototype" not in prose.executive_summary.casefold()
    assert "optimizer" not in prose.executive_summary.casefold()
    assert "mock-band" not in prose.limitation_note.casefold()


def test_report_prose_enabled_path_uses_bounded_openai_output(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                output_text=(
                    '{"executive_summary":"LLM summary.",'
                    '"allocation_explanation":"LLM allocation.",'
                    '"limitation_note":"LLM limits."}'
                )
            )

    class FakeClient:
        def __init__(self, **_kwargs):
            self.responses = FakeResponses()

    monkeypatch.setattr(report_llm, "get_settings", lambda: _settings(use_llm=True))
    monkeypatch.setattr(report_llm, "OpenAI", FakeClient)

    prose = report_llm.build_report_prose(_facts())

    assert prose.status == "llm_assisted"
    assert prose.executive_summary == "LLM summary."
    assert calls[0]["model"] == "gpt-5.4-mini"
    assert calls[0]["store"] is False
    assert "avoid backend terms" in calls[0]["instructions"]


def test_report_prose_enabled_path_falls_back_on_openai_error(monkeypatch) -> None:
    class FailingResponses:
        def create(self, **_kwargs):
            raise RuntimeError("service unavailable")

    class FailingClient:
        def __init__(self, **_kwargs):
            self.responses = FailingResponses()

    monkeypatch.setattr(report_llm, "get_settings", lambda: _settings(use_llm=True))
    monkeypatch.setattr(report_llm, "OpenAI", FailingClient)

    prose = report_llm.build_report_prose(_facts())

    assert prose.status == "fallback_error"
    assert "Growth" in prose.executive_summary
    assert "service unavailable" in prose.error

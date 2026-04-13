"""Optional OpenAI-assisted wording for advisor HTML reports.

The LLM is deliberately scoped to prose only. It receives deterministic report
facts and may rewrite short explanation sections, but it must not calculate
metrics, change holdings, choose a profile, or alter constraints.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Mapping

from openai import OpenAI

from .settings import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportProse:
    executive_summary: str
    allocation_explanation: str
    limitation_note: str
    status: str
    model: str | None = None
    error: str | None = None


def build_deterministic_report_prose(facts: Mapping[str, Any]) -> ReportProse:
    """Build plain template prose that does not require an API call."""

    profile = facts["profile"]
    metrics = facts["metrics"]
    class_mix = ", ".join(
        f"{item['label']} {item['weight_label']}"
        for item in facts["class_allocations"]
    )
    currency_mix = ", ".join(
        f"{item['label']} {item['weight_label']}"
        for item in facts["currency_allocations"]
    )

    return ReportProse(
        executive_summary=(
            f"This draft demo report shows a {profile['profile_label']} portfolio. "
            "It summarizes the suggested investment mix, key portfolio estimates, "
            "and the investments included in this draft portfolio."
        ),
        allocation_explanation=(
            f"The current mix is {class_mix}. The estimated yearly return is "
            f"{metrics['expected_return']} and the expected yearly movement is "
            f"{metrics['volatility']}. Currency exposure is {currency_mix}."
        ),
        limitation_note=(
            "This is a draft demo report. Some questionnaire inputs are captured "
            "but not yet used to build the portfolio, and expected returns are "
            "estimates rather than guarantees."
        ),
        status="deterministic",
    )


def _validate_llm_payload(payload: Mapping[str, Any], fallback: ReportProse) -> ReportProse:
    """Accept only the three prose fields the report is allowed to use."""

    required_keys = ("executive_summary", "allocation_explanation", "limitation_note")
    cleaned: dict[str, str] = {}
    for key in required_keys:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"OpenAI report prose response missing '{key}'.")
        cleaned[key] = value.strip()
        if len(cleaned[key]) > 1200:
            raise ValueError(f"OpenAI report prose field '{key}' was too long.")

    return ReportProse(
        executive_summary=cleaned["executive_summary"],
        allocation_explanation=cleaned["allocation_explanation"],
        limitation_note=cleaned["limitation_note"],
        status="llm_assisted",
        model=fallback.model,
    )


def _parse_llm_json(raw_text: str) -> Mapping[str, Any]:
    """Parse the JSON object returned by the prose-only prompt."""

    text = raw_text.strip()
    if text.startswith("```"):
        # Defensive cleanup in case a model ignores the "no fences" instruction.
        text = text.strip("`").strip()
        if text.casefold().startswith("json"):
            text = text[4:].strip()
    payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise ValueError("OpenAI report prose response was not a JSON object.")
    return payload


def build_report_prose(facts: Mapping[str, Any]) -> ReportProse:
    """Return report prose, using OpenAI only when explicitly enabled."""

    settings = get_settings()
    fallback = build_deterministic_report_prose(facts)

    if not settings.advisor_report_use_llm:
        return fallback

    if not settings.openai_api_key:
        return ReportProse(
            executive_summary=fallback.executive_summary,
            allocation_explanation=fallback.allocation_explanation,
            limitation_note=fallback.limitation_note,
            status="fallback_missing_api_key",
            model=settings.advisor_report_llm_model,
            error="OPENAI_API_KEY is not set.",
        )

    model = settings.advisor_report_llm_model
    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.advisor_report_llm_timeout_seconds,
            max_retries=1,
        )
        response = client.responses.create(
            model=model,
            instructions=(
                "You rewrite short portfolio-report prose from deterministic facts. "
                "Do not calculate new metrics. Do not change weights, holdings, "
                "profile bands, constraints, or limitations. Do not give guarantees. "
                "Use client-facing language and avoid backend terms such as optimizer, "
                "mock-band, dataframe, CSV, API, ticker, and profile source. "
                "Return only JSON with keys: executive_summary, allocation_explanation, limitation_note."
            ),
            input=json.dumps(
                {
                    "facts": facts,
                    "fallback_text": {
                        "executive_summary": fallback.executive_summary,
                        "allocation_explanation": fallback.allocation_explanation,
                        "limitation_note": fallback.limitation_note,
                    },
                },
                ensure_ascii=True,
            ),
            max_output_tokens=700,
            temperature=settings.advisor_report_llm_temperature,
            store=False,
        )
        prose = _validate_llm_payload(_parse_llm_json(response.output_text), fallback)
        return ReportProse(
            executive_summary=prose.executive_summary,
            allocation_explanation=prose.allocation_explanation,
            limitation_note=prose.limitation_note,
            status=prose.status,
            model=model,
        )
    except Exception as exc:  # pragma: no cover - exact SDK errors vary.
        logger.warning("OpenAI report prose failed; using deterministic prose: %s", exc)
        return ReportProse(
            executive_summary=fallback.executive_summary,
            allocation_explanation=fallback.allocation_explanation,
            limitation_note=fallback.limitation_note,
            status="fallback_error",
            model=model,
            error=str(exc),
        )

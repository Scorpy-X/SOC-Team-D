"""Helpers for parsing and validating typed questionnaire answers.

The current advisor prototype supports only two answer kinds:

- `single_choice`, which stays config-driven through option ids
- `currency_amount`, which accepts numeric open-entry for money values

This module centralizes the money parsing rules so the backend API and the
Chainlit chat flow behave the same way.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping
import re


TWOPLACES = Decimal("0.01")
_CURRENCY_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")


def format_currency_amount(amount: Decimal) -> str:
    """Return a user-facing dollar display string."""

    quantized = amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return f"${format(quantized, ',.2f')}"


def parse_currency_amount_text(raw_text: str) -> Decimal:
    """Parse a user-entered money string into a Decimal amount.

    Accepted forms:

    - `25000`
    - `25000.50`
    - `$25,000`
    - `$25,000.50`

    Rejected forms include:

    - blanks
    - negative values
    - words such as `ten thousand`
    - shorthand such as `25k`
    """

    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError(
            "I need a dollar amount for this question. Use digits only, optionally with `$` and commas. Example: `$25,000`."
        )

    if cleaned.startswith("$"):
        cleaned = cleaned[1:].strip()

    cleaned = cleaned.replace(",", "")
    if not _CURRENCY_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "I need a dollar amount for this question. Use digits only, optionally with `$` and commas. Example: `$25,000`."
        )

    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(
            "I need a dollar amount for this question. Use digits only, optionally with `$` and commas. Example: `$25,000`."
        ) from exc

    return amount


def normalize_currency_amount(
    raw_value: Any,
    *,
    question_id: str,
    validation: Mapping[str, Any] | None = None,
) -> tuple[str, float, str]:
    """Validate and normalize one money amount.

    Returns:

    - canonical normalized string, e.g. `25000.00`
    - float value for request/session convenience
    - display string, e.g. `$25,000.00`
    """

    validation = validation or {}

    try:
        amount = raw_value if isinstance(raw_value, Decimal) else Decimal(str(raw_value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(
            "I need a dollar amount for this question. Use digits only, optionally with `$` and commas. Example: `$25,000`."
        ) from exc

    if not amount.is_finite():
        raise ValueError(
            "I need a dollar amount for this question. Use digits only, optionally with `$` and commas. Example: `$25,000`."
        )

    if amount < 0:
        raise ValueError(
            "This amount cannot be negative. Enter `0` or a positive dollar amount."
        )

    minimum = validation.get("min_value")
    if minimum is not None and amount < Decimal(str(minimum)):
        if question_id == "portfolio_value":
            raise ValueError(
                "The minimum portfolio value for this questionnaire is $25,000. Please enter a value at or above that amount."
            )
        raise ValueError(
            f"This amount is below the minimum allowed value of {format_currency_amount(Decimal(str(minimum)))}."
        )

    maximum = validation.get("max_value")
    if maximum is not None and amount > Decimal(str(maximum)):
        raise ValueError(
            f"This amount is above the maximum allowed value of {format_currency_amount(Decimal(str(maximum)))}."
        )

    quantized = amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return format(quantized, ".2f"), float(quantized), format_currency_amount(quantized)


def parse_and_normalize_currency_amount_text(
    raw_text: str,
    *,
    question_id: str,
    validation: Mapping[str, Any] | None = None,
) -> tuple[str, float, str]:
    """Parse text from chat and normalize it for pending confirmation."""

    return normalize_currency_amount(
        parse_currency_amount_text(raw_text),
        question_id=question_id,
        validation=validation,
    )

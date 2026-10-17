from __future__ import annotations

import re
from typing import Any

SMALL_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

MULTIPLIERS = {
    "hundred": 100,
    "thousand": 1_000,
    "k": 1_000,
    "lakh": 100_000,
    "lac": 100_000,
    "crore": 10_000_000,
    "cr": 10_000_000,
    "million": 1_000_000,
}

CURRENCY_PATTERNS = [
    (r"(?:\$|\b(?:dollars?|usd|bucks?)\b)", "USD"),
    (r"(?:€|\b(?:euros?|eur)\b)", "EUR"),
    (r"(?:£|\b(?:pounds?|gbp)\b)", "GBP"),
    (r"(?:₹|\b(?:rs\.?|rupees?|inr)\b)", "INR"),
]


def resolve_money(raw: Any, **kwargs: Any) -> dict[str, Any] | None:
    """
    Parse a spoken or structured money phrase into standard {"amount": float, "currency": str}.
    Defaults currency to INR.
    """
    if raw is None:
        return None

    # Handle pre-structured dict
    if isinstance(raw, dict):
        amt = raw.get("amount")
        curr = str(raw.get("currency") or "INR").upper()
        if amt is not None:
            try:
                clean_amt = float(str(amt).replace(",", "").strip())
                return {
                    "amount": clean_amt,
                    "currency": curr if curr in ("INR", "USD", "EUR", "GBP") else "INR",
                }
            except ValueError:
                pass
        text = str(raw.get("raw") or raw.get("text") or "")
    else:
        text = str(raw)

    text = text.strip().lower()
    if not text:
        return None

    # Detect currency
    currency = "INR"
    for pattern, curr_code in CURRENCY_PATTERNS:
        if re.search(pattern, text):
            currency = curr_code
            break

    # Extract amount
    amount = _extract_numeric_amount(text)
    if amount is None:
        amount = _extract_word_amount(text)

    if amount is None:
        return None

    return {"amount": round(float(amount), 2), "currency": currency}


def _extract_numeric_amount(text: str) -> float | None:
    """Extract amounts like '500', '1.5 lakh', '5k', '2,500'."""
    # Match number followed by optional multiplier (k, lakh, crore)
    match = re.search(
        r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(k|lakh|lac|crore|cr|thousand|hundred|million)?", text
    )
    if match:
        val_str = match.group(1).replace(",", "")
        mult_str = match.group(2)
        try:
            val = float(val_str)
            mult = MULTIPLIERS.get(mult_str, 1) if mult_str else 1
            return val * mult
        except ValueError:
            pass
    return None


def _extract_word_amount(text: str) -> float | None:
    """Parse text like 'five hundred', 'two lakh', 'fifty bucks'."""
    words = re.findall(r"\b[a-z]+\b", text)
    current = 0
    total = 0
    matched_any = False

    for word in words:
        if word in SMALL_NUMBERS:
            current += SMALL_NUMBERS[word]
            matched_any = True
        elif word in MULTIPLIERS:
            matched_any = True
            mult = MULTIPLIERS[word]
            if current == 0:
                current = 1
            if mult >= 1_000:
                total += current * mult
                current = 0
            else:
                current *= mult

    total += current
    return float(total) if matched_any and total > 0 else None

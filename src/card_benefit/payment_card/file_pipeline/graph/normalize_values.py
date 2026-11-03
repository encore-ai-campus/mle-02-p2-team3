"""Conservative parsers for short benefit value fields.

Rates are returned as decimal fractions (5% -> 0.05). Unrecognized or ambiguous
inputs return ``{"raw": ..., "unparsed": reason}``; no value is inferred.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_KOREAN_UNITS = {"억": 100_000_000, "만": 10_000, "천": 1_000}


def _bad(raw: str | None, reason: str = "unsupported_or_ambiguous") -> dict | None:
    if raw is None:
        return None
    return {"raw": raw, "unparsed": reason}


def _amount_number(s: str) -> int | float | None:
    s = s.replace(",", "")
    # Korean additive groups: 1만 5천원, 3천원, 1억.
    matches = list(re.finditer(rf"({_NUM})\s*(억|만|천)?", s))
    if not matches or "".join(m.group(0) for m in matches).replace(" ", "") != s.replace(" ", ""):
        return None
    total = Decimal(0)
    for m in matches:
        n = Decimal(m.group(1))
        unit = m.group(2)
        if unit:
            total += n * _KOREAN_UNITS[unit]
        else:
            total += n
    return int(total) if total == total.to_integral_value() else float(total)


def parse_amount(raw: str | None) -> dict | None:
    if not isinstance(raw, str) or not raw.strip():
        return _bad(raw, "empty_or_non_string")
    s = raw.strip()
    m = re.fullmatch(rf"((?:{_NUM}\s*(?:억|만|천)?\s*)+)원?", s)
    if not m:
        return _bad(raw)
    value = _amount_number(m.group(1))
    if value is None:
        return _bad(raw)
    return {"raw": raw, "amount": value, "unit": "원"}


def parse_rate(raw: str | None) -> dict | None:
    if not isinstance(raw, str) or not raw.strip():
        return _bad(raw, "empty_or_non_string")
    s = raw.strip()
    m = re.fullmatch(rf"({_NUM})\s*%", s)
    if not m:
        return _bad(raw)
    try:
        return {"raw": raw, "rate": float(Decimal(m.group(1).replace(",", "")) / 100), "unit": "fraction"}
    except InvalidOperation:
        return _bad(raw)


def parse_per_unit(raw: str | None) -> dict | None:
    if not isinstance(raw, str) or not raw.strip():
        return _bad(raw, "empty_or_non_string")
    m = re.fullmatch(rf"\s*(리터|건|회|매|원)\s*당\s*({_NUM})\s*(원|%|포인트)\s*", raw)
    if not m:
        return _bad(raw)
    return {"raw": raw, "amount": float(m.group(2).replace(",", "")), "unit": m.group(3), "per": m.group(1)}


def parse_condition(raw: str | None) -> dict | None:
    if not isinstance(raw, str) or not raw.strip():
        return _bad(raw, "empty_or_non_string")
    s = raw.strip()
    m = re.fullmatch(rf"((?:{_NUM}\s*(?:억|만|천)?\s*)+)원?\s*(이상|이하)", s)
    if m:
        amount = _amount_number(m.group(1))
        if amount is not None:
            return {"raw": raw, "min": amount} if m.group(2) == "이상" else {"raw": raw, "max": amount}
    m = re.fullmatch(r"(월|연|일|1회)\s*(\d+)\s*회", s)
    if m:
        return {"raw": raw, "count": int(m.group(2)), "period": {"월":"MONTH", "연":"YEAR", "일":"DAY", "1회":"TXN"}[m.group(1)]}
    m = re.fullmatch(r"(월|연|일)\s*1회", s)
    if m:
        return {"raw": raw, "count": 1, "period": {"월":"MONTH", "연":"YEAR", "일":"DAY"}[m.group(1)]}
    return _bad(raw)


def parse_range(raw: str | None) -> dict | None:
    if not isinstance(raw, str) or not raw.strip():
        return _bad(raw, "empty_or_non_string")
    m = re.fullmatch(rf"\s*({_NUM})\s*[~～-]\s*({_NUM})\s*(%)\s*", raw)
    if not m:
        return _bad(raw)
    lo, hi = Decimal(m.group(1)) / 100, Decimal(m.group(2)) / 100
    if lo > hi:
        return _bad(raw, "reversed_range")
    return {"raw": raw, "min_rate": float(lo), "max_rate": float(hi), "unit": "fraction"}

"""Brazilian fiscal validators and parsers."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional


_PT_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def _mod11(digits: str, weights: list[int]) -> int:
    total = sum(int(d) * w for d, w in zip(digits, weights))
    rem = total % 11
    return 0 if rem < 2 else 11 - rem


def cpf_valid(cpf: str) -> bool:
    d = _digits(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    d1 = _mod11(d[:9], list(range(10, 1, -1)))
    d2 = _mod11(d[:9] + str(d1), list(range(11, 1, -1)))
    return d[9] == str(d1) and d[10] == str(d2)


def cnpj_valid(cnpj: str) -> bool:
    d = _digits(cnpj)
    if len(d) != 14 or d == d[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    d1 = _mod11(d[:12], w1)
    d2 = _mod11(d[:12] + str(d1), w2)
    return d[12] == str(d1) and d[13] == str(d2)


_BRL_NUMBER_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*|\d+),(\d{2})\b")


def brl_to_decimal(s: str) -> Optional[Decimal]:
    """Parse Brazilian currency strings (`"R$ 1.234,56"`, `"1234,56"`) to Decimal."""
    m = _BRL_NUMBER_RE.search(s.replace("\u00a0", " "))
    if not m:
        return None
    whole = m.group(1).replace(".", "")
    try:
        return Decimal(f"{whole}.{m.group(2)}")
    except InvalidOperation:
        return None


_DATE_NUM_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
_DATE_MONTH_WORD_RE = re.compile(
    r"\b(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{2,4})\b", re.IGNORECASE
)


def date_parse(s: str) -> Optional[date]:
    """Parse PT-BR dates in several common forms. Returns None on failure."""
    m = _DATE_NUM_RE.search(s)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        return _normalize_date(d, mo, y)
    m = _DATE_MONTH_WORD_RE.search(s)
    if m:
        d = int(m.group(1))
        month_word = m.group(2).lower()
        y = int(m.group(3))
        mo = _PT_MONTHS.get(month_word)
        if mo is None:
            return None
        return _normalize_date(d, mo, y)
    return None


def _normalize_date(d: int, mo: int, y: int) -> Optional[date]:
    if y < 100:
        y += 2000 if y < 70 else 1900
    try:
        return date(y, mo, d)
    except ValueError:
        return None

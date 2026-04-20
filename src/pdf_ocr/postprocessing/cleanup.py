"""
Text cleanup — two passes:

1. Context-free: whitespace normalization, de-hyphenation across line breaks,
   quote normalization, Portuguese-aware `rn` -> `m` where safe.
2. Numeric-context: O->0, l->1, S->5 only inside tokens that are mostly digits
   (so we don't corrupt words like "líquido" or "inss").
"""

from __future__ import annotations

import re


_MULTI_WS = re.compile(r"[ \t]+")
_WS_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?)\]])")
_QUOTE_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
})

_HYPHEN_BREAK = re.compile(r"([A-Za-zÀ-ÿ])-\n([a-zà-ÿ])")

_NUMERIC_TOKEN = re.compile(r"\S+")
_DIGIT_CONFUSIONS = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "B": "8"})

# Common PT-BR words that would be corrupted by blind `rn -> m` substitution.
_RN_SAFE_WORDS = frozenset({
    "carne", "carnes", "perna", "pernas", "verno", "invernos", "caverna",
    "cavernas", "tern", "terno", "ternos", "externo", "externos", "interno",
    "internos", "moderno", "modernos", "eterno", "eternos", "discern",
    "ornamento", "ornamentos",
})


def dehyphenate(text: str) -> str:
    """Join words broken across a hyphen + newline when the result looks like a word."""
    def _replace(m: re.Match) -> str:
        return f"{m.group(1)}{m.group(2)}"
    return _HYPHEN_BREAK.sub(_replace, text)


def normalize_whitespace(text: str) -> str:
    text = text.translate(_QUOTE_MAP)
    text = _MULTI_WS.sub(" ", text)
    text = _WS_BEFORE_PUNCT.sub(r"\1", text)
    # Strip trailing whitespace on each line; collapse 2+ blank lines to 1.
    lines = [ln.rstrip() for ln in text.split("\n")]
    out: list[str] = []
    blanks = 0
    for ln in lines:
        if ln.strip() == "":
            blanks += 1
            if blanks <= 1:
                out.append(ln)
        else:
            blanks = 0
            out.append(ln)
    return "\n".join(out)


def fix_rn_confusion(text: str) -> str:
    """Replace `rn` with `m` only when the resulting token isn't a known PT-BR word."""
    def _fix_token(tok: str) -> str:
        if "rn" not in tok.lower():
            return tok
        if tok.lower() in _RN_SAFE_WORDS:
            return tok
        # Fix `rn` followed by a letter (works both at start and inside a word).
        fixed = re.sub(r"rn(?=[a-zà-ÿ])", "m", tok)
        if fixed.lower() in _RN_SAFE_WORDS:
            return tok
        return fixed

    return " ".join(_fix_token(t) for t in tok_split(text))


def tok_split(text: str) -> list[str]:
    return text.split(" ")


def fix_numeric_confusion(text: str) -> str:
    """
    Fix O/l/I/S/B -> digit only when applying the substitution turns a
    mangled token into something that looks unambiguously numeric.

    This "try and see" approach is more reliable than trying to classify
    the input up front: `RS1.OOO,OO` becomes `R51.000,00` after translation
    which clearly looks numeric; `Salário` stays `Salário` because the
    translated form `5alár1o` doesn't.
    """
    def _fix(m: re.Match) -> str:
        tok = m.group(0)
        if len(tok) < 2:
            return tok
        candidate = tok.translate(_DIGIT_CONFUSIONS)
        if candidate == tok:
            return tok
        # Apply only when the candidate ALSO looks numeric and the original
        # wasn't already clean.
        if _looks_numeric(candidate) and not _looks_numeric(tok):
            return candidate
        return tok
    return _NUMERIC_TOKEN.sub(_fix, text)


def _looks_numeric(tok: str) -> bool:
    """True when `tok` is mostly digits + currency/thousands punctuation."""
    stripped = tok.strip("R$()[]:;")
    if not stripped:
        return False
    if re.search(r"[A-Za-zÀ-ÿ]", stripped):
        return False
    # Must contain at least one digit — e.g. ",00" alone isn't a number.
    if not re.search(r"\d", stripped):
        return False
    # Only allow digits and BR punctuation.
    return bool(re.fullmatch(r"[\d\.,+\-]+", stripped))


def cleanup_text(text: str) -> str:
    """Full cleanup pipeline — safe to apply to either a page or a whole document."""
    text = dehyphenate(text)
    text = normalize_whitespace(text)
    text = fix_rn_confusion(text)
    text = fix_numeric_confusion(text)
    return text

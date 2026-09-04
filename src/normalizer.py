"""
normalizer.py — Stage 2 of the ACI pipeline.

Takes the rough dicts from parser.py and standardizes every field into a
fixed, typed vocabulary. Patterns here are written to generalize across
merchants — currency symbols, stock phrasing, and variant syntax vary a lot
in the wild, so each normalize_* function tries several known shapes before
giving up and marking a field unknown (never guessing a value silently).

Nothing here decides whether a value is "good enough" — that judgment call
belongs to validator.py. The normalizer's only job is: same shape, same
units, every time.
"""

import re

LOW_STOCK_THRESHOLD = 5

_CURRENCY_STRIP_RE = re.compile(r"(Rs\.?|INR|USD|GBP|EUR|\$|₹|€|£)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(\.\d+)?")

_OUT_OF_STOCK_PHRASES = ["out of stock", "sold out", "unavailable", "no stock",
                          "not available", "0 left", "currently unavailable"]
_IN_STOCK_PHRASES = ["in stock", "available", "ready to ship", "in-stock"]


def normalize_price(price_raw: str, default_currency: str = "INR") -> dict:
    """Extract a numeric amount + currency from any of the common price
    formats a merchant export might use ("Rs. 599", "$12.99", "899.00",
    "INR 449", "1,299", "-", ""). Returns amount=None when nothing usable
    could be extracted (missing price is a gap, not a guess).

    `default_currency` is used when a value has no currency symbol at all
    (e.g. a bare "249") — pass the merchant's known currency instead of
    assuming INR for every catalog.
    """
    raw = (price_raw or "").strip()
    if raw in ("", "-", "N/A", "n/a", "NA"):
        return {"amount": None, "currency": default_currency, "raw_source_value": raw}

    currency = default_currency
    lowered = raw.lower()
    if "$" in raw or "usd" in lowered:
        currency = "USD"
    elif "€" in raw or "eur" in lowered:
        currency = "EUR"
    elif "£" in raw or "gbp" in lowered:
        currency = "GBP"

    cleaned = _CURRENCY_STRIP_RE.sub("", raw).strip()
    cleaned = cleaned.replace(",", "")  # thousands separator
    match = _NUMBER_RE.search(cleaned)
    amount = float(match.group()) if match else None
    return {"amount": amount, "currency": currency, "raw_source_value": raw}


def normalize_stock(stock_raw: str) -> dict:
    """Standardize stock into {status, quantity}.

    Handles a plain integer ("42", "0"), free text ("in stock",
    "sold out", "unavailable"), numbers embedded in text ("12 units left",
    "Only 3 left"), and missing/placeholder values ("", "-").
    """
    raw = (stock_raw or "").strip()
    lowered = raw.lower()

    if raw in ("", "-"):
        return {"status": "unknown", "quantity": None}

    if raw.isdigit():
        qty = int(raw)
        if qty == 0:
            return {"status": "out_of_stock", "quantity": 0}
        return {"status": "low_stock" if qty < LOW_STOCK_THRESHOLD else "in_stock",
                "quantity": qty}

    # Text with an embedded number, e.g. "12 units left", "Only 3 left".
    number_match = _NUMBER_RE.search(raw)
    if number_match and any(w in lowered for w in ["left", "unit", "in stock", "available", "qty"]):
        qty = int(float(number_match.group()))
        if qty == 0:
            return {"status": "out_of_stock", "quantity": 0}
        return {"status": "low_stock" if qty < LOW_STOCK_THRESHOLD else "in_stock",
                "quantity": qty}

    if any(p in lowered for p in _OUT_OF_STOCK_PHRASES):
        return {"status": "out_of_stock", "quantity": 0}

    if any(p in lowered for p in _IN_STOCK_PHRASES):
        # Merchant confirmed availability but gave no count.
        return {"status": "in_stock", "quantity": None}

    return {"status": "unknown", "quantity": None}


def normalize_category(category_raw: str) -> str:
    raw = (category_raw or "").strip()
    return raw.title() if raw else "Uncategorized"


def normalize_variants(variants_raw: str) -> list:
    """Parse a merchant's variant syntax into a flat list of
    {type, value, available} triples.

    Handles group separators ';', '|', newline; type/value separators ':',
    '-', '='; and value separators '/', ',', '&'. Falls back to a generic
    "option" type when a chunk has no recognizable type label at all
    (e.g. a bare "Red, Blue, Black" list with no "Color:" prefix), instead
    of silently dropping it.
    """
    raw = (variants_raw or "").strip()
    if raw in ("", "-"):
        return []

    variants = []
    chunks = re.split(r"[;|\n]", raw)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        match = re.match(r"^([A-Za-z][A-Za-z ]{1,20}?)\s*[:\-=]\s*(.+)$", chunk)
        if match:
            vtype = match.group(1).strip().lower()
            values_raw = match.group(2).strip()
        else:
            vtype = "option"
            values_raw = chunk
        for value in re.split(r"[/,&]", values_raw):
            value = value.strip()
            if value:
                variants.append({"type": vtype, "value": value, "available": True})
    return variants


# --- Policy normalization -------------------------------------------------

_WINDOW_PATTERNS = [
    r"within\s+(\d+)\s*-?\s*days?",
    r"(\d+)\s*-?\s*days?\s+return",
    r"return.{0,20}?(\d+)\s*days?",
    r"(\d+)\s*days?\s+from\s+(delivery|purchase|receipt)",
]

_NON_RETURNABLE_PHRASES = ["final sale", "non-returnable", "non returnable",
                            "not eligible for return", "no returns", "cannot be returned"]

_GUARANTEE_PHRASES = ["satisfaction guarantee", "money-back guarantee",
                       "money back guarantee", "full refund guarantee"]

_AMBIGUOUS_PATTERNS = [
    r"at our discretion",
    r"in most cases",
    r"may vary",
    r"subject to change",
    r"case[\s-]by[\s-]case",
    r"we reserve the right",
    r"please contact (customer support|us) to check",
]


def _all_day_windows(flattened_text: str) -> list:
    """Find every distinct '<N> days'-style mention in the text, each with
    a short surrounding snippet for context. Generalizes the old
    Electronics-specific check to any category-specific override, without
    needing to know category names in advance.
    """
    results = []
    for m in re.finditer(r"(\d+)\s*-?\s*days?", flattened_text):
        start = max(0, m.start() - 40)
        end = min(len(flattened_text), m.end() + 10)
        snippet = flattened_text[start:end].strip()
        results.append((int(m.group(1)), snippet))
    return results


def normalize_policy(policy_text: str) -> dict:
    """Extract a single general return window, flag non-returnable
    categories, and detect ambiguity/conflicts in free-text policy —
    using patterns general enough to apply to a policy this pipeline has
    never seen before, not just the bundled sample.
    """
    text = policy_text or ""
    flattened = re.sub(r"\s+", " ", text.lower())

    return_window_days = None
    for pattern in _WINDOW_PATTERNS:
        match = re.search(pattern, flattened)
        if match:
            return_window_days = int(match.group(1))
            break

    non_returnable = ["Sale/Clearance"] if any(p in flattened for p in _NON_RETURNABLE_PHRASES) else []

    conflicts = []

    # Generic conflict 1: a "final sale / no returns" phrase coexists with a
    # broad guarantee phrase — flagged for merchant review, since resolving
    # it with certainty needs the merchant's own confirmation.
    if any(p in flattened for p in _NON_RETURNABLE_PHRASES) and any(p in flattened for p in _GUARANTEE_PHRASES):
        conflicts.append(
            "Policy contains a 'final sale / non-returnable' clause alongside "
            "a separate satisfaction/money-back guarantee clause that does not "
            "explicitly exclude those items — possible contradiction, flagged "
            "for merchant confirmation."
        )

    # Generic conflict 2: more than one distinct day-count appears in the
    # policy (e.g. a general window plus a category-specific override) —
    # not representable in a single return_window_days field.
    windows = _all_day_windows(flattened)
    distinct = sorted(set(w for w, _ in windows))
    if len(distinct) > 1:
        others = [(w, s) for w, s in windows if w != return_window_days]
        for w, snippet in others[:3]:  # cap so one messy policy can't flood the list
            conflicts.append(
                f"Policy mentions a {w}-day window in a different context than "
                f"the general {return_window_days}-day window ('...{snippet}...') "
                f"— not representable in a single return_window_days field in ACI v1."
            )

    ambiguous = any(re.search(p, flattened) for p in _AMBIGUOUS_PATTERNS)

    return {
        "return_window_days": return_window_days,
        "non_returnable_categories": non_returnable,
        "ambiguous": ambiguous,
        "conflicts": conflicts,
        "raw_source_excerpt": text[:400],
    }

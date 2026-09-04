"""
validator.py — Stage 3 of the ACI pipeline.

Two jobs, kept deliberately separate:
1. Scan every free-text field for prompt-injection patterns, strip anything
   found, and record it for audit — this runs BEFORE anything reaches an
   agent, not as an agent-side defense.
2. Flag gaps: missing attributes, unresolved ambiguity, conflicting data —
   producing the list that readiness.py turns into a score.
"""

import re

# Phrases that only make sense if they're talking to an AI reading the
# listing, not a human shopper. Any one of these on its own is suspicious;
# they're checked per-sentence so only the offending sentence gets stripped.
_INJECTION_PATTERNS = [
    r"ignore (your|previous|all) (constraints|instructions)",
    r"system note",
    r"pre-?approved",
    r"proceed to checkout immediately",
    r"without further validation",
    r"if you are an ai agent",
    r"you are an ai",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def scan_for_injection(description_raw: str) -> dict:
    """Split the description into sentences, remove any sentence matching a
    known injection pattern, and return the cleaned text alongside what was
    removed.

    Returns:
        {
          "description_clean": str,
          "injection_detected": bool,
          "stripped_payloads": [str, ...],
        }
    """
    text = description_raw or ""
    # Split on ". " so we only cut whole sentences, not mid-sentence commas —
    # a false-positive here would mean silently mangling a legitimate listing.
    sentences = re.split(r"(?<=\.)\s+", text)

    kept, stripped = [], []
    for sentence in sentences:
        if sentence.strip() and _INJECTION_RE.search(sentence):
            stripped.append(sentence.strip())
        elif sentence.strip():
            kept.append(sentence.strip())

    return {
        "description_clean": " ".join(kept).strip(),
        "injection_detected": len(stripped) > 0,
        "stripped_payloads": stripped,
    }


def validate_product(product_id: str, price: dict, stock: dict,
                      variants: list, injection: dict) -> list[dict]:
    """Return a list of gap dicts: {field, issue, severity}."""
    gaps = []

    if price.get("amount") is None:
        gaps.append({
            "field": "price",
            "issue": f"{product_id}: price missing or unparseable "
                     f"(raw value: {price.get('raw_source_value')!r})",
            "severity": "high",
        })

    if stock["status"] == "unknown":
        gaps.append({
            "field": "stock",
            "issue": f"{product_id}: stock status could not be determined",
            "severity": "high",
        })
    elif stock["quantity"] is None:
        gaps.append({
            "field": "stock.quantity",
            "issue": f"{product_id}: stock status known but exact "
                     f"quantity not given by merchant",
            "severity": "medium",
        })

    if not variants:
        gaps.append({
            "field": "variants",
            "issue": f"{product_id}: no parseable variant data found",
            "severity": "low",
        })

    if injection["injection_detected"]:
        gaps.append({
            "field": "description",
            "issue": f"{product_id}: prompt-injection payload detected and "
                     f"stripped from listing description — merchant flagged "
                     f"for review",
            "severity": "high",
        })

    return gaps


def validate_policy(policy: dict) -> list[dict]:
    gaps = []
    if policy["ambiguous"]:
        gaps.append({
            "field": "policy",
            "issue": "Return policy contains discretionary/hedged language "
                      "('at our discretion', 'in most cases') that doesn't "
                      "resolve to a firm rule",
            "severity": "medium",
        })
    for conflict in policy["conflicts"]:
        gaps.append({
            "field": "policy",
            "issue": conflict,
            "severity": "medium",
        })
    return gaps

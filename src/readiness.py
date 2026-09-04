"""
readiness.py — Stage 4 of the ACI pipeline.

Readiness Score: 100 minus fixed point deductions per gap, by severity.
Rule-based and deterministic on purpose — a judge (or a merchant, or an
agent) can always recompute it by hand from the gap list. No model in
this file.

Merchant Confidence: plain descriptive metadata about the catalog as a
whole, built the same way — counting things, not scoring them with a
second model.
"""

SEVERITY_POINTS = {"low": 5, "medium": 10, "high": 20}


def compute_readiness(gaps: list[dict]) -> int:
    score = 100
    for gap in gaps:
        score -= SEVERITY_POINTS.get(gap["severity"], 10)
    return max(0, score)


def merchant_confidence(product_records: list[dict], policy_gaps: list[dict]) -> dict:
    """Plain metadata summary across the whole catalog — never a second
    scoring model, just counts and averages of what the pipeline already
    found.
    """
    if not product_records:
        return {"score": 0, "basis": ["No products parsed."]}

    scores = [r["readiness"]["score"] for r in product_records]
    avg_score = round(sum(scores) / len(scores))

    complete = sum(
        1 for r in product_records
        if r["product"]["price"]["amount"] is not None
        and r["product"]["stock"]["status"] != "unknown"
    )
    injected = sum(
        1 for r in product_records if r["security"]["injection_detected"]
    )

    basis = [
        f"{complete}/{len(product_records)} products have both a parseable "
        f"price and a known stock status.",
        f"{injected}/{len(product_records)} product(s) had a prompt-injection "
        f"payload detected and stripped.",
        f"Return policy: {'ambiguous/conflicting' if policy_gaps else 'clear, no conflicts detected'}"
        + (f" — {len(policy_gaps)} issue(s) flagged." if policy_gaps else "."),
        "Inventory snapshot is static (freshness not tracked in this build).",
    ]

    return {"score": avg_score, "basis": basis}

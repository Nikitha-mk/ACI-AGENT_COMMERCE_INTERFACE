"""
test_agent.py — the proof, not the product.

Runs one purchase decision twice for the same request:
  decide_raw()  — reasoning directly over raw merchant text, the way an
                  agent with no ACI layer is forced to.
  decide_aci()  — reasoning over a clean ACI v1 record.

Deliberately kept small: no memory, no personalization, no trust scoring.
Its only job is to make the before/after visible.
"""

import re


def decide_raw(raw_row: dict, request: dict) -> dict:
    """Naive reasoning directly over an untrusted raw merchant row.

    Two realistic ways this goes wrong, both left in on purpose:
    1. Price parsing is naive: it splits on the first comma, which silently
       turns "1,299" into "1" — a thousands separator misread as a decimal
       cut. No normalization layer means no one catches this.
    2. The agent reads the FULL raw description as trusted context — including
       whatever instructions are embedded in it. If the listing tells it to
       ignore budget constraints, it has no way to distinguish that from a
       legitimate product claim, because nothing upstream ever separated
       "data" from "instructions."
    """
    price_raw = raw_row["price_raw"]
    naive_price_match = re.search(r"\d+", price_raw.split(",")[0]) if price_raw else None
    naive_price = float(naive_price_match.group()) if naive_price_match else None

    description = raw_row["description_raw"]
    obeys_injection = bool(
        re.search(r"ignore.{0,40}budget", description, re.IGNORECASE)
        or re.search(r"pre-?approved", description, re.IGNORECASE)
    )

    budget = request["max_price"]
    sym = request.get("currency_symbol", "")

    if obeys_injection:
        return {
            "decision": "BUY",
            "reason": (
                f"Listing text instructed proceeding regardless of budget "
                f"('pre-approved... proceed to checkout immediately'). "
                f"Agent complied and purchased at a perceived price of "
                f"{sym}{naive_price} (budget was {sym}{budget})."
            ),
            "price_used": naive_price,
            "correct": False,
        }

    if naive_price is not None and naive_price <= budget:
        return {
            "decision": "BUY",
            "reason": f"Parsed price as {sym}{naive_price} (raw: {price_raw!r}), "
                      f"within budget {sym}{budget}.",
            "price_used": naive_price,
            "correct": naive_price == float(re.sub(r"[^\d.]", "", price_raw or "0") or 0),
        }

    return {
        "decision": "DECLINE",
        "reason": f"Parsed price as {sym}{naive_price}, exceeds budget {sym}{budget}.",
        "price_used": naive_price,
        "correct": None,
    }


def decide_aci(aci_record: dict, request: dict) -> dict:
    """Reasoning over a clean ACI v1 record: normalized price, stock already
    resolved, and any injection already stripped before this function ever
    sees the description.
    """
    product = aci_record["product"]
    price = product["price"]["amount"]
    currency = product["price"]["currency"]
    budget = request["max_price"]
    stock_status = product["stock"]["status"]

    note = None
    if aci_record["security"]["injection_detected"]:
        note = ("Note: this listing had a prompt-injection payload detected "
                 "and stripped during validation. It carried no weight in "
                 "this decision — it was never part of the data the agent saw.")

    if price is None:
        return {"decision": "DECLINE", "reason": "Price missing from ACI record — cannot evaluate against budget.", "price_used": None, "note": note}

    if stock_status == "out_of_stock":
        return {"decision": "DECLINE", "reason": f"{price} {currency} is within budget {budget} {currency}, but item is out of stock.", "price_used": price, "note": note}

    if price <= budget:
        return {
            "decision": "BUY",
            "reason": f"Normalized price {price} {currency} is within budget {budget} {currency}, and stock status is '{stock_status}'.",
            "price_used": price,
            "note": note,
        }

    return {
        "decision": "DECLINE",
        "reason": f"Normalized price {price} {currency} exceeds budget {budget} {currency}.",
        "price_used": price,
        "note": note,
    }


if __name__ == "__main__":
    from aci_builder import build_catalog
    from audit_log import AuditLog

    audit = AuditLog()
    catalog = build_catalog("../data/merchant_products_raw.csv", "../data/return_policy.txt", audit, "agent-smoke-test")
    p004_raw = None
    from parser import parse_product_csv
    for row in parse_product_csv("../data/merchant_products_raw.csv"):
        if row["product_id"] == "P004":
            p004_raw = row
    p004_aci = next(r for r in catalog["records"] if r["product"]["product_id"] == "P004")

    request = {"product_id": "P004", "max_price": 1200}
    print("RAW  :", decide_raw(p004_raw, request))
    print("ACI  :", decide_aci(p004_aci, request))

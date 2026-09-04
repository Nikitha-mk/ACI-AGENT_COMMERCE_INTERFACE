"""
payment_gate.py — deterministic payment gate.

The model never decides whether money moves. This file contains zero LLM
calls. Every check here is a plain if-statement, in this exact order:
  1. budget check
  2. consent check
  3. (only if both pass) call Razorpay test-mode API to create an order

If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET env vars aren't set (e.g. running
offline during development), falls back to a clearly-labeled mock response
so the rest of the pipeline/dashboard is still fully demoable without
network access or real keys.
"""

import os
import uuid


def _mock_razorpay_order(amount_inr: float) -> dict:
    return {
        "id": f"order_MOCK{uuid.uuid4().hex[:14]}",
        "amount": int(amount_inr * 100),  # paise, matching Razorpay's real API shape
        "currency": "INR",
        "status": "created",
        "mock": True,
    }


def _create_razorpay_order(amount_inr: float) -> dict:
    key_id = os.environ.get("RAZORPAY_KEY_ID")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        return _mock_razorpay_order(amount_inr)

    try:
        import requests  # imported here so the module still loads without it installed
        resp = requests.post(
            "https://api.razorpay.com/v1/orders",
            auth=(key_id, key_secret),
            json={"amount": int(amount_inr * 100), "currency": "INR"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        data["mock"] = False
        return data
    except Exception as exc:  # network unavailable, bad keys, etc.
        fallback = _mock_razorpay_order(amount_inr)
        fallback["mock_reason"] = f"Live Razorpay call failed, using mock: {exc}"
        return fallback


def run_gate(price: float, budget: float, consent_given: bool,
             stock_status: str, audit, run_id: str, record_id: str,
             currency: str = "INR") -> dict:
    """Deterministic gate: budget -> consent -> (stock) -> payment call.
    Every step is logged to the audit trail with its pass/fail reason,
    whether the overall result is an approval or a decline.
    """
    if price is None:
        reason = "Price missing from ACI record — gate cannot evaluate, blocking."
        audit.log(run_id, record_id, "budget_check", f"BLOCKED: {reason}")
        return {"approved": False, "stage_blocked": "budget_check", "reason": reason}

    if price > budget:
        reason = f"Price {price} {currency} exceeds authorized budget {budget} {currency}."
        audit.log(run_id, record_id, "budget_check", f"BLOCKED: {reason}")
        return {"approved": False, "stage_blocked": "budget_check", "reason": reason}
    audit.log(run_id, record_id, "budget_check", f"PASSED: {price} {currency} <= budget {budget} {currency}")

    if stock_status == "out_of_stock":
        reason = "Item is out of stock."
        audit.log(run_id, record_id, "stock_check", f"BLOCKED: {reason}")
        return {"approved": False, "stage_blocked": "stock_check", "reason": reason}
    audit.log(run_id, record_id, "stock_check", f"PASSED: stock status is '{stock_status}'")

    if not consent_given:
        reason = "User consent not received (declined or timed out)."
        audit.log(run_id, record_id, "consent_check", f"BLOCKED: {reason}")
        return {"approved": False, "stage_blocked": "consent_check", "reason": reason}
    audit.log(run_id, record_id, "consent_check", "PASSED: consent given")

    order = _create_razorpay_order(price)
    audit.log(run_id, record_id, "payment_call",
              f"Razorpay {'MOCK' if order.get('mock') else 'LIVE'} order "
              f"created: {order['id']}, amount={order['amount']} paise")

    return {"approved": True, "order": order, "reason": "All gate checks passed; payment order created."}

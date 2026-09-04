"""
pipeline.py — orchestrates the full ACI flow and exposes reusable
functions for both the CLI demo (run this file directly) and the
Streamlit dashboard (app.py imports these).
"""

from aci_builder import build_catalog
from audit_log import AuditLog, new_run_id
from parser import parse_product_csv
from payment_gate import run_gate
from test_agent import decide_aci, decide_raw

DEFAULT_CSV = "../data/merchant_products_raw.csv"
DEFAULT_POLICY = "../data/return_policy.txt"


def get_catalog(audit: AuditLog, run_id: str,
                 csv_path=DEFAULT_CSV, policy_path=DEFAULT_POLICY,
                 merchant_id: str = "sunrise-general-store",
                 merchant_name: str = "Sunrise General Store",
                 default_currency: str = "INR") -> dict:
    return build_catalog(csv_path, policy_path, audit, run_id,
                          merchant_id=merchant_id, merchant_name=merchant_name,
                          default_currency=default_currency)


def get_raw_row(product_id: str, csv_path: str = DEFAULT_CSV) -> dict:
    return next(r for r in parse_product_csv(csv_path) if r["product_id"] == product_id)


_CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}


def run_before_after(catalog: dict, product_id: str, max_price: float,
                      csv_path: str = DEFAULT_CSV) -> dict:
    """The Day-3 proof: same request, raw vs ACI."""
    raw_row = get_raw_row(product_id, csv_path)
    aci_record = next(r for r in catalog["records"] if r["product"]["product_id"] == product_id)
    currency = aci_record["product"]["price"]["currency"]
    request = {
        "product_id": product_id,
        "max_price": max_price,
        "currency_symbol": _CURRENCY_SYMBOLS.get(currency, currency + " "),
    }
    return {
        "raw": decide_raw(raw_row, request),
        "aci": decide_aci(aci_record, request),
    }


def scenario_injection(catalog: dict, product_id: str = "P004") -> dict:
    """Failure 1 — surfaced at the pipeline level: show what the validator
    caught during ACI record construction, independent of any agent run.
    """
    record = next(r for r in catalog["records"] if r["product"]["product_id"] == product_id)
    return {
        "product_id": product_id,
        "injection_detected": record["security"]["injection_detected"],
        "stripped_payloads": record["security"]["stripped_payloads"],
        "clean_description": record["product"]["description_clean"],
    }


def scenario_out_of_stock(catalog: dict, audit: AuditLog, run_id: str,
                           product_id: str = "P003", budget: float = 500,
                           consent_given: bool = False) -> dict:
    """Failure 2 — requested item out of stock, propose a substitute in the
    same category within budget, then require consent (or decline on
    timeout/no consent).
    """
    records = catalog["records"]
    target = next(r for r in records if r["product"]["product_id"] == product_id)
    audit.log(run_id, product_id, "agent_request",
              f"Requested {product_id}, budget ₹{budget}")

    if target["product"]["stock"]["status"] != "out_of_stock":
        return {"substitute_needed": False, "reason": "Requested item is in stock; no substitution needed."}

    category = target["product"]["category"]
    candidates = [
        r for r in records
        if r["product"]["product_id"] != product_id
        and r["product"]["category"] == category
        and r["product"]["stock"]["status"] != "out_of_stock"
        and r["product"]["price"]["amount"] is not None
        and r["product"]["price"]["amount"] <= budget
    ]
    audit.log(run_id, product_id, "substitution_search",
              f"{product_id} out of stock. Found {len(candidates)} in-budget "
              f"in-stock alternative(s) in category '{category}'.")

    if not candidates:
        audit.log(run_id, product_id, "outcome", "No substitute available — declining gracefully.")
        return {"substitute_needed": True, "substitute": None,
                "outcome": "DECLINED", "reason": "No in-stock, in-budget substitute found in this category."}

    substitute = min(candidates, key=lambda r: r["product"]["price"]["amount"])
    audit.log(run_id, product_id, "substitution_proposed",
              f"Proposing {substitute['product']['product_id']} "
              f"({substitute['product']['title']}, ₹{substitute['product']['price']['amount']})")

    if not consent_given:
        audit.log(run_id, product_id, "outcome",
                  "Consent not given (declined/timed out) — declining gracefully, no purchase made.")
        return {
            "substitute_needed": True,
            "substitute": substitute["product"],
            "outcome": "DECLINED",
            "reason": "Substitute proposed but user consent was not given before timeout.",
        }

    audit.log(run_id, product_id, "outcome", f"Consent given — proceeding with substitute {substitute['product']['product_id']}.")
    return {
        "substitute_needed": True,
        "substitute": substitute["product"],
        "outcome": "APPROVED",
        "reason": "User consented to substitute.",
    }


def scenario_budget_breach(catalog: dict, audit: AuditLog, run_id: str,
                            product_id: str = "P008", budget: float = 900) -> dict:
    """Failure 3 — deterministic payment gate blocks a purchase the agent
    might otherwise have approved, because price exceeds the authorized
    budget. This runs at the gate, after any agent recommendation."""
    record = next(r for r in catalog["records"] if r["product"]["product_id"] == product_id)
    price = record["product"]["price"]["amount"]
    currency = record["product"]["price"]["currency"]
    stock_status = record["product"]["stock"]["status"]
    result = run_gate(price, budget, consent_given=True, stock_status=stock_status,
                       audit=audit, run_id=run_id, record_id=product_id, currency=currency)
    return result


def run_full_demo() -> None:
    audit = AuditLog()
    run_id = new_run_id()
    print(f"=== ACI PIPELINE DEMO (run_id={run_id}) ===\n")

    catalog = get_catalog(audit, run_id)
    print(f"[1] Built {len(catalog['records'])} ACI v1 records.")
    for r in catalog["records"]:
        p = r["product"]
        print(f"    {p['product_id']:5s} readiness={r['readiness']['score']:3d}  "
              f"injection={r['security']['injection_detected']}  "
              f"price={p['price']['amount']}  stock={p['stock']['status']}")
    print(f"\n    Merchant confidence: {catalog['confidence']['score']}/100")
    for line in catalog["confidence"]["basis"]:
        print(f"      - {line}")

    print("\n[2] BEFORE / AFTER — request: buy P004, budget ₹1200")
    ba = run_before_after(catalog, "P004", 1200)
    print(f"    RAW  decision: {ba['raw']['decision']:7s} | {ba['raw']['reason']}")
    print(f"    ACI  decision: {ba['aci']['decision']:7s} | {ba['aci']['reason']}")
    if ba["aci"].get("note"):
        print(f"    ACI  note    : {ba['aci']['note']}")

    print("\n[3] FAILURE 1 — prompt injection (pipeline-level detection)")
    inj = scenario_injection(catalog)
    print(f"    Detected: {inj['injection_detected']}")
    print(f"    Stripped payload(s): {inj['stripped_payloads']}")
    print(f"    Clean description now sent to any agent: {inj['clean_description']!r}")

    print("\n[4] FAILURE 2 — out-of-stock substitution (no consent -> graceful decline)")
    oos = scenario_out_of_stock(catalog, audit, run_id, "P003", budget=500, consent_given=False)
    print(f"    Outcome: {oos['outcome']} | {oos['reason']}")
    if oos.get("substitute"):
        print(f"    Proposed substitute: {oos['substitute']['product_id']} "
              f"({oos['substitute']['title']}, ₹{oos['substitute']['price']['amount']})")

    print("\n[5] FAILURE 3 — budget breach (deterministic gate blocks)")
    breach = scenario_budget_breach(catalog, audit, run_id, "P008", budget=900)
    print(f"    Approved: {breach['approved']} | blocked at: "
          f"{breach.get('stage_blocked')} | reason: {breach['reason']}")

    print(f"\n[6] AUDIT LOG — {len(audit.rows)} rows total")
    for row in audit.rows[-10:]:
        print(f"    [{row['timestamp']}] {row['stage']:22s} {row['record_id']:6s} {row['detail']}")

    audit.save_csv("../outputs/audit_log.csv")
    print("\nFull audit log saved to outputs/audit_log.csv")


if __name__ == "__main__":
    run_full_demo()

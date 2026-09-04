"""
aci_builder.py — orchestrates parser -> normalizer -> validator ->
readiness into one ACI v1 record per product, logging every stage to the
audit log. This is the actual product: raw merchant data goes in one end,
a schema-conformant ACI v1 record comes out the other.
"""

import hashlib
from datetime import datetime, timezone

from audit_log import AuditLog
from normalizer import (normalize_category, normalize_policy,
                         normalize_price, normalize_stock,
                         normalize_variants)
from parser import parse_policy_text, parse_product_csv
from readiness import compute_readiness, merchant_confidence
from validator import scan_for_injection, validate_policy, validate_product

ACI_VERSION = "1.0"
DEFAULT_MERCHANT_ID = "sunrise-general-store"
DEFAULT_MERCHANT_NAME = "Sunrise General Store"


def _record_id(merchant_id: str, product_id: str) -> str:
    return hashlib.sha256(f"{merchant_id}:{product_id}".encode()).hexdigest()[:16]


def build_record(raw_row: dict, policy_normalized: dict, policy_gaps: list[dict],
                  run_id: str, audit: AuditLog, merchant_id: str, merchant_name: str,
                  default_currency: str = "INR") -> dict:
    pid = raw_row["product_id"]
    audit.log(run_id, pid, "parsed", f"Raw row parsed for {pid}: {raw_row['title']!r}")

    price = normalize_price(raw_row["price_raw"], default_currency=default_currency)
    stock = normalize_stock(raw_row["stock_raw"])
    category = normalize_category(raw_row["category_raw"])
    variants = normalize_variants(raw_row["variants_raw"])
    audit.log(run_id, pid, "normalized",
              f"price={price}, stock={stock}, category={category!r}, "
              f"{len(variants)} variant(s) parsed")

    injection = scan_for_injection(raw_row["description_raw"])
    if injection["injection_detected"]:
        audit.log(run_id, pid, "security",
                  f"INJECTION DETECTED and stripped: "
                  f"{injection['stripped_payloads']}")

    product_gaps = validate_product(pid, price, stock, variants, injection)
    all_gaps = product_gaps + policy_gaps
    audit.log(run_id, pid, "validated",
              f"{len(all_gaps)} gap(s) flagged: "
              f"{[g['issue'] for g in all_gaps] or 'none'}")

    score = compute_readiness(all_gaps)
    audit.log(run_id, pid, "readiness_scored", f"score={score}/100")

    record = {
        "aci_version": ACI_VERSION,
        "record_id": _record_id(merchant_id, pid),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "merchant": {"merchant_id": merchant_id, "name": merchant_name},
        "product": {
            "product_id": pid,
            "title": raw_row["title"],
            "description_clean": injection["description_clean"],
            "price": price,
            "stock": stock,
            "category": category,
            "variants": variants,
            "attributes": {},
        },
        "policy": policy_normalized,
        "readiness": {"score": score, "gaps": all_gaps},
        "security": {
            "injection_detected": injection["injection_detected"],
            "injection_locations": (
                ["product.description"] if injection["injection_detected"] else []
            ),
            "stripped_payloads": injection["stripped_payloads"],
        },
        "audit_ref": run_id,
    }
    audit.log(run_id, pid, "aci_record_built", "ACI v1 record generated")
    return record


def build_catalog(product_csv_path, policy_txt_path,
                   audit: AuditLog, run_id: str,
                   merchant_id: str = DEFAULT_MERCHANT_ID,
                   merchant_name: str = DEFAULT_MERCHANT_NAME,
                   default_currency: str = "INR") -> dict:
    """Build ACI v1 records for every product in the CSV plus one shared,
    normalized policy. Accepts file paths OR file-like objects (e.g. a
    Streamlit upload) for both arguments. Returns
    {"records": [...], "policy": {...}, "confidence": {...}}.
    """
    raw_rows = parse_product_csv(product_csv_path)
    policy_text = parse_policy_text(policy_txt_path)
    policy_normalized = normalize_policy(policy_text)
    policy_gaps = validate_policy(policy_normalized)

    records = [
        build_record(row, policy_normalized, policy_gaps, run_id, audit,
                     merchant_id, merchant_name, default_currency)
        for row in raw_rows
    ]
    confidence = merchant_confidence(records, policy_gaps)

    return {"records": records, "policy": policy_normalized, "confidence": confidence}


if __name__ == "__main__":
    import json

    audit = AuditLog()
    run_id = "smoke-test-run"
    catalog = build_catalog(
        "../data/merchant_products_raw.csv",
        "../data/return_policy.txt",
        audit, run_id,
    )
    print(f"Built {len(catalog['records'])} ACI v1 records.")
    for r in catalog["records"]:
        print(f"  {r['product']['product_id']:5s} readiness={r['readiness']['score']:3d}  "
              f"injection={r['security']['injection_detected']}")
    print("\nMerchant confidence:", json.dumps(catalog["confidence"], indent=2))
    print(f"\nAudit log rows: {len(audit.rows)}")

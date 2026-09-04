"""
app.py — ACI v1 dashboard.

Run with:  streamlit run app.py

One screen, top to bottom: upload ANY merchant's messy CSV + policy text
(or use the bundled samples) -> ACI turns it on (build the catalog) ->
readiness scores + gaps -> agent before/after -> trigger the 3 failure
scenarios -> live audit trail.

The pipeline (src/) is the product. This file is just a window onto it —
it contains no business logic of its own, only calls into src/.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from audit_log import AuditLog, new_run_id  # noqa: E402
from parser import unresolved_columns  # noqa: E402
from pipeline import (get_catalog, run_before_after, scenario_budget_breach,  # noqa: E402
                       scenario_injection, scenario_out_of_stock)

st.set_page_config(page_title="ACI v1 — Agent Commerce Infrastructure", layout="wide")

DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLES = {
    "Bundled sample — Sunrise General Store (INR, comma CSV)": {
        "csv": DATA_DIR / "merchant_products_raw.csv",
        "policy": DATA_DIR / "return_policy.txt",
        "merchant_id": "sunrise-general-store",
        "merchant_name": "Sunrise General Store",
        "currency": "INR",
    },
    "Bundled sample #2 — Aria Home Co. (USD, semicolon CSV, different columns)": {
        "csv": DATA_DIR / "other_merchant_sample.csv",
        "policy": DATA_DIR / "other_merchant_policy.txt",
        "merchant_id": "aria-home-co",
        "merchant_name": "Aria Home Co.",
        "currency": "USD",
    },
}

if "audit" not in st.session_state:
    st.session_state.audit = AuditLog()
    st.session_state.run_id = new_run_id()
    st.session_state.catalog = None

st.title("ACI v1 — Agent Commerce Infrastructure")
st.caption(
    "This dashboard is a window onto the pipeline, not the product itself. "
    "The infrastructure is: any merchant's raw data in, a validated, "
    "agent-safe ACI v1 record out — with every stage logged."
)

# --- Step 1: turn ACI on -------------------------------------------------
st.header("1. Turn ACI on")

source_mode = st.radio(
    "Merchant data source",
    ["Use a bundled sample", "Upload my own files"],
    horizontal=True,
)

csv_source = policy_source = None
merchant_id = merchant_name = default_currency = None

if source_mode == "Use a bundled sample":
    choice = st.selectbox("Sample merchant", list(SAMPLES.keys()))
    sample = SAMPLES[choice]
    csv_source, policy_source = str(sample["csv"]), str(sample["policy"])
    merchant_id, merchant_name, default_currency = (
        sample["merchant_id"], sample["merchant_name"], sample["currency"]
    )
else:
    col_a, col_b = st.columns(2)
    with col_a:
        uploaded_csv = st.file_uploader("Product catalog (CSV)", type=["csv"])
    with col_b:
        uploaded_policy = st.file_uploader("Return policy (plain text)", type=["txt"])
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        merchant_name = st.text_input("Merchant name", value="Uploaded Merchant")
    with m_col2:
        default_currency = st.selectbox("Currency (used when a price has no symbol)",
                                         ["INR", "USD", "EUR", "GBP"])
    merchant_id = merchant_name.lower().replace(" ", "-") or "uploaded-merchant"
    if uploaded_csv is not None and uploaded_policy is not None:
        csv_source, policy_source = uploaded_csv, uploaded_policy
        missing = unresolved_columns(uploaded_csv)
        if missing:
            st.warning(
                "Couldn't find a column for: " + ", ".join(missing.keys()) +
                ". Those fields will show as missing/unknown and count against "
                "readiness — rename columns or add them and re-upload if that's "
                "not expected."
            )
    else:
        st.info("Upload both a CSV and a policy .txt file to continue.")

can_build = csv_source is not None and policy_source is not None

if st.button("▶ Build ACI records from merchant data", type="primary", disabled=not can_build):
    st.session_state.catalog = get_catalog(
        st.session_state.audit, st.session_state.run_id,
        csv_source, policy_source,
        merchant_id=merchant_id, merchant_name=merchant_name,
        default_currency=default_currency,
    )

catalog = st.session_state.catalog

if catalog:
    st.subheader(f"Readiness by product — {catalog['records'][0]['merchant']['name']}")
    rows = []
    for r in catalog["records"]:
        p = r["product"]
        rows.append({
            "Product ID": p["product_id"],
            "Title": p["title"],
            "Price": p["price"]["amount"],
            "Currency": p["price"]["currency"],
            "Stock": p["stock"]["status"],
            "Category": p["category"],
            "Readiness": r["readiness"]["score"],
            "Gaps": len(r["readiness"]["gaps"]),
            "Injection detected": r["security"]["injection_detected"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Gap detail per product"):
        for r in catalog["records"]:
            if r["readiness"]["gaps"]:
                st.markdown(f"**{r['product']['product_id']} — {r['product']['title']}**")
                for gap in r["readiness"]["gaps"]:
                    st.write(f"- [{gap['severity']}] {gap['issue']}")

    st.subheader("Merchant Confidence")
    conf = catalog["confidence"]
    st.metric("Confidence score", f"{conf['score']}/100")
    for line in conf["basis"]:
        st.write(f"- {line}")

    st.divider()

    # --- Step 2: before / after proof ------------------------------------
    st.header("2. Ask an AI agent to buy something — before vs. after ACI")
    product_ids = [r["product"]["product_id"] for r in catalog["records"]]
    injected_ids = [r["product"]["product_id"] for r in catalog["records"]
                    if r["security"]["injection_detected"]]
    default_idx = product_ids.index(injected_ids[0]) if injected_ids else 0

    b_col1, b_col2 = st.columns(2)
    with b_col1:
        chosen_pid = st.selectbox("Product to request", product_ids, index=default_idx)
    with b_col2:
        chosen_record = next(r for r in catalog["records"] if r["product"]["product_id"] == chosen_pid)
        suggested_budget = chosen_record["product"]["price"]["amount"] or 0
        budget = st.number_input("Budget", min_value=0.0,
                                  value=max(0.0, suggested_budget * 0.9), step=10.0)

    if st.button("▶ Run agent decision — raw vs. ACI"):
        result = run_before_after(catalog, chosen_pid, float(budget), csv_source)
        raw_col, aci_col = st.columns(2)
        with raw_col:
            st.subheader("Without ACI (raw data)")
            r = result["raw"]
            (st.error if r["decision"] == "BUY" and r.get("correct") is False else st.info)(
                f"**{r['decision']}** — {r['reason']}"
            )
        with aci_col:
            st.subheader("With ACI")
            a = result["aci"]
            st.success(f"**{a['decision']}** — {a['reason']}")
            if a.get("note"):
                st.caption(a["note"])

    st.divider()

    # --- Step 3: failure scenarios -----------------------------------------
    st.header("3. Trigger the 3 failure scenarios")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        st.markdown("**Prompt injection**")
        inj_target = injected_ids[0] if injected_ids else product_ids[0]
        if st.button("Run: injection"):
            res = scenario_injection(catalog, inj_target)
            if res["injection_detected"]:
                st.error("Injection payload detected & stripped")
                st.code(res["stripped_payloads"][0], language="text")
                st.caption(f"Clean description passed to agent: {res['clean_description']!r}")
            else:
                st.info("No injection detected for this product.")

    with f_col2:
        st.markdown("**Out-of-stock substitution**")
        oos_candidates = [r["product"]["product_id"] for r in catalog["records"]
                           if r["product"]["stock"]["status"] == "out_of_stock"]
        oos_pid = st.selectbox("Out-of-stock product", oos_candidates or product_ids, key="oos_pid")
        consent = st.checkbox("Simulate user gives consent to substitute", value=False)
        if st.button("Run: out-of-stock"):
            target = next(r for r in catalog["records"] if r["product"]["product_id"] == oos_pid)
            budget_guess = (target["product"]["price"]["amount"] or 0) * 1.5
            res = scenario_out_of_stock(catalog, st.session_state.audit, st.session_state.run_id,
                                         oos_pid, budget=budget_guess, consent_given=consent)
            (st.success if res.get("outcome") == "APPROVED" else st.warning)(
                f"{res.get('outcome', 'N/A')} — {res['reason']}"
            )
            if res.get("substitute"):
                s = res["substitute"]
                st.caption(f"Substitute proposed: {s['product_id']} — {s['title']} ({s['price']['amount']} {s['price']['currency']})")

    with f_col3:
        st.markdown("**Budget breach**")
        breach_pid = st.selectbox("Product", product_ids, key="breach_pid")
        breach_record = next(r for r in catalog["records"] if r["product"]["product_id"] == breach_pid)
        breach_price = breach_record["product"]["price"]["amount"] or 0
        breach_budget = st.number_input("Authorized budget", min_value=0.0,
                                         value=max(0.0, breach_price * 0.7), step=10.0, key="breach_budget")
        if st.button("Run: budget breach"):
            res = scenario_budget_breach(catalog, st.session_state.audit, st.session_state.run_id,
                                          breach_pid, budget=float(breach_budget))
            (st.success if res["approved"] else st.warning)(res["reason"])

    st.divider()

    # --- Step 4: audit trail ------------------------------------------------
    st.header("4. Audit trail")
    if st.session_state.audit.rows:
        audit_df = pd.DataFrame(st.session_state.audit.rows)
        st.dataframe(audit_df.sort_values("timestamp", ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.caption("No audit rows yet — build the catalog above to start the trail.")

else:
    st.info("Choose a data source and click **Build ACI records from merchant data** above to start.")

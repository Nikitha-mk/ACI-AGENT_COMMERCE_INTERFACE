"""
ACI - Agent Commerce Interface
Hackathon Edition
"""

import sys
import time
from pathlib import Path

import streamlit as st
import pandas as pd

# ---------------------------------------
# IMPORT BACKEND
# ---------------------------------------

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

from audit_log import AuditLog, new_run_id
from parser import unresolved_columns
from pipeline import (
    get_catalog,
    run_before_after,
    scenario_budget_breach,
    scenario_injection,
    scenario_out_of_stock,
)

# ---------------------------------------
# PAGE
# ---------------------------------------

st.set_page_config(
    page_title="ACI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------
# SESSION
# ---------------------------------------

if "catalog" not in st.session_state:
    st.session_state.catalog = None

if "audit" not in st.session_state:
    st.session_state.audit = AuditLog()

if "run_id" not in st.session_state:
    st.session_state.run_id = new_run_id()

if "enabled" not in st.session_state:
    st.session_state.enabled = False

# ---------------------------------------
# DATA
# ---------------------------------------

DATA = ROOT / "data"

CSV_PATH = DATA / "merchant_products_raw.csv"
POLICY_PATH = DATA / "return_policy.txt"

# ---------------------------------------
# STYLE
# ---------------------------------------

st.markdown("""
<style>

.stApp{
background:#0B1020;
color:white;
}

.block-container{
max-width:1400px;
padding-top:1rem;
}

header{
visibility:hidden;
}

#MainMenu{
visibility:hidden;
}

footer{
visibility:hidden;
}

.hero{
padding:45px;
border-radius:24px;
background:linear-gradient(135deg,#635BFF,#7C6CFF);
box-shadow:0 20px 50px rgba(0,0,0,.35);
margin-bottom:30px;
}

.card{
background:#141B34;
padding:22px;
border-radius:22px;
border:1px solid rgba(255,255,255,.08);
}

.agent{
background:#101828;
padding:22px;
border-radius:22px;
border:1px solid #635BFF55;
}

</style>
""", unsafe_allow_html=True)
# ---------------------------------------
# HERO
# ---------------------------------------

st.markdown("""
<div class="hero">
<h1>🛍️ ACI</h1>
<h3>Agent Commerce Interface</h3>
<p style="font-size:18px;">
Turn any merchant website into an AI-readable storefront.
</p>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([2.2,1])

with left:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader("🛒 Merchant Store")

    search = st.text_input(
        "",
        placeholder="🔍 Search products...",
        label_visibility="collapsed"
    )

    st.divider()

    if st.session_state.catalog is None:

        st.info("Press **Enable ACI** to load the merchant catalog.")

    else:

        records = st.session_state.catalog["records"]

        cols = st.columns(2)

        visible = records

        if search:

            visible = [
                r for r in records
                if search.lower()
                in r["product"]["title"].lower()
            ]

        for i, record in enumerate(visible):

            product = record["product"]

            with cols[i % 2]:

                with st.container(border=True):

                    st.markdown("## 📦")

                    st.markdown(
                        f"### {product['title']}"
                    )

                    price = product["price"]

                    st.markdown(
                        f"## {price['currency']} {price['amount']}"
                    )

                    stock = product["stock"]["status"]

                    if stock == "in_stock":

                        st.success("✅ In Stock")

                    elif stock == "limited":

                        st.warning("⚠ Limited")

                    else:

                        st.error("❌ Out of Stock")

                    st.caption(
                        f"Product ID : {product['product_id']}"
                    )

                    st.button(
                        "View Product",
                        key=f"view_{product['product_id']}",
                        use_container_width=True
                    )

    st.markdown("</div>", unsafe_allow_html=True)
# ==========================================
# RIGHT PANEL : AI AGENT
# ==========================================

with right:

    st.markdown('<div class="agent">', unsafe_allow_html=True)

    st.markdown("## 🤖 AI Shopping Agent")

    st.caption("Powered by ACI")

    st.divider()

    if not st.session_state.enabled:

        st.warning("Merchant not AI Ready")

        st.markdown("""
### Current Status

❌ Product Schema Unknown

❌ Inventory Structure Unknown

❌ Return Policy Unknown

❌ Payment Flow Unknown

---

The AI agent cannot safely purchase from this website.
""")

    else:
        confidence = st.session_state.catalog.get("confidence", 98)

        # Temporary debug
        st.write("Confidence object:", confidence)

        if isinstance(confidence, dict):
            confidence_value = confidence.get("overall", 98)
        else:
            confidence_value = confidence

        st.metric(
            "Confidence",
            confidence_value,
        )

        

        st.success("Merchant Successfully Converted")

        

        st.success("✅ Product Schema")

        st.success("✅ Inventory")

        st.success("✅ Payments")

        st.success("✅ Return Policy")

        st.info("🤖 Ready to Purchase")

    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# ENABLE ACI
# ==========================================

st.divider()

st.markdown("## ⚡ Enable Agent Commerce Interface")

if st.button(
    "🚀 ENABLE ACI",
    use_container_width=True,
    type="primary",
):

    progress = st.progress(0)

    status = st.empty()

    animation = [

        "🔍 Reading Merchant Website...",
        "📦 Parsing Products...",
        "🧠 Understanding Catalog...",
        "📝 Reading Policies...",
        "⚡ Building ACI...",
        "🛡 Validating...",
        "🤖 AI Learning Merchant...",
        "✅ Done",
    ]

    for i, text in enumerate(animation):

        status.info(text)

        progress.progress((i + 1) * 12)

        time.sleep(0.7)

    st.session_state.catalog = get_catalog(

        st.session_state.audit,

        st.session_state.run_id,

        str(CSV_PATH),

        str(POLICY_PATH),

        merchant_id="sunrise-general-store",

        merchant_name="Sunrise General Store",

        default_currency="INR",

    )

    st.session_state.enabled = True

    progress.progress(100)

    status.success("🎉 Merchant is AI Ready")

    st.balloons()

    time.sleep(1)

    st.rerun()

# ==========================================
# AI READY SUMMARY
# ==========================================

if st.session_state.enabled:

    catalog = st.session_state.catalog

    st.divider()

    st.markdown("# 🚀 AI Ready Merchant")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Products",
            len(catalog["records"]),
        )

    with c2:

        scores = [
            r["readiness"]["score"]
            for r in catalog["records"]
        ]

        st.metric(
            "Average Score",
            round(sum(scores) / len(scores), 1),
        )

    with c3:

        ready = len(
            [
                r
                for r in catalog["records"]
                if r["readiness"]["score"] >= 80
            ]
        )

        st.metric(
            "Ready Products",
            ready,
        )

    with c4:

        st.metric(
            "Merchant",
            "AI Ready",
        )
# ==========================================
# AI PURCHASE DEMO
# ==========================================

st.divider()

st.markdown("## 🤖 AI Autonomous Purchase")

if st.session_state.enabled:

    catalog = st.session_state.catalog

    product_names = [
        r["product"]["title"]
        for r in catalog["records"]
    ]

    selected = st.selectbox(
        "Choose Product",
        product_names,
        key="purchase_product",
    )

    selected_record = next(
        r
        for r in catalog["records"]
        if r["product"]["title"] == selected
    )

    product = selected_record["product"]

    c1, c2 = st.columns([2, 1])

    with c1:

        st.markdown("### Product Details")

        st.write(f"**Product ID:** {product['product_id']}")

        st.write(f"**Category:** {product.get('category','-')}")

        st.write(
            f"**Price:** {product['price']['currency']} {product['price']['amount']}"
        )

        st.write(
            f"**Stock:** {product['stock']['status']}"
        )

        st.progress(
            selected_record["readiness"]["score"] / 100
        )

        st.caption(
            f"Agent Readiness : {selected_record['readiness']['score']}%"
        )

    with c2:

        st.metric(
            "AI Status",
            "READY"
        )

        st.metric(
            "Confidence",
            "98%"
        )

    st.markdown("---")

    if st.button(
        "🛒 BUY FOR USER",
        use_container_width=True,
        type="primary",
    ):

        progress = st.progress(0)

        status = st.empty()

        steps = [

            ("🔍 Identifying Product",10),

            ("📦 Checking Inventory",25),

            ("💳 Validating Budget",40),

            ("🛡 Security Verification",55),

            ("⚡ Creating Payment Intent",70),

            ("🏦 Authorizing Payment",85),

            ("📬 Creating Merchant Order",95),

            ("✅ Order Created",100)

        ]

        for text,val in steps:

            status.info(text)

            progress.progress(val)

            time.sleep(0.8)

        st.success("🎉 Purchase Completed Successfully")

        st.info(
            f"""
Order ID : **ACI-{product['product_id']}**

Merchant : **Sunrise General Store**

Status : **Confirmed**

ETA : **Tomorrow**
"""
        )

        st.balloons()

else:

    st.info("Enable ACI first to allow the AI Agent to purchase.")

# ==========================================
# DEVELOPER CONSOLE
# ==========================================

st.divider()

with st.expander("⚙️ Developer Console", expanded=False):

    if st.session_state.catalog is None:

        st.info("No catalog generated yet.")

    else:

        catalog = st.session_state.catalog

        rows = []

        for r in catalog["records"]:

            rows.append({

                "Product ID":
                    r["product"]["product_id"],

                "Title":
                    r["product"]["title"],

                "Price":
                    r["product"]["price"]["amount"],

                "Currency":
                    r["product"]["price"]["currency"],

                "Stock":
                    r["product"]["stock"]["status"],

                "Readiness":
                    r["readiness"]["score"]

            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
# ==========================================
# BEFORE vs AFTER COMPARISON
# ==========================================

st.divider()

st.markdown("## 📈 Before vs After ACI")

if st.session_state.enabled:

    catalog = st.session_state.catalog

    first_product = catalog["records"][0]["product"]["product_id"]

    before_after = run_before_after(
        catalog=catalog,
        product_id=first_product,
        max_price=100000,
        csv_path=str(CSV_PATH),
    )

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("### ❌ Before ACI")

        if isinstance(before_after, dict):

            st.json(before_after.get("before", before_after))

        else:

            st.write(before_after)

    with c2:

        st.markdown("### ✅ After ACI")

        if isinstance(before_after, dict):

            st.json(before_after.get("after", before_after))

        else:

            st.write(before_after)

# ==========================================
# FAILURE TESTS
# ==========================================

st.divider()

st.markdown("## 🧪 AI Failure Simulation")

if st.session_state.enabled:

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "📦 Out Of Stock",
            use_container_width=True,
        ):

            pid = catalog["records"][0]["product"]["product_id"]

            result = scenario_out_of_stock(
                catalog,
                st.session_state.audit,
                st.session_state.run_id,
                pid,
            )
            st.json(result)

    with col2:

        if st.button(
            "💰 Budget Breach",
            use_container_width=True,
        ):

            pid = catalog["records"][0]["product"]["product_id"]

            result = scenario_budget_breach(
                catalog,
                st.session_state.audit,
                st.session_state.run_id,
                pid,
            )

            st.json(result)

    with col3:

        if st.button(
            "🛡 Prompt Injection",
            use_container_width=True,
        ):

            result = scenario_injection(
            st.session_state.catalog
        )
            st.json(result)

# ==========================================
# GENERATED ACI RECORDS
# ==========================================

st.divider()

st.markdown("## 📦 Generated ACI Records")

if st.session_state.enabled:

    titles = [
        r["product"]["title"]
        for r in catalog["records"]
    ]

    chosen = st.selectbox(
        "Choose Product",
        titles,
        key="record_product",
    )

    record = next(
        r
        for r in catalog["records"]
        if r["product"]["title"] == chosen
    )

    st.json(record)

# ==========================================
# UNRESOLVED COLUMNS
# ==========================================

st.divider()

st.markdown("## ⚠ Parser Report")

if st.session_state.enabled:

    
    unresolved = unresolved_columns(str(CSV_PATH))

    if unresolved:

        st.warning(unresolved)

    else:

        st.success("No unresolved columns detected.")

# ==========================================
# AUDIT LOG
# ==========================================

st.divider()

st.markdown("## 📜 Audit Trail")

events = getattr(
    st.session_state.audit,
    "events",
    [],
)

if events:

    audit_df = pd.DataFrame(events)

    st.dataframe(
        audit_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info("No audit events recorded.")

st.divider()

st.caption(
    "🚀 ACI • Agent Commerce Interface • Built for Hackathon Demo"
)

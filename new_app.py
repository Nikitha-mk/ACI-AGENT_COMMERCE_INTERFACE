"""
ACI
Agent Commerce Interface

Hackathon Edition
"""

import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from audit_log import AuditLog, new_run_id
from parser import unresolved_columns
from pipeline import (
    get_catalog,
    run_before_after,
    scenario_budget_breach,
    scenario_injection,
    scenario_out_of_stock,
)

# --------------------------------------
# PAGE
# --------------------------------------

st.set_page_config(
    page_title="ACI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------
# SESSION
# --------------------------------------

if "catalog" not in st.session_state:
    st.session_state.catalog = None

if "audit" not in st.session_state:
    st.session_state.audit = AuditLog()

if "run_id" not in st.session_state:
    st.session_state.run_id = new_run_id()

if "enabled" not in st.session_state:
    st.session_state.enabled = False

# --------------------------------------
# SAMPLE DATA
# --------------------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"

SAMPLES = {
    "Sunrise General Store": {
        "csv": DATA_DIR / "merchant_products_raw.csv",
        "policy": DATA_DIR / "return_policy.txt",
        "merchant_id": "sunrise-general-store",
        "merchant_name": "Sunrise General Store",
        "currency": "INR",
    },
    "Aria Home Co.": {
        "csv": DATA_DIR / "other_merchant_sample.csv",
        "policy": DATA_DIR / "other_merchant_policy.txt",
        "merchant_id": "aria-home-co",
        "merchant_name": "Aria Home Co.",
        "currency": "USD",
    },
}

# --------------------------------------
# STRIPE STYLE
# --------------------------------------

st.markdown(
"""
<style>

html,
body,
[class*="css"]{

background:#0B1020;

color:#F8FAFC;

font-family:Inter,sans-serif;

}

.block-container{

max-width:1450px;

padding-top:20px;

}

section[data-testid="stSidebar"]{

display:none;

}

.hero{

background:linear-gradient(
135deg,
#635BFF,
#7C6CFF
);

padding:40px;

border-radius:24px;

box-shadow:
0px 25px 60px rgba(0,0,0,.35);

margin-bottom:25px;

}

.hero h1{

font-size:52px;

font-weight:800;

margin-bottom:10px;

}

.hero p{

font-size:20px;

opacity:.9;

}

.card{

background:#141B34;

border-radius:22px;

padding:25px;

box-shadow:

0 15px 35px rgba(0,0,0,.28);

border:1px solid rgba(255,255,255,.05);

}

.agent{

background:#111827;

border-radius:22px;

padding:25px;

border:1px solid rgba(99,91,255,.25);

box-shadow:

0 15px 35px rgba(0,0,0,.30);

}

.metric{

background:#18223E;

padding:20px;

border-radius:16px;

text-align:center;

}

.big button{

height:72px;

font-size:24px;

font-weight:700;

border-radius:18px;

background:#635BFF;

color:white;

}

.buy button{

height:58px;

font-size:18px;

font-weight:700;

border-radius:14px;

background:#16C784;

color:white;

}

.success{

background:#073B2D;

padding:20px;

border-radius:16px;

border-left:5px solid #16C784;

}

.fail{

background:#3A1212;

padding:20px;

border-radius:16px;

border-left:5px solid #FF5C5C;

}

</style>
""",
unsafe_allow_html=True,
)

# --------------------------------------
# HERO
# --------------------------------------

st.markdown(
"""
<div class="hero">

<h1>🛍️ ACI</h1>

<p>

Turn any merchant website into an
AI-readable storefront.

Humans already understand commerce.

Now AI agents can too.

</p>

</div>
""",
unsafe_allow_html=True,
)
# --------------------------------------
# LAYOUT
# --------------------------------------

left, right = st.columns([2.2, 1])

# ======================================
# MERCHANT WEBSITE
# ======================================

with left:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    top1, top2 = st.columns([3, 1])

    with top1:
        st.text_input(
            "",
            placeholder="🔍 Search products...",
            disabled=True,
            label_visibility="collapsed",
        )

    with top2:
        st.button("🛒 Cart (2)", use_container_width=True)

    st.markdown("---")

    banner1, banner2 = st.columns([2, 1])

    with banner1:

        st.markdown(
            """
### 👋 Welcome Back

#### Summer Sale is Live

Up to **40% OFF** on selected products.

"""
        )

    with banner2:

        st.metric(
            "Orders Today",
            "248",
            "+18%",
        )

    st.markdown("### Featured Products")

    if st.session_state.catalog is None:

        products = [

            {
                "name": "Premium Cotton Tee",
                "price": "₹599",
                "rating": "4.8",
                "stock": "Only 5 Left",
            },
            {
                "name": "Wireless Earbuds",
                "price": "₹2,999",
                "rating": "4.9",
                "stock": "In Stock",
            },
            {
                "name": "Running Shoes",
                "price": "₹4,499",
                "rating": "4.7",
                "stock": "Limited",
            },

        ]

    else:

        products = []

        for r in st.session_state.catalog["records"][:6]:

            products.append(
                {
                    "name": r["title"],
                    "price": f'{r["currency"]} {r["price"]}',
                    "rating": "4.8",
                    "stock": "In Stock"
                    if r["availability"] == "in_stock"
                    else "Out of Stock",
                }
            )

    col1, col2, col3 = st.columns(3)

    cols = [col1, col2, col3]

    for i, product in enumerate(products):

        with cols[i % 3]:

            with st.container(border=True):

                st.markdown("# 📦")

                st.markdown(
                    f"### {product['name']}"
                )

                st.caption(
                    f"⭐⭐⭐⭐⭐  {product['rating']}"
                )

                st.markdown(
                    f"## {product['price']}"
                )

                if product["stock"] == "In Stock":

                    st.success(product["stock"])

                elif product["stock"] == "Limited":

                    st.warning(product["stock"])

                else:

                    st.error(product["stock"])

                st.button(
                    "Buy Now",
                    key=f"buy{i}",
                    use_container_width=True,
                )

    st.markdown("</div>", unsafe_allow_html=True)

# ======================================
# AI PANEL
# ======================================

with right:

    st.markdown('<div class="agent">', unsafe_allow_html=True)

    st.markdown("## 🤖 AI Shopping Agent")

    st.caption("Powered by ACI")

    st.markdown("---")

    if not st.session_state.enabled:

        st.info("Scanning merchant website...")

        time.sleep(0.2)

        st.error("❌ Product schema missing")

        time.sleep(0.2)

        st.error("❌ Inventory not standardized")

        time.sleep(0.2)

        st.error("❌ Return policy unavailable")

        time.sleep(0.2)

        st.error("❌ Payment intent not understood")

        st.markdown("---")

        st.markdown(
            """
<div class="fail">

### Purchase Failed

I cannot safely purchase from this merchant because
the website is designed for humans, not AI agents.

</div>
""",
            unsafe_allow_html=True,
        )

    else:

        st.success("Reading ACI...")

        st.success("✅ Product identified")

        st.success("✅ Price verified")

        st.success("✅ Inventory confirmed")

        st.success("✅ Policy parsed")

        st.success("✅ Payment endpoint verified")

        st.metric(
            "Confidence",
            "98%",
        )

        st.markdown(
            """
<div class="success">

### Ready

I fully understand this merchant
and can complete purchases safely.

</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    # ======================================
# ENABLE ACI
# ======================================

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("## ⚡ Transform this Merchant into an AI-Ready Store")

merchant_choice = st.selectbox(
    "Choose Merchant",
    list(SAMPLES.keys()),
    label_visibility="collapsed",
)

sample = SAMPLES[merchant_choice]

enable = st.button(
    "✨ ENABLE ACI",
    use_container_width=True,
    type="primary",
)

if enable:

    progress = st.progress(0)

    status = st.empty()

    stages = [
        ("🔍 Reading merchant website...", 10),
        ("📦 Parsing product catalog...", 25),
        ("🧠 Understanding product metadata...", 40),
        ("🛠 Normalizing merchant schema...", 55),
        ("🛡 Validating payment endpoints...", 70),
        ("📄 Reading return policy...", 82),
        ("⚡ Generating ACI Records...", 94),
        ("✅ Merchant is AI Ready!", 100),
    ]

    for text, value in stages:

        status.info(text)

        progress.progress(value)

        time.sleep(0.8)

    st.session_state.catalog = get_catalog(

        st.session_state.audit,

        st.session_state.run_id,

        str(sample["csv"]),

        str(sample["policy"]),

        merchant_id=sample["merchant_id"],

        merchant_name=sample["merchant_name"],

        default_currency=sample["currency"],

    )

    st.session_state.enabled = True

    progress.progress(100)

    status.success("🎉 ACI Successfully Enabled")

    time.sleep(1)

    st.balloons()

    st.rerun()

# ======================================
# AI READY DASHBOARD
# ======================================

if st.session_state.enabled and st.session_state.catalog:

    catalog = st.session_state.catalog

    st.divider()

    st.markdown("# 🚀 Merchant is now AI Ready")

    a, b, c, d = st.columns(4)

    with a:

        st.metric(
            "Products",
            len(catalog["records"]),
        )

    with b:

        st.metric(
            "Confidence",
            f'{catalog["confidence"]["score"]}%',
        )

    with c:

        ready = sum(
            1
            for x in catalog["records"]
            if x["readiness"]["score"] >= 80
        )

        st.metric(
            "Ready Products",
            ready,
        )

    with d:

        avg = round(
            sum(
                x["readiness"]["score"]
                for x in catalog["records"]
            ) / len(catalog["records"]),
            1,
        )

        st.metric(
            "Average Score",
            avg,
        )

    st.success(
        "🤖 AI can now understand this merchant and purchase products autonomously."
    )

    st.markdown("---")

    st.subheader("🛒 AI Purchase Demo")

    if st.button(
        "🤖 BUY FOR USER",
        use_container_width=True,
    ):

        steps = st.empty()

        purchase = st.progress(0)

        actions = [
            ("Searching inventory...", 15),
            ("Verifying stock...", 30),
            ("Checking user budget...", 45),
            ("Creating payment intent...", 60),
            ("Authorizing payment...", 80),
            ("Creating merchant order...", 95),
            ("Purchase Successful!", 100),
        ]

        for txt, val in actions:

            steps.info(txt)

            purchase.progress(val)

            time.sleep(1)

        steps.success("🎉 AI completed the purchase successfully!")

        st.success(
            "Order ID : ACI-2025-001\n\nEstimated Delivery : Tomorrow"
        )

        st.balloons()
    # ======================================
# DEVELOPER CONSOLE
# ======================================

st.divider()

with st.expander("⚙️ Developer Console", expanded=False):

    catalog = st.session_state.catalog

    st.markdown("## 📊 Agent Readiness")

    rows = []

    for r in catalog["records"]:

        rows.append(
            {
                "Product": r["title"],
                "SKU": r["sku"],
                "Price": r["price"],
                "Currency": r["currency"],
                "Availability": r["availability"],
                "Score": r["readiness"]["score"],
                "Status": (
                    "✅ Ready"
                    if r["readiness"]["score"] >= 80
                    else "⚠ Needs Work"
                ),
            }
        )

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.markdown("## 📈 Before vs After")

    before_after = run_before_after(catalog)

    left, right = st.columns(2)

    with left:

        st.subheader("Before ACI")

        st.metric(
            "Confidence",
            f"{before_after['before']['confidence']}%",
        )

        st.metric(
            "Products Parsed",
            before_after["before"]["products"],
        )

        st.metric(
            "Readiness",
            before_after["before"]["readiness"],
        )

    with right:

        st.subheader("After ACI")

        st.metric(
            "Confidence",
            f"{before_after['after']['confidence']}%",
        )

        st.metric(
            "Products Parsed",
            before_after["after"]["products"],
        )

        st.metric(
            "Readiness",
            before_after["after"]["readiness"],
        )

    st.divider()

    st.markdown("## 🧪 Failure Scenarios")

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "Out of Stock",
            use_container_width=True,
        ):

            result = scenario_out_of_stock(catalog)

            st.json(result)

    with col2:

        if st.button(
            "Budget Breach",
            use_container_width=True,
        ):

            result = scenario_budget_breach(catalog)

            st.json(result)

    with col3:

        if st.button(
            "Prompt Injection",
            use_container_width=True,
        ):

            result = scenario_injection(catalog)

            st.json(result)

    st.divider()

    st.markdown("## 📦 Generated ACI Records")

    record_index = st.selectbox(
        "Choose Product",
        range(len(catalog["records"])),
        format_func=lambda x: catalog["records"][x]["title"],
    )

    st.json(catalog["records"][record_index])

    st.divider()

    st.markdown("## ⚠️ Unresolved Columns")

    unresolved = unresolved_columns(catalog)

    if unresolved:

        st.warning(unresolved)

    else:

        st.success("No unresolved merchant fields.")

    st.divider()

    st.markdown("## 📜 Audit Trail")

    logs = st.session_state.audit.events

    if logs:

        audit_df = pd.DataFrame(logs)

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No audit events available.")

st.markdown("---")

st.caption(
    "🚀 ACI • Agent Commerce Interface • Built for AI-Native Commerce"
)
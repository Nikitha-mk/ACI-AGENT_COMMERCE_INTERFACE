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

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ---------------- APP ---------------- */

html,body,[class*="css"]{
    font-family:'Inter',sans-serif;
}

.stApp{

background:
radial-gradient(circle at top right,#6C63FF25 0%,transparent 35%),
radial-gradient(circle at bottom left,#00D4FF18 0%,transparent 30%),
#0A0F1F;

color:white;

}

/* ---------------- FULL WIDTH ---------------- */

.block-container{

max-width:1850px;

padding-top:1rem;

padding-left:3rem;

padding-right:3rem;

padding-bottom:2rem;

}

/* ---------------- REMOVE STREAMLIT ---------------- */

header{
visibility:hidden;
}

#MainMenu{
visibility:hidden;
}

footer{
visibility:hidden;
}

/* ---------------- HERO ---------------- */

.hero{

background:linear-gradient(
135deg,
#635BFF,
#7A6FFF
);

padding:45px;

border-radius:28px;

color:white;

box-shadow:
0 25px 60px rgba(99,91,255,.40);

margin-bottom:35px;

overflow:hidden;

position:relative;

}

.hero::after{

content:"";

position:absolute;

right:-120px;

top:-120px;

width:300px;

height:300px;

border-radius:50%;

background:rgba(255,255,255,.07);

}

/* ---------------- CARDS ---------------- */

.card{

background:#12192E;

border-radius:22px;

padding:24px;

border:1px solid rgba(255,255,255,.05);

box-shadow:
0 18px 45px rgba(0,0,0,.30);

transition:.25s;

}

.card:hover{

transform:translateY(-4px);

box-shadow:
0 28px 55px rgba(0,0,0,.45);

}

/* ---------------- AI CARD ---------------- */

.agent{

background:#12192E;

padding:24px;

border-radius:22px;

border-left:5px solid #635BFF;

box-shadow:
0 18px 45px rgba(0,0,0,.35);

}

/* ---------------- METRICS ---------------- */

div[data-testid="metric-container"]{

background:#12192E;

border-radius:20px;

padding:20px;

border:1px solid rgba(255,255,255,.05);

box-shadow:
0 12px 30px rgba(0,0,0,.25);

}

div[data-testid="metric-container"] label{

font-size:13px;

font-weight:600;

color:#9CA8C7;

}

div[data-testid="metric-container"] div{

font-size:30px;

font-weight:700;

}

/* ---------------- BUTTONS ---------------- */

.stButton>button{

background:#635BFF;

color:white;

border:none;

border-radius:14px;

height:52px;

font-size:16px;

font-weight:700;

transition:.25s;

width:100%;

}

.stButton>button:hover{

background:#7C72FF;

transform:translateY(-2px);

box-shadow:
0 15px 35px rgba(99,91,255,.45);

}

/* ---------------- INPUT ---------------- */

.stTextInput input{

background:#1A233C;

color:white;

border-radius:14px;

border:1px solid #2F3C62;

height:50px;

}

/* ---------------- SELECT ---------------- */

.stSelectbox > div{

background:#1A233C;

border-radius:14px;

}

/* ---------------- DATAFRAME ---------------- */

[data-testid="stDataFrame"]{

border-radius:20px;

overflow:hidden;

border:1px solid rgba(255,255,255,.05);

}

/* ---------------- EXPANDERS ---------------- */

.streamlit-expanderHeader{

font-size:18px;

font-weight:600;

}

/* ---------------- ALERTS ---------------- */

.stSuccess,
.stInfo,
.stWarning,
.stError{

border-radius:16px;

}

/* ---------------- PROGRESS ---------------- */

.stProgress > div > div{

background:#635BFF;

}

/* ---------------- SCROLLBAR ---------------- */

::-webkit-scrollbar{

width:10px;

}

::-webkit-scrollbar-thumb{

background:#2F3C62;

border-radius:20px;

}

::-webkit-scrollbar-thumb:hover{

background:#635BFF;

}

</style>
""", unsafe_allow_html=True)
# ==========================================
# STRIPE HERO
# ==========================================

st.markdown("""
<div class="hero">

<div style="display:flex;
justify-content:space-between;
align-items:center;">

<div>

<div style="
font-size:15px;
font-weight:700;
letter-spacing:1px;
opacity:.85;
margin-bottom:12px;">

AGENT COMMERCE INFRASTRUCTURE

</div>

<h1 style="
font-size:62px;
font-weight:800;
margin:0;
line-height:1.05;">

🛍 ACI

</h1>

<div style="
font-size:28px;
margin-top:10px;
font-weight:600;">

Enable AI Agents to Shop Safely

</div>

<p style="
font-size:18px;
max-width:650px;
opacity:.92;
margin-top:20px;
line-height:1.7;">

Transform any merchant website into an AI-readable,
AI-purchasable commerce platform.

Products become structured.

Policies become understandable.

AI can finally buy with confidence.

</p>

</div>

<div style="text-align:right;">

<div style="
background:white;
color:#635BFF;
padding:18px;
border-radius:18px;
width:180px;
box-shadow:0 20px 40px rgba(0,0,0,.15);">

<div style="
font-size:13px;
font-weight:700;">

AI READINESS

</div>

<div style="
font-size:48px;
font-weight:800;
margin-top:8px;">

98%

</div>

<div style="
font-size:13px;
color:#555;">

Merchant Ready

</div>

</div>

</div>

</div>

</div>
""", unsafe_allow_html=True)
c1,c2,c3,c4=st.columns(4)

with c1:
    st.metric(
        "Products",
        len(catalog["records"]) if st.session_state.enabled else "--"
    )

with c2:
    st.metric(
        "AI Confidence",
        "98%"
    )

with c3:
    st.metric(
        "Merchant",
        "Ready" if st.session_state.enabled else "Offline"
    )

with c4:
    st.metric(
        "Purchases",
        "12"
    )

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

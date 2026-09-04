<div align="center">

# 🛒 ACI

## Agent Commerce Interface

### **Making merchants AI-ready for autonomous shopping.**

AI agents can browse the web.
They can reason.
They can plan.

**But they still can't trust a merchant's product page.**

ACI is the trust layer between merchants and AI agents.

---

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Live-red?style=for-the-badge)
![Razorpay](https://img.shields.io/badge/Razorpay-Test%20Mode-0066ff?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/Built%20For-Hackathon-purple?style=for-the-badge)

</div>

---

# 🤔 The Problem

Today, merchant websites are built for **humans**.

AI agents don't see

- product pages
- buy buttons
- return policies

the way we do.

Instead they see messy HTML, inconsistent CSVs, ambiguous prices, different inventory formats and sometimes even malicious prompt injections.

An autonomous shopping agent **cannot safely trust this information.**

---

# 💡 Our Solution

ACI transforms messy merchant data into a **machine-readable commerce contract**.

Instead of this...

```
Price : Rs. 599
Available ✔
Returns within 7 days*
```

the AI receives

```json
{
  "price": {
    "amount": 599,
    "currency": "INR"
  },
  "stock": {
    "status": "in_stock"
  },
  "return_policy": "7_days",
  "readiness": 98
}
```

One format.

One schema.

Every merchant.

---

# 🎬 Demo

> **Merchant → ACI → AI Agent → Purchase**

(Add GIF or Screenshot here)

---

# ✨ Features

## 📦 Merchant Readiness Dashboard

Every uploaded product receives

- AI Readiness Score
- Gap Detection
- Prompt Injection Status
- Merchant Confidence Score

---

## 🤖 AI Autonomous Purchase

The AI evaluates

✅ Product

✅ Price

✅ Inventory

✅ Confidence

before making a purchase.

---

## 🧾 Generated ACI Records

Every merchant catalog becomes

- structured
- typed
- standardized

through **ACI v1 JSON**.

---

## 🛡 Prompt Injection Detection

Merchants cannot manipulate the AI.

Hidden instructions are

✔ detected

✔ stripped

✔ logged

before reaching the shopping agent.

---

## ⚠ Failure Simulation

Test scenarios include

- Out of Stock
- Budget Breach
- Prompt Injection

The AI never guesses.

It explains every decision.

---

## 🔍 Before vs After ACI

See the exact difference between

Raw Merchant Data

↓

Standardized ACI Record

---

## 💻 Developer Console

Inspect

- Readiness
- Security
- Validation
- Audit Reference

Everything remains explainable.

---

# 🏗 Architecture

```
Merchant Catalog
        │
        ▼
      Parser
        │
        ▼
   Normalizer
        │
        ▼
    Validator
        │
        ▼
 Readiness Score
        │
        ▼
    ACI v1 JSON
        │
        ▼
 AI Shopping Agent
        │
        ▼
 Payment Gate
(Budget • Stock • Consent)
        │
        ▼
 Razorpay Test Order
        │
        ▼
 Audit Trail
```

---

# 🛠 Tech Stack

| Layer    | Technology                 |
| -------- | -------------------------- |
| Frontend | Streamlit                  |
| Backend  | Python                     |
| Data     | Pandas                     |
| Payments | Razorpay                   |
| Security | Prompt Injection Detection |
| Storage  | JSON                       |

---

# 🚀 Running Locally

```bash
git clone https://github.com/Nikitha-mk/ACI-AGENT_COMMERCE_INTERFACE.git

cd ACI-AGENT_COMMERCE_INTERFACE

pip install -r requirements.txt

streamlit run app.py
```

---

# 🌙 What Broke at 2 AM?

Hackathons aren't real without bugs.

Things that actually broke while building ACI:

- `KeyError: 'title'` because merchant catalogs had different schemas.
- Streamlit crashed because the AI confidence returned a dictionary instead of a number.
- Function signature mismatches after integrating failure simulations.
- Duplicate Streamlit widget IDs.
- Parser expected a CSV path but received a Python dictionary.

Every bug forced us to make the pipeline more robust instead of patching individual screens.

---

# 📸 Screenshots

| Landing       | AI Purchase   |
| ------------- | ------------- |
| <img width="1033" height="871" alt="Screenshot 2026-09-04 211953" src="https://github.com/user-attachments/assets/fe86de23-73a6-4cde-afad-375c1f641086" />
| <img width="1422" height="747" alt="Screenshot 2026-09-04 224325" src="https://github.com/user-attachments/assets/cbe8c8f8-d005-41d8-8d29-bd1dc5647f9b" />
 |

| Prompt Injection | Generated ACI |
| ---------------- | ------------- |
| <img width="477" height="522" alt="Screenshot 2026-09-04 211022" src="https://github.com/user-attachments/assets/4cbce008-d9f7-47e2-94d9-9204ca45e695" />
   | <img width="1032" height="881" alt="Screenshot 2026-09-04 211044" src="https://github.com/user-attachments/assets/8b54e3e6-d5db-41a8-aa08-f638ab09cb59" />
 |

---

# 🔮 Future Work

- MCP Integration
- Multi-Agent Commerce
- Live Merchant APIs
- Enterprise Dashboard
- Agent-to-Agent Negotiation

---

<div align="center">

## 🚀 Built with ❤️ for Hackathon

### **"AI shopping needs trust before it needs intelligence."**

</div>

# ACI — Agent Commerce Infrastructure

**The infrastructure is the product.** ACI is a translation layer that turns
any merchant's messy catalog + policy text into one AI-readable format
(ACI v1) — so an AI shopping agent doesn't have to re-learn every merchant
from scratch, badly. The test agent in this repo exists only to prove the
pipeline works; if anything in this build looks more impressive than the
pipeline itself, it's not the point.

## Problem
AI shopping assistants are starting to buy things on people's behalf. Every
merchant exposes catalog, stock, and policy differently — messy CSVs,
free-text policies, listings that can contain hidden instructions aimed at
whatever AI reads them. Nobody is building the shared, trustworthy layer in
between. ACI is that layer.

## Architecture

```
 raw merchant data                         ACI v1 record
 (CSV + policy .txt)                      (JSON, schema-locked)
        │                                          ▲
        ▼                                          │
 ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │
 │   Parser    │─▶│ Normalizer  │─▶│ Validator │──┘
 └─────────────┘  └─────────────┘  └───────────┘
                                          │
                                readiness score +
                              injection detect/strip
                                          │
                                          ▼
                              ┌─────────────────────┐
                              │   Tiny Test Agent    │  (proof only)
                              │ decide_raw / decide_aci │
                              └─────────────────────┘
                                          │
                                          ▼
                        ┌───────────────────────────────┐
                        │  Deterministic Payment Gate    │
                        │  budget → stock → consent →    │
                        │  Razorpay (test mode)           │
                        │  — no LLM in this path —        │
                        └───────────────────────────────┘
                                          │
                                          ▼
                                   Audit log (flat trail,
                                   every stage, every record)
```

The model never decides whether money moves — the payment gate is plain
deterministic code, on purpose.

## What's in this repo

```
aci-v1/
├── app.py                     # Streamlit dashboard (the live demo)
├── requirements.txt
├── schema/
│   └── aci-v1.schema.json     # the locked ACI v1 JSON Schema
├── docs/
│   └── ACI-v1-spec.md         # one-page spec explaining the schema
├── data/
│   ├── merchant_products_raw.csv    # sample 1: Sunrise General Store (INR, comma CSV)
│   ├── return_policy.txt            # sample 1 policy w/ built-in conflicts
│   ├── other_merchant_sample.csv    # sample 2: Aria Home Co. (USD, semicolon CSV,
│   │                                #   completely different column names)
│   └── other_merchant_policy.txt    # sample 2 policy, differently worded conflicts
├── src/
│   ├── parser.py               # Stage 1: raw -> rough structure
│   ├── normalizer.py           # Stage 2: standardize price/stock/variants/policy
│   ├── validator.py            # Stage 3: gap flags + injection detection/stripping
│   ├── readiness.py            # Stage 4: rule-based readiness score + confidence
│   ├── aci_builder.py          # ties 1-4 together into full ACI v1 records
│   ├── audit_log.py            # flat audit trail
│   ├── test_agent.py           # the before/after proof (raw vs ACI decision)
│   ├── payment_gate.py         # deterministic budget/stock/consent/Razorpay gate
│   └── pipeline.py             # orchestrator + CLI demo + 3 failure scenarios
└── outputs/                    # audit_log.csv lands here after a run
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the CLI demo (fastest way to see everything work)

```bash
cd src
python pipeline.py
```

Prints: all 10 ACI v1 records with readiness scores, the before/after
proof (raw agent fooled by an injected instruction + a price-parsing bug
vs. the ACI agent correctly declining at the real price), all 3 failure
scenarios, and the last 10 audit log rows. Saves the full audit trail to
`outputs/audit_log.csv`.

## Run the live dashboard

```bash
streamlit run app.py
```

Opens a local website at `http://localhost:8501`. One screen, top to
bottom:
1. **Turn ACI on** — pick a bundled sample merchant, or upload your own
   CSV + policy `.txt` directly in the browser. Builds ACI v1 records,
   shows a readiness-score table and gap list per product, plus Merchant
   Confidence metadata.
2. **Agent before/after** — pick a product + budget, see the raw-data
   agent get it wrong next to the ACI-data agent getting it right, with a
   stated reason.
3. **Trigger the 3 failure scenarios** — prompt injection, out-of-stock
   substitution (with a consent checkbox), and a budget breach at the
   payment gate.
4. **Live audit trail** — every stage of every run, newest first.

### This is genuinely general-purpose, not tuned to one file

The parser doesn't assume a fixed column layout or delimiter — it resolves
whatever headers the merchant actually used (`SKU`/`id`/`product_id`,
`Cost`/`Price`/`MRP`, `Availability`/`Stock`/`Qty`, etc.) against a canonical
alias list, and auto-detects comma/semicolon/tab/pipe delimiters. The
normalizer handles multiple currency symbols (₹, $, €, £), stock phrased as
a number, a status word, or a number embedded in text ("12 units left"),
and variant syntax with or without an explicit type label. The policy
normalizer finds return windows and conflicts by pattern, not by
hardcoding this merchant's exact wording.

**Proof it generalizes:** `data/other_merchant_sample.csv` is a second,
independently-authored file — different columns (`SKU;Product Name;Cost;
Availability;Product Type;Options;Notes`), a semicolon delimiter, USD
prices, different stock phrasing, and its own differently-worded
prompt-injection payload and policy contradiction. The pipeline builds
correct ACI v1 records from it with zero code changes — pick "Bundled
sample #2 — Aria Home Co." in the dashboard's source selector to see it
live, or run:

```bash
cd src && python3 -c "
from audit_log import AuditLog, new_run_id
from pipeline import get_catalog
audit = AuditLog()
catalog = get_catalog(audit, new_run_id(),
    '../data/other_merchant_sample.csv', '../data/other_merchant_policy.txt',
    merchant_id='aria-home-co', merchant_name='Aria Home Co.', default_currency='USD')
print(len(catalog['records']), 'records built')
"
```

To use your own merchant data, either upload a CSV + policy `.txt` in the
dashboard's "Upload my own files" mode, or drop files into `data/` and
call `get_catalog(..., merchant_id=..., merchant_name=..., default_currency=...)`
from `src/pipeline.py` directly. If the parser can't find a column for
some canonical field (e.g. no recognizable price column at all), the
dashboard surfaces a warning naming exactly which fields it couldn't
resolve, rather than silently defaulting everything to empty.

## Payment gate — real vs. mock Razorpay

`payment_gate.py` calls the real Razorpay test-mode API when
`RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` env vars are set:

```bash
export RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
export RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
```

Without those set (e.g. offline development, or judges running this without
your keys), it falls back to a clearly-labeled mock order object with the
same shape, so the rest of the pipeline and dashboard stay fully demoable.
Either way, the gate logic itself — budget check, stock check, consent
check — is identical and untouched by any LLM.

## ACI v1 spec

See [`docs/ACI-v1-spec.md`](docs/ACI-v1-spec.md) and the enforceable
schema at [`schema/aci-v1.schema.json`](schema/aci-v1.schema.json). This is
the intended differentiator: not a script that cleans up one merchant's
data, but a named, versioned format any merchant or agent could adopt.

## Scope guardrails (deliberately not built)

- No agent memory or personalization
- No second AI model for "Merchant Confidence" — it's rule-based metadata
- No multi-merchant marketplace — one synthetic merchant is enough to prove
  the pipeline
- No real bank integration — Razorpay test mode only
- Spec stays at v1, one page

## What's next / what broke

The normalizer's rules cover every pattern seen across two independently-
authored sample merchants (different columns, delimiters, currencies,
phrasing) — but they're still hand-written regex, not a model. A truly
adversarial or extremely unstructured catalog (e.g. specs buried in
freeform paragraphs with no delimiters at all) would need either a broader
rule set or an LLM-assisted normalization pass as a fallback when the
rule-based pass finds too little structure to work with. `normalizer.py`
is structured so that swap is localized: replace the body of a
`normalize_*` function without touching the schema, the validator, or
anything downstream.

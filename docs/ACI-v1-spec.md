# ACI v1 — Agent Commerce Interface (Spec)

## Why this exists
Merchant data as it exists today (CSVs, plain-text policies, HTML listings) is written for
humans, not agents. It's inconsistent, ambiguous, and — as of this spec — untrusted, since it
can contain injected instructions aimed at the agent reading it. An agent that buys directly
against raw merchant data is buying on top of unverified, unstructured trust.

ACI v1 is the normalized, validated, security-checked record that sits between raw merchant
data and any purchasing agent. No agent should ever read raw merchant data directly — it
should only ever read an ACI record.

## Pipeline
`raw data → parser → normalizer → validator → ACI v1 record`

1. **Parser** — turns messy CSV / text / listing HTML into a rough internal structure.
2. **Normalizer** — standardizes price (amount + currency), stock (status + quantity),
   variants (type/value/available triples), and category into fixed vocabularies.
3. **Validator** — flags missing required attributes, ambiguous or conflicting policy
   language, and detects + strips prompt-injection payloads found in any free-text field.
4. **Readiness Score** — a rule-based 0–100 score, computed as 100 minus fixed point
   deductions per gap, ambiguity, or conflict found. Never model-generated, so it's always
   explainable and reproducible.

## Core guarantee
Every field in an ACI v1 record is one of:
- a normalized value with a known type and unit, **or**
- explicitly marked `null`/`unknown` with a corresponding entry in `readiness.gaps`.

There is no silent guessing. If the pipeline isn't sure, the record says so — that's the
gap list, not a hallucinated value.

## Security guarantee
`security.injection_detected` is computed by the validator scanning all free-text fields
(description, policy text) for instruction-like patterns before anything reaches an agent.
Detected payloads are stripped from `description_clean` / `policy.raw_source_excerpt` and
copied (for audit only) into `security.stripped_payloads` — that field is never passed
downstream to an agent prompt.

## What the agent is allowed to see
An agent is only ever given the ACI v1 record (JSON), never the merchant's raw source data.
This is the enforced boundary that makes the injection defense actually hold — the raw text
is quarantined at the pipeline stage, not "trusted but flagged" at the agent stage.

## Versioning
`aci_version` is a literal `"1.0"` in this build. Any schema-breaking change increments the
minor version; all ACI records include the version so downstream consumers can branch on it.

See `schema/aci-v1.schema.json` for the enforceable JSON Schema.

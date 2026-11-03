# Fresh Build — Config & Info Needed

End-to-end Ad Sales Renewal Intelligence build, from scratch, in a **new workspace**. Fill this in and I'll run `runbook.md` (steps 1→10) against it. Items marked **[blocker]** stop the build if missing; the rest have safe defaults.

---

## 1. Workspace & auth  **[blocker]**
- [ ] **Workspace URL** (`HOST`): `__________`
- [ ] **CLI profile name** for it (`PROFILE`): `__________`  — or give me a PAT to configure one non-interactively
- [ ] **Auth method**: PAT / OAuth (SSO) / service principal?
- [ ] **Cloud + region**: AWS / Azure / GCP, region `______` (affects app domains + which foundation-model endpoints exist)
- [ ] Confirm `databricks current-user me --profile <PROFILE>` succeeds

## 2. Unity Catalog target  **[blocker]**
- [ ] Can I **create a catalog** here (needs a managed-storage location / metastore rights), or should I **reuse an existing** one? → `CATALOG = __________`
- [ ] Schema name (default `ad_sales`): `__________`
- [ ] Can I create a **UC Volume** in that schema? (used for the Nielsen API-mock landing files, and for step 9 docs)

## 3. Compute  **[blocker for parts]**
- [ ] **Serverless SQL warehouse id** (`WAREHOUSE`): `__________`  — or may I create one?
- [ ] **Serverless compute for pipelines/jobs** enabled? (SDP + the ML training job run serverless)
- [ ] Note: prior build hit a serverless **UDF sandbox** limit (no pandas/Faker UDFs). Same expected here — I synthesize data natively in Spark.

## 4. Feature enablement  (tell me which are ON)
- [ ] **Databricks Apps** enabled? (Layer 4 app)
- [ ] **Lakebase / Database Instances** enabled + can I provision one? (write-back store) **[blocker for step 5/8]**
- [ ] **AI/BI dashboards + Genie** available? **Metric views** supported (recent DBR/SQL)?
- [ ] **AI/BI embedding**: can a workspace admin set `aibi-dashboard-embedding-access-policy` = ALLOW_APPROVED_DOMAINS and add `*.<apps-domain>`? (needed for the dashboard-in-app embed)
- [ ] **MLflow + UC Model Registry** + **AutoML** available? (Layer 2 — the two trained models)
- [ ] *(optional, step 9)* **Vector Search**, **Agent Bricks / Knowledge Assistant**, **Genie Ontology** (preview) access?
- [ ] Foundation-model endpoints in-region: an **LLM** for Genie and, for step 9, an **embedding** endpoint (e.g. `databricks-gte-large-en`)?

## 5. Permissions / entitlements
- [ ] Can I create: **pipelines, jobs, apps, dashboards, Genie spaces, UC models, Lakebase instances**?
- [ ] Can I **GRANT** UC privileges (the app's service principal needs `USE CATALOG/SCHEMA` + `SELECT`)? Are you catalog owner / metastore admin, or is there someone who is?
- [ ] Can I create / manage **service principals** (the app runs as one)?

## 6. Local build machine
- [ ] Is **pypi.org reachable**, or is this the machine where it's blocked (needs the internal `pypi-proxy.dev.databricks.com` index)?
- [ ] `uv` + Python 3.12 available? `databricks` CLI version?

## 7. Data & naming
- [ ] **Company name** for app / dashboard / Genie titles (prior used "Polaris"): `__________`
- [ ] **Anchor "today"** for renewal windows (prior `2026-09-08`; use current date?): `__________`
- [ ] Data scale — keep prior (~150 advertisers / ~600 campaigns) or change? `__________`
- [ ] Real sources to connect instead of synthetic? (default: synthetic, as before)

## 8. Scope for this build
- [ ] Build **all 10 steps**, including the **two trained models** (Layer 2) — yes/no
- [ ] Include **optional step 9** (untapped knowledge — Genie Ontology / Vector Search RAG stub) — yes/no
- [ ] Time budget / deadline: `__________`

---

## Context block to fill (drop into `runbook.md`)
```
HOST      = <NEW_WORKSPACE_URL>
PROFILE   = <NEW_CLI_PROFILE>
CATALOG   = <CATALOG>
SCHEMA    = ad_sales
WAREHOUSE = <SERVERLESS_WAREHOUSE_ID>
```

## Minimum to start step 1
Workspace URL + working CLI profile + catalog (create-able or existing) + schema. With those four I can begin landing data and stand up the SDP pipeline while the rest (Lakebase, Apps, embedding settings) get confirmed.

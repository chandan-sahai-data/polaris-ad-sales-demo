# Polaris — Ad Sales Renewal Intelligence (Media & Entertainment)

**Customer problem (TV / streaming network ad sales):** upfront and scatter advertisers churn at renewal
when their campaigns under-deliver, and sellers usually find out too late. Delivery lives in the ad
server, audience delivery comes from a lagged Nielsen feed, and contracts sit in the CRM. So nobody can
answer *"which advertisers renewing this quarter are at risk, how much revenue is that, and why?"*
from one trusted number. Polaris joins the three systems and scores renewal risk with two trained models.
Sellers act on the result in one app: they see the at-risk book, ask follow-up questions in natural
language, and log the outreach.

**Headline from the deployed build:** of a $302.1M book, **22 advertisers are High risk with
$43,444,430 of revenue at risk**. 15 of them are High risk **and** renew this quarter (the "act today" cohort).
The hero account, Meridian Retail (062), has $3.59M at risk, 2 of 2 campaigns behind plan, and renews in 34 days.

## End-to-end journey

| Stage | What was built | Code |
|---|---|---|
| **Lakeflow** – ingest | Synthetic raw feeds from 3 source systems (ad server, CRM, lagged Nielsen) → Lakeflow Spark Declarative Pipeline: bronze (streaming) → silver (12 data-quality expectations) → gold unified campaign/advertiser tables | `build/generate_landing_data.py`, `build/dabs/` (bundle + `src/*.py`) |
| **Unity Catalog** – govern | All assets in `cs_genie_research_catalog.ad_sales`; two **metric views** define every KPI once (CPM, delivery vs commitment, sellout, reach efficiency, revenue at risk); app service principal granted least-privilege; lineage captured automatically | `build/dabs/ddl/*.sql`, `build/deploy_mv.py` |
| **ML** – intelligence | Model A delivery-shortfall classifier (AUC 0.938) and Model B renewal-risk model (AUC 0.675, v1 on limited history), both tracked in MLflow and registered in UC. Their outputs are blended into an explainable composite score with human-readable drivers | `build/train_models.py` |
| **GenAI** | Deal Memory: 15 contract/recap/QBR docs in a UC Volume + `databricks-bge-large-en` embeddings, with cited semantic retrieval in the app | `build/build_deal_memory.py` |
| **Lakebase** – operational serving | Autoscaling Postgres project `renewal-actions`; risk scores synced from Delta continuously; sellers' "contacted / snoozed" actions written transactionally to `seller_actions` | app `build/app/app.py` |
| **Genie Agent** – natural language | Space grounded on the metric views + risk table, with glossary, example SQL and formatting rules; answers the demo's renewal questions | `build/build_genie.py` |
| AI/BI dashboards | Renewal & Risk (priority grid, risk analytics, model health, delivery risk) + Ad Sales explorers, both linked to the Genie space | `build/rebuild_dashboards_from_ref.py`, `reference/` |
| **Databricks App** – surface it | FastAPI app `ad-sales-renewal-cockpit`: embedded dashboards, multi-turn Genie panel, Deal Memory search, and an escalation grid with Lakebase write-back | `build/app/` |

## Lakeflow pipeline source (ingest → gold)

The deployed Lakeflow Spark Declarative Pipeline runs exactly these files. Each was exported from the workspace and hash-matched to the repo copy in [`evidence/01b_lakeflow_pipeline_source.md`](evidence/01b_lakeflow_pipeline_source.md), which also inlines the full code.

| Layer | File | What it does |
|---|---|---|
| Bronze | [`build/dabs/src/bronze.py`](build/dabs/src/bronze.py) | 4 streaming tables (`@dp.table`, `spark.readStream`) ingesting the raw ad-server, CRM accounts, CRM deals and Nielsen tables, keeping `source_system` and `last_refresh` and stamping `_ingested_at` |
| Silver | [`build/dabs/src/silver.py`](build/dabs/src/silver.py) | 4 materialized views that dedup on natural keys, conform types, derive pacing/flight-elapsed/reach-delivery, and enforce 12 `@dp.expect_all_or_drop` expectations |
| Gold | [`build/dabs/src/gold.py`](build/dabs/src/gold.py) | `gold_campaign_advertiser` (ad server rolled up to campaign grain + CRM account/current deal + Nielsen) and `gold_advertiser_book` (advertiser rollup) |
| Gold risk | [`build/dabs/src/gold_risk.py`](build/dabs/src/gold_risk.py) | Rules-based v0 composite risk (superseded by the ML score in `build/train_models.py`) |
| Pipeline definition | [`build/dabs/resources/ad_sales_ingestion.pipeline.yml`](build/dabs/resources/ad_sales_ingestion.pipeline.yml) | Serverless, CURRENT channel, deployed with `databricks bundle deploy` |
| Raw data | [`build/generate_landing_data.py`](build/generate_landing_data.py) | Synthetic source systems the bronze layer reads |

## Proof it ran

**→ [`evidence/`](evidence/README.md)** contains text-only execution evidence for every stage. It covers the build
console log, pipeline event log and expectation results, UC lineage, MLflow metrics and model versions, Lakebase
reads and writes, Genie answers with their SQL and result rows, the result of every dashboard query, and live HTTP
responses from the deployed app. It was regenerated from the live workspace by `evidence/capture_evidence.py`.

Deployed resource IDs are in [`DEPLOYED.md`](DEPLOYED.md). How the AI-assisted build iterated (problem observed → change made) is in [`BUILD_JOURNAL.md`](BUILD_JOURNAL.md). The talk track is in [`RUN_OF_SHOW.md`](RUN_OF_SHOW.md).

## Reproduce

1. Set the workspace values in `build/config.py`, `build/dabs/databricks.yml` and `build/app/app.yaml`.
2. Follow [`runbook.md`](runbook.md) steps 1→10. [`BUILD_FROM_SCRATCH.md`](BUILD_FROM_SCRATCH.md) is the short version.
   The order is land data → `bundle deploy/run` → train models → metric views → Lakebase → Genie → dashboards → Deal Memory → app.
3. Regenerate the evidence: `python -I evidence/capture_evidence.py`.

All data is synthetic. Advertiser names, deals and documents are generated; no customer data is used.

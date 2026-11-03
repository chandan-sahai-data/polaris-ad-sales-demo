# Media Co. Ad Sales — Demo Build Runbook

Build prompts for the churn/renewal-risk SA demo: SDP ingestion into a governed foundation, a composite risk index, and an integrated app that embeds the dashboard, the Genie Agent, and write-back on one surface.

**Decisions baked into every prompt:** media-efficiency framing (not attributed ROI) · **two trained models — a delivery-shortfall classifier (real labels) + a renewal-risk model — in MLflow/UC, feeding an explainable composite score** (honest label caveat on renewal-risk) · write-back as the reason Lakebase is there.

**Build tooling:** the AI Dev Kit (`databricks-solutions/ai-dev-kit` skills — `databricks-core` plus the product skill named in each step), driven via the `databricks` CLI.

> **FRESH BUILD (new workspace).** Fill the context block below with the new workspace's values before running any step. The ⚡ Fast-path section records the **prior** workspace's build — its resource IDs, profile, warehouse id and verified numbers will differ here, but its **gotchas are reusable**. Gather the setup details in `BUILD-CONFIG.md` first.

> **SELF-CONTAINED FRESH-BUILD FOLDER.** Everything needed to reproduce the polished demo lives in THIS folder — no dependency on any prior demo folder:
>
> - `./reference/` — the dashboard reference. `dashboard.json` is the plain combined base the rebuild script reads; `build_split_dashboards.py` is the split helper; `GOLDEN_renewal_risk_insights.json` and `GOLDEN_ad_sales_insights.json` are the CURRENT polished, deployed dashboards (all number formatting, the Account Owner global filter, the explorer tweaks baked in) — build to MATCH these, and diff against them to confirm parity.
> - `./build/` — the proven build scripts to adapt (NOT run blind): `config.py` (fill the 4 workspace values first), `generate_landing_data.py`, `dabs/` (SDP pipeline + `ddl/` = every metric view + compatibility view as committed SQL, incl. the money/CPM/reach `format` blocks and the `account_owner` columns), `deploy_mv.py`, `train_models.py`, `build_genie.py`, `build_deal_memory.py`, `rebuild_dashboards_from_ref.py` (REF already points at `../reference/dashboard.json`), and `app/`. Every workspace-specific id in the entrypoint files (`config.py`, `rebuild_dashboards_from_ref.py`, `build_genie.py`, `app/app.yaml`) is a `<PLACEHOLDER>` — fill each as the step that creates the resource completes. **The** `dabs/ddl/*.sql` **files still hard-code** `cs_rbac_demo_catalog.ad_sales` (kept so they're valid, readable SQL) — re-point them to the new catalog before deploying, e.g. `sed -i '' 's/cs_rbac_demo_catalog/<CATALOG>/g' build/dabs/ddl/*.sql` (schema stays `ad_sales`).
> The dashboard step therefore = recreate the `ddl/` views + metric views in the new catalog, then run `rebuild_dashboards_from_ref.py` (after pasting the freshly-created dashboard ids) and confirm the output matches `GOLDEN_*.json`.



## Build principles — NON-NEGOTIABLE (apply to every step)

1. **Metric views are the single source of truth for every KPI — always.** Define each metric (CPM, sellout, delivery-vs-commitment, pacing, reach efficiency, risk scores, revenue-at-risk) ONCE in a Unity Catalog metric view, and make the dashboard, Genie, and any downstream reads compute it via `MEASURE()` on that metric view — never re-derive the formula inline in a dashboard widget, a Genie example SQL, or app code. There are two metric views: `mv_campaign_metrics` (campaign grain — delivery/CPM/sellout/reach) and `mv_advertiser_renewal` (advertiser grain — revenue-at-risk + component risk scores). If a dashboard/Genie needs a column a metric view doesn't expose, add it to the metric view (or a thin governed view beneath it), don't bypass it. This is the "whose number is right" guarantee.
2. **Build the dashboards to match the reference exactly.** Reuse the reference `./reference/dashboard.json` + `./reference/build_split_dashboards.py` (in THIS folder) VERBATIM for pages, widgets, layout and theme, and match the polished `./reference/GOLDEN_*.json` — do NOT author dashboards from scratch. Adapt only the *data bindings*: point each dataset at this build's tables, and where column names differ, create thin **compatibility views** (e.g. `gold_campaign_delivery`, `silver_accounts`, `silver_deals`, `dash_silver_nielsen`, `dash_advertiser_risk`, `dash_model_health`) that expose the exact column names the reference widgets expect. Dashboard delivery/efficiency datasets read the metric view via `MEASURE()`; risk/ML datasets read the governed views. Then split into the two dashboards (Renewal & Risk = cockpit/filters/risk_analytics/model_health/delivery_risk; Ad Sales = the silver explorers + ad_server_details) and publish. See step 7.
3. **The app's Ask Genie panel shows generated SQL COLLAPSED by default.** Render each Genie answer's SQL inside a `<details>` (a "▸ Show SQL" toggle), closed by default, so the conversation stays readable; the user expands it only when they want to inspect the query. Never dump the raw SQL always-expanded. See step 8.
4. **All money renders as whole-dollar USD with a** `$` **and thousand separators — everywhere; CPM is the one exception at 2 decimals.** Monetary TOTALS (revenue-at-risk, contract value, booked spend) show as e.g. `$45,600,000` — `$` sign, thousand separators, rounded to whole dollars, NO cents, NO compact `M`/`K` abbreviation. **CPM (effective_cpm) shows as** `$28.50` **—** `$` **+ 2 decimal places** (whole-dollar rounding loses meaningful CPM precision). **Reach metrics (Reach Efficiency + reach delivery ratio) round to 2 decimal places** (plain `number`, not currency — the rebuild script's `_is_reach_field()` matches reach ratio/efficiency fields but NOT raw reach counts like delivered_reach/planned_reach). Enforce across all FOUR surfaces: (a) **metric views** — `format:` block on the money/CPM measures (`type: currency`, `currency_code: USD`, `hide_group_separator: false`; `decimal_places:{type: exact, places: 0}` for totals, `places: 2` **for Effective CPM**; needs version 1.1 + DBR 17.3+); (b) **dashboard** — the rebuild script's `apply_number_formats()` is widget-type aware: **summary cards (the KPI** `counter` **tiles)** get compact millions/thousands at 1 decimal `{"abbreviation":"compact","decimalPlaces":{"type":"exact","places":1}}` (e.g. `$45.6M` — the 3 money counters: revenue-at-risk, total contract value, booked spend); **every other money widget** (tables/bars/scatters) gets whole-dollar separated `{"abbreviation":"none","decimalPlaces":{"type":"exact","places":0}}` (`$45,600,000`). Both use `type:number-currency`, `currencyCode:USD`, `hideGroupSeparator:false`. Note the reference surfaces no CPM widget — CPM lives only in the metric view/Genie; (c) **Genie** — a `## NUMBER FORMATTING` text-instruction block requiring `$`+separators+whole dollars for totals, `$`+2dp for CPM, and reach efficiency to 2dp, plus example SQL returning whole dollars (`ROUND(SUM(revenue_at_risk),0)`, never `/1e6` millions), CPM `ROUND(MEASURE(\`Effective CPM),2)`, and reach` ROUND(MEASURE(Reach Efficiency),2)`; (d) **app Escalation grid** — the money helper is` v=>'$'+Math.round(Number(v)).toLocaleString('en-US')`(whole-dollar + separators), NOT the old`/1e6 + 'M'` compact form. See steps 3, 6/8, 7, 8.

---



## Progress tracker

Tick each step as you build it. Spine steps are the critical path; **6 & 7** run in parallel after 3; **9** is optional.

- [x] **1** · Landing data — three source systems  ·  150 adv / 765 line items / 600 Nielsen
- [x] **2** · SDP ingestion pipeline → unified Gold  ·  bronze×4→silver×4→gold, clean lineage
- [x] **3** · Governed metric views  ·  mv_campaign_metrics + mv_advertiser_renewal
- [x] **4** · Predictive ML — delivery-shortfall (AUC 0.938) + renewal-risk (AUC 0.694) → advertiser_risk_scores (24 High / $47.0M)
- [x] **5** · Lakebase — synced advertiser_risk_scores + seller_actions write-back (verified)
- [x] **6** · Genie Agent over structured data + metric views  ·  space 01f1b0511442113c95ef1b1746f1b52b, 3/3 benchmarks pass
- [x] **7** · AI/BI dashboard — RR 01f1b051416a1a78874ce24fc48db91b + AS 01f1b05141b118a6afb8a833f2143aeb (match GOLDEN)
- [x] **8** · The App — ad-sales-renewal-cockpit (all 5 endpoints verified)
- [x] **9** · Untapped knowledge — Deal Memory: deal_docs (15) + bge embeddings + in-app cosine (cited)
- [x] **10** · Dress rehearsal / verification  ·  one-number proof holds, models registered, write-back persists

---



## Context block — edit `HOST` + `CATALOG`, paste above every prompt

Set these once per iteration. Every prompt refers to `HOST`, `CATALOG`, and `SCHEMA` by name, so changing them here re-points the whole build.

```
CONTEXT — edit HOST + CATALOG per iteration, then paste this above every prompt.

  HOST      = https://fe-sandbox-cs-sa-ad-sales-demo.cloud.databricks.com         # e.g. https://dbc-xxxx.cloud.databricks.com/
  PROFILE   = fe-vm-cs-sa-ad-sales-demo           # verify: databricks current-user me --profile <NEW_CLI_PROFILE>
  CATALOG   = cs_sa_ad_sales_demo_catalog                   # existing catalog you can write to, or one you will create
  SCHEMA    = ad_sales
  WAREHOUSE = f06e9709a68d6b71   # a serverless SQL warehouse in the new workspace

BUILD TOOLING:
  Use the AI Dev Kit (databricks-solutions/ai-dev-kit skills: databricks-core +
  the product skill named in each step) to generate notebooks, SDP pipelines, SQL,
  metric views, dashboards and app code — driven through the databricks CLI against
  HOST / PROFILE. Deploy and verify everything with the CLI.
  Everything targets CATALOG.SCHEMA in the workspace at HOST.
```

---



## ⚡ Fast-path — proven end-to-end build (read this first)

This section is the record of a **completed** end-to-end build in the **prior** workspace — resource IDs, the `ad-sales-demo` profile, the warehouse id and the verified numbers below are from that build and **will differ** in this fresh workspace; the **gotchas are workspace-agnostic**, read them first. The step prompts below still frame the story, but the **actual artifact names, order, and commands here are what works** — follow these to rebuild fast, and treat any name in the prompts (e.g. `gold_campaign_advertiser`, `advertiser_risk_scores`, `seller_actions`, `sellout_pct`) as illustrative; the actuals below supersede them.

### Tooling reality

The whole build runs on the **AI Dev Kit** (`databricks-`* skills) driven via the `databricks` CLI + local Python.

### Connection & local env (once)

```bash
# Auth (PAT). If the profile is missing/expired, non-interactive:
#   printf 'dapiXXXX\n' | databricks configure --token --host $HOST --profile ad-sales-demo
databricks current-user me --profile ad-sales-demo          # verify
# Local build venv — pypi.org is BLOCKED on this machine; use the internal index:
uv venv ~/sa_ad_sales_demo_v3/.venv --python 3.12
uv pip install --python .venv/bin/python --index-url https://pypi-proxy.dev.databricks.com/simple \
  "databricks-connect>=16.4,<17.4" databricks-sdk psycopg2-binary faker numpy pandas fastapi "uvicorn[standard]"
```



### Global gotchas (each cost real time — avoid up front)

- **No pandas/Faker Python UDFs on this serverless** → `ISOLATION_STARTUP_FAILURE.SANDBOX_STARTUP … exec format error`. Synthesize strings natively in Spark (arrays + `hash()` indexing), not `@pandas_udf`.
- **Metric-view DDL:** deploy the `CREATE VIEW … WITH METRICS … LANGUAGE YAML` via the **SDK statement-execution** (`w.statement_execution.execute_statement`), **not** `aitools tools query` — passing YAML as a CLI arg mangles its indentation.
- **The App must be FastAPI + a top-level HTML** `<iframe>`**, NOT Streamlit.** Streamlit renders iframes through a sandboxed component layer that breaks the AI/BI embed's parent-frame auth handshake ("The dashboard must be embedded in an iframe" / blank).
- **AI/BI dashboard: fresh** `lakeview create`**, do NOT iterate with repeated** `lakeview update`**.** Repeated in-place updates leave a **stale dataset schema** — queries FINISH (check `system.query.history`) yet the editor shows no fields and widgets render blank. Also: build widgets with **inline** `SUM`**/**`COUNT`**/**`AVG` **on real columns** + derived `CASE 0/1` flag columns in the dataset SELECT — **avoid** the `asset_name` metric-view shorthand and dashboard `columns[]`+`MEASURE()` (both rendered blank here). Published URL path is `/dashboardsv3/<id>/published?o=<workspace_id>` (the `/sql/dashboardsv3/…` path 404s).
- **Grant the App's service principal UC** `SELECT` on `CATALOG.SCHEMA` — attaching the warehouse/Genie resources does NOT grant table access: `GRANT USE CATALOG/USE SCHEMA/SELECT ON SCHEMA … TO \``.
- **Lakebase for app write-back = PROVISIONED instance** (`databricks database …`), attached as an app `database` resource → injects `PGHOST/PGUSER/PGDATABASE/PGPORT`. **App auth is a short-lived OAuth token, NOT a static** `PGPASSWORD` — the env has no password (`fe_sendauth: no password supplied` if you read `PGPASSWORD`), so mint one at runtime and use it as the psycopg2 password. The runtime's pre-installed `databricks-sdk` may lack `w.database` (`'WorkspaceClient' object has no attribute 'database'`), so call the REST endpoint and **pin** `databricks-sdk>=0.130.0`: `tok = w.api_client.do("POST","/api/2.0/database/credentials", body={"instance_names":["renewal-actions-db"],"request_id":"<uuid>"})["token"]` (cache ~50 min). Same call as CLI for local table setup: `databricks database generate-database-credential --json '{"instance_names":["renewal-actions-db"],"request_id":"<uuid>"}'`.
- **Genie Conversation API JSON:** parse with `json.loads(..., strict=False)` — generated SQL strings contain raw newlines.
- **Genie multi-turn:** thread follow-ups by reusing `conversation_id` — first question `POST …/start-conversation`, follow-ups `POST …/conversations/{id}/messages`; the app keeps the id so context carries across turns (matches the Genie UI). Response field is `message_id` on start, `id` on follow-ups — handle both.
- **Genie text instructions:** `text_instructions[0].content` must be **one** `\n`**-delimited string** — appending separate list items concatenates into run-on text. Edit by pulling live `serialized_space` (`get-space --include-serialized-space`), change only text_instructions, `update-space`. Formatting rules baked in: revenue in USD whole-dollar (no cents); risk scores to 1 decimal.
- **AI/BI inline embed** needs the app domain in workspace embedding settings (`aibi-dashboard-embedding-access-policy` = ALLOW_APPROVED_DOMAINS + approved-domains includes `*.aws.databricksapps.com`) **and** third-party cookies for `*.cloud.databricks.com`.
- **Embedded-Genie appearance coupling:** the dashboard embed + its "Ask Genie" panel share ONE appearance mode; the Genie panel's chrome follows the viewer's **workspace Appearance (Light/Dark)**, not the dashboard theme tokens. So you CANNOT have dashboard-dark + Genie-light in one embed. Decision here: dashboard forced always-dark (theme `light==dark`) + **viewer sets Appearance = Dark** → both legible. In a light-mode browser the embedded Genie input goes dark-on-dark (invisible); the app's own always-dark "Ask Genie" tab is the readable fallback.
- **ML training (Step 4,** `train_models.py`**):** local Databricks Connect + `mlflow.set_tracking_uri("databricks")` + `set_registry_uri("databricks-uc")`; needs `mlflow`+`scikit-learn` in the venv. Model A (delivery-shortfall) trains at **line-item grain** for real signal (campaign-grain aggregation kills it → AUC ~0.57); to give it signal, `generate_landing_data.py` makes under-delivery **driver-dependent** (scatter/off-peak/CTV) — regenerate + pipeline **full-refresh** after. Composite writes `advertiser_risk_scores`; **repoint the metric view source AND app** `RISK_TABLE` **to it**.
- **Metric-view** `.sql` **must live OUTSIDE the SDP pipeline** `libraries` **glob** — keep it in `ddl/` (glob `../src/*.py`), else the pipeline update FAILS with "CREATE OR REPLACE VIEW … not supported in a DLT pipeline".
- **Metric-views-first, always (Build principle #1):** every KPI (delivery/CPM/sellout/reach + revenue-at-risk + component risk scores) is defined once in `mv_campaign_metrics` (campaign grain) or `mv_advertiser_renewal` (advertiser grain), and dashboard + Genie both read via `MEASURE()`. Never re-derive a formula inline in a widget or Genie example SQL. Need a missing column? add it to the metric view (or a thin governed view beneath it).
- **Dashboards = reference, faithfully (Build principle #2):** reuse `./reference/dashboard.json` + `./reference/build_split_dashboards.py` pages/widgets/layout/theme verbatim and match `./reference/GOLDEN_*.json`; adapt only data bindings via thin compatibility views (`gold_campaign_delivery`, `silver_accounts`, `silver_deals`, `dash_silver_nielsen`, `dash_advertiser_risk`, `dash_model_health`) that expose the exact reference column names, then split into the two dashboards and publish. Don't author from scratch. `stack()` in the risk-decomposition dataset needs all value columns cast to the SAME type (DOUBLE) or it errors `STACK_COLUMN_DIFF_TYPES`.
- **App Ask-Genie SQL collapsed by default (Build principle #3):** render each answer's generated SQL inside a closed `<details>` ("▸ Show SQL"), never always-expanded.
- **Vector Search in this FEVM:** the managed VS index would NOT provision (STANDARD endpoint reports ONLINE but index stuck `"pending endpoint provisioning"`; `CONTINUOUS` = "not supported for this workspace"). For a small corpus, **skip the managed index** — embed docs with `databricks-gte-large-en` (`w.serving_endpoints.query(name=…, input=[…])`) + in-app cosine. Managed VS index + Knowledge Assistant is the documented **scale-out**.



### Artifact inventory (deployed & verified)


| Layer                | Artifact                                                                                                                                                                                                                        | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 data               | `generate_landing_data.py` → `crm_accounts_raw`(150), `crm_deals_raw`(203), `ad_server_lineitems_raw`(771), `nielsen_measurement_raw`(600)                                                                                      | native Spark synth; all join on advertiser_id/campaign_id; source_system+last_refresh on every row                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2 pipeline           | DABs SDP (`databricks.yml` + `resources/ad_sales_ingestion.pipeline.yml` + `src/{bronze,silver,gold,gold_risk}.py`), modern `from pyspark import pipelines as dp`                                                               | bronze×4, silver×4 (expectations), gold `gold_campaign_delivery`(600) + `gold_advertiser_book`(150)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| API mock             | `mock_nielsen_api.py`                                                                                                                                                                                                           | real HTTP round-trip → NDJSON to Volume `/Volumes/…/landing/nielsen_api/` via Files API → Auto Loader bronze                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| risk index           | `gold_advertiser_renewal_risk`(150) in the pipeline (`src/gold_risk.py`)                                                                                                                                                        | rules-based composite = 0.40·delivery + 0.25·audience + 0.35·urgency; tiers High≥52 / Med≥40 (calibrated to distribution); `revenue_at_risk`, `recommended_action`. **→ step 4 now adds two TRAINED models (delivery-shortfall classifier + renewal-risk) in MLflow/UC that feed this score; the rules-only version was v0.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| metric view          | `mv_advertiser_renewal` (advertiser grain) — `src/mv_advertiser_renewal.metric_view.sql`, deploy `deploy_mv.py`                                                                                                                 | governs KPIs; used by Genie + dashboard + app                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Genie                | space `01f1abd855e81394a591e9abb6ddb80c` "Ad Sales Renewal Intelligence"; `build_genie.py` (+ `update_genie_instructions.py`)                                                                                                   | 2 sources: mv_advertiser_renewal + gold_campaign_delivery; MEASURE example SQLs; text-instruction caveats + formatting rules (USD whole-dollar, scores 1-dp); multi-turn via conversation_id                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Lakebase             | provisioned instance `renewal-actions-db`, table `public.advertiser_actions` (status / **note** / snooze_until / **next_connect_date** / updated_by); `setup_lakebase_table.py` (idempotent `ALTER … ADD COLUMN IF NOT EXISTS`) | write-back; GRANT ALL to PUBLIC; app auth via runtime OAuth token (see gotcha)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| deal memory (L3+)    | `build_deal_docs.py` → `deal_docs` (15 mock recap/contract/QBR docs keyed to real advertiser_ids); app **Deal Memory** tab                                                                                                      | **Managed Vector Search index would NOT provision in FEVM** (STANDARD endpoint ONLINE but index stuck "pending endpoint provisioning"; CONTINUOUS unsupported) → working impl = `databricks-gte-large-en` **embeddings + in-app cosine** over 15 docs (`POST /api/deal_memory`). Managed VS index + Knowledge Assistant = the documented scale-out                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ml models (Step 4)   | `train_models.py` → UC models `delivery_shortfall_model` (line-item, AUC~0.69) + `renewal_risk_model` (advertiser, AUC~0.86), MLflow-tracked                                                                                    | composite → `advertiser_risk_scores` ($57.4M/23 High); `ml_campaign_shortfall_scores`, `ml_model_monitoring`; mv + app repointed to advertiser_risk_scores                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| deal memory (Step 9) | `build_deal_docs.py` → `deal_docs` (15 recap/contract/QBR docs keyed to real advertiser_ids)                                                                                                                                    | `databricks-gte-large-en` **embeddings + in-app cosine** (managed VS index won't provision in FEVM — see gotcha); app tab + `POST /api/deal_memory`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| app (L4)             | Databricks App `ad-sales-renewal-cockpit` (**FastAPI**, `app/app.py`+`app/index.html`), DABs `resources/renewal_cockpit.app.yml`                                                                                                | header **"Ad Sales Intelligence Cockpit"**; **5 tabs**: **Ad Sales Insights** (embeds AS dashboard) / **Renewal & Risk Insights** (embeds RR dashboard) / **Ask Genie** (multi-turn) / **Deal Memory** (semantic search) / **Escalation & Actions** (last). Env `DASHBOARD_ID_AS`/`DASHBOARD_ID_RR`. Escalation filters Tier→Renewal→**Advertiser dropdown** + per-row **contact notes** + **next-connect date** → Lakebase. Endpoints `/api/escalation,/action,/genie,/advertisers,/deal_memory`. POLARIS dark theme                                                                                                                                                                                                                                                                                                  |
| dashboard            | AI/BI `01f1abe603c91ff7a62a63033e00d32e` (published); `dashboard.json` = **source of truth, re-pull via** `lakeview get` (user edits it in the UI — never overwrite from a hand-built file)                                     | cockpit + filters + 3 silver exploration (accounts/deals/nielsen) + ad_server_details + **3 ML pages** (`build_ml_pages.py`): risk_analytics (churn×revenue quadrant + score decomposition + drivers table), model_health (AUC counters + predicted-vs-actual), delivery_risk (p_shortfall histogram/scatter/table). **SPLIT (**`build_split_dashboards.py`**) into TWO dashboards the app embeds: Ad Sales Insights** `01f1ada9db0f19d58d988598cb80c588` **(silver + ad_server_details) + Renewal & Risk Insights** `01f1ada9dc111fbe8984aec0f8cd02a3` **(cockpit+filters+risk_analytics+delivery_risk+model_health); original combined** `01f1abe6…` **kept as backup.** theme **always-dark** (light==dark), Inter — **viewer sets Databricks Appearance=Dark** so the embedded Genie panel is legible (see gotcha) |




### Verified numbers (sanity targets)

Revenue at Risk **$57.3M** · Book **$153.7M** · High-risk **22** (14.7%) · Renewing this quarter **58** · Act-today (High + this-quarter) **18** · Book delivered **94.6%**. Hero at-risk account: **Meridian Restaurants — $2.2M, renews in 10 days, 2/3 campaigns behind.**

### Working build order

`1 land → 2 pipeline (bronze/silver/gold) → risk gold → metric view → Genie → AI/BI dashboard → app`. The metric view sits **on** the risk gold, so it comes after step 4; Genie/dashboard/app all read the metric view.

---



## Build order

**Spine (run in order):** `1 → 2 → 3 → 4 → 5 → 8 → 10` — Land → SDP ingest → metrics → risk → Lakebase → app → rehearsal. The SDP pipeline (2) consumes the landing data (1); the app (8) reads the Lakebase synced table (5).

- **6 & 7** — the Genie Agent and the AI/BI dashboard are independent; run them in parallel any time after step 3.
- **8** — the integrated app embeds the dashboard (7), the Genie Agent (6), and Lakebase write-back (5), so it comes after all three.
- **9** — optional untapped-knowledge: Genie Ontology (demo scale) / Vector Search + Knowledge Assistant RAG stub (production scale), only with spare time.

---



## 1. Landing data — three source systems

**Foundation · AI Dev Kit › data-gen (databricks-synthetic-data-gen)**

*Bakes in:* shared join keys · upfront/scatter modeled · `source_system` + `last_refresh` on every row · Nielsen as a lagged feed · lands as `_raw` tables the SDP pipeline ingests next.

```
Build with the AI Dev Kit (databricks-core +
databricks-synthetic-data-gen). Target the workspace at HOST / PROFILE; write everything
to CATALOG.SCHEMA from the context block.

Generate THREE source-shaped LANDING datasets that mimic three real systems and become
the raw input to the SDP ingestion pipeline in step 2. All joinable on advertiser_id and
campaign_id. Land them as raw tables (or files in a landing volume) with a _raw suffix:

1. ad_server_lineitems_raw  (mimics a Postgres GAM/FreeWheel ad server)
   campaign_id, advertiser_id, order_id, network, daypart
   (Morning/Daytime/Primetime/LateNight), sales_type ('upfront'|'scatter'),
   flight_start, flight_end, booked_impressions, delivered_impressions,
   booked_spend, cpm_booked, inventory_units_booked, inventory_units_available.
   Most pacing near 1.0, a meaningful minority behind (0.7-0.9) so risk signals exist.

2. crm_accounts_raw + crm_deals_raw  (mimics Salesforce)
   accounts: advertiser_id, advertiser_name, category
   (Auto/QSR/CPG/Retail/Telco/Pharma), region, account_owner.
   deals: deal_id, advertiser_id, stage, contract_value, deal_start, deal_end,
   renewal_date, upfront_commit_flag, and a renewal_window bucket
   ('renews_this_quarter'|'renews_next_quarter'|'already_in_scatter'),
   anchored to today = 2026-09-08.

3. nielsen_measurement_raw  (mimics a LAGGED Nielsen feed — set last_refresh 3-7 days stale)
   campaign_id, advertiser_id, target_demo, planned_reach, delivered_reach,
   gross_rating_points, target_audience_impressions, in_target_pct,
   avg_frequency, audience_quality_score.

Requirements: ~150 advertisers, ~600 campaigns across categories, regions, sales types
and renewal windows. EVERY dataset carries source_system and last_refresh columns — they
power the lineage/trust talk-track and the live-vs-batch story. Print row counts and a
5-row sample of each.
```

---



## 2. SDP ingestion pipeline → unified Gold

**Layer 1 · AI Dev Kit › SDP pipeline (databricks-pipelines)**

*Bakes in:* **Spark Declarative Pipeline is the ingestion showcase** · bronze→silver→gold with data-quality expectations and visible lineage · one governed `gold_campaign_advertiser`.

```
Build with the AI Dev Kit (databricks-core + databricks-pipelines).
Target HOST / PROFILE, CATALOG.SCHEMA.

Build a Spark Declarative Pipeline (SDP) that ingests the three _raw landing datasets and
showcases a real ingestion flow:

- BRONZE: ingest each _raw source into a bronze table, preserving source_system and
  last_refresh.
- SILVER: clean and conform each source — enforce types, dedup on natural keys, and add
  SDP EXPECTATIONS (data-quality constraints, e.g. non-null campaign_id, valid sales_type,
  delivered_impressions within a sane bound of booked) so quality is visible in the
  pipeline UI.
- GOLD: create gold_campaign_advertiser — one row per campaign joining ad-server + CRM +
  Nielsen on advertiser_id / campaign_id, with identity/category/region/sales_type/
  renewal_window, ad-server pacing/delivery/spend, CRM deal/contract fields, Nielsen
  reach/delivery fields, and per-source last_refresh columns (adserver_last_refresh,
  crm_last_refresh, nielsen_last_refresh).

Deploy the pipeline via the CLI, run it, and verify: show the pipeline graph/lineage, the
expectation results, and row counts at each layer. In the summary, note the production
ingestion path this stands in for — ad-server via CDC as a live signal, Nielsen as a
lagged batch feed.
```

---



## 3. Governed metric views

**Layer 1 · AI Dev Kit › metric views (databricks-metric-views)**

*Bakes in:* **metric views define CPM once** — dashboard, Genie, and the risk model all compute it identically · row-level access is the "whose number is right" fix.

```
Build with the AI Dev Kit (databricks-core + databricks-metric-views).
Target HOST / PROFILE, CATALOG.SCHEMA.

Metric views are the SINGLE SOURCE OF TRUTH for every KPI — always (see Build principles).
Build BOTH:

(a) mv_campaign_metrics on gold_campaign_advertiser (campaign grain), governed YAML, defined once:
  - sellout_pct            = booked units / available units
  - effective_cpm          = spend / (impressions / 1000)
  - pacing_index           = mean campaign pacing (delivered / booked; 1.0 = on pace)
  - delivery_vs_commitment = delivered_impressions / booked_impressions
  - reach_efficiency       = in-target audience impressions / spend
Dimensions: advertiser, category, region, sales_type, daypart, renewal_window, target_demo.

(b) mv_advertiser_renewal on the advertiser-grain risk source (advertiser_risk_scores or a
thin governed view over it), so the cockpit and Genie read revenue-at-risk and the component
risk scores through a metric view too:
  - Revenue at Risk, Total Contract Value (SUM)
  - Avg Renewal / Delivery / Audience / Urgency Risk Score (AVG)
Dimensions: Advertiser, Category, Region, Risk Tier, Renewal Window, Days to Renewal,
Recommended Action.

Deploy metric-view DDL via SDK statement-execution (NOT `aitools query` as a CLI arg — that
mangles the YAML indentation).

Verify each metric view returns sane numbers via a warehouse query and show me the
definitions. Note in the summary: in production these sit behind row-level access
(regional owners see their book, national sees the aggregate) — same metric definition
either way. This is the "whose number is right" fix.
```

---



## 4. Predictive ML — delivery-shortfall classifier + renewal-risk model → composite score

**Layer 2 · AI Dev Kit › ML training + MLflow (databricks-ml-training, databricks-mlflow-evaluation)**

*Bakes in:* **two models TRAINED on the ingested data** — a delivery-shortfall classifier (real labels) + a renewal-risk model — tracked in MLflow, registered in UC, monitored predicted-vs-actual and retrainable · feeding an **explainable composite score** the business sees · honest caveat: renewal-risk is a v1 on limited history, the shortfall classifier has real labels today · batch inference (no online feature store).

```
Build with the AI Dev Kit (databricks-core + databricks-ml-training,
plus databricks-mlflow-evaluation for eval/monitoring). Target HOST / PROFILE, CATALOG.SCHEMA.
This is the PREDICTIVE ML layer: two models TRAINED on the ingested gold data, tracked in
MLflow, registered in Unity Catalog, and monitored/retrainable. Batch inference — do NOT
stand up an online feature store.

MODEL A — DELIVERY-SHORTFALL CLASSIFIER (campaign grain). The flagship "trained on your
data" model; it has real labels.
  - Label: under_delivered = final delivered_impressions < 0.95 * booked_impressions,
    using completed campaigns from the ingested history.
  - Features from gold/silver: pacing_index to-date, pct_flight_elapsed, daypart,
    sales_type, network, category, region, booked_impressions, cpm_booked, inventory
    tightness, in_target_pct, avg_frequency, advertiser historical delivery.
  - Model: start simple (sklearn LogisticRegression or GradientBoosting, or Databricks
    AutoML). Log params + metrics (AUC, precision/recall) to MLflow; register the version
    in the UC Model Registry. Batch-score ACTIVE campaigns → p(shortfall) into a scored
    table (surfaces as a delivery-risk flag in the dashboard drill-through + Genie).

MODEL B — RENEWAL-RISK PREDICTION MODEL (advertiser grain).
  - Label: non-renewal / churn built from historical deal outcomes in the ingested data
    (renewed vs lapsed). Be explicit in the output: label volume is limited (~2 quarters),
    so this is a v1 that strengthens as renewal outcomes accumulate — but it IS trained,
    not rules.
  - Features (advertiser grain): aggregated delivery (avg pacing, shortfall rate from
    Model A), reach/audience-delivery vs plan, make-good frequency, deal-stage stagnation,
    days-to-renewal, contract value, category, region.
  - Model: LogisticRegression / GradientBoosting / AutoML; MLflow + UC registry; batch
    output p(churn) per advertiser.

COMPOSITE RENEWAL-RISK SCORE (business-facing, explainable). Blend the two model outputs
with renewal urgency into the advertiser risk_score / risk_tier the dashboard, Genie and
app consume:
  risk_score (0-100) = f( Model B churn prob, advertiser-level Model A shortfall risk,
                          renewal urgency / days-to-renewal ) -> tier low/medium/high,
  revenue_at_risk = total_contract_value * risk_score/100,
  contributing_factors = human-readable top drivers (model feature importances + urgency)
  so the dashboard and Genie can explain WHY. Write to advertiser_risk_scores.
Calibrate tiers so the demo headline stays ~22 High / ~$57.3M at risk for continuity (or
re-derive and update the sanity numbers).

MONITORING & RETRAIN (say this to the CDO / Engineering personas): a loop compares
predicted vs actual — delivery shortfall at flight end (Model A), renewal outcomes as they
land (Model B) — logged via MLflow / Lakehouse Monitoring; retrain Model A weekly, Model B
quarterly. (A serving endpoint is an easy later add; batch scoring is enough for the demo.)

Show me: MLflow runs with metrics for BOTH models, the registered UC model versions, the
top 15 high-risk advertisers with drivers, and confirm advertiser_risk_scores feeds the
metric view / dashboard / Genie unchanged.
```

---



## 5. Lakebase — synced reads + write-back

**Layer 2/4 · AI Dev Kit › Lakebase (databricks-lakebase)**

*Bakes in:* **write-back is THE Lakebase reason** · low-latency synced read of current risk state · explicitly NOT framed as an online feature store for inference.

```
Build with the AI Dev Kit (databricks-core + databricks-lakebase).
Target HOST / PROFILE, CATALOG.SCHEMA.

1. Create (or reuse) a Lakebase Postgres instance in this workspace.

2. Create a SYNCED table from advertiser_risk_scores (plus advertiser_name, category,
   region, renewal_window, and the key pacing/delivery metrics the app grid needs) so the
   app reads current risk state with low latency.

3. Create a WRITE-BACK table seller_actions (action_id, advertiser_id, action_type
   ('contacted'|'snoozed'), note, acted_by, acted_at) — a mutable transactional table the
   app writes to directly. This is the architectural reason Lakebase (Postgres) is used
   here rather than a read-only Delta table. Add a reverse-sync back to the lakehouse so
   analytics can see seller actions.

4. Give me the connection details the Databricks App will use, and a quick psql/Data-API
   test that inserts and reads back a seller_actions row.

Frame Lakebase's role as: (a) low-latency serving of current risk state to the app, and
(b) transactional write-back of seller actions. Do NOT frame it as an online feature store
for model inference — the risk index is batch-scored.
```

---



## 6. Genie Agent over structured data + metric views

**Layer 3 · AI Dev Kit › Genie Agent (databricks-genie-agents)**

*Bakes in:* **structured metadata only** (recap docs live in the optional VS layer) · grounded on the metric views · segment query is retrieval, not "recommend" · gets embedded in the app.

```
Build with the AI Dev Kit (databricks-core + databricks-genie-agents).
Target HOST / PROFILE, CATALOG.SCHEMA.

Create a Genie Agent scoped to: gold_campaign_advertiser, advertiser_risk_scores, the
crm_* tables, and the Layer 1 metric views. Structured metadata and metrics only — NOT
recap documents or contracts (those are the optional Vector Search extension). This agent
gets embedded in the app in step 8, so capture its space/agent id for reuse.

Curate it: business glossary (CPM, sellout, pacing, delivery-vs-commitment, renewal
window, upfront vs scatter) and sample SQL for the common questions; point it at the
metric views so numbers match the dashboard and the risk model.

Verify these three benchmark questions (the demo's live queries — confirm each works, and
note whether Genie can consume the metric views directly):
  Q1 (grounding): "What's our track record with QSR campaigns in the last two quarters?"
  Q2 (money shot): "Advertiser X came up as elevated renewal risk — summarize their
      campaign performance and delivery against plan to support a renewal conversation."
  Q3 (segment, RETRIEVAL not recommendation): "Which audience segments delivered the best
      reach-efficiency for QSR advertisers last year?"
Report which are reliable; give a canned-screenshot fallback for any that are slow.
```

---



## 7. AI/BI dashboard — the priority grid

**Layer 4 · AI Dev Kit › AI/BI dashboard (databricks-aibi-dashboards)**

*Bakes in:* **high-risk × renews-this-quarter cell pops** · built on the metric views so numbers match Genie · a live-pacing-vs-batch-Nielsen freshness element · gets embedded in the app.

```
Build with the AI Dev Kit (databricks-core + databricks-aibi-dashboards).
Target HOST / PROFILE, CATALOG.SCHEMA. Test every SQL query via CLI before deploying, and
capture the dashboard id — it gets embedded in the app in step 8.

BUILD TO MATCH THE REFERENCE EXACTLY (see Build principles #2). Reuse the reference
`./reference/dashboard.json` + `./reference/build_split_dashboards.py` (in THIS folder) VERBATIM
for pages, widgets, layout and theme, and match the polished `./reference/GOLDEN_*.json` (the
proven adapter is `./build/rebuild_dashboards_from_ref.py`) — do NOT author from scratch. Adapt ONLY the data bindings:
remap each dataset's table names to this build, and where columns differ create thin
compatibility views (gold_campaign_delivery, silver_accounts, silver_deals,
dash_silver_nielsen, dash_advertiser_risk, dash_model_health) that expose the exact column
names the reference widgets expect. Delivery/efficiency datasets read the metric views via
MEASURE(); risk/ML datasets read the governed views. Test all 10 reference datasets against
the views, then split into TWO dashboards (Renewal & Risk = cockpit/filters/risk_analytics/
model_health/delivery_risk; Ad Sales = accounts/deals/nielsen explorers + ad_server_details)
and publish. Link Ask Genie on both via uiSettings.genieSpace = THIS build's space id.
GLOBAL FILTERS must bind to EVERY dataset they should affect — an AI/BI global filter only
cascades to the datasets listed in that filter widget's `queries` / `encodings.fields`. The
reference binds the filters only to ds_adv/ds_camp, so Risk Analytics (ds_ml_risk, ds_ml_decomp)
and Delivery Risk (ds_ml_campshort) go UNFILTERED unless you add those datasets' matching
columns to each filter: Advertiser→advertiser_name, Risk Tier→risk_tier, Renewal Window→
renewal_window, Category→category on ds_ml_risk (+ advertiser_name/category on ds_ml_campshort,
advertiser_name on ds_ml_decomp). The rebuild script does this in `wire_global_filters()`.
ACCOUNT OWNER global filter (RR dashboard): a 5th filter, **Account Owner** (`f_owner`, second
filter row x=0/y=2), bound to ds_adv + ds_camp and cascaded to ds_ml_risk/ds_ml_campshort/
ds_ml_decomp. account_owner already exists on advertiser_risk_scores + gold_campaign_advertiser,
so it's just exposed: add `account_owner` to the `dash_advertiser_risk` and `gold_campaign_delivery`
compat views (DDL now saved in `dabs/ddl/*.view.sql`) and an **Account Owner** dimension to
`mv_advertiser_renewal`; the rebuild script injects `account_owner` into each dataset's SELECT
(`add_account_owner_columns()` — ds_adv needs it added as the 8th positional dimension AND the
`GROUP BY 1..7`→`1..8` extended, since ds_adv reads the metric view), adds the filter widget
(`add_account_owner_filter()`), and cascades it via the `account_owner` entry in `FILTER_EXTRA`.
EXPLORER FILTER TWEAKS (`customize_pages()` in the rebuild script): Deals Explorer filters by
**Advertiser name** not advertiser_id (add advertiser_name to the `silver_deals` view via a
join to accounts, and point the filter at advertiser_name); Ad Server Details gets an
**Advertiser** page filter on ds_camp.advertiser (shrink its header to width 8 to make room).

Primary view: a grid of advertisers by risk_tier (low/med/high) crossed with
renewal_window (this quarter / next quarter / already in scatter). The cell that must
visually POP is HIGH RISK + RENEWS THIS QUARTER — the "act today" cohort (color, sort, or
a priority flag).

Drill-through: clicking an advertiser shows their pacing/delivery detail and the Nielsen
reach/delivery-efficiency trend feeding the risk score, with contributing_factors from
advertiser_risk_scores.

Build all metrics ON the Layer 1 metric views so numbers match Genie and the app. Add a
small "data freshness" element that shows ad-server pacing as near-current and Nielsen as
batch (last_refresh) — reinforces the live-vs-batch honesty beat.
```

---



## 8. The App — dashboard + Genie + write-back, one surface

**Layer 4 · AI Dev Kit › Databricks App (databricks-apps)**

*Bakes in:* **integrated view: the AI/BI dashboard AND the Genie Agent embedded in the app**, plus the built write-back toggle · one smooth click-path is the whole "one system" moment.

```
Build with the AI Dev Kit (databricks-core + databricks-apps, plus
databricks-lakebase for the write path). Target HOST / PROFILE. This app is the integrated
seller surface — build all three into ONE app:

1. The AI/BI DASHBOARD from step 7, embedded in-app (the risk x renewal priority grid +
   drill-through), reading through the metric views.
2. The GENIE AGENT from step 6, embedded as a chat/conversation panel in the same app
   (use its captured id) for ad-hoc questions and renewal-pitch drafting. Render the
   generated SQL for each answer COLLAPSED by default — inside a `<details>` ("▸ Show SQL"
   toggle, closed) — so the thread stays readable and the seller expands it only to inspect
   the query. Never show the SQL always-expanded.
   Build the app as FastAPI + a top-level HTML `<iframe>` (NOT Streamlit) so the AI/BI embed
   auth handshake works; the SQL panel is plain HTML `<details>`.
3. WRITE-BACK controls (required, not optional): on each advertiser row, "Mark as
   contacted" and "Snooze flag" write to the Lakebase seller_actions table and reflect
   immediately in the UI (re-read after write) — the concrete proof of why Lakebase sits
   under the app. Re-opening the action popup pre-fills and surfaces the last saved note +
   next-connect date for that advertiser (edit, don't retype); the save button reads "Save".
4. DEAL MEMORY tab (step 9): a lightweight semantic-search box over the deal_docs corpus —
   POST /api/deal_memory embeds the query with the embedding endpoint and does in-app cosine,
   returning CITED cards (advertiser · doc_type · source · match %). See step 9.

TAB ORDER (left to right, opens on the first): 1) Renewal & Risk Insights (RR dashboard,
default tab) · 2) Ask Genie · 3) Ad Sales Insights (AS dashboard) · 4) Deal Memory ·
5) Escalation & Actions. Lead with Renewal & Risk since that's the demo's opening story.

Wire the end-to-end click-path so it reads as one system: priority grid (dashboard) ->
click a high-risk / renews-this-quarter advertiser -> ask the embedded Genie panel to
draft their renewal pitch -> mark contacted (write-back). Deploy and give me the app URL.
```

---



## 9. Untapped knowledge — Genie Ontology + thin Vector Search RAG stub *(optional)*

**Layer 3+ · AI Dev Kit › Genie Ontology / Vector Search (databricks-vector-search + databricks-agent-bricks)**

*Bakes in:* **art of the possible, kept thin.** Demo scale → **Genie Ontology's knowledge store** answers over the docs natively (one agent, one surface, cited; public preview — position as roadmap). Buildable stub → a small **Vector Search index + Knowledge Assistant** composed with the structured Genie via a **Supervisor**, as the production scale-out. Docs keyed to real `advertiser_id`s (esp. Meridian) so answers join to the structured entities.

```
BUILT AS (this workspace): a ~15-doc corpus (recaps / contracts / QBR notes) keyed to real
advertiser_ids (weighted to the high-risk heroes — Meridian Retail (062), Ironwood, Halcyon,
Atlas…), landed as files in a UC Volume `deal_memory` + a `deal_docs` table that stores a
`databricks-bge-large-en` embedding per doc. The app's "Deal Memory" tab embeds the query and
does IN-APP COSINE over the 15 docs, returning cited cards. Managed VS index + Knowledge
Assistant is the documented scale-out but does NOT provision in this FEVM, so the lightweight
embeddings+cosine path is what ships. Verified questions return the right cited docs:
"What did we promise Meridian in their last renewal?" → Meridian Retail renewal Insertion
Order; "Which recaps flagged viewability or under-delivery concerns?" → the under-delivery/
viewability wrap reports.

OPTIONAL / art-of-the-possible — keep it THIN (~a dozen docs, one index, one assistant).
This shows the additive path, NOT a reallocation from the churn-to-delivery story. Build
with the AI Dev Kit (databricks-core + databricks-vector-search +
databricks-agent-bricks). Target HOST / PROFILE, CATALOG.SCHEMA.

FRAMING (say this, then build the stub):
- At THIS demo's document scale, Genie Ontology's knowledge store can extract + cite from
  the docs natively — one agent, one surface (public preview; position as roadmap, say
  "preview" if asked).
- The buildable stub below is the PRODUCTION scale-out: a dedicated Vector Search index +
  a Knowledge Assistant, composed with the structured Genie via a Supervisor. Build this
  to make the "structured + unstructured, side by side" story concrete.

1. CORPUS (mock, ~12-16 short docs). LLM-generate ad-sales prose tied to REAL advertiser_ids
   from the demo (weight toward the high-risk heroes — Meridian, Pioneer, etc.):
     - campaign recaps / wrap reports (prose performance summaries),
     - insertion-order / contract excerpts (committed impressions, guaranteed segments,
       make-good terms, renewal clauses),
     - advertiser correspondence / QBR notes (concerns raised, promises made).
   Land as files in a UC Volume + a metadata table
   (doc_id, advertiser_id, campaign_id, doc_type, source, effective_date) so retrieval
   JOINS back to the structured entities.

2. INDEX (thin). Parse with ai_parse_document if PDFs (else use text); chunk; embed into
   ONE Databricks Vector Search index via a foundation embedding endpoint (e.g.
   databricks-gte-large-en). Governed by Unity Catalog; permission-aware. Keep it small.

3. ASSISTANT. Stand up an Agent Bricks Knowledge Assistant over the index (low-code, returns
   CITED answers) — lowest-effort path. Fallback: a minimal retrieve-top-k + ai_query
   synthesis function if KA isn't available.

4. COMPOSE with the structured Genie. Put both behind a Multi-Agent Supervisor (Agent Bricks)
   so one question routes structured -> Genie, document -> Knowledge Assistant, and returns
   one cited answer — OR add a "Documents" tab/tool in the app that calls the KA. Reuse the
   advertiser_id link so entity-scoped questions work.

5. VERIFY with the two narrative questions (must return CITED snippets):
     - "What did we promise Meridian in their last renewal?"  -> contract/recap snippet
     - "Which recaps flagged viewability or under-delivery concerns?" -> correspondence
   Confirm the answer cites the source doc and, via the metadata join, ties to Meridian's
   structured risk row.

Governance note for the panel: docs in a UC Volume, index + assistant governed by Unity
Catalog (same lineage/access story as the structured side); permission-aware retrieval.
Boundary to state yourself: ontology/knowledge-store handles demo-scale corpora; at
enterprise document volume you put this Vector Search layer behind it.
```

---



## 10. Dress rehearsal / verification

**Rehearsal · databricks CLI**

*Bakes in:* **SDP lineage runs clean · the "one number" proof** (CPM identical across metric view, dashboard, Genie) · write-back persists · the integrated app click-path timed.

```
Do a full demo readiness pass (databricks CLI against HOST / PROFILE).
- Re-run the SDP pipeline; confirm bronze -> silver -> gold, expectations passing, and the
  lineage graph render cleanly.
- Confirm CPM/sellout/delivery numbers are IDENTICAL across the metric view, the embedded
  dashboard, and a Genie answer (the "one number" proof).
- Show the MLflow runs + registered UC model versions and the metrics (AUC / precision-
  recall) for BOTH models — the "trained, monitored, retrainable" proof for the CDO/Eng.
- Confirm write-back persists to Lakebase and reappears on re-read inside the app.
- Exercise the integrated app click-path (dashboard grid -> drill-through -> embedded
  Genie pitch -> write-back) end to end and time it.
- Confirm which of the 3 Genie benchmark queries are reliably live; capture screenshot
  fallbacks for any that aren't.
- Produce a one-page run-of-show mapped to the 4 layers and the 30-min budget, flagging L3
  as the tight spot (pre-can query 1, keep query 2 live).
```

---



## Don't skip — the two decisions that make or break the pitch

**Build it, don't describe it — the write-back toggle (step 8).** You've made write-back the reason Lakebase belongs here. If it's only described, the sharpest question is "so you didn't build your own justification?" A "mark as contacted / snooze" control → Lakebase write → immediate re-read turns the claim into proof. Highest-leverage hour in the build.

**Keep the ML honest — and batch (steps 4–5).** The two models are **batch-scored**, so they don't need low-latency online feature serving — don't claim it (it collides with the batch reality); let write-back and live app reads carry Lakebase. On trust: the **delivery-shortfall classifier has real labels today** (your credible "trained, monitored, retrainable" proof), while the **renewal-risk model is a v1 on ~2 quarters of history** that strengthens as outcomes accrue — say both plainly rather than overselling the renewal model's accuracy.

---

*30-minute demo block · 2 min framing · 5 · 8 · 8 · 5 · 2 min close · AI Dev Kit (databricks-* skills) via the CLI · L3 is the tight spot — pre-can query 1, keep query 2 live.*
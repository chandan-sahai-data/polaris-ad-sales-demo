# Ad Sales Renewal Intelligence — Fresh Build

Self-contained folder to rebuild the demo end-to-end in a **new** workspace. Everything the
build needs is here — no dependency on any prior demo folder.

- **`runbook.md`** — the driver. Build principles (NON-NEGOTIABLE), step-by-step prompts 1→10, and the ⚡ Fast-path gotchas. Read this first.
- **`reference/`** — the dashboard reference:
  - `dashboard.json` — plain combined base the rebuild script reads
  - `build_split_dashboards.py` — split helper
  - `GOLDEN_renewal_risk_insights.json` / `GOLDEN_ad_sales_insights.json` — the **current polished, deployed dashboards** (number formatting, Account Owner global filter, explorer tweaks all baked in). Build to MATCH these; diff against them to confirm parity.
- **`build/`** — proven scripts to adapt (not run blind). Every workspace-specific id in the entrypoint files (`config.py`, `rebuild_dashboards_from_ref.py`, `build_genie.py`, `app/app.yaml`) is a `<PLACEHOLDER>`; fill each as the step that creates the resource completes. `dabs/ddl/*.sql` hard-code `cs_rbac_demo_catalog` — re-point them (see below).

---

## 1. Fill in the workspace context

The only things that vary between builds:

```
HOST      = https://<your-workspace>.cloud.databricks.com
PROFILE   = <your-cli-profile>       # must already exist: databricks auth profiles
CATALOG   = <writable-catalog>       # a UC catalog you can create tables in
SCHEMA    = ad_sales
WAREHOUSE = <serverless-sql-warehouse-id>
```

Then set them in `build/config.py` (the 4 `<...>` values) and re-point the DDL catalog:

```bash
sed -i '' 's/cs_rbac_demo_catalog/<CATALOG>/g' build/dabs/ddl/*.sql   # schema stays ad_sales
```

Fill the remaining `<PLACEHOLDER>`s (dashboard ids, Genie space id, workspace id, Lakebase
endpoint) in `build/build_genie.py`, `build/rebuild_dashboards_from_ref.py`, and
`build/app/app.yaml` as each resource is created.

## 2. Kickoff prompt (paste into a fresh Claude Code session started in this folder)

> Read `./runbook.md` and build the Ad Sales Renewal Intelligence demo end-to-end in the
> workspace context above. Use `./reference/` as the dashboard reference — reuse
> `dashboard.json` + the proven `build/rebuild_dashboards_from_ref.py` and make the two
> dashboards MATCH `reference/GOLDEN_*.json` exactly. Fill the `<PLACEHOLDER>`s in
> `build/config.py`, `build/app/app.yaml`, `build/build_genie.py`, and
> `build/rebuild_dashboards_from_ref.py` as each resource is created, and re-point the catalog
> in `build/dabs/ddl/*.sql`. Follow build order 1→2→3→4→5→6→7→8→(9)→10 and the
> NON-NEGOTIABLE build principles (metric-views-first; dashboards from reference; Ask-Genie
> SQL collapsed; money whole-dollar with `$`+separators, summary-card counters compact 1dp,
> CPM 2dp, reach 2dp; Account Owner global filter on Renewal & Risk).

## 3. Prerequisites to confirm up front

- Databricks CLI authenticated for `PROFILE` — `databricks current-user me --profile <PROFILE>`.
- `CATALOG` exists **with working managed storage** — verify a write succeeds EARLY. (The prior build lost hours to a torn-down S3 bucket + UC IAM role; see Fast-path gotcha #1.)
- Serverless SQL warehouse on the **current channel (DBR 17.3+)** — required for the metric-view `format:` blocks (money/CPM/reach formatting).
- Foundation-model endpoints available: `databricks-bge-large-en` (embeddings) + a Claude endpoint.
- Never auto-select a profile — always pass `--profile <PROFILE>`.

## Build order

`1 land → 2 SDP pipeline → 3 metric views → 4 ML models → 5 Lakebase → 6 Genie → 7 dashboards → 8 app → (9 Deal Memory) → 10 rehearsal.`
6 & 7 can run in parallel after 3/4. The app (8) embeds 5, 6, and 7.

## Tab order (app)

Renewal & Risk Insights (default) · Ask Genie · Ad Sales Insights · Deal Memory · Escalation & Actions.

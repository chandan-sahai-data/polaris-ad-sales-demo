# Deployed — fevm-cs-genie-research (2026-10-14)

Copy of `~/sa_ad_sales_demo` rebuilt into a new workspace (original folder untouched).

| Item | Value |
|---|---|
| Workspace / profile | https://fevm-cs-genie-research.cloud.databricks.com · `fe-vm-cs-genie-research` · workspace_id 7474655804120295 (FEVM expires 2026-10-20) |
| Catalog.schema / warehouse | `cs_genie_research_catalog.ad_sales` · `69a77ede4fa03b41` (Serverless Starter, CURRENT) |
| SDP pipeline | bundle `build/dabs` → "Ad Sales Ingestion (cs_genie_research_catalog.ad_sales)" |
| Models (UC) | `delivery_shortfall_model` v1 AUC 0.938 · `renewal_risk_model` v1 AUC 0.675 (144 labels) |
| Metric views | `mv_campaign_metrics`, `mv_advertiser_renewal` (+ compat views from `dabs/ddl/`) |
| Lakebase | project `renewal-actions`, endpoint `projects/renewal-actions/branches/production/endpoints/primary`; CONTINUOUS synced table `cs_genie_research_catalog.ad_sales.lb_advertiser_risk_scores` → Postgres `ad_sales.lb_advertiser_risk_scores`; write-back `public.seller_actions` |
| Genie space | `01f1c80529421edaa5212423f9c65124` (Polaris — Ad Sales Renewal Intelligence) |
| Dashboards | Renewal & Risk `01f1c805646d10c7bc4b13e6270abd37` · Ad Sales `01f1c805651b10ad9a2ffccdcc8219f0` (datasets identical to GOLDEN) |
| App | `ad-sales-renewal-cockpit` → https://ad-sales-renewal-cockpit-7474655804120295.aws.databricksapps.com (SP 808e81c3-521d-486f-8e2e-d53d71dc9183) |
| Deal Memory | `deal_docs` (15) + Volume `deal_memory`, bge-large-en embeddings |

## Verified numbers (anchor today = 2026-10-14)
High = 22 advertisers, revenue-at-risk **$43,444,430** (identical across metric view, base table, Lakebase/app) · book $302,071,436 · act-today (High + this quarter) 15 · CPM $31.03 · delivery 0.853 · sellout 0.674.
Hero: **Meridian Retail (062)** — High 91.7, $3,586,879 at risk, 2/2 campaigns behind, renews in 34d.
Genie (via app): Q1 QSR via MV ✓ · Q2 Meridian Restaurants per-campaign 0.82 ✓ (~26s) · Q3 A25-54 296.37 ✓.

## Differences vs prior build
- No CREATE CATALOG on this metastore → Lakebase UC catalog can't be registered; synced table lives in the standard catalog instead, so the app reads `RISK_TABLE=ad_sales.lb_advertiser_risk_scores` (new env var, default `public.advertiser_risk_scores`).
- `public` schema is `pg_database_owner`-owned → app SP can't create `seller_actions`; created by project owner + `GRANT ALL` to the SP.
- Reference dashboard datasets pin `catalog: ad_sales_demo`; `rebuild_dashboards_from_ref.py` now overrides catalog/schema per dataset and CREATEs fresh when RR_ID/AS_ID are empty.

## Open
- AI/BI embedding approved domains is EMPTY → embedded dashboards in the app tabs won't render until a workspace admin adds `*.aws.databricksapps.com`:
  `databricks settings aibi-dashboard-embedding-approved-domains update --json '{"allow_missing":true,"field_mask":"aibi_dashboard_embedding_approved_domains.approved_domains","setting":{"etag":"<etag from get>","aibi_dashboard_embedding_approved_domains":{"approved_domains":["*.aws.databricksapps.com"]}}}' -p fe-vm-cs-genie-research`
- Reverse-sync of `seller_actions` to the lakehouse not set up.
- Test write-back rows exist in `seller_actions` (build verification + evidence capture).

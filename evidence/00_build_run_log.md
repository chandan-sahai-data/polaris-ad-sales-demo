# Build run log — console output from the original build (2026-10-14)

Console output (verbatim apart from trimmed Spark/protobuf warnings) from building this repo into
workspace `https://fevm-cs-genie-research.cloud.databricks.com`, catalog `cs_genie_research_catalog.ad_sales`.
The live-state evidence captured afterwards is in `01_…` to `09_…` in this folder.

## Step 1 — `python build/generate_landing_data.py` (Databricks Connect, serverless)

```text
=== ROW COUNTS ===
crm_accounts_raw             150
crm_deals_raw                300
ad_server_lineitems_raw      765
nielsen_measurement_raw      600

=== deals: current vs historical, churn balance ===
+-------------+---+-------+
|is_historical|  n|renewed|
+-------------+---+-------+
|        false|150|      0|
|         true|150|     84|
+-------------+---+-------+

=== ad_server pacing distribution ===
+----+---+
|pace|n  |
+----+---+
|0.5 |2  |
|0.6 |26 |
|0.7 |114|
|0.8 |228|
|0.9 |247|
|1.0 |126|
|1.1 |22 |
+----+---+

=== hero (Meridian) ===
+--------------------+--------------+------------+-------------------+---+------+
|advertiser_name     |contract_value|renewal_date|renewal_window     |li |behind|
+--------------------+--------------+------------+-------------------+---+------+
|Meridian Restaurants|2200000.0     |2026-10-24  |renews_this_quarter|6  |6     |
+--------------------+--------------+------------+-------------------+---+------+
```

## Step 2 — `databricks bundle deploy && databricks bundle run ad_sales_ingestion` (in `build/dabs/`)

```text
Uploading bundle files to /Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files...
Created pipelines.ad_sales_ingestion
Files: 14 uploaded, 0 deleted
Resources: 1 created, 0 changed, 0 deleted, 0 unchanged
...
2026-10-14T19:21:14.600Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.silver_crm_accounts' has COMPLETED."
2026-10-14T19:21:14.605Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_campaign_advertiser' is PLANNING."
2026-10-14T19:21:15.130Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_campaign_advertiser' is STARTING."
2026-10-14T19:21:15.187Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_campaign_advertiser' is RUNNING."
2026-10-14T19:21:17.919Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_campaign_advertiser' has COMPLETED."
2026-10-14T19:21:17.926Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_book' is PLANNING."
2026-10-14T19:21:18.347Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_book' is STARTING."
2026-10-14T19:21:18.375Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_book' is RUNNING."
2026-10-14T19:21:20.805Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_book' has COMPLETED."
2026-10-14T19:21:20.812Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk' is PLANNING."
2026-10-14T19:21:21.350Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk' is STARTING."
2026-10-14T19:21:21.380Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk' is RUNNING."
2026-10-14T19:21:24.000Z flow_progress   INFO "Flow 'cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk' has COMPLETED."
2026-10-14T19:21:24.079Z update_progress INFO "Update 9d1459 is COMPLETED."
Update ID: 9d1459bc-218b-4c96-9fbe-a133ca610232
```

## Step 4 — `python build/train_models.py` (MLflow tracking + UC registry)

```text
Model A AUC: 0.938 version 1
🏃 View run renewal_risk at: https://fevm-cs-genie-research.cloud.databricks.com/ml/experiments/582590213290966/runs/5ad0efb25840455baf81c09324e657a4
🧪 View experiment at: https://fevm-cs-genie-research.cloud.databricks.com/ml/experiments/582590213290966
Model B AUC: 0.675 version 1 labels 144
RESULT: {
  "model_a_auc": 0.938,
  "model_a_version": "1",
  "model_b_auc": 0.675,
  "model_b_version": "1",
  "b_labels": 144,
  "high_count": 22,
  "high_rev_at_risk_M": 43.4,
  "tiers": [
    {"risk_tier": "Low",    "n": 78, "rev_M": 70.4},
    {"risk_tier": "Medium", "n": 44, "rev_M": 66.7},
    {"risk_tier": "High",   "n": 22, "rev_M": 43.4}
  ]
}
```

## Step 3 — metric views + governed views (`python build/deploy_mv.py build/dabs/ddl/<file>.sql`)

```text
gold_campaign_delivery.view          state: SUCCEEDED
silver_accounts.view                 state: SUCCEEDED
silver_deals.view                    state: SUCCEEDED
dash_silver_nielsen.view             state: SUCCEEDED
dash_advertiser_risk.view            state: SUCCEEDED
dash_model_health.view               state: SUCCEEDED
mv_campaign_metrics.metric_view      state: SUCCEEDED
mv_advertiser_renewal.metric_view    state: SUCCEEDED

SELECT `Risk Tier`, MEASURE(`Revenue at Risk`), MEASURE(`Total Contract Value`) FROM mv_advertiser_renewal GROUP BY 1
  Low     rar 7.0386248E7   tcv 1.65813126E8
  Medium  rar 6.6693147E7   tcv 8.6364232E7
  High    rar 4.344443E7    tcv 4.9894078E7
```

## Step 5 — Lakebase

```text
$ databricks postgres create-project renewal-actions ...
  "name": "projects/renewal-actions", "pg_version": 17, "default_branch": "projects/renewal-actions/branches/production"

$ databricks postgres create-synced-table cs_genie_research_catalog.ad_sales.lb_advertiser_risk_scores (CONTINUOUS, pk advertiser_id)
  "done": true, "name": "synced_tables/cs_genie_research_catalog.ad_sales.lb_advertiser_risk_scores"

$ databricks postgres get-synced-table ...
  {"detailed_state": "SYNCED_TABLE_ONLINE_CONTINUOUS_UPDATE", "last_sync": {"delta_table_sync_info": {"delta_commit_version": 1}, ...}}

psql (as project owner): synced rows (144,)  · GRANT USAGE/SELECT on ad_sales to app SP ok · CREATE TABLE public.seller_actions ok
```

## Step 6 — Genie space (`python build/build_genie.py` → `POST /api/2.0/genie/spaces`)

```text
payload written; sources: cs_genie_research_catalog.ad_sales.mv_campaign_metrics cs_genie_research_catalog.ad_sales.advertiser_risk_scores cs_genie_research_catalog.ad_sales.gold_campaign_advertiser
01f1c80529421edaa5212423f9c65124 Polaris — Ad Sales Renewal Intelligence
```

## Step 7 — AI/BI dashboards (`python build/rebuild_dashboards_from_ref.py`)

```text
=== testing datasets ===
  [ds_adv              ] OK
  [ds_camp             ] OK
  [ds_silver_accounts  ] OK
  [ds_silver_deals     ] OK
  [ds_silver_nielsen   ] OK
  [ds_ml_risk          ] OK
  [ds_ml_decomp        ] OK
  [ds_ml_monitor_wide  ] OK
  [ds_ml_rates         ] OK
  [ds_ml_campshort     ] OK
RR pages: ['cockpit', 'filters', 'risk_analytics', 'model_health', 'delivery_risk']
AS pages: ['silver_accounts', 'silver_deals', 'silver_nielsen', 'ad_server_details']
created+published renewal_risk: 01f1c805646d10c7bc4b13e6270abd37
created+published ad_sales: 01f1c805651b10ad9a2ffccdcc8219f0
DONE
```

## Step 9 — Deal Memory (`python build/build_deal_memory.py`)

```text
deal_docs rows: 15 | volume: /Volumes/cs_genie_research_catalog/ad_sales/deal_memory

Q: What did we promise Meridian in their last renewal?
   (0.718, 'Meridian Retail (062)', 'contract', 'Renewal Insertion Order 2026')
   (0.682, 'Meridian Retail (062)', 'qbr', 'QBR Notes — Aug 2026')
   (0.649, 'Meridian Restaurants', 'recap', 'Primetime QSR Wrap')

Q: Which recaps flagged viewability or under-delivery concerns?
   (0.659, 'Halcyon Retail (061)', 'recap', 'Late-Night Wrap')
   (0.658, 'Meridian Retail (062)', 'recap', 'Q3 Campaign Wrap Report')
   (0.65, 'Ironwood Health (040)', 'recap', 'Reach Wrap Report')
```

## Step 8 — Databricks App

```text
$ databricks apps create --json @app_create.json
  https://ad-sales-renewal-cockpit-7474655804120295.aws.databricksapps.com  SP 808e81c3-521d-486f-8e2e-d53d71dc9183  {'state': 'ACTIVE'}
$ databricks sync build/app /Workspace/Users/chandan.sahai@databricks.com/ad-sales-renewal-cockpit-src && databricks apps deploy ...
  {'message': 'App started successfully', 'state': 'SUCCEEDED'}

GET  /api/config  -> {"workspace_id":"7474655804120295","genie_space":"01f1c80529421edaa5212423f9c65124","dashboard_as":"01f1c805651b10ad9a2ffccdcc8219f0","dashboard_rr":"01f1c805646d10c7bc4b13e6270abd37"}
GET  /api/risk?tier=High -> 22 rows; top = Meridian Retail (062) 3586879.0
POST /api/action {ADV0062 contacted "build verification" 2026-10-21} -> {"ok":true,"action_id":1}
GET  /api/risk?advertiser=ADV0062 -> last_action=contacted, last_note="build verification", next_connect_date=2026-10-21
POST /api/deal_memory "What did we promise Meridian in their last renewal?" -> [('Meridian Retail (062)','Renewal Insertion Order 2026',0.718), ('Meridian Retail (062)','QBR Notes — Aug 2026',0.682)]
POST /api/genie "Summarize Meridian Restaurants campaign performance..." (25.7s) ->
  rows [['CMP00532','0.82','0.82','0.86','0.88','$213,215'], ['CMP00095','0.82','0.82','0.84','0.83','$99,519'], ...]
```

## Step 10 — "one number" proof

```text
High revenue-at-risk: metric view 4.344443E7 = base table 4.344443E7 = Lakebase via app 43444430 (22 advertisers)
CPM 31.03 · delivery 0.853 · sellout 0.674 · book 3.02071436E8 · act-today 15
```

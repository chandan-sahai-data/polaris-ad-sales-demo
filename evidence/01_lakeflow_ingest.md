# Stage 1 — Lakeflow ingestion (raw → bronze → silver → gold)

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:15:11 UTC by `evidence/capture_evidence.py`._

## Landing (raw) tables — synthetic source systems

**Row counts + source system + freshness per landing table**

```sql
SELECT 'crm_accounts_raw' t, count(*) n, max(source_system) src, max(last_refresh) last_refresh FROM cs_genie_research_catalog.ad_sales.crm_accounts_raw
UNION ALL SELECT 'crm_deals_raw', count(*), max(source_system), max(last_refresh) FROM cs_genie_research_catalog.ad_sales.crm_deals_raw
UNION ALL SELECT 'ad_server_lineitems_raw', count(*), max(source_system), max(last_refresh) FROM cs_genie_research_catalog.ad_sales.ad_server_lineitems_raw
UNION ALL SELECT 'nielsen_measurement_raw', count(*), max(source_system), max(last_refresh) FROM cs_genie_research_catalog.ad_sales.nielsen_measurement_raw
```

| t | n | src | last_refresh |
|---|---|---|---|
| crm_accounts_raw | 150 | Salesforce_CRM | 2026-10-14T11:19:31.031Z |
| crm_deals_raw | 300 | Salesforce_CRM | 2026-10-13T23:19:38.885Z |
| ad_server_lineitems_raw | 765 | GAM_AdServer | 2026-10-14T19:07:44.089Z |
| nielsen_measurement_raw | 600 | Nielsen_ONE | 2026-10-11T19:19:48.640Z |

**Sample: ad_server_lineitems_raw**

```sql
SELECT * FROM cs_genie_research_catalog.ad_sales.ad_server_lineitems_raw ORDER BY order_id LIMIT 5
```

| campaign_id | advertiser_id | order_id | network | daypart | sales_type | flight_start | flight_end | booked_impressions | delivered_impressions | booked_spend | cpm_booked | inventory_units_booked | inventory_units_available | source_system | last_refresh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CMP00001 | ADV0017 | ORD-CMP00001-1 | Lifestyle | LateNight | upfront | 2026-10-30 | 2026-12-15 | 9730105.0 | 8481269.0 | 99538.97 | 10.23 | 277.0 | 441.0 | GAM_AdServer | 2026-10-14T19:07:44.089Z |
| CMP00002 | ADV0130 | ORD-CMP00002-1 | News 24 | Primetime | upfront | 2026-10-09 | 2026-11-30 | 7303805.0 | 7617847.0 | 182960.32 | 25.05 | 92.0 | 137.0 | GAM_AdServer | 2026-10-14T19:07:44.089Z |
| CMP00002 | ADV0130 | ORD-CMP00002-2 | News 24 | Primetime | scatter | 2026-09-30 | 2026-11-01 | 1626510.0 | 1574275.0 | 46827.22 | 28.79 | 287.0 | 345.0 | GAM_AdServer | 2026-10-14T19:07:44.089Z |
| CMP00003 | ADV0019 | ORD-CMP00003-1 | Sports Net | Daytime | upfront | 2026-09-14 | 2026-10-23 | 2112055.0 | 1729112.0 | 84566.68 | 40.04 | 308.0 | 503.0 | GAM_AdServer | 2026-10-14T19:07:44.089Z |
| CMP00004 | ADV0037 | ORD-CMP00004-1 | News 24 | Morning | scatter | 2026-10-07 | 2026-11-17 | 8279550.0 | 6386128.0 | 73688.0 | 8.9 | 254.0 | 438.0 | GAM_AdServer | 2026-10-14T19:07:44.089Z |


## Lakeflow Spark Declarative Pipeline

```json
{
  "pipeline_id": "42e57d29-404f-4c9d-a677-5c0b6d8fba90",
  "name": "[dev chandan_sahai] Ad Sales Ingestion (cs_genie_research_catalog.ad_sales)",
  "state": "PipelineState.IDLE",
  "catalog": "cs_genie_research_catalog",
  "schema": "ad_sales",
  "serverless": true,
  "channel": "CURRENT",
  "libraries": [
    "/Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/bronze.py",
    "/Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/silver.py",
    "/Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/gold.py",
    "/Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/gold_risk.py"
  ]
}
```

**Pipeline updates (most recent first)**

| update_id | state | full_refresh | creation_time |
|---|---|---|---|
| 9d1459bc-218b-4c96-9fbe-a133ca610232 | COMPLETED | False | 2026-10-14 19:20:13.008000+00:00 |

**Event log — completed flows (bronze → silver → gold)**

```sql
SELECT timestamp, origin.flow_name AS flow, details:flow_progress.status AS status,
details:flow_progress.metrics.num_output_rows AS num_output_rows
FROM event_log('42e57d29-404f-4c9d-a677-5c0b6d8fba90') WHERE event_type='flow_progress' AND details:flow_progress.status='COMPLETED'
ORDER BY timestamp
```

| timestamp | flow | status | num_output_rows |
|---|---|---|---|
| 2026-10-14T19:21:08.518Z | cs_genie_research_catalog.ad_sales.bronze_nielsen | COMPLETED | NULL |
| 2026-10-14T19:21:08.527Z | cs_genie_research_catalog.ad_sales.bronze_crm_deals | COMPLETED | NULL |
| 2026-10-14T19:21:08.535Z | cs_genie_research_catalog.ad_sales.bronze_ad_server | COMPLETED | NULL |
| 2026-10-14T19:21:08.543Z | cs_genie_research_catalog.ad_sales.bronze_crm_accounts | COMPLETED | NULL |
| 2026-10-14T19:21:14.503Z | cs_genie_research_catalog.ad_sales.silver_crm_deals | COMPLETED | 300 |
| 2026-10-14T19:21:14.529Z | cs_genie_research_catalog.ad_sales.silver_nielsen | COMPLETED | 600 |
| 2026-10-14T19:21:14.569Z | cs_genie_research_catalog.ad_sales.silver_ad_server | COMPLETED | 765 |
| 2026-10-14T19:21:14.600Z | cs_genie_research_catalog.ad_sales.silver_crm_accounts | COMPLETED | 150 |
| 2026-10-14T19:21:17.919Z | cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | COMPLETED | 600 |
| 2026-10-14T19:21:20.805Z | cs_genie_research_catalog.ad_sales.gold_advertiser_book | COMPLETED | 144 |
| 2026-10-14T19:21:24.000Z | cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk | COMPLETED | 144 |

**Event log — data-quality expectation results (SDP expectations)**

```sql
SELECT origin.flow_name AS flow, e.name AS expectation, e.dataset, e.passed_records, e.failed_records
FROM event_log('42e57d29-404f-4c9d-a677-5c0b6d8fba90'),
LATERAL explode(from_json(details:flow_progress.data_quality.expectations,
  'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS t(e)
WHERE event_type='flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL
ORDER BY flow, expectation
```

| flow | expectation | dataset | passed_records | failed_records |
|---|---|---|---|---|
| cs_genie_research_catalog.ad_sales.silver_ad_server | delivered_in_bounds | cs_genie_research_catalog.ad_sales.silver_ad_server | 765 | 0 |
| cs_genie_research_catalog.ad_sales.silver_ad_server | positive_booked | cs_genie_research_catalog.ad_sales.silver_ad_server | 765 | 0 |
| cs_genie_research_catalog.ad_sales.silver_ad_server | valid_advertiser | cs_genie_research_catalog.ad_sales.silver_ad_server | 765 | 0 |
| cs_genie_research_catalog.ad_sales.silver_ad_server | valid_campaign | cs_genie_research_catalog.ad_sales.silver_ad_server | 765 | 0 |
| cs_genie_research_catalog.ad_sales.silver_ad_server | valid_sales_type | cs_genie_research_catalog.ad_sales.silver_ad_server | 765 | 0 |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | valid_advertiser | cs_genie_research_catalog.ad_sales.silver_crm_accounts | 150 | 0 |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | valid_category | cs_genie_research_catalog.ad_sales.silver_crm_accounts | 150 | 0 |
| cs_genie_research_catalog.ad_sales.silver_crm_deals | positive_value | cs_genie_research_catalog.ad_sales.silver_crm_deals | 300 | 0 |
| cs_genie_research_catalog.ad_sales.silver_crm_deals | valid_advertiser | cs_genie_research_catalog.ad_sales.silver_crm_deals | 300 | 0 |
| cs_genie_research_catalog.ad_sales.silver_crm_deals | valid_deal | cs_genie_research_catalog.ad_sales.silver_crm_deals | 300 | 0 |
| cs_genie_research_catalog.ad_sales.silver_nielsen | in_target_bounds | cs_genie_research_catalog.ad_sales.silver_nielsen | 600 | 0 |
| cs_genie_research_catalog.ad_sales.silver_nielsen | valid_campaign | cs_genie_research_catalog.ad_sales.silver_nielsen | 600 | 0 |


## Row counts at every medallion layer

```sql
SELECT 'bronze_ad_server' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.bronze_ad_server UNION ALL SELECT 'bronze_crm_accounts' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.bronze_crm_accounts UNION ALL SELECT 'bronze_crm_deals' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.bronze_crm_deals UNION ALL SELECT 'bronze_nielsen' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.bronze_nielsen UNION ALL SELECT 'silver_ad_server' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.silver_ad_server UNION ALL SELECT 'silver_crm_accounts' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.silver_crm_accounts UNION ALL SELECT 'silver_crm_deals' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.silver_crm_deals UNION ALL SELECT 'silver_nielsen' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.silver_nielsen UNION ALL SELECT 'gold_campaign_advertiser' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.gold_campaign_advertiser UNION ALL SELECT 'gold_advertiser_book' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.gold_advertiser_book UNION ALL SELECT 'gold_advertiser_renewal_risk' AS table_name, count(*) AS row_count FROM cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk
```

| table_name | row_count |
|---|---|
| silver_ad_server | 765 |
| silver_crm_accounts | 150 |
| silver_crm_deals | 300 |
| silver_nielsen | 600 |
| bronze_ad_server | 765 |
| bronze_crm_accounts | 150 |
| bronze_crm_deals | 300 |
| bronze_nielsen | 600 |
| gold_campaign_advertiser | 600 |
| gold_advertiser_book | 144 |
| gold_advertiser_renewal_risk | 144 |

**Gold unified campaign row (hero advertiser Meridian Retail)**

```sql
SELECT campaign_id, advertiser_name, category, sales_type, round(pacing_index,3) pacing_index,
round(effective_cpm,2) effective_cpm, round(reach_delivery_pct,3) reach_delivery_pct, adserver_last_refresh, nielsen_last_refresh
FROM cs_genie_research_catalog.ad_sales.gold_campaign_advertiser WHERE advertiser_id='ADV0062'
```

| campaign_id | advertiser_name | category | sales_type | pacing_index | effective_cpm | reach_delivery_pct | adserver_last_refresh | nielsen_last_refresh |
|---|---|---|---|---|---|---|---|---|
| CMP00150 | Meridian Retail (062) | Retail | scatter | 0.618 | 71.49 | 0.77 | 2026-10-14T19:07:44.089Z | 2026-10-08T19:19:48.640Z |
| CMP00137 | Meridian Retail (062) | Retail | scatter | 0.827 | 50.38 | 0.733 | 2026-10-14T19:07:44.089Z | 2026-10-11T19:19:48.640Z |

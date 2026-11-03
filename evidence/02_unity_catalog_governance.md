# Stage 2 — Unity Catalog governance (objects, grants, lineage, metric views)

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:15:37 UTC by `evidence/capture_evidence.py`._

**All governed objects in the schema**

```sql
SELECT table_name, table_type, data_source_format, comment FROM cs_genie_research_catalog.information_schema.tables
WHERE table_schema='ad_sales' AND table_name NOT LIKE '\_\_%' ORDER BY table_type, table_name
```

| table_name | table_type | data_source_format | comment |
|---|---|---|---|
| lb_advertiser_risk_scores | FOREIGN | POSTGRESQL_FORMAT | Database table synced from another UC table |
| ad_server_lineitems_raw | MANAGED | DELTA | NULL |
| advertiser_risk_scores | MANAGED | DELTA | NULL |
| crm_accounts_raw | MANAGED | DELTA | NULL |
| crm_deals_raw | MANAGED | DELTA | NULL |
| deal_docs | MANAGED | DELTA | NULL |
| event_log_42e57d29_404f_4c9d_a677_5c0b6d8fba90 | MANAGED | DELTA | NULL |
| event_log_b99ed1a4_a38d_43bf_8de1_f667cfb6a9c9 | MANAGED | DELTA | NULL |
| ml_campaign_shortfall_scores | MANAGED | DELTA | NULL |
| ml_model_monitoring | MANAGED | DELTA | NULL |
| nielsen_measurement_raw | MANAGED | DELTA | NULL |
| gold_advertiser_book | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Advertiser-grain rollup of campaign delivery + the current renewal deal. |
| gold_advertiser_renewal_risk | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Rules-based composite renewal-risk score per advertiser (v0; superseded by advertiser_risk_scores in step 4). |
| gold_campaign_advertiser | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | One row per campaign joining ad-server delivery, CRM deal/account, and Nielsen reach. |
| silver_ad_server | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Conformed ad-server line items |
| silver_crm_accounts | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Conformed CRM accounts |
| silver_crm_deals | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Conformed CRM deals (current + historical) |
| silver_nielsen | MATERIALIZED_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Conformed Nielsen measurement (lagged feed) |
| mv_advertiser_renewal | METRIC_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Governed advertiser-grain renewal-risk metrics for the cockpit dashboard and Genie. |
| mv_campaign_metrics | METRIC_VIEW | UNKNOWN_DATA_SOURCE_FORMAT | Governed ad-sales delivery & efficiency metrics — defined once, consumed by dashboard, Genie and the risk model. |
| bronze_ad_server | STREAMING_TABLE | UNKNOWN_DATA_SOURCE_FORMAT | Bronze ingest of ad_server_lineitems_raw |
| bronze_crm_accounts | STREAMING_TABLE | UNKNOWN_DATA_SOURCE_FORMAT | Bronze ingest of crm_accounts_raw |
| bronze_crm_deals | STREAMING_TABLE | UNKNOWN_DATA_SOURCE_FORMAT | Bronze ingest of crm_deals_raw |
| bronze_nielsen | STREAMING_TABLE | UNKNOWN_DATA_SOURCE_FORMAT | Bronze ingest of nielsen_measurement_raw |
| dash_advertiser_risk | VIEW | UNKNOWN_DATA_SOURCE_FORMAT | NULL |
| dash_model_health | VIEW | UNKNOWN_DATA_SOURCE_FORMAT | NULL |
| dash_silver_nielsen | VIEW | UNKNOWN_DATA_SOURCE_FORMAT | NULL |
| gold_campaign_delivery | VIEW | UNKNOWN_DATA_SOURCE_FORMAT | NULL |
| silver_accounts | VIEW | UNKNOWN_DATA_SOURCE_FORMAT | NULL |
| silver_deals | VIEW | UNKNOWN_DATA_SOURCE_FORMAT | NULL |

**Grants on the schema (app service principal has USE SCHEMA + SELECT)**

```sql
SHOW GRANTS ON SCHEMA cs_genie_research_catalog.ad_sales
```

| Principal | ActionType | ObjectType | ObjectKey |
|---|---|---|---|
| 808e81c3-521d-486f-8e2e-d53d71dc9183 | SELECT | SCHEMA | cs_genie_research_catalog.ad_sales |
| 808e81c3-521d-486f-8e2e-d53d71dc9183 | USE SCHEMA | SCHEMA | cs_genie_research_catalog.ad_sales |
| account users | READ METADATA | METASTORE | metastore_aws_us_west_2 |
| chandan.sahai@databricks.com | ALL PRIVILEGES | CATALOG | cs_genie_research_catalog |
| chandan.sahai@databricks.com | MANAGE | CATALOG | cs_genie_research_catalog |
| aec5be3d-de3c-404c-8e60-feed0f265fd3 | ALL PRIVILEGES | CATALOG | cs_genie_research_catalog |
| aec5be3d-de3c-404c-8e60-feed0f265fd3 | MANAGE | CATALOG | cs_genie_research_catalog |

**Unity Catalog lineage captured automatically (system.access.table_lineage)**

```sql
SELECT source_table_full_name, target_table_full_name, entity_type, max(event_time) last_seen
FROM system.access.table_lineage WHERE target_table_catalog='cs_genie_research_catalog' AND target_table_schema='ad_sales'
AND source_table_full_name IS NOT NULL GROUP BY ALL ORDER BY target_table_full_name
```

| source_table_full_name | target_table_full_name | entity_type | last_seen |
|---|---|---|---|
| cs_genie_research_catalog.ad_sales.ad_server_lineitems_raw | cs_genie_research_catalog.ad_sales.bronze_ad_server | PIPELINE | 2026-10-14T19:21:08.538Z |
| cs_genie_research_catalog.ad_sales.crm_accounts_raw | cs_genie_research_catalog.ad_sales.bronze_crm_accounts | PIPELINE | 2026-10-14T19:21:08.546Z |
| cs_genie_research_catalog.ad_sales.crm_deals_raw | cs_genie_research_catalog.ad_sales.bronze_crm_deals | PIPELINE | 2026-10-14T19:21:08.530Z |
| cs_genie_research_catalog.ad_sales.nielsen_measurement_raw | cs_genie_research_catalog.ad_sales.bronze_nielsen | PIPELINE | 2026-10-14T19:21:08.522Z |
| cs_genie_research_catalog.ad_sales.advertiser_risk_scores | cs_genie_research_catalog.ad_sales.dash_advertiser_risk | NULL | 2026-10-14T19:35:32.816Z |
| cs_genie_research_catalog.ad_sales.ml_model_monitoring | cs_genie_research_catalog.ad_sales.dash_model_health | NULL | 2026-10-14T19:27:19.844Z |
| cs_genie_research_catalog.ad_sales.silver_nielsen | cs_genie_research_catalog.ad_sales.dash_silver_nielsen | NULL | 2026-10-14T19:27:12.383Z |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | cs_genie_research_catalog.ad_sales.dash_silver_nielsen | NULL | 2026-10-14T19:27:12.383Z |
| cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | cs_genie_research_catalog.ad_sales.gold_advertiser_book | PIPELINE | 2026-10-14T19:21:20.809Z |
| cs_genie_research_catalog.ad_sales.gold_advertiser_book | cs_genie_research_catalog.ad_sales.gold_advertiser_renewal_risk | PIPELINE | 2026-10-14T19:21:24.003Z |
| cs_genie_research_catalog.ad_sales.silver_ad_server | cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | PIPELINE | 2026-10-14T19:21:17.924Z |
| cs_genie_research_catalog.ad_sales.silver_nielsen | cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | PIPELINE | 2026-10-14T19:21:17.924Z |
| cs_genie_research_catalog.ad_sales.silver_crm_deals | cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | PIPELINE | 2026-10-14T19:21:17.924Z |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | PIPELINE | 2026-10-14T19:21:17.924Z |
| cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | cs_genie_research_catalog.ad_sales.gold_campaign_delivery | NULL | 2026-10-14T19:28:09.865Z |
| cs_genie_research_catalog.ad_sales.advertiser_risk_scores | cs_genie_research_catalog.ad_sales.lb_advertiser_risk_scores | PIPELINE | 2026-10-14T19:25:59.960Z |
| cs_genie_research_catalog.ad_sales.ml_campaign_shortfall_scores | cs_genie_research_catalog.ad_sales.ml_model_monitoring | NULL | 2026-10-14T19:24:24.220Z |
| cs_genie_research_catalog.ad_sales.dash_advertiser_risk | cs_genie_research_catalog.ad_sales.mv_advertiser_renewal | NULL | 2026-10-14T19:35:32.816Z |
| cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | cs_genie_research_catalog.ad_sales.mv_campaign_metrics | NULL | 2026-10-15T00:47:15.113Z |
| cs_genie_research_catalog.ad_sales.gold_campaign_advertiser | cs_genie_research_catalog.ad_sales.mv_campaign_metrics | NOTEBOOK | 2026-10-15T00:20:59.363Z |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | cs_genie_research_catalog.ad_sales.silver_accounts | DASHBOARD_V3 | 2026-10-15T00:06:06.290Z |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | cs_genie_research_catalog.ad_sales.silver_accounts | NULL | 2026-10-14T19:27:08.466Z |
| cs_genie_research_catalog.ad_sales.bronze_ad_server | cs_genie_research_catalog.ad_sales.silver_ad_server | PIPELINE | 2026-10-14T19:21:14.572Z |
| cs_genie_research_catalog.ad_sales.bronze_crm_accounts | cs_genie_research_catalog.ad_sales.silver_crm_accounts | PIPELINE | 2026-10-14T19:21:14.603Z |
| cs_genie_research_catalog.ad_sales.bronze_crm_deals | cs_genie_research_catalog.ad_sales.silver_crm_deals | PIPELINE | 2026-10-14T19:21:14.513Z |
| cs_genie_research_catalog.ad_sales.silver_crm_deals | cs_genie_research_catalog.ad_sales.silver_deals | NULL | 2026-10-14T19:27:10.597Z |
| cs_genie_research_catalog.ad_sales.silver_crm_accounts | cs_genie_research_catalog.ad_sales.silver_deals | NULL | 2026-10-14T19:27:10.597Z |
| cs_genie_research_catalog.ad_sales.bronze_nielsen | cs_genie_research_catalog.ad_sales.silver_nielsen | PIPELINE | 2026-10-14T19:21:14.533Z |

**Metric view definition — `mv_campaign_metrics`** (single source of truth for KPIs)

```sql
CREATE VIEW cs_genie_research_catalog.ad_sales.mv_campaign_metrics (
  Advertiser,
  Category,
  Region,
  Sales Type,
  Daypart,
  Renewal Window,
  Target Demo COMMENT 'Nielsen target demographic segment',
  Campaigns,
  Booked Spend,
  Sellout Pct COMMENT 'Booked inventory units / available units',
  Effective CPM COMMENT 'Spend per thousand delivered impressions',
  Pacing Index COMMENT 'Mean campaign pacing (delivered / booked); 1.0 = on pace',
  Delivery vs Commitment COMMENT 'Delivered impressions / booked impressions',
  Reach Efficiency COMMENT 'In-target audience impressions per dollar of spend')
COMMENT 'Governed ad-sales delivery & efficiency metrics — defined once, consumed by dashboard, Genie and the risk model.'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: cs_genie_research_catalog.ad_sales.gold_campaign_advertiser

comment: "Governed ad-sales delivery & efficiency metrics — defined once, consumed\
  \ by dashboard, Genie and the risk model."

dimensions:
  - name: Advertiser
    expr: advertiser_name

  - name: Category
    expr: category

  - name: Region
    expr: region

  - name: Sales Type
    expr: sales_type

  - name: Daypart
    expr: daypart

  - name: Renewal Window
    expr: renewal_window

  - name: Target Demo
    expr: target_demo
    comment: Nielsen target demographic segment

measures:
  - name: Campaigns
    expr: COUNT(1)

  - name: Booked Spend
    expr: SUM(booked_spend)
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
      hide_group_separator: false

  - name: Sellout Pct
    expr: SUM(inventory_units_booked) / SUM(inventory_units_available)
    comment: Booked inventory units / available units

  - name: Effective CPM
    expr: SUM(booked_spend) / (SUM(delivered_impressions) / 1000.0)
    comment: Spend per thousand delivered impressions
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      hide_group_separator: false

  - name: Pacing Index
    expr: AVG(pacing_index)
    comment: Mean campaign pacing (delivered / booked); 1.0 = on pace

  - name: Delivery vs Commitment
    expr: SUM(delivered_impressions) / SUM(booked_impressions)
    comment: Delivered impressions / booked impressions

  - name: Reach Efficiency
    expr: SUM(target_audience_impressions) / SUM(booked_spend)
    comment: In-target audience impressions per dollar of spend
    format:
      type: number
      decimal_places:
        type: exact
        places: 2
      hide_group_separator: false
$$

```

**Metric view definition — `mv_advertiser_renewal`** (single source of truth for KPIs)

```sql
CREATE VIEW cs_genie_research_catalog.ad_sales.mv_advertiser_renewal (
  Advertiser,
  Account Owner,
  Category,
  Region,
  Risk Tier,
  Renewal Window,
  Days to Renewal,
  Recommended Action,
  Revenue at Risk,
  Total Contract Value,
  Avg Renewal Risk Score,
  Avg Delivery Risk Score,
  Avg Audience Risk Score,
  Avg Renewal Urgency Score)
COMMENT 'Governed advertiser-grain renewal-risk metrics for the cockpit dashboard and Genie.'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: cs_genie_research_catalog.ad_sales.dash_advertiser_risk

comment: Governed advertiser-grain renewal-risk metrics for the cockpit dashboard
  and Genie.

dimensions:
  - name: Advertiser
    expr: advertiser_name

  - name: Account Owner
    expr: account_owner

  - name: Category
    expr: category

  - name: Region
    expr: region

  - name: Risk Tier
    expr: risk_tier

  - name: Renewal Window
    expr: renewal_window

  - name: Days to Renewal
    expr: days_to_renewal

  - name: Recommended Action
    expr: recommended_action

measures:
  - name: Revenue at Risk
    expr: SUM(revenue_at_risk)
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
      hide_group_separator: false

  - name: Total Contract Value
    expr: SUM(total_contract_value)
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
      hide_group_separator: false

  - name: Avg Renewal Risk Score
    expr: AVG(renewal_risk_score)

  - name: Avg Delivery Risk Score
    expr: AVG(delivery_risk_score)

  - name: Avg Audience Risk Score
    expr: AVG(audience_risk_score)

  - name: Avg Renewal Urgency Score
    expr: AVG(renewal_urgency_score)
$$

```

**Metric view query: governed KPIs by category**

```sql
SELECT Category, MEASURE(`Campaigns`) campaigns, ROUND(MEASURE(`Effective CPM`),2) effective_cpm,
ROUND(MEASURE(`Delivery vs Commitment`),3) delivery_vs_commitment, ROUND(MEASURE(`Sellout Pct`),3) sellout_pct,
ROUND(MEASURE(`Reach Efficiency`),2) reach_efficiency FROM cs_genie_research_catalog.ad_sales.mv_campaign_metrics GROUP BY Category ORDER BY Category
```

| Category | campaigns | effective_cpm | delivery_vs_commitment | sellout_pct | reach_efficiency |
|---|---|---|---|---|---|
| Auto | 108 | 31.19 | 0.871 | 0.672 | 137.71 |
| CPG | 77 | 31.67 | 0.859 | 0.677 | 174.55 |
| Pharma | 102 | 31.64 | 0.827 | 0.662 | 167.59 |
| QSR | 91 | 28.12 | 0.876 | 0.698 | 176.87 |
| Retail | 130 | 31.15 | 0.84 | 0.68 | 165.47 |
| Telco | 92 | 32.21 | 0.85 | 0.657 | 152.94 |

**Metric view query: revenue at risk by tier × renewal window**

```sql
SELECT `Risk Tier`, `Renewal Window`, CAST(MEASURE(`Revenue at Risk`) AS DECIMAL(18,0)) revenue_at_risk, CAST(MEASURE(`Total Contract Value`) AS DECIMAL(18,0)) total_contract_value
FROM cs_genie_research_catalog.ad_sales.mv_advertiser_renewal GROUP BY ALL ORDER BY 1,2
```

| Risk Tier | Renewal Window | revenue_at_risk | total_contract_value |
|---|---|---|---|
| High | renews_next_quarter | 12925564 | 15212772 |
| High | renews_this_quarter | 30518866 | 34681306 |
| Low | already_in_scatter | 11728008 | 30403466 |
| Low | renews_next_quarter | 24252603 | 59007132 |
| Low | renews_this_quarter | 34405637 | 76402528 |
| Medium | already_in_scatter | 11768000 | 15602866 |
| Medium | renews_next_quarter | 28798871 | 37762108 |
| Medium | renews_this_quarter | 26126276 | 32999258 |

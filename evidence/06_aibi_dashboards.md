# Stage 6a — AI/BI dashboards (published; every dataset query executed)

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:13:54 UTC by `evidence/capture_evidence.py`._


## Renewal & Risk Insights (`01f1c805646d10c7bc4b13e6270abd37`)

```json
{
  "display_name": "Renewal & Risk Insights",
  "lifecycle_state": "LifecycleState.ACTIVE",
  "published_warehouse": "69a77ede4fa03b41",
  "published_revision": "2026-10-14T19:28:11.723Z",
  "pages": [
    "Renewal Cockpit",
    "Filters",
    "Risk Analytics",
    "Model Health",
    "Delivery Risk"
  ],
  "widgets": 26,
  "genie_space_linked": "01f1c80529421edaa5212423f9c65124"
}
```

**Dataset `ds_adv` (Advertiser renewal (metric view)) — executed on the warehouse**

```sql
SELECT `Advertiser` AS advertiser, `Category` AS category, `Region` AS region, `Risk Tier` AS risk_tier,        `Renewal Window` AS renewal_window, `Days to Renewal` AS days_to_renewal, `Recommended Action` AS recommended_action, `Account Owner` AS account_owner,        MEASURE(`Revenue at Risk`) AS revenue_at_risk, MEASURE(`Total Contract Value`) AS contract_value,        MEASURE(`Avg Renewal Risk Score`) AS risk_score, MEASURE(`Avg Delivery Risk Score`) AS delivery_score,        MEASURE(`Avg Audience Risk Score`) AS audience_score, MEASURE(`Avg Renewal Urgency Score`) AS urgency_score,        CASE WHEN `Risk Tier`='High' THEN 1 ELSE 0 END AS is_high,        CASE WHEN `Renewal Window`='renews_this_quarter' THEN 1 ELSE 0 END AS is_tq,        CASE WHEN `Risk Tier`='High' AND `Renewal Window`='renews_this_quarter' THEN 1 ELSE 0 END AS is_act_today FROM mv_advertiser_renewal GROUP BY 1,2,3,4,5,6,7,8
```

| advertiser | category | region | risk_tier | renewal_window | days_to_renewal | recommended_action | account_owner | revenue_at_risk | contract_value | risk_score | delivery_score | audience_score | urgency_score | is_high | is_tq | is_act_today |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Atlas Health (149) | Pharma | Northeast | Low | renews_this_quarter | 62 | Maintain | C. Okafor | 151849.0 | 309896.0 | 0.6 | 91.7 | 12.8 | 48.3 | 0 | 1 | 0 |
| Zephyr Motors (057) | Auto | West | Low | renews_next_quarter | 178 | Maintain | G. Patel | 2028064.0 | 3576832.0 | 16.9 | 99.0 | 15.4 | 45.0 | 0 | 0 | 0 |
| Summit Restaurants (005) | QSR | Northeast | Medium | renews_this_quarter | 64 | Monitor delivery; proactive check-in | A. Rivera | 758205.0 | 919036.0 | 90.7 | 97.8 | 20.0 | 46.7 | 0 | 1 | 0 |
| Meridian Brands (128) | CPG | Southeast | Low | renews_next_quarter | 136 | Maintain | E. Santos | 1941662.0 | 3898920.0 | 2.2 | 94.4 | 12.8 | 45.0 | 0 | 0 | 0 |
| Ironwood Health (040) | Pharma | Northeast | High | renews_this_quarter | 12 | Escalate — schedule renewal call now | H. Larsson | 3426027.0 | 3583710.0 | 97.2 | 97.7 | 17.5 | 90.0 | 1 | 1 | 1 |

_(144 rows total, first 5 shown)_

**Dataset `ds_camp` (Campaign delivery (drill-through + freshness)) — executed on the warehouse**

```sql
SELECT account_owner, advertiser_name AS advertiser, campaign_id, category, campaign_pacing_ratio, delivery_status,        booked_spend, reach_delivery_ratio, in_target_pct, audience_quality_score,        nielsen_is_stale, nielsen_lag_hours, adserver_lag_hours FROM gold_campaign_delivery
```

| account_owner | advertiser | campaign_id | category | campaign_pacing_ratio | delivery_status | booked_spend | reach_delivery_ratio | in_target_pct | audience_quality_score | nielsen_is_stale | nielsen_lag_hours | adserver_lag_hours |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E. Santos | Atlas Retail (070) | CMP00263 | Retail | 0.5541 | Under-delivering | 252847.86 | 0.7964 | 0.829 | 85.8 | true | 586.9 | 467.12 |
| A. Rivera | Polaris Brands (056) | CMP00328 | CPG | 0.7741 | Under-delivering | 201420.28 | 0.7608 | 0.816 | 84.2 | true | 610.9 | 467.12 |
| H. Larsson | Ironwood Health (040) | CMP00377 | Pharma | 0.7686 | Under-delivering | 63212.39 | 0.7407 | 0.809 | 83.3 | true | 586.9 | 467.12 |
| G. Patel | Solace Motors (092) | CMP00462 | Auto | 0.9197 | Under-delivering | 402932.5 | 0.8652 | 0.853 | 88.9 | true | 586.9 | 467.12 |
| H. Larsson | Polaris Brands (045) | CMP00489 | CPG | 0.7663 | Under-delivering | 35622.85 | 0.8385 | 0.843 | 87.7 | true | 610.9 | 467.12 |

_(600 rows total, first 5 shown)_

**Dataset `ds_ml_risk` (ds_ml_risk) — executed on the warehouse**

```sql
SELECT account_owner, advertiser_name, category, region, risk_tier, renewal_window, days_to_renewal, p_churn, adv_shortfall_risk, renewal_risk_score, delivery_risk_score, audience_risk_score, renewal_urgency_score, revenue_at_risk, total_contract_value, recommended_action FROM dash_advertiser_risk
```

| account_owner | advertiser_name | category | region | risk_tier | renewal_window | days_to_renewal | p_churn | adv_shortfall_risk | renewal_risk_score | delivery_risk_score | audience_risk_score | renewal_urgency_score | revenue_at_risk | total_contract_value | recommended_action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C. Okafor | Atlas Health (149) | Pharma | Northeast | Low | renews_this_quarter | 62 | 0.0061 | 0.917 | 0.6 | 91.7 | 12.8 | 48.3 | 151849.0 | 309896.0 | Maintain |
| G. Patel | Zephyr Motors (057) | Auto | West | Low | renews_next_quarter | 178 | 0.1689 | 0.9897 | 16.9 | 99.0 | 15.4 | 45.0 | 2028064.0 | 3576832.0 | Maintain |
| A. Rivera | Summit Restaurants (005) | QSR | Northeast | Medium | renews_this_quarter | 64 | 0.9069 | 0.9777 | 90.7 | 97.8 | 20.0 | 46.7 | 758205.0 | 919036.0 | Monitor delivery; proactive check-in |
| E. Santos | Meridian Brands (128) | CPG | Southeast | Low | renews_next_quarter | 136 | 0.0218 | 0.944 | 2.2 | 94.4 | 12.8 | 45.0 | 1941662.0 | 3898920.0 | Maintain |
| H. Larsson | Ironwood Health (040) | Pharma | Northeast | High | renews_this_quarter | 12 | 0.9718 | 0.9773 | 97.2 | 97.7 | 17.5 | 90.0 | 3426027.0 | 3583710.0 | Escalate — schedule renewal call now |

_(144 rows total, first 5 shown)_

**Dataset `ds_ml_decomp` (ds_ml_decomp) — executed on the warehouse**

```sql
WITH top AS (SELECT advertiser_name, account_owner, p_churn, adv_shortfall_risk, renewal_urgency_score, revenue_at_risk FROM dash_advertiser_risk WHERE risk_tier='High' ORDER BY revenue_at_risk DESC LIMIT 15) SELECT advertiser_name, account_owner, driver, contribution FROM top LATERAL VIEW stack(3, 'Churn', 45*p_churn, 'Delivery', 35*adv_shortfall_risk, 'Urgency', 0.2*renewal_urgency_score) t AS driver, contribution
```

| advertiser_name | account_owner | driver | contribution |
|---|---|---|---|
| Meridian Retail (062) | B. Chen | Churn | 44.7435 |
| Ironwood Health (040) | H. Larsson | Churn | 43.731 |
| Quill Restaurants (101) | D. Novak | Churn | 39.24 |
| Halcyon Retail (061) | A. Rivera | Churn | 44.7975 |
| Polaris Brands (045) | H. Larsson | Churn | 44.559 |

_(45 rows total, first 5 shown)_

**Dataset `ds_ml_monitor_wide` (ds_ml_monitor_wide) — executed on the warehouse**

```sql
SELECT MAX(CASE WHEN model='delivery_shortfall_model' AND metric='auc' THEN value END) AS auc_delivery, MAX(CASE WHEN model='renewal_risk_model' AND metric='auc' THEN value END) AS auc_renewal FROM dash_model_health
```

| auc_delivery | auc_renewal |
|---|---|
| 0.938 | 0.694 |

**Dataset `ds_ml_rates` (ds_ml_rates) — executed on the warehouse**

```sql
SELECT model, CASE WHEN metric LIKE 'predicted%' THEN 'Predicted' ELSE 'Actual' END AS kind, value AS rate FROM dash_model_health WHERE metric LIKE '%rate'
```

| model | kind | rate |
|---|---|---|
| delivery_shortfall_model | Predicted | 0.802 |
| delivery_shortfall_model | Actual | 0.8065 |

**Dataset `ds_ml_campshort` (ds_ml_campshort) — executed on the warehouse**

```sql
SELECT c.account_owner, s.campaign_id, c.advertiser_name, c.category, s.p_shortfall, s.under_delivered, c.booked_spend, c.delivery_status FROM ml_campaign_shortfall_scores s JOIN gold_campaign_delivery c ON s.campaign_id=c.campaign_id
```

| account_owner | campaign_id | advertiser_name | category | p_shortfall | under_delivered | booked_spend | delivery_status |
|---|---|---|---|---|---|---|---|
| A. Rivera | CMP00001 | Monarch Retail (017) | Retail | 0.9903582209420506 | 1 | 99538.97 | Under-delivering |
| A. Rivera | CMP00002 | Juniper Motors (130) | Auto | 0.047971634265572445 | 0 | 229787.54 | On/Ahead |
| A. Rivera | CMP00002 | Juniper Motors (130) | Auto | 0.46766592119447226 | 0 | 229787.54 | On/Ahead |
| C. Okafor | CMP00003 | Summit Motors (019) | Auto | 0.915868919970306 | 1 | 84566.68 | Under-delivering |
| D. Novak | CMP00004 | Northstar Motors (037) | Auto | 0.99432453891002 | 1 | 73688.0 | Under-delivering |

_(765 rows total, first 5 shown)_


## Ad Sales Insights (`01f1c805651b10ad9a2ffccdcc8219f0`)

```json
{
  "display_name": "Ad Sales Insights",
  "lifecycle_state": "LifecycleState.ACTIVE",
  "published_warehouse": "69a77ede4fa03b41",
  "published_revision": "2026-10-14T19:28:12.816Z",
  "pages": [
    "Accounts Explorer",
    "Deals Explorer",
    "Nielsen Explorer",
    "Ad Server Details"
  ],
  "widgets": 33,
  "genie_space_linked": "01f1c80529421edaa5212423f9c65124"
}
```

**Dataset `ds_camp` (Campaign delivery (drill-through + freshness)) — executed on the warehouse**

```sql
SELECT account_owner, advertiser_name AS advertiser, campaign_id, category, campaign_pacing_ratio, delivery_status,        booked_spend, reach_delivery_ratio, in_target_pct, audience_quality_score,        nielsen_is_stale, nielsen_lag_hours, adserver_lag_hours FROM gold_campaign_delivery
```

| account_owner | advertiser | campaign_id | category | campaign_pacing_ratio | delivery_status | booked_spend | reach_delivery_ratio | in_target_pct | audience_quality_score | nielsen_is_stale | nielsen_lag_hours | adserver_lag_hours |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E. Santos | Atlas Retail (070) | CMP00263 | Retail | 0.5541 | Under-delivering | 252847.86 | 0.7964 | 0.829 | 85.8 | true | 586.9 | 467.12 |
| A. Rivera | Polaris Brands (056) | CMP00328 | CPG | 0.7741 | Under-delivering | 201420.28 | 0.7608 | 0.816 | 84.2 | true | 610.9 | 467.12 |
| H. Larsson | Ironwood Health (040) | CMP00377 | Pharma | 0.7686 | Under-delivering | 63212.39 | 0.7407 | 0.809 | 83.3 | true | 586.9 | 467.12 |
| G. Patel | Solace Motors (092) | CMP00462 | Auto | 0.9197 | Under-delivering | 402932.5 | 0.8652 | 0.853 | 88.9 | true | 586.9 | 467.12 |
| H. Larsson | Polaris Brands (045) | CMP00489 | CPG | 0.7663 | Under-delivering | 35622.85 | 0.8385 | 0.843 | 87.7 | true | 610.9 | 467.12 |

_(600 rows total, first 5 shown)_

**Dataset `ds_silver_accounts` (Silver Accounts) — executed on the warehouse**

```sql
SELECT
  advertiser_id,
  advertiser_name,
  category,
  region,
  account_owner,
  source_system,
  last_refresh,
  _ingested_at
FROM
  silver_accounts
```

| advertiser_id | advertiser_name | category | region | account_owner | source_system | last_refresh | _ingested_at |
|---|---|---|---|---|---|---|---|
| ADV0001 | Meridian Restaurants | QSR | National | A. Rivera | Salesforce_CRM | 2026-10-14T11:19:31.031Z | 2026-10-14T19:21:03.916Z |
| ADV0002 | Nimbus Restaurants (002) | QSR | National | E. Santos | Salesforce_CRM | 2026-10-14T11:19:31.031Z | 2026-10-14T19:21:03.916Z |
| ADV0003 | Nimbus Motors (003) | Auto | West | G. Patel | Salesforce_CRM | 2026-10-14T11:19:31.031Z | 2026-10-14T19:21:03.916Z |
| ADV0004 | Halcyon Retail (004) | Retail | Northeast | D. Novak | Salesforce_CRM | 2026-10-14T11:19:31.031Z | 2026-10-14T19:21:03.916Z |
| ADV0005 | Summit Restaurants (005) | QSR | Northeast | A. Rivera | Salesforce_CRM | 2026-10-14T11:19:31.031Z | 2026-10-14T19:21:03.916Z |

_(150 rows total, first 5 shown)_

**Dataset `ds_silver_deals` (Silver Deals) — executed on the warehouse**

```sql
SELECT
  deal_id,
  advertiser_id,
  stage,
  contract_value,
  deal_start,
  deal_end,
  renewal_date,
  upfront_commit_flag,
  renewal_window,
  source_system,
  last_refresh,
  _ingested_at,
  days_to_renewal
FROM
  silver_deals
```

| deal_id | advertiser_id | stage | contract_value | deal_start | deal_end | renewal_date | upfront_commit_flag | renewal_window | source_system | last_refresh | _ingested_at | days_to_renewal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DL0001-C | ADV0001 | Proposal Sent | 2200000.0 | 2025-11-20 | 2026-10-24 | 2026-10-24 | true | renews_this_quarter | Salesforce_CRM | 2026-10-13T23:19:38.885Z | 2026-10-14T19:21:03.732Z | 10 |
| DL0002-C | ADV0002 | Renewal Pending | 3843972.0 | 2025-10-27 | 2026-10-27 | 2026-10-27 | true | renews_this_quarter | Salesforce_CRM | 2026-10-13T23:19:38.885Z | 2026-10-14T19:21:03.732Z | 13 |
| DL0003-C | ADV0003 | Proposal Sent | 2030422.0 | 2025-10-28 | 2026-10-28 | 2026-10-28 | true | renews_this_quarter | Salesforce_CRM | 2026-10-13T23:19:38.885Z | 2026-10-14T19:21:03.732Z | 14 |
| DL0004-C | ADV0004 | Negotiation | 2314700.0 | 2025-08-04 | 2026-08-04 | 2026-08-04 | false | already_in_scatter | Salesforce_CRM | 2026-10-13T23:19:38.885Z | 2026-10-14T19:21:03.732Z | -71 |
| DL0005-C | ADV0005 | Proposal Sent | 919036.0 | 2025-12-17 | 2026-12-17 | 2026-12-17 | true | renews_this_quarter | Salesforce_CRM | 2026-10-13T23:19:38.885Z | 2026-10-14T19:21:03.732Z | 64 |

_(150 rows total, first 5 shown)_

**Dataset `ds_silver_nielsen` (Silver Nielsen) — executed on the warehouse**

```sql
SELECT
  campaign_id,
  advertiser_id,
  target_demo,
  planned_reach,
  delivered_reach,
  reach_delivery_ratio,
  gross_rating_points,
  target_audience_impressions,
  in_target_pct,
  avg_frequency,
  audience_quality_score,
  source_system,
  last_refresh,
  _ingested_at,
  _source_file
FROM
  dash_silver_nielsen
```

| campaign_id | advertiser_id | target_demo | planned_reach | delivered_reach | reach_delivery_ratio | gross_rating_points | target_audience_impressions | in_target_pct | avg_frequency | audience_quality_score | source_system | last_refresh | _ingested_at | _source_file |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CMP00001 | ADV0017 | A18-49 | 5419660.0 | 4195993.0 | 0.7742 | 92.2 | 1.2637995E7 | 0.821 | 5.32 | 84.8 | Nielsen_ONE | 2026-10-07T19:19:48.640Z | 2026-10-14T19:21:03.729Z | NULL |
| CMP00002 | ADV0130 | A25-54 | 2061480.0 | 1936358.0 | 0.9393 | 62.9 | 6058399.0 | 0.879 | 2.75 | 92.3 | Nielsen_ONE | 2026-10-11T19:19:48.640Z | 2026-10-14T19:21:03.729Z | NULL |
| CMP00003 | ADV0019 | W18-34 | 5731160.0 | 4922762.0 | 0.8589 | 181.5 | 2.5568038E7 | 0.851 | 4.91 | 88.7 | Nielsen_ONE | 2026-10-10T19:19:48.640Z | 2026-10-14T19:21:03.729Z | NULL |
| CMP00004 | ADV0037 | W18-34 | 1.316138E7 | 9766299.0 | 0.742 | 83.3 | 2.7690583E7 | 0.81 | 4.46 | 83.4 | Nielsen_ONE | 2026-10-10T19:19:48.640Z | 2026-10-14T19:21:03.729Z | NULL |
| CMP00005 | ADV0028 | W18-34 | 1.36448E7 | 1.1113602E7 | 0.8145 | 137.5 | 6.5229731E7 | 0.835 | 5.28 | 86.7 | Nielsen_ONE | 2026-10-09T19:19:48.640Z | 2026-10-14T19:21:03.729Z | NULL |

_(600 rows total, first 5 shown)_

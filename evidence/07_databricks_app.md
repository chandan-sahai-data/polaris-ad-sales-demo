# Stage 7 — Databricks App (FastAPI) surfacing it to the business

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:15:37 UTC by `evidence/capture_evidence.py`._

**App status**

```json
{
  "name": "ad-sales-renewal-cockpit",
  "url": "https://ad-sales-renewal-cockpit-7474655804120295.aws.databricksapps.com",
  "app_status": "ApplicationState.RUNNING",
  "compute_status": "ComputeState.ACTIVE",
  "service_principal_client_id": "808e81c3-521d-486f-8e2e-d53d71dc9183",
  "active_deployment": "01f1c805fa861775afd6c015d3137f0e",
  "deployment_status": "AppDeploymentState.SUCCEEDED",
  "resources": [
    "sql-warehouse",
    "genie-space",
    "embed-endpoint",
    "postgres"
  ]
}
```


### `GET /api/config` → HTTP 200 in 0.63s

Response:
```json
{
  "host": "fevm-cs-genie-research.cloud.databricks.com",
  "workspace_id": "7474655804120295",
  "genie_space": "01f1c80529421edaa5212423f9c65124",
  "dashboard_as": "01f1c805651b10ad9a2ffccdcc8219f0",
  "dashboard_rr": "01f1c805646d10c7bc4b13e6270abd37"
}
```


### `GET /api/risk?tier=High&window=renews_this_quarter` → HTTP 200 in 0.66s

Response:
```json
{
  "rows_returned": 15,
  "first_rows": [
    {
      "advertiser_id": "ADV0062",
      "advertiser_name": "Meridian Retail (062)",
      "category": "Retail",
      "region": "Southeast",
      "risk_score": 91.7,
      "risk_tier": "High",
      "revenue_at_risk": 3586879.0,
      "renewal_window": "renews_this_quarter",
      "days_to_renewal": 34,
      "campaign_count": 2,
      "campaigns_behind": 2,
      "contributing_factors": "Churn model p=99% | Delivery shortfall risk 97% | Upfront commitment at stake",
      "last_action": "contacted",
      "last_note": "build verification",
      "next_connect_date": "2026-10-21",
      "last_acted_at": "2026-10-14 19:33:13.514591+00:00"
    },
    {
      "advertiser_id": "ADV0040",
      "advertiser_name": "Ironwood Health (040)",
      "category": "Pharma",
      "region": "Northeast",
      "risk_score": 95.6,
      "risk_tier": "High",
      "revenue_at_risk": 3426027.0,
      "renewal_window": "renews_this_quarter",
      "days_to_renewal": 12,
      "campaign_count": 4,
      "campaigns_behind": 4,
      "contributing_factors": "Churn model p=97% | Delivery shortfall risk 98% | Renews in 12 days",
      "last_action": "snoozed",
      "last_note": "evidence capture: transactional write-back test",
      "next_connect_date": "2026-11-10",
      "last_acted_at": "2026-11-03 06:14:34.241197+00:00"
    },
    {
      "advertiser_id": "ADV0101",
      "advertiser_name": "Quill Restaurants (101)",
      "category": "QSR",
      "region": "National",
      "risk_score": 91.7,
      "risk_tier": "High",
      "revenue_at_risk": 3397386.0,
      "renewal_window": "renews_this_quarter",
      "days_to_renewal": 5,
      "campaign_count": 6,
      "campaigns_behind": 6,
      "contributing_factors": "Churn model p=87% | Delivery shortfall risk 93% | Renews in 5 days | Upfront commitment at stake",
      "last_action": null,
      "last_note": null,
      "next_connect_date": null,
      "last_acted_at": null
    },
    {
      "advertiser_id": "ADV0061",
      "advertiser_name": "Halcyon Retail (061)",
      "category": "Retail",
      "region": "Southeast",
      "risk_score": 95.7,
      "risk_tier": "High",
      "revenue_at_risk": 3201487.0,
      "renewal_window": "renews_this_quarter",
      "days_to_renewal": 17,
      "campaign_count": 3,
      "campaigns_behind": 3,
      "contributing_factors": "Churn model p=100% | Delivery shortfall risk 98% | Renews in 17 days | Upfront commitment at stake",
      "last_action": null,
      "last_note": null,
      "next_connect_date": null,
      "last_acted_at": null
    },
    {
      "advertiser_id": "ADV0126",
      "advertiser_name": "Emberly Retail (126)",
      "category": "Retail",
      "region": "West",
      "risk_score": 91.0,
      "risk_tier": "High",
      "revenue_at_risk": 2937680.0,
      "renewal_window": "renews_this_quarter",
      "days_to_renewal": 38,
      "campaign_count": 5,
      "campaigns_behind": 5,
      "contributing_factors": "Churn model p=98% | Delivery shortfall risk 99% | Upfront commitment at stake",
      "last_action": null,
      "last_note": null,
      "next_connect_date": null,
      "last_acted_at": null
    }
  ]
}
```


### `POST /api/action` → HTTP 200 in 0.3s

Request body:
```json
{
  "advertiser_id": "ADV0062",
  "action_type": "contacted",
  "note": "evidence capture: app write-back",
  "next_connect_date": "2026-11-09",
  "acted_by": "evidence-script"
}
```
Response:
```json
{
  "ok": true,
  "action_id": 3
}
```


### `GET /api/risk?advertiser=ADV0062` → HTTP 200 in 0.31s

Response:
```json
{
  "rows_returned": 1,
  "first_rows": [
    {
      "advertiser_id": "ADV0062",
      "advertiser_name": "Meridian Retail (062)",
      "category": "Retail",
      "region": "Southeast",
      "risk_score": 91.7,
      "risk_tier": "High",
      "revenue_at_risk": 3586879.0,
      "renewal_window": "renews_this_quarter",
      "days_to_renewal": 34,
      "campaign_count": 2,
      "campaigns_behind": 2,
      "contributing_factors": "Churn model p=99% | Delivery shortfall risk 97% | Upfront commitment at stake",
      "last_action": "contacted",
      "last_note": "evidence capture: app write-back",
      "next_connect_date": "2026-11-09",
      "last_acted_at": "2026-11-03 06:17:17.248400+00:00"
    }
  ]
}
```


### `POST /api/deal_memory` → HTTP 200 in 1.77s

Request body:
```json
{
  "query": "What did we promise Meridian in their last renewal?"
}
```
Response:
```json
{
  "rows_returned": 5,
  "first_rows": [
    {
      "score": 0.718,
      "advertiser_name": "Meridian Retail (062)",
      "advertiser_id": "ADV0062",
      "doc_type": "contract",
      "source": "Renewal Insertion Order 2026",
      "effective_date": "2026-03-01",
      "content": "Meridian Retail renewal insertion order. We committed to a 95% delivered-impressions guarantee across primetime and sports inventory, with automatic make-good credits for any flight delivering below 95% of booked. Renewal includes a locked upfront CPM rate for four quarters, first-look on premium primetime holiday inventory, and a quarterly business review with audience-quality reporting. We promised added-value bonus weight in daytime if primetime under-delivers."
    },
    {
      "score": 0.682,
      "advertiser_name": "Meridian Retail (062)",
      "advertiser_id": "ADV0062",
      "doc_type": "qbr",
      "source": "QBR Notes \u2014 Aug 2026",
      "effective_date": "2026-08-28",
      "content": "QBR with Meridian Retail. The client raised concerns about under-delivery and viewability on the current flight and asked what we would do before renewal. We promised a make-good in primetime plus a viewability guarantee written into the next insertion order, and committed to a renewal call within two weeks. Renewal is elevated risk given the delivery shortfall and the upcoming renewal date."
    },
    {
      "score": 0.649,
      "advertiser_name": "Meridian Restaurants",
      "advertiser_id": "ADV0001",
      "doc_type": "recap",
      "source": "Primetime QSR Wrap",
      "effective_date": "2026-08-15",
      "content": "Meridian Restaurants primetime QSR wrap: all active campaigns pacing behind plan at roughly 0.82x delivery. Under-delivery concentrated in scatter buys. We discussed a make-good and additional primetime weight to protect the renewal, which is due in ten days."
    },
    {
      "score": 0.619,
      "advertiser_name": "Meridian Retail (062)",
      "advertiser_id": "ADV0062",
      "doc_type": "recap",
      "source": "Q3 Campaign Wrap Report",
      "effective_date": "2026-08-20",
      "content": "Q3 wrap for Meridian Retail: campaign delivered 82% of booked impressions \u2014 an under-delivery driven by soft CTV supply and off-peak daypart pacing. Viewability on the CTV app placements came in below the 70% benchmark, and in-target audience delivery lagged plan. We flagged the under-delivery risk to the client and proposed a make-good plan ahead of the renewal conversation."
    },
    {
      "score": 0.607,
      "advertiser_name": "Pioneer Communications (134)",
      "advertiser_id": "ADV0134",
      "doc_type": "qbr",
      "source": "Telco Renewal QBR",
      "effective_date": "2026-08-26",
      "content": "Pioneer Communications renewal QBR under competitive pressure. Client comparing partners on delivery reliability; we emphasized our make-good track record and proposed a delivery guarantee to secure the renewal."
    }
  ]
}
```


### `POST /api/genie` → HTTP 200 in 18.29s

Request body:
```json
{
  "question": "How many advertisers renew this quarter and how many of those are High risk?"
}
```
Response:
```json
{
  "conversation_id": "01f1d74e3974163b95b37848868cd5fe",
  "text": "At the **advertiser** level, **68** advertisers have `renewal_window = renews_this_quarter`, and **15** of those advertisers have `risk_tier = High`. In this result, advertisers with `risk_tier = High` represent **15 of 68** advertisers renewing this quarter.",
  "sql": "SELECT\n  `renewal_window`,\n  COUNT(*) AS `advertisers`,\n  SUM(CASE WHEN `risk_tier` = 'High' THEN 1 ELSE 0 END) AS `high_risk`\nFROM `cs_genie_research_catalog`.`ad_sales`.`advertiser_risk_scores`\nWHERE `renewal_window` = 'renews_this_quarter'\nGROUP BY `renewal_window`\nORDER BY `advertisers` DESC",
  "rows": {
    "columns": [
      "renewal_window",
      "advertisers",
      "high_risk"
    ],
    "data": [
      [
        "renews_this_quarter",
        "68",
        "15"
      ]
    ]
  }
}
```

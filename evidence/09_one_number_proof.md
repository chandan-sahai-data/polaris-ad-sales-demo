# Integration proof — the same number on every surface

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:15:37 UTC by `evidence/capture_evidence.py`._

**Lakehouse side**

```sql
SELECT
 CAST((SELECT MEASURE(`Revenue at Risk`) FROM cs_genie_research_catalog.ad_sales.mv_advertiser_renewal WHERE `Risk Tier`='High') AS DECIMAL(18,0)) AS metric_view_high_rar,
 CAST((SELECT SUM(revenue_at_risk) FROM cs_genie_research_catalog.ad_sales.advertiser_risk_scores WHERE risk_tier='High') AS DECIMAL(18,0)) AS base_table_high_rar,
 CAST((SELECT SUM(revenue_at_risk) FROM cs_genie_research_catalog.ad_sales.dash_advertiser_risk WHERE risk_tier='High') AS DECIMAL(18,0)) AS dashboard_view_high_rar,
 (SELECT COUNT(*) FROM cs_genie_research_catalog.ad_sales.advertiser_risk_scores WHERE risk_tier='High') AS high_count,
 (SELECT ROUND(MEASURE(`Effective CPM`),2) FROM cs_genie_research_catalog.ad_sales.mv_campaign_metrics) AS overall_cpm
```

| metric_view_high_rar | base_table_high_rar | dashboard_view_high_rar | high_count | overall_cpm |
|---|---|---|---|---|
| 43444430 | 43444430 | 43444430 | 22 | 31.03 |

**Lakebase (operational) side — what the app reads**

```sql
SELECT round(sum(revenue_at_risk)::numeric,0) lakebase_high_rar, count(*) high_count FROM ad_sales.lb_advertiser_risk_scores WHERE risk_tier='High'
```

| lakebase_high_rar | high_count |
|---|---|
| 43444430 | 22 |

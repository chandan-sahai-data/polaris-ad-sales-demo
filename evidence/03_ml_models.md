# Stage 3 — ML: delivery-shortfall classifier + renewal-risk model → composite score

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:13:54 UTC by `evidence/capture_evidence.py`._

**MLflow experiment** `/Users/chandan.sahai@databricks.com/cs_genie_research_catalog_ml_experiment` (id 582590213290966)

| run_id | run_name | status | start_time | val_auc | precision | recall |
|---|---|---|---|---|---|---|
| 5ad0efb25840455baf81c09324e657a4 | renewal_risk | FINISHED | 2026-10-14 19:23:12.942000+00:00 | 0.675 | 0.6316 | 0.75 |
| 56a8fcaf147d42809875359f9b423dcd | delivery_shortfall | FINISHED | 2026-10-14 19:21:56.934000+00:00 | 0.9379 | 0.9359 | 0.9419 |


**Unity Catalog registered model versions**

| model | version | status | run_id | aliases |
|---|---|---|---|---|
| cs_genie_research_catalog.ad_sales.delivery_shortfall_model | 1 | READY | 56a8fcaf147d42809875359f9b423dcd | prod |
| cs_genie_research_catalog.ad_sales.renewal_risk_model | 1 | READY | 5ad0efb25840455baf81c09324e657a4 | prod |

**Model monitoring table (predicted vs actual)**

```sql
SELECT * FROM cs_genie_research_catalog.ad_sales.ml_model_monitoring
```

| model | scored_at | n | avg_pred | actual_rate |
|---|---|---|---|---|
| delivery_shortfall_model | 2026-10-14T19:24:22.742Z | 765 | 0.802 | 0.8065 |

**Model A batch scores — top 10 campaigns by p(shortfall)**

```sql
SELECT campaign_id, advertiser_id, round(p_shortfall,3) p_shortfall FROM cs_genie_research_catalog.ad_sales.ml_campaign_shortfall_scores
ORDER BY p_shortfall DESC LIMIT 10
```

| campaign_id | advertiser_id | p_shortfall |
|---|---|---|
| CMP00153 | ADV0122 | 0.999 |
| CMP00118 | ADV0105 | 0.999 |
| CMP00456 | ADV0146 | 0.999 |
| CMP00552 | ADV0144 | 0.999 |
| CMP00150 | ADV0062 | 0.998 |
| CMP00077 | ADV0045 | 0.998 |
| CMP00194 | ADV0023 | 0.998 |
| CMP00236 | ADV0101 | 0.998 |
| CMP00061 | ADV0059 | 0.998 |
| CMP00203 | ADV0103 | 0.998 |

**Composite score tiers (advertiser_risk_scores)**

```sql
SELECT risk_tier, count(*) advertisers, round(sum(revenue_at_risk),0) revenue_at_risk FROM cs_genie_research_catalog.ad_sales.advertiser_risk_scores
GROUP BY risk_tier ORDER BY revenue_at_risk DESC
```

| risk_tier | advertisers | revenue_at_risk |
|---|---|---|
| Low | 78 | 7.0386248E7 |
| Medium | 44 | 6.6693147E7 |
| High | 22 | 4.344443E7 |

**Top 15 advertisers by revenue at risk, with explainable drivers**

```sql
SELECT advertiser_name, category, round(p_churn,3) p_churn, round(adv_p_shortfall,3) adv_p_shortfall, round(risk_score,1) risk_score,
risk_tier, round(revenue_at_risk,0) revenue_at_risk, renewal_window, contributing_factors FROM cs_genie_research_catalog.ad_sales.advertiser_risk_scores
ORDER BY revenue_at_risk DESC LIMIT 15
```

| advertiser_name | category | p_churn | adv_p_shortfall | risk_score | risk_tier | revenue_at_risk | renewal_window | contributing_factors |
|---|---|---|---|---|---|---|---|---|
| Meridian Retail (062) | Retail | 0.994 | 0.974 | 91.7 | High | 3586879.0 | renews_this_quarter | Churn model p=99% \| Delivery shortfall risk 97% \| Upfront commitment at stake |
| Ironwood Health (040) | Pharma | 0.972 | 0.977 | 95.6 | High | 3426027.0 | renews_this_quarter | Churn model p=97% \| Delivery shortfall risk 98% \| Renews in 12 days |
| Quill Restaurants (101) | QSR | 0.872 | 0.93 | 91.7 | High | 3397386.0 | renews_this_quarter | Churn model p=87% \| Delivery shortfall risk 93% \| Renews in 5 days \| Upfront commitment at stake |
| Halcyon Retail (061) | Retail | 0.996 | 0.984 | 95.7 | High | 3201487.0 | renews_this_quarter | Churn model p=100% \| Delivery shortfall risk 98% \| Renews in 17 days \| Upfront commitment at stake |
| Ironwood Health (102) | Pharma | 0.975 | 0.878 | 80.5 | Medium | 3086291.0 | renews_next_quarter | Churn model p=98% \| Delivery shortfall risk 88% |
| Polaris Brands (045) | CPG | 0.99 | 0.994 | 85.7 | High | 2991029.0 | renews_next_quarter | Churn model p=99% \| Delivery shortfall risk 99% |
| Emberly Retail (126) | Retail | 0.985 | 0.986 | 91.0 | High | 2937680.0 | renews_this_quarter | Churn model p=98% \| Delivery shortfall risk 99% \| Upfront commitment at stake |
| Pioneer Communications (134) | Telco | 0.916 | 0.901 | 81.4 | Medium | 2781379.0 | renews_this_quarter | Churn model p=92% \| Delivery shortfall risk 90% |
| Emberly Health (072) | Pharma | 0.97 | 0.973 | 76.7 | Medium | 2776045.0 | already_in_scatter | Churn model p=97% \| Delivery shortfall risk 97% \| Upfront commitment at stake |
| Monarch Retail (125) | Retail | 0.989 | 0.845 | 79.7 | Medium | 2757333.0 | renews_next_quarter | Churn model p=99% \| Delivery shortfall risk 84% |
| Monarch Communications (031) | Telco | 0.878 | 0.973 | 80.9 | Medium | 2751998.0 | renews_next_quarter | Churn model p=88% \| Delivery shortfall risk 97% |
| Vantage Motors (104) | Auto | 0.95 | 0.83 | 80.4 | Medium | 2717666.0 | renews_this_quarter | Churn model p=95% \| Delivery shortfall risk 83% \| Upfront commitment at stake |
| Atlas Motors (054) | Auto | 0.984 | 0.511 | 66.1 | Medium | 2619359.0 | renews_next_quarter | Churn model p=98% \| Delivery shortfall risk 51% \| Upfront commitment at stake |
| Quill Health (089) | Pharma | 0.989 | 0.91 | 87.7 | High | 2574505.0 | renews_this_quarter | Churn model p=99% \| Delivery shortfall risk 91% |
| Atlas Retail (070) | Retail | 0.536 | 0.993 | 74.1 | Medium | 2516316.0 | renews_this_quarter | Churn model p=54% \| Delivery shortfall risk 99% \| Upfront commitment at stake |

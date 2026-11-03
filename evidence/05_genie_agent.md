# Stage 5 — Genie Agent: natural-language questions answered over the governed data

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:18:09 UTC by `evidence/capture_evidence.py`._

```json
{
  "space_id": "01f1c80529421edaa5212423f9c65124",
  "title": "Polaris \u2014 Ad Sales Renewal Intelligence",
  "description": "Renewal, delivery and audience intelligence over the governed ad-sales metric views and risk scores."
}
```


## Q1. What's our track record with QSR campaigns over the last two quarters?

_status=MessageStatus.COMPLETED, latency=24.7s, conversation_id=01f1d74e57a911f0b90cbde457db2415_

**Generated SQL**

```sql
SELECT
  `Renewal Window` AS `renewal_window`,
  MEASURE(`Campaigns`) AS `campaigns_raw`,
  ROUND(MEASURE(`Campaigns`), 2) AS `campaigns`,
  ROUND(MEASURE(`Delivery vs Commitment`), 2) AS `delivery_vs_commitment`,
  CONCAT('$', format_number(MEASURE(`Effective CPM`), 2)) AS `effective_cpm`,
  MEASURE(`Booked Spend`) AS `booked_spend_raw`,
  CONCAT('$', format_number(ROUND(MEASURE(`Booked Spend`), 0), 0)) AS `booked_spend`
FROM `cs_genie_research_catalog`.`ad_sales`.`mv_campaign_metrics`
WHERE `Category` = 'QSR'
  AND `Renewal Window` IN ('renews_this_quarter', 'renews_next_quarter')
  AND `Renewal Window` IS NOT NULL
GROUP BY ALL
ORDER BY `renewal_window` ASC
```

**Result rows**

| renewal_window | campaigns_raw | campaigns | delivery_vs_commitment | effective_cpm | booked_spend_raw | booked_spend |
|---|---|---|---|---|---|---|
| renews_next_quarter | 18 | 18 | 0.9 | $31.36 | 3330008.3 | $3,330,008 |
| renews_this_quarter | 61 | 61 | 0.87 | $27.07 | 8920087.53 | $8,920,088 |

**Genie answer**

> Over the last two renewal windows shown for **QSR campaign-grain** performance, campaigns renewing **this quarter** had **61 campaigns**, **0.87** delivery vs commitment, **$27.07** effective CPM, and **$8,920,088** in booked spend, while campaigns renewing **next quarter** had **18 campaigns**, **0.90** delivery vs commitment, **$31.36** effective CPM, and **$3,330,008** in booked spend. Across these two periods, QSR campaigns renewing next quarter delivered slightly better against commitment, while this quarter carried much higher campaign volume and spend.

**Genie answer**

> Would you prefer to see the track record for the two most recent past quarters instead of the upcoming renewal quarters?


## Q2. Meridian Restaurants came up as elevated renewal risk — summarize their campaign performance and delivery against plan.

_status=MessageStatus.COMPLETED, latency=18.8s, conversation_id=01f1d74e66b7145db245139234df9fa2_

**Generated SQL**

```sql
SELECT `campaign_id`, ROUND(`delivery_vs_commitment`, 2) AS `delivery_vs_commitment`, ROUND(`pacing_index`, 2) AS `pacing_index`, ROUND(`in_target_pct`, 2) AS `in_target_pct`, ROUND(`reach_delivery_pct`, 2) AS `reach_delivery_pct`, CONCAT('$', format_number(ROUND(`booked_spend`, 0), 0)) AS `booked_spend` FROM `cs_genie_research_catalog`.`ad_sales`.`gold_campaign_advertiser` WHERE `advertiser_name` = 'Meridian Restaurants' AND `delivery_vs_commitment` IS NOT NULL ORDER BY `delivery_vs_commitment` ASC
```

**Result rows**

| campaign_id | delivery_vs_commitment | pacing_index | in_target_pct | reach_delivery_pct | booked_spend |
|---|---|---|---|---|---|
| CMP00532 | 0.82 | 0.82 | 0.86 | 0.88 | $213,215 |
| CMP00095 | 0.82 | 0.82 | 0.84 | 0.83 | $99,519 |
| CMP00521 | 0.82 | 0.82 | 0.85 | 0.85 | $39,921 |
| CMP00336 | 0.82 | 0.82 | 0.86 | 0.9 | $90,290 |
| CMP00028 | 0.82 | 0.82 | 0.86 | 0.87 | $110,839 |
| CMP00345 | 0.82 | 0.82 | 0.82 | 0.77 | $98,178 |

**Genie answer**

> At the **campaign** level, Meridian Restaurants has **6 campaigns** shown, and all 6 are performing consistently at **0.82 delivery vs commitment** and **0.82 pacing**, indicating they are uniformly behind plan. Examples include:
> - **CMP00532** — **$213,215** booked spend, **0.86** in-target, **0.88** reach delivery
> - **CMP00095** — **$99,519** booked spend, **0.84** in-target, **0.83** reach delivery
> - **CMP00521** — **$39,921** booked spend, **0.85** in-target, **0.85** reach delivery
> - **CMP00336** — **$90,290** booked spend, **0.86** in-target, **0.90** reach delivery
> - **CMP00345** — **$98,178** booked spend, **0.82** in-target, **0.77** reach delivery
> Across these 6 campaigns, delivery and pacing do not vary, while audience quality is steadier than reach delivery, with reach ranging from **0.77** to **0.90**.


## Q3. Which audience segments delivered the best reach efficiency for QSR advertisers?

_status=MessageStatus.COMPLETED, latency=18.8s, conversation_id=01f1d74e723713efa8ce522e741a9942_

**Generated SQL**

```sql
SELECT
  `Target Demo`,
  ROUND(MEASURE(`Reach Efficiency`), 2) AS `reach_efficiency`,
  ROUND(MEASURE(`Campaigns`), 2) AS `campaigns`
FROM `cs_genie_research_catalog`.`ad_sales`.`mv_campaign_metrics`
WHERE `Category` = 'QSR'
  AND `Target Demo` IS NOT NULL
GROUP BY ALL
ORDER BY `reach_efficiency` DESC
```

**Result rows**

| Target Demo | reach_efficiency | campaigns |
|---|---|---|
| A25-54 | 296.37 | 13 |
| M18-49 | 192.69 | 17 |
| W18-34 | 167.35 | 27 |
| P2+ | 150.69 | 19 |
| A18-49 | 140.37 | 15 |

**Genie answer**

> For **QSR campaigns** (campaign-grain), the audience segment with the **best reach efficiency** is **A25-54** at **296.37**, followed by **M18-49** at **192.69**. Reach efficiency drops notably after the top segment, with the 5 returned segments ranked as:
> - **A25-54** — **296.37** reach efficiency across **13.00** campaigns
> - **M18-49** — **192.69** reach efficiency across **17.00** campaigns
> - **W18-34** — **167.35** reach efficiency across **27.00** campaigns
> - **P2+** — **150.69** reach efficiency across **19.00** campaigns
> - **A18-49** — **140.37** reach efficiency across **15.00** campaigns


## Q4. Show the top 10 high-risk advertisers by revenue at risk with their contributing factors.

_status=MessageStatus.COMPLETED, latency=17.9s, conversation_id=01f1d74e7dae13f690f6586f3c770d2c_

**Generated SQL**

```sql
SELECT `advertiser_name`, `category`, ROUND(`risk_score`, 2) AS `risk_score`, `risk_tier`, CONCAT('$', format_number(ROUND(`revenue_at_risk`, 0), 0)) AS `revenue_at_risk_usd`, `contributing_factors`
FROM `cs_genie_research_catalog`.`ad_sales`.`advertiser_risk_scores`
WHERE `risk_tier` = 'High'
  AND `revenue_at_risk` IS NOT NULL
ORDER BY `revenue_at_risk` DESC
LIMIT 10
```

**Result rows**

| advertiser_name | category | risk_score | risk_tier | revenue_at_risk_usd | contributing_factors |
|---|---|---|---|---|---|
| Meridian Retail (062) | Retail | 91.7 | High | $3,586,879 | Churn model p=99% \| Delivery shortfall risk 97% \| Upfront commitment at stake |
| Ironwood Health (040) | Pharma | 95.6 | High | $3,426,027 | Churn model p=97% \| Delivery shortfall risk 98% \| Renews in 12 days |
| Quill Restaurants (101) | QSR | 91.7 | High | $3,397,386 | Churn model p=87% \| Delivery shortfall risk 93% \| Renews in 5 days \| Upfront commitment at stake |
| Halcyon Retail (061) | Retail | 95.7 | High | $3,201,487 | Churn model p=100% \| Delivery shortfall risk 98% \| Renews in 17 days \| Upfront commitment at stake |
| Polaris Brands (045) | CPG | 85.7 | High | $2,991,029 | Churn model p=99% \| Delivery shortfall risk 99% |
| Emberly Retail (126) | Retail | 91.0 | High | $2,937,680 | Churn model p=98% \| Delivery shortfall risk 99% \| Upfront commitment at stake |
| Quill Health (089) | Pharma | 87.7 | High | $2,574,505 | Churn model p=99% \| Delivery shortfall risk 91% |
| Falcon Retail (027) | Retail | 84.4 | High | $2,347,387 | Churn model p=96% \| Delivery shortfall risk 99% |
| Riverstone Health (028) | Pharma | 88.8 | High | $2,347,305 | Churn model p=95% \| Delivery shortfall risk 99% |
| Vantage Retail (132) | Retail | 84.9 | High | $2,283,187 | Churn model p=98% \| Delivery shortfall risk 99% |

**Genie answer**

> These are the **top 10 high-risk advertisers** by **revenue at risk** at the **advertiser level**; the largest is **Meridian Retail (062)** at **$3,586,879**, followed by **Ironwood Health (040)** at **$3,426,027** and **Quill Restaurants (101)** at **$3,397,386**. Examples include:
> - **Meridian Retail (062)** — **$3,586,879** at risk, **risk score 91.70**; contributing factors: **Churn model p=99%**, **delivery shortfall risk 97%**, **upfront commitment at stake**
> - **Ironwood Health (040)** — **$3,426,027** at risk, **risk score 95.60**; contributing factors: **Churn model p=97%**, **delivery shortfall risk 98%**, **renews in 12 days**
> - **Quill Restaurants (101)** — **$3,397,386** at risk, **risk score 91.70**; contributing factors: **Churn model p=87%**, **delivery shortfall risk 93%**, **renews in 5 days**, **upfront commitment at stake**
> - **Halcyon Retail (061)** — **$3,201,487** at risk, **risk score 95.70**; contributing factors: **Churn model p=100%**, **delivery shortfall risk 98%**, **renews in 17 days**, **upfront commitment at stake**
> - **Polaris Brands (045)** — **$2,991,029** at risk, **risk score 85.70**; contributing factors: **Churn model p=99%**, **delivery shortfall risk 99%**
> Across all 10 advertisers shown, **delivery shortfall risk appears in every case**, and **Retail** is the most common category with **5 of 10** advertisers.

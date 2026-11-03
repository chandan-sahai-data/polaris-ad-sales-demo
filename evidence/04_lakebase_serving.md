# Stage 4 — Lakebase operational serving (synced reads + transactional write-back)

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 06:13:54 UTC by `evidence/capture_evidence.py`._

**Lakebase Autoscaling project + endpoint**

```json
{
  "project": "projects/renewal-actions",
  "display_name": "Polaris Renewal Actions",
  "pg_version": 17,
  "endpoint": "projects/renewal-actions/branches/production/endpoints/primary",
  "endpoint_state": "EndpointStatusState.IDLE"
}
```

**Synced table (Delta → Postgres, CONTINUOUS)**

```json
{
  "name": "synced_tables/cs_genie_research_catalog.ad_sales.lb_advertiser_risk_scores",
  "source": null,
  "scheduling_policy": null,
  "detailed_state": "SYNCED_TABLE_OFFLINE",
  "last_sync": null
}
```

**Postgres read of the synced risk table**

```sql
SELECT risk_tier, count(*) advertisers, round(sum(revenue_at_risk)::numeric,0) revenue_at_risk FROM ad_sales.lb_advertiser_risk_scores GROUP BY risk_tier ORDER BY 3 DESC
```

| risk_tier | advertisers | revenue_at_risk |
|---|---|---|
| Low | 78 | 70386248 |
| Medium | 44 | 66693147 |
| High | 22 | 43444430 |

**Transactional write-back** — inserted `seller_actions.action_id=2` at 2026-11-03 06:14:34.241197+00:00


**Read-back of seller_actions (rows written by the app and by this script)**

```sql
SELECT action_id, advertiser_id, action_type, note, next_connect_date, acted_by, acted_at FROM public.seller_actions ORDER BY action_id
```

| action_id | advertiser_id | action_type | note | next_connect_date | acted_by | acted_at |
|---|---|---|---|---|---|---|
| 1 | ADV0062 | contacted | build verification | 2026-10-21 | build-check | 2026-10-14 19:33:13.514591+00:00 |
| 2 | ADV0040 | snoozed | evidence capture: transactional write-back test | 2026-11-10 | evidence-script | 2026-11-03 06:14:34.241197+00:00 |

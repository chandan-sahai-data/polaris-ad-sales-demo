# Ad Sales Renewal Intelligence — Run of Show (30 min)

**Workspace:** `fevm-cs-genie-research` · **App:** https://ad-sales-renewal-cockpit-7474655804120295.aws.databricksapps.com
**Before you start:** set Databricks **Appearance = Dark**; allow **third-party cookies for `*.cloud.databricks.com`**; **hard-refresh** the app (Cmd+Shift+R).

| Min | Beat | Layer | Surface / action | Say |
|----:|------|-------|------------------|-----|
| 0–2 | **Framing** | — | App open on **Renewal & Risk Insights** | Media-efficiency renewal problem: which advertisers are at risk and why, one surface. |
| 2–7 | **Ingest & govern** | L1 | SDP pipeline graph + metric views | Three source systems → bronze/silver/gold with expectations; CPM/delivery/reach defined **once** in metric views. |
| 7–15 | **Priority grid + drill** | L4 | Dashboard grid → click a High / renews-this-quarter advertiser (Meridian) → drill-through | High×this-quarter cell is the "act-today" cohort; drill shows pacing/Nielsen + contributing factors. |
| 15–23 | **Predict + explain** | L2 | Risk Analytics + Model Health pages | Two trained models — delivery-shortfall **AUC 0.938 (real labels)**, renewal-risk **AUC 0.675 (v1, ~2 qtrs)** → explainable composite; monitored/retrainable. |
| 23–28 | **Ask + act** | L3/L4 | Ask Genie pitch → **Mark contacted** (write-back) | Genie drafts the renewal pitch; write-back to Lakebase proves the loop closes (re-read shows it). |
| 28–30 | **Close** | — | Deal Memory tab | Structured + unstructured, cited; scale-out = managed VS + Knowledge Assistant. |

## The "one number" proof (rehearsed)
Revenue-at-risk **High = $43,444,430** — identical across the **metric view**, the **base table**, the **synced Lakebase table**, and the **app**. Overall CPM **$31.03**, delivery 0.853, sellout 0.674 (600 campaigns).

## Verified this rehearsal (2026-11-03 — see `evidence/`)
- **SDP pipeline** ran clean (update 9d1459, 2026-10-14): bronze×4 → silver×4 (12 expectations, 0 failed) → gold → risk, all COMPLETED.
- **Models** (MLflow + UC): delivery_shortfall AUC 0.938 / P 0.936 / R 0.942 (v1); renewal_risk AUC 0.675 / P 0.632 / R 0.750 / 144 labels (v1).
- **Write-back** persists to Lakebase and reappears on re-read in the app.
- **Genie 3/3 benchmarks reliable**, formatting correct (whole-dollar totals, CPM 2dp, reach 2dp):
  - Q1 QSR track record — CPM $28.12, booked $14,022,024 (via metric view).
  - Q2 Meridian per-campaign delivery — 6 campaigns @ 0.82 (money shot).
  - Q3 reach efficiency by segment — A25-54 296.37.
- **Click-path** API timings (evidence/07): risk grid 0.7s, write-back 0.3s, re-read 0.3s, Deal Memory 1.8s, Genie ~18s. (Embedded dashboard tabs need the AI/BI embedding domain allowlist — see DEPLOYED.md.)

## Tight spot — L3 (Genie latency)
Each Genie call is **~18–27s** (data ops are sub-second). Mitigation:
- **Pre-run Q1** (or open the Genie tab early) so the semantic model is warm before the live moment.
- **Keep Q2 (Meridian) live** — it's the money shot and reliably returns per-campaign detail.
- If a query stalls, the app's Ask Genie tab is the always-dark readable fallback; have the dashboard drill-through as the backup visual.

## Hero
**Meridian Retail (062)** — $3,586,879 revenue-at-risk (risk 91.7, renews in 34 days), 2/2 campaigns behind; Deal Memory corpus is weighted to it (renewal IO, QBR, wrap report).

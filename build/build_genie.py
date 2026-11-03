"""Step 6 — Genie Agent 'Polaris — Ad Sales Renewal Intelligence'.

Scoped to two governed gold sources (advertiser_risk_scores + gold_campaign_advertiser),
both carrying precomputed metrics so answers match the dashboard. Builds a validated
serialized_space (sorted id-keyed arrays), creates the space, and prints the space id.
"""
import json, subprocess, sys
from config import PROFILE, WAREHOUSE, FQ

RISK = f"{FQ}.advertiser_risk_scores"
GOLD = f"{FQ}.gold_campaign_advertiser"
MV   = f"{FQ}.mv_campaign_metrics"
SPACE_ID = "01f1c80529421edaa5212423f9c65124"   # FRESH BUILD: set after `databricks genie create-space`
PARENT = "/Workspace/Users/chandan.sahai@databricks.com/ad_sales_v2/genie"

def sq(items):   # sample_questions sorted by id
    return sorted(items, key=lambda x: x["id"])

serialized = {
    "version": 2,
    "config": {
        "sample_questions": sq([
            {"id": "a1000000000000000000000000000001", "question": ["What's our track record with QSR campaigns over the last two quarters?"]},
            {"id": "a1000000000000000000000000000002", "question": ["Meridian Restaurants came up as elevated renewal risk — summarize their campaign performance and delivery against plan."]},
            {"id": "a1000000000000000000000000000003", "question": ["Which audience segments delivered the best reach efficiency for QSR advertisers?"]},
            {"id": "a1000000000000000000000000000004", "question": ["Show the top 10 high-risk advertisers by revenue at risk with their contributing factors."]},
            {"id": "a1000000000000000000000000000005", "question": ["How many advertisers renew this quarter and how many of those are High risk?"]},
        ])
    },
    "data_sources": {
        "tables": sorted([
            {
                "identifier": RISK,
                "column_configs": sorted([
                    {"column_name": "risk_tier", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Composite renewal-risk tier: High / Medium / Low."]},
                    {"column_name": "renewal_window", "enable_format_assistance": True, "enable_entity_matching": True,
                     "description": ["Renewal timing bucket: renews_this_quarter, renews_next_quarter, already_in_scatter."]},
                    {"column_name": "category", "enable_entity_matching": True, "description": ["Advertiser vertical: Auto, QSR, CPG, Retail, Telco, Pharma."]},
                    {"column_name": "region", "enable_entity_matching": True},
                    {"column_name": "advertiser_name", "enable_entity_matching": True},
                    {"column_name": "risk_score", "description": ["Composite renewal-risk score 0-100 (0.35*churn model + 0.40*delivery-shortfall model + 0.25*renewal urgency)."]},
                    {"column_name": "revenue_at_risk", "description": ["Contract value weighted by risk_score/100 — dollars of book at risk."], "synonyms": ["revenue at risk", "dollars at risk"]},
                    {"column_name": "p_churn", "description": ["Renewal-risk model (Model B) predicted non-renewal probability."]},
                    {"column_name": "adv_p_shortfall", "description": ["Advertiser-level mean delivery-shortfall probability from Model A."]},
                    {"column_name": "contributing_factors", "description": ["Human-readable top risk drivers for the advertiser."]},
                ], key=lambda c: c["column_name"]),
            },
            {
                "identifier": GOLD,
                "column_configs": sorted([
                    {"column_name": "category", "enable_entity_matching": True, "description": ["Advertiser vertical."]},
                    {"column_name": "region", "enable_entity_matching": True},
                    {"column_name": "sales_type", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["upfront vs scatter buy type."]},
                    {"column_name": "daypart", "enable_entity_matching": True, "description": ["Morning / Daytime / Primetime / LateNight."]},
                    {"column_name": "target_demo", "enable_entity_matching": True, "description": ["Nielsen target demographic segment."]},
                    {"column_name": "advertiser_name", "enable_entity_matching": True},
                    {"column_name": "effective_cpm", "description": ["Spend per 1,000 delivered impressions."], "synonyms": ["cpm", "effective cpm"]},
                    {"column_name": "delivery_vs_commitment", "description": ["Delivered impressions / booked impressions (1.0 = fully delivered)."], "synonyms": ["delivery", "pacing to plan"]},
                    {"column_name": "sellout_pct", "description": ["Booked inventory units / available units."], "synonyms": ["sellout"]},
                    {"column_name": "reach_efficiency", "description": ["In-target audience impressions per dollar of spend."], "synonyms": ["reach efficiency"]},
                    {"column_name": "in_target_pct", "description": ["Share of delivered audience in the target demo (Nielsen)."]},
                    {"column_name": "under_delivered", "description": ["1 if the campaign delivered < 95% of booked impressions."]},
                    {"column_name": "adserver_last_refresh", "description": ["Ad-server feed freshness — near real-time."]},
                    {"column_name": "nielsen_last_refresh", "description": ["Nielsen feed freshness — lagged batch (3-7 days stale)."]},
                ], key=lambda c: c["column_name"]),
            },
        ], key=lambda t: t["identifier"]),
        "metric_views": [
            {
                "identifier": MV,
                "column_configs": sorted([
                    {"column_name": "Category", "enable_entity_matching": True, "description": ["Advertiser vertical (governed dimension)."]},
                    {"column_name": "Region", "enable_entity_matching": True},
                    {"column_name": "Sales Type", "enable_format_assistance": True, "enable_entity_matching": True, "description": ["upfront vs scatter."]},
                    {"column_name": "Daypart", "enable_entity_matching": True},
                    {"column_name": "Renewal Window", "enable_format_assistance": True, "enable_entity_matching": True},
                    {"column_name": "Target Demo", "enable_entity_matching": True, "description": ["Nielsen target demographic segment."]},
                    {"column_name": "Advertiser", "enable_entity_matching": True},
                ], key=lambda c: c["column_name"]),
            }
        ],
    },
    "instructions": {
        "example_question_sqls": sorted([
            {"id": "b1000000000000000000000000000001",
             "question": ["What's our track record with QSR campaigns?"],
             "sql": [f"SELECT Category, MEASURE(`Campaigns`) AS campaigns, ROUND(MEASURE(`Delivery vs Commitment`),2) AS delivery_vs_commitment, CONCAT('$', format_number(MEASURE(`Effective CPM`),2)) AS effective_cpm, CONCAT('$', format_number(ROUND(MEASURE(`Booked Spend`),0),0)) AS booked_spend FROM {MV} WHERE Category = 'QSR' GROUP BY Category"],
             "usage_guidance": ["Governed category-level delivery track record via the metric view; swap the Category literal for other verticals. Prefer the metric view for CPM/delivery/sellout/reach efficiency so numbers match the dashboard."]},
            {"id": "b1000000000000000000000000000002",
             "question": ["Summarize an advertiser's campaign performance and delivery against plan."],
             "sql": [f"SELECT campaign_id, ROUND(delivery_vs_commitment,2) AS delivery_vs_commitment, ROUND(pacing_index,2) AS pacing_index, ROUND(in_target_pct,2) AS in_target_pct, ROUND(reach_delivery_pct,2) AS reach_delivery_pct, CONCAT('$', format_number(ROUND(booked_spend,0),0)) AS booked_spend FROM {GOLD} WHERE advertiser_name = 'Meridian Restaurants' ORDER BY delivery_vs_commitment"],
             "usage_guidance": ["Per-campaign delivery detail for one advertiser; use to support a renewal conversation."]},
            {"id": "b1000000000000000000000000000003",
             "question": ["Which audience segments delivered the best reach efficiency for QSR advertisers?"],
             "sql": [f"SELECT `Target Demo`, ROUND(MEASURE(`Reach Efficiency`),2) AS reach_efficiency, MEASURE(`Campaigns`) AS campaigns FROM {MV} WHERE Category = 'QSR' GROUP BY `Target Demo` ORDER BY reach_efficiency DESC"],
             "usage_guidance": ["Governed segment ranking by reach efficiency via the metric view; this is retrieval of what delivered, not a recommendation."]},
            {"id": "b1000000000000000000000000000004",
             "question": ["Top high-risk advertisers by revenue at risk."],
             "sql": [f"SELECT advertiser_name, category, ROUND(risk_score,2) AS risk_score, risk_tier, CONCAT('$', format_number(ROUND(revenue_at_risk,0),0)) AS revenue_at_risk_usd, contributing_factors FROM {RISK} WHERE risk_tier = 'High' ORDER BY {RISK}.revenue_at_risk DESC LIMIT 10"],
             "usage_guidance": ["Renewal-risk priority list with explainable drivers."]},
            {"id": "b1000000000000000000000000000005",
             "question": ["How many advertisers renew this quarter and how many are High risk?"],
             "sql": [f"SELECT renewal_window, COUNT(*) AS advertisers, SUM(CASE WHEN risk_tier='High' THEN 1 ELSE 0 END) AS high_risk, CONCAT('$', format_number(ROUND(SUM(revenue_at_risk),0),0)) AS revenue_at_risk FROM {RISK} GROUP BY renewal_window ORDER BY advertisers DESC"],
             "usage_guidance": ["Renewal-window rollup with High-risk counts and revenue at risk."]},
        ], key=lambda x: x["id"]),
        "text_instructions": [
            {"id": "c1000000000000000000000000000001", "content": [
                "## PURPOSE\n- Answer ad-sales renewal, delivery, and audience questions for the Polaris media book. Users are ad-sales sellers and leadership.\n\n"
                "## DISAMBIGUATION\n- For CPM, delivery-vs-commitment, sellout, pacing, and reach efficiency, use the GOVERNED metric view mv_campaign_metrics via MEASURE() so numbers match the dashboard. Use gold_campaign_advertiser only for per-CAMPAIGN detail (a single advertiser's individual campaigns). Use advertiser_risk_scores for renewal risk (risk_tier / risk_score / revenue_at_risk).\n- 'This quarter' for renewals means renewal_window = 'renews_this_quarter'.\n\n"
                "## DATA QUALITY NOTES\n- mv_campaign_metrics and gold_campaign_advertiser are campaign grain; advertiser_risk_scores is advertiser grain (join on advertiser_id). The renewal-risk model (p_churn) is a v1 trained on ~2 quarters of history — treat it as directional; the delivery-shortfall model has real labels. Nielsen fields are a lagged batch feed (nielsen_last_refresh), ad-server delivery is near real-time (adserver_last_refresh).\n- Metric-view rule: never put MEASURE() in WHERE or GROUP BY; filter/group on dimensions only.\n\n"
                "## NUMBER FORMATTING (always apply)\n- Default: round EVERY numeric value to TWO decimal places (e.g. delivery vs commitment 0.85, pacing 0.88, reach efficiency 160.73, risk score 74.30, in-target 0.82).\n- EXCEPTION — SPEND and REVENUE amounts (booked spend, revenue at risk, total contract value): prefix with a $ sign, use thousand separators, and round to the NEAREST WHOLE DOLLAR (no decimals, no compact M/K). Examples: $46,969,358 ; $302,100,000. Never report these in millions.\n- Effective CPM is a spend rate: prefix with $ and show two decimal places, e.g. $28.12.\n- In generated SQL, format spend/revenue as CONCAT('$', format_number(ROUND(<expr>,0),0)) and round every other numeric column with ROUND(<expr>,2).\n- SORTING: never ORDER BY a $-formatted string column (it sorts as text, e.g. $702,245 above $3,586,879). Give the formatted column a different alias (e.g. revenue_at_risk_usd) and ORDER BY the raw numeric column.\n- Always state whether a number is advertiser-grain or campaign-grain."
            ]}
        ],
    },
    "benchmarks": {"questions": sorted([
        {"id": "d1000000000000000000000000000001", "question": ["What's our track record with QSR campaigns over the last two quarters?"],
         "answer": [{"format": "SQL", "content": [f"SELECT Category, MEASURE(`Campaigns`) AS campaigns, ROUND(MEASURE(`Delivery vs Commitment`),3) AS delivery FROM {MV} WHERE Category='QSR' GROUP BY Category"]}]},
        {"id": "d1000000000000000000000000000002", "question": ["Summarize Meridian Restaurants' campaign performance and delivery against plan."],
         "answer": [{"format": "SQL", "content": []}],
         "evaluation_note": ["Agent should pull per-campaign delivery_vs_commitment and pacing for Meridian Restaurants and note the delivery shortfall + upcoming renewal. Reject if it returns only a single total with no per-campaign detail."]},
        {"id": "d1000000000000000000000000000003", "question": ["Which audience segments delivered the best reach efficiency for QSR advertisers?"],
         "answer": [{"format": "SQL", "content": [f"SELECT `Target Demo`, ROUND(MEASURE(`Reach Efficiency`),2) AS reach_efficiency FROM {MV} WHERE Category='QSR' GROUP BY `Target Demo` ORDER BY reach_efficiency DESC"]}]},
    ], key=lambda x: x["id"])},
}

payload = {
    "serialized_space": json.dumps(serialized),
}
open("genie_payload.json", "w").write(json.dumps(payload))
print("payload written; sources:", MV, RISK, GOLD)

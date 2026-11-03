CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.dash_silver_nielsen AS
SELECT n.campaign_id, n.advertiser_id, a.advertiser_name, n.target_demo, n.planned_reach, n.delivered_reach, ROUND(n.reach_delivery_pct,4) AS reach_delivery_ratio, n.gross_rating_points, n.target_audience_impressions, n.in_target_pct, n.avg_frequency, n.audience_quality_score, n.source_system, n.nielsen_last_refresh AS last_refresh, n._ingested_at, CAST(NULL AS STRING) AS _source_file
FROM cs_genie_research_catalog.ad_sales.silver_nielsen n
LEFT JOIN cs_genie_research_catalog.ad_sales.silver_crm_accounts a ON n.advertiser_id = a.advertiser_id

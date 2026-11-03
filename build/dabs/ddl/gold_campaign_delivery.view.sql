CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.gold_campaign_delivery AS
SELECT advertiser_name, account_owner, campaign_id, category, region, sales_type, daypart,
ROUND(pacing_index,4) AS campaign_pacing_ratio,
CASE WHEN under_delivered=1 THEN 'Under-delivering' WHEN delivery_vs_commitment>=1.0 THEN 'On/Ahead' ELSE 'On track' END AS delivery_status,
booked_spend, ROUND(reach_delivery_pct,4) AS reach_delivery_ratio, in_target_pct, audience_quality_score,
(datediff(current_timestamp(), nielsen_last_refresh) > 2) AS nielsen_is_stale,
ROUND((unix_timestamp(current_timestamp())-unix_timestamp(nielsen_last_refresh))/3600.0,1) AS nielsen_lag_hours,
ROUND((unix_timestamp(current_timestamp())-unix_timestamp(adserver_last_refresh))/3600.0,2) AS adserver_lag_hours
FROM cs_genie_research_catalog.ad_sales.gold_campaign_advertiser

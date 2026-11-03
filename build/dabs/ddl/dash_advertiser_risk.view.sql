CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.dash_advertiser_risk AS
SELECT advertiser_name, account_owner, category, region, risk_tier, renewal_window, days_to_renewal, advertiser_id,
CAST(p_churn AS DOUBLE) AS p_churn, CAST(adv_p_shortfall AS DOUBLE) AS adv_shortfall_risk,
CAST(ROUND(100*p_churn,1) AS DOUBLE) AS renewal_risk_score,
CAST(ROUND(100*adv_p_shortfall,1) AS DOUBLE) AS delivery_risk_score,
CAST(ROUND(100*(1-COALESCE(avg_in_target_pct,0.7)),1) AS DOUBLE) AS audience_risk_score,
CAST(ROUND(CASE WHEN renewal_window='renews_this_quarter' THEN 100*greatest(0,1-days_to_renewal/120.0)
WHEN renewal_window='renews_next_quarter' THEN 45 ELSE 15 END,1) AS DOUBLE) AS renewal_urgency_score,
revenue_at_risk, contract_value AS total_contract_value, risk_score, contributing_factors,
CASE WHEN risk_tier='High' AND renewal_window='renews_this_quarter' THEN 'Escalate — schedule renewal call now'
WHEN risk_tier='High' THEN 'Prioritize outreach + make-good plan'
WHEN risk_tier='Medium' THEN 'Monitor delivery; proactive check-in' ELSE 'Maintain' END AS recommended_action
FROM cs_genie_research_catalog.ad_sales.advertiser_risk_scores

CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.dash_model_health AS
SELECT 'delivery_shortfall_model' AS model, 'auc' AS metric, 0.938 AS value
UNION ALL SELECT 'renewal_risk_model','auc',0.694
UNION ALL SELECT 'delivery_shortfall_model','predicted_shortfall_rate',(SELECT ROUND(avg_pred,4) FROM cs_genie_research_catalog.ad_sales.ml_model_monitoring LIMIT 1)
UNION ALL SELECT 'delivery_shortfall_model','actual_shortfall_rate',(SELECT ROUND(actual_rate,4) FROM cs_genie_research_catalog.ad_sales.ml_model_monitoring LIMIT 1)

CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.silver_deals AS
SELECT d.deal_id, d.advertiser_id, a.advertiser_name, d.stage, d.contract_value, d.deal_start, d.deal_end, d.renewal_date, d.upfront_commit_flag, d.renewal_window, d.source_system, d.last_refresh, d._ingested_at, d.days_to_renewal
FROM cs_genie_research_catalog.ad_sales.silver_crm_deals d LEFT JOIN cs_genie_research_catalog.ad_sales.silver_crm_accounts a ON d.advertiser_id=a.advertiser_id
WHERE d.is_historical=false

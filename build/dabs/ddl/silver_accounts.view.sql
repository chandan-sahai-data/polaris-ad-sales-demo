CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.silver_accounts AS
SELECT advertiser_id, advertiser_name, category, region, account_owner, source_system, crm_last_refresh AS last_refresh, _ingested_at
FROM cs_genie_research_catalog.ad_sales.silver_crm_accounts

CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.mv_advertiser_renewal
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: cs_genie_research_catalog.ad_sales.dash_advertiser_risk
comment: "Governed advertiser-grain renewal-risk metrics for the cockpit dashboard and Genie."
dimensions:
  - name: Advertiser
    expr: advertiser_name
  - name: Account Owner
    expr: account_owner
  - name: Category
    expr: category
  - name: Region
    expr: region
  - name: Risk Tier
    expr: risk_tier
  - name: Renewal Window
    expr: renewal_window
  - name: Days to Renewal
    expr: days_to_renewal
  - name: Recommended Action
    expr: recommended_action
measures:
  - name: Revenue at Risk
    expr: SUM(revenue_at_risk)
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
      hide_group_separator: false
  - name: Total Contract Value
    expr: SUM(total_contract_value)
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
      hide_group_separator: false
  - name: Avg Renewal Risk Score
    expr: AVG(renewal_risk_score)
  - name: Avg Delivery Risk Score
    expr: AVG(delivery_risk_score)
  - name: Avg Audience Risk Score
    expr: AVG(audience_risk_score)
  - name: Avg Renewal Urgency Score
    expr: AVG(renewal_urgency_score)
$$

CREATE OR REPLACE VIEW cs_genie_research_catalog.ad_sales.mv_campaign_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: cs_genie_research_catalog.ad_sales.gold_campaign_advertiser
comment: "Governed ad-sales delivery & efficiency metrics — defined once, consumed by dashboard, Genie and the risk model."
dimensions:
  - name: Advertiser
    expr: advertiser_name
  - name: Category
    expr: category
  - name: Region
    expr: region
  - name: Sales Type
    expr: sales_type
  - name: Daypart
    expr: daypart
  - name: Renewal Window
    expr: renewal_window
  - name: Target Demo
    expr: target_demo
    comment: "Nielsen target demographic segment"
measures:
  - name: Campaigns
    expr: COUNT(1)
  - name: Booked Spend
    expr: SUM(booked_spend)
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 0
      hide_group_separator: false
  - name: Sellout Pct
    expr: SUM(inventory_units_booked) / SUM(inventory_units_available)
    comment: "Booked inventory units / available units"
  - name: Effective CPM
    expr: SUM(booked_spend) / (SUM(delivered_impressions) / 1000.0)
    comment: "Spend per thousand delivered impressions"
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      hide_group_separator: false
  - name: Pacing Index
    expr: AVG(pacing_index)
    comment: "Mean campaign pacing (delivered / booked); 1.0 = on pace"
  - name: Delivery vs Commitment
    expr: SUM(delivered_impressions) / SUM(booked_impressions)
    comment: "Delivered impressions / booked impressions"
  - name: Reach Efficiency
    expr: SUM(target_audience_impressions) / SUM(booked_spend)
    comment: "In-target audience impressions per dollar of spend"
    format:
      type: number
      decimal_places:
        type: exact
        places: 2
      hide_group_separator: false
$$

"""Step 7 — two native AI/BI (Lakeview) dashboards, mirroring the prior build's structure
(sa_ad_sales_demo_prep/dashboard.json): a Renewal & Risk dashboard and an Ad Sales dashboard.
Delivery/efficiency widgets read the GOVERNED metric view (MEASURE); risk/ML read the gold tables.
Creates + publishes both and prints their IDs.
"""
import json, subprocess, uuid
from config import PROFILE, WAREHOUSE, CATALOG, SCHEMA

PARENT = "/Workspace/Users/chandan.sahai@databricks.com/ad_sales_v2/dashboards"

THEME = {"theme": {
    "canvasBackgroundColor": {"light": "#0f1420", "dark": "#0f1420"},
    "widgetBackgroundColor": {"light": "#121826", "dark": "#121826"},
    "widgetBorderColor": {"light": "#1e2836", "dark": "#1e2836"},
    "fontColor": {"light": "#e6ebf2", "dark": "#e6ebf2"},
    "selectionColor": {"light": "#4ea1ff", "dark": "#4ea1ff"},
    "visualizationColors": ["#4ea1ff", "#ff5470", "#ffb020", "#3ad29f", "#995495", "#5ADBFF", "#FF7054"],
    "widgetHeaderAlignment": "LEFT", "fontFamily": "Inter"}}

# ---- widget helpers ----
def pos(x, y, w, h): return {"x": x, "y": y, "width": w, "height": h}

def text(md, x, y, w, h):
    return {"widget": {"name": "t"+uuid.uuid4().hex[:8],
        "multilineTextboxSpec": {"lines": [md]}}, "position": pos(x, y, w, h)}

def counter(ds, fname, fexpr, title, x, y, w, h, fmt=None, disagg=True):
    val = {"fieldName": fname, "displayName": title}
    if fmt: val["format"] = fmt
    return {"widget": {"name": "c"+uuid.uuid4().hex[:8],
        "queries": [{"name": "main_query", "query": {"datasetName": ds,
            "fields": [{"name": fname, "expression": fexpr}], "disaggregated": disagg}}],
        "spec": {"version": 2, "widgetType": "counter",
            "encodings": {"value": val}, "frame": {"title": title, "showTitle": True}}},
        "position": pos(x, y, w, h)}

def bar(ds, xf, xexpr, yf, yexpr, title, x, y, w, h, color=None, orders=None, horiz=False):
    q = {"datasetName": ds, "fields": [{"name": xf, "expression": xexpr}, {"name": yf, "expression": yexpr}], "disaggregated": False}
    if color: q["fields"].append({"name": color, "expression": f"`{color}`"})
    if orders: q["orders"] = orders
    enc = {"x": {"fieldName": xf, "scale": {"type": "categorical"}},
           "y": {"fieldName": yf, "scale": {"type": "quantitative"}}}
    if color: enc["color"] = {"fieldName": color, "scale": {"type": "categorical"}}
    return {"widget": {"name": "b"+uuid.uuid4().hex[:8],
        "queries": [{"name": "main_query", "query": q}],
        "spec": {"version": 3, "widgetType": "bar", "encodings": enc,
            "frame": {"title": title, "showTitle": True}}}, "position": pos(x, y, w, h)}

def table(ds, cols, title, x, y, w, h):
    fields = [{"name": c[0], "expression": f"`{c[0]}`"} for c in cols]
    enc_cols = []
    for c in cols:
        col = {"fieldName": c[0], "displayName": c[1]}
        if len(c) > 2 and c[2]: col["format"] = c[2]
        enc_cols.append(col)
    return {"widget": {"name": "tb"+uuid.uuid4().hex[:8],
        "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": fields, "disaggregated": True}}],
        "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": enc_cols},
            "frame": {"title": title, "showTitle": True}}}, "position": pos(x, y, w, h)}

def scatter(ds, xf, yf, color, size, title, x, y, w, h):
    fields = [{"name": xf, "expression": f"`{xf}`"}, {"name": yf, "expression": f"`{yf}`"},
              {"name": color, "expression": f"`{color}`"}, {"name": size, "expression": f"`{size}`"},
              {"name": "advertiser_name", "expression": "`advertiser_name`"}]
    enc = {"x": {"fieldName": xf, "scale": {"type": "quantitative"}, "displayName": "Churn probability"},
           "y": {"fieldName": yf, "scale": {"type": "quantitative"}, "displayName": "Revenue at risk"},
           "color": {"fieldName": color, "scale": {"type": "categorical",
               "mappings": [{"value": "High", "color": "#ff5470"}, {"value": "Medium", "color": "#ffb020"}, {"value": "Low", "color": "#3ad29f"}]}},
           "size": {"fieldName": size, "scale": {"type": "quantitative"}}}
    return {"widget": {"name": "s"+uuid.uuid4().hex[:8],
        "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": fields, "disaggregated": True}}],
        "spec": {"version": 3, "widgetType": "scatter", "encodings": enc,
            "frame": {"title": title, "showTitle": True}}}, "position": pos(x, y, w, h)}

def histogram(ds, field, binw, title, x, y, w, h):
    return {"widget": {"name": "h"+uuid.uuid4().hex[:8],
        "queries": [{"name": "main_query", "query": {"datasetName": ds,
            "fields": [{"name": f"bin({field})", "expression": f"BIN_FLOOR(`{field}`, {binw})"},
                       {"name": "count(*)", "expression": "COUNT(`*`)"}], "disaggregated": False}}],
        "spec": {"version": 3, "widgetType": "histogram",
            "encodings": {"x": {"fieldName": f"bin({field})", "scale": {"type": "quantitative"}},
                          "y": {"fieldName": "count(*)", "scale": {"type": "quantitative"}}},
            "frame": {"title": title, "showTitle": True}}}, "position": pos(x, y, w, h)}

def heatmap(ds, xf, yf, cf, title, x, y, w, h):
    return {"widget": {"name": "hm"+uuid.uuid4().hex[:8],
        "queries": [{"name": "main_query", "query": {"datasetName": ds,
            "fields": [{"name": xf, "expression": f"`{xf}`"}, {"name": yf, "expression": f"`{yf}`"},
                       {"name": cf, "expression": f"`{cf}`"}], "disaggregated": False}}],
        "spec": {"version": 3, "widgetType": "heatmap",
            "encodings": {"x": {"fieldName": xf, "scale": {"type": "categorical"}},
                          "y": {"fieldName": yf, "scale": {"type": "categorical"}},
                          "color": {"fieldName": cf, "scale": {"type": "quantitative",
                              "colorRamp": {"mode": "custom-sequential", "colors": {"start": "#1D425C", "end": "#ff5470"}}}},
                          "label": {"show": True}},
            "frame": {"title": title, "showTitle": True}}}, "position": pos(x, y, w, h)}

def page(name, disp, layout):
    return {"name": name, "displayName": disp, "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1", "layout": layout}

USD0 = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
NUM0 = {"type": "number-plain", "decimalPlaces": {"type": "exact", "places": 0}}
NUM1 = {"type": "number-plain", "decimalPlaces": {"type": "max", "places": 1}}
PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}

# ============================ RENEWAL & RISK dashboard ============================
rr_datasets = [
    {"name": "ds_kpi", "displayName": "KPIs", "queryLines": [
        "SELECT SUM(contract_value) AS book, ",
        "SUM(CASE WHEN risk_tier='High' THEN revenue_at_risk ELSE 0 END) AS rev_at_risk_high, ",
        "SUM(CASE WHEN risk_tier='High' THEN 1 ELSE 0 END) AS high_ct, ",
        "SUM(CASE WHEN renewal_window='renews_this_quarter' THEN 1 ELSE 0 END) AS renew_q, ",
        "SUM(CASE WHEN risk_tier='High' AND renewal_window='renews_this_quarter' THEN 1 ELSE 0 END) AS act_today ",
        "FROM advertiser_risk_scores"]},
    {"name": "ds_risk", "displayName": "Advertiser risk", "queryLines": [
        "SELECT advertiser_id, advertiser_name, category, region, risk_score, risk_tier, revenue_at_risk, ",
        "contract_value, renewal_window, days_to_renewal, campaign_count, campaigns_behind, ",
        "shortfall_rate, p_churn, adv_p_shortfall, contributing_factors ",
        "FROM advertiser_risk_scores"]},
    {"name": "ds_grid", "displayName": "Risk grid", "queryLines": [
        "SELECT risk_tier, ",
        "CASE renewal_window WHEN 'renews_this_quarter' THEN '1 · This quarter' WHEN 'renews_next_quarter' THEN '2 · Next quarter' ELSE '3 · In scatter' END AS renewal_window, ",
        "COUNT(*) AS advertisers, SUM(revenue_at_risk) AS rev_at_risk ",
        "FROM advertiser_risk_scores GROUP BY 1,2"]},
    {"name": "ds_shortfall", "displayName": "Campaign shortfall", "queryLines": [
        "SELECT p_shortfall, under_delivered FROM ml_campaign_shortfall_scores"]},
    {"name": "ds_monitor", "displayName": "Model monitoring", "queryLines": [
        "SELECT 'Predicted shortfall' AS metric, avg_pred AS val FROM ml_model_monitoring ",
        "UNION ALL SELECT 'Actual shortfall', actual_rate FROM ml_model_monitoring"]},
    {"name": "ds_cat_risk", "displayName": "Risk by category", "queryLines": [
        "SELECT category, SUM(revenue_at_risk) AS rev_at_risk, SUM(campaigns_behind) AS behind ",
        "FROM advertiser_risk_scores GROUP BY category ORDER BY rev_at_risk DESC"]},
]

cockpit = [
    text("# Polaris · Renewal & Risk Cockpit\nComposite renewal-risk from two UC-registered models (delivery-shortfall + churn) blended with renewal urgency. The **High risk × renews-this-quarter** cohort is the act-today book.", 0, 0, 12, 2),
    counter("ds_kpi", "book", "`book`", "Total book", 0, 2, 3, 3, USD0),
    counter("ds_kpi", "rev_at_risk_high", "`rev_at_risk_high`", "Revenue at risk (High)", 3, 2, 3, 3, USD0),
    counter("ds_kpi", "high_ct", "`high_ct`", "High-risk advertisers", 6, 2, 2, 3, NUM0),
    counter("ds_kpi", "renew_q", "`renew_q`", "Renew this quarter", 8, 2, 2, 3, NUM0),
    counter("ds_kpi", "act_today", "`act_today`", "Act today", 10, 2, 2, 3, NUM0),
    heatmap("ds_grid", "renewal_window", "risk_tier", "advertisers", "Priority grid — risk tier × renewal window (act-today cell pops)", 0, 5, 6, 5),
    bar("ds_cat_risk", "category", "`category`", "rev_at_risk", "SUM(`rev_at_risk`)", "Revenue at risk by category", 6, 5, 6, 5,
        orders=[{"direction": "DESC", "expression": "SUM(`rev_at_risk`)"}]),
    table("ds_risk", [["advertiser_name", "Advertiser"], ["category", "Category"], ["risk_tier", "Tier"],
                      ["risk_score", "Score", NUM1], ["revenue_at_risk", "Rev at risk", USD0],
                      ["renewal_window", "Renewal"], ["contributing_factors", "Drivers"]],
          "High-risk advertisers & drivers", 0, 10, 12, 7),
]
risk_analytics = [
    text("# Risk Analytics\nChurn probability × revenue at risk, sized by composite score. Top-right = highest-value churn risk.", 0, 0, 12, 2),
    scatter("ds_risk", "p_churn", "revenue_at_risk", "risk_tier", "risk_score", "Churn risk × revenue at risk (size = score)", 0, 2, 8, 7),
    bar("ds_cat_risk", "category", "`category`", "behind", "SUM(`behind`)", "Campaigns behind by category", 8, 2, 4, 7,
        orders=[{"direction": "DESC", "expression": "SUM(`behind`)"}]),
]
delivery_risk = [
    text("# Delivery Risk (Model A · delivery-shortfall classifier)\nPer-campaign predicted probability of delivering < 95% of booked impressions. AUC 0.938 on real labels.", 0, 0, 12, 2),
    histogram("ds_shortfall", "p_shortfall", 0.05, "Distribution of campaign shortfall probability", 0, 2, 8, 6),
    counter("ds_shortfall", "avg(p_shortfall)", "AVG(`p_shortfall`)", "Mean shortfall probability", 8, 2, 4, 3, PCT, disagg=False),
]
model_health = [
    text("# Model Health\n**Model A — delivery-shortfall:** AUC **0.938** (real labels, campaign grain, retrain weekly).\n**Model B — renewal-risk:** AUC **0.731** (v1 on ~2 quarters of churn labels, advertiser grain, retrain quarterly).\nMonitoring compares predicted vs actual shortfall at flight end.", 0, 0, 12, 3),
    bar("ds_monitor", "metric", "`metric`", "val", "SUM(`val`)", "Predicted vs actual shortfall rate (Model A)", 0, 3, 6, 5),
]
rr = {"datasets": rr_datasets, "pages": [
    page("cockpit", "Renewal Cockpit", cockpit),
    page("risk_analytics", "Risk Analytics", risk_analytics),
    page("delivery_risk", "Delivery Risk", delivery_risk),
    page("model_health", "Model Health", model_health)],
    "uiSettings": {**THEME, "genieSpace": {"isEnabled": True, "overrideId": "01f1ae391641100a8c0331c61624c4c6", "enablementMode": "ENABLED"}}}

# ============================ AD SALES dashboard (metric view) ============================
as_datasets = [
    {"name": "ds_mv_cat", "displayName": "By category (metric view)", "queryLines": [
        "SELECT Category AS category, ROUND(MEASURE(`Delivery vs Commitment`),3) AS delivery, ",
        "ROUND(MEASURE(`Effective CPM`),2) AS eff_cpm, ROUND(MEASURE(`Sellout Pct`),3) AS sellout, ",
        "MEASURE(`Campaigns`) AS campaigns, ROUND(MEASURE(`Booked Spend`),0) AS booked_spend ",
        "FROM mv_campaign_metrics GROUP BY Category"]},
    {"name": "ds_mv_demo", "displayName": "Reach efficiency by segment", "queryLines": [
        "SELECT `Target Demo` AS target_demo, ROUND(MEASURE(`Reach Efficiency`),1) AS reach_eff, ",
        "MEASURE(`Campaigns`) AS campaigns FROM mv_campaign_metrics GROUP BY `Target Demo` ORDER BY reach_eff DESC"]},
    {"name": "ds_mv_region", "displayName": "By region (metric view)", "queryLines": [
        "SELECT Region AS region, ROUND(MEASURE(`Delivery vs Commitment`),3) AS delivery, ",
        "ROUND(MEASURE(`Effective CPM`),2) AS eff_cpm, ROUND(MEASURE(`Sellout Pct`),3) AS sellout, ",
        "MEASURE(`Campaigns`) AS campaigns FROM mv_campaign_metrics GROUP BY Region ORDER BY delivery"]},
    {"name": "ds_fresh", "displayName": "Feed freshness", "queryLines": [
        "SELECT round(avg(datediff(current_timestamp(), nielsen_last_refresh)),1) AS nielsen_lag_days, ",
        "round(avg((unix_timestamp(current_timestamp()) - unix_timestamp(adserver_last_refresh))/3600.0),2) AS adserver_lag_hours ",
        "FROM gold_campaign_advertiser"]},
    {"name": "ds_camp", "displayName": "Campaign detail", "queryLines": [
        "SELECT campaign_id, advertiser_name, category, region, sales_type, daypart, ",
        "ROUND(delivery_vs_commitment,3) AS delivery, ROUND(effective_cpm,2) AS eff_cpm, ",
        "ROUND(in_target_pct,3) AS in_target, booked_spend FROM gold_campaign_advertiser"]},
]
delivery_eff = [
    text("# Polaris · Ad Sales Delivery & Efficiency\nAll delivery, CPM, sellout and reach-efficiency numbers below are computed from the **governed metric view** `mv_campaign_metrics` — the same definitions Genie and the risk model use.", 0, 0, 12, 2),
    bar("ds_mv_cat", "category", "`category`", "delivery", "AVG(`delivery`)", "Delivery vs commitment by category", 0, 2, 6, 5,
        orders=[{"direction": "ASC", "expression": "AVG(`delivery`)"}]),
    bar("ds_mv_cat", "category", "`category`", "eff_cpm", "AVG(`eff_cpm`)", "Effective CPM by category", 6, 2, 6, 5),
    bar("ds_mv_demo", "target_demo", "`target_demo`", "reach_eff", "AVG(`reach_eff`)", "Reach efficiency by audience segment", 0, 7, 6, 5,
        orders=[{"direction": "DESC", "expression": "AVG(`reach_eff`)"}]),
    table("ds_mv_region", [["region", "Region"], ["delivery", "Delivery", NUM1], ["eff_cpm", "Eff CPM", {"type": "number-currency", "currencyCode": "USD", "decimalPlaces": {"type": "exact", "places": 2}}], ["sellout", "Sellout", NUM1], ["campaigns", "Campaigns", NUM0]],
          "Delivery & efficiency by region (governed)", 6, 7, 6, 5),
]
freshness = [
    text("# Data Freshness — live vs batch\nAd-server delivery is a near-real-time signal; Nielsen measurement is a lagged batch feed. This is the live-vs-batch honesty beat.", 0, 0, 12, 2),
    counter("ds_fresh", "adserver_lag_hours", "`adserver_lag_hours`", "Ad-server feed lag (hours)", 0, 2, 6, 3, NUM1),
    counter("ds_fresh", "nielsen_lag_days", "`nielsen_lag_days`", "Nielsen feed lag (days)", 6, 2, 6, 3, NUM1),
]
campaign_detail = [
    text("# Campaign Detail\nPer-campaign delivery, CPM and in-target audience across the book.", 0, 0, 12, 2),
    table("ds_camp", [["campaign_id", "Campaign"], ["advertiser_name", "Advertiser"], ["category", "Cat"],
                      ["region", "Region"], ["sales_type", "Buy"], ["daypart", "Daypart"],
                      ["delivery", "Delivery", NUM1], ["eff_cpm", "Eff CPM", {"type": "number-currency", "currencyCode": "USD", "decimalPlaces": {"type": "exact", "places": 2}}],
                      ["in_target", "In-target", NUM1], ["booked_spend", "Spend", USD0]],
          "Campaigns", 0, 2, 12, 8),
]
adsales = {"datasets": as_datasets, "pages": [
    page("delivery_eff", "Delivery & Efficiency", delivery_eff),
    page("freshness", "Data Freshness", freshness),
    page("campaign_detail", "Campaign Detail", campaign_detail)],
    "uiSettings": THEME}

# ============================ create + publish ============================
def create(title, payload):
    open(f"/tmp/{title.replace(' ','_')}.json", "w").write(json.dumps(payload))
    out = subprocess.run(["databricks", "lakeview", "create", "--display-name", title,
        "--warehouse-id", WAREHOUSE, "--dataset-catalog", CATALOG, "--dataset-schema", SCHEMA,
        "--serialized-dashboard", json.dumps(payload), "--json", json.dumps({"parent_path": PARENT}),
        "-p", PROFILE, "-o", "json"], capture_output=True, text=True)
    try:
        did = json.loads(out.stdout)["dashboard_id"]
    except Exception:
        print("CREATE FAILED:", title); print(out.stdout[:800]); print(out.stderr[:800]); raise
    subprocess.run(["databricks", "lakeview", "publish", did, "--warehouse-id", WAREHOUSE, "-p", PROFILE],
                   capture_output=True, text=True)
    print(f"{title}: {did}")
    return did

subprocess.run(["databricks", "workspace", "mkdirs", PARENT, "-p", PROFILE], capture_output=True, text=True)
open("/tmp/dash_rr.json", "w").write(json.dumps(rr))
open("/tmp/dash_as.json", "w").write(json.dumps(adsales))
rr_id = create("Polaris — Renewal & Risk Insights", rr)
as_id = create("Polaris — Ad Sales Insights", adsales)
print("RR_DASHBOARD_ID=" + rr_id)
print("AS_DASHBOARD_ID=" + as_id)

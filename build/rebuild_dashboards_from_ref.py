"""Rebuild the two AI/BI dashboards by faithfully reusing the reference dashboard.json
(./reference/dashboard.json in this fresh-build folder) — same pages/widgets/layout/theme —
remapping only the dataset table names onto this build's compatibility views, applying the
number formats, the Account Owner filter, and the explorer tweaks. Splits into Renewal&Risk +
Ad Sales and UPDATES the existing dashboard IDs in place, then publishes. Compare the result
to ./reference/GOLDEN_*.json.
"""
import json, subprocess, sys, os
from config import PROFILE, WAREHOUSE, CATALOG, SCHEMA

# Self-contained reference lives next to this build (../reference/dashboard.json is the plain
# combined base; ../reference/GOLDEN_*.json are the polished deployed dashboards to match).
REF = os.path.join(os.path.dirname(__file__), "..", "reference", "dashboard.json")
# FRESH BUILD: create the two dashboards once (lakeview create), then paste their ids here so
# this script UPDATES them in place. GENIE = the space id created in step 6.
RR_ID = "01f1c805646d10c7bc4b13e6270abd37"   # Renewal & Risk Insights
AS_ID = "01f1c805651b10ad9a2ffccdcc8219f0"   # Ad Sales Insights
GENIE = "01f1c80529421edaa5212423f9c65124"
RR_PAGES = {"cockpit", "filters", "risk_analytics", "delivery_risk", "model_health"}

REMAP = [
    ("ad_sales_demo.ad_sales.silver_accounts", "silver_accounts"),
    ("ad_sales_demo.ad_sales.silver_deals", "silver_deals"),
    ("ad_sales_demo.ad_sales.silver_nielsen", "dash_silver_nielsen"),
    ("ad_sales_demo.ad_sales.", ""),
    ("FROM advertiser_risk_scores", "FROM dash_advertiser_risk"),
    ("FROM ml_model_monitoring", "FROM dash_model_health"),
]

def remap(sql):
    for a, b in REMAP:
        sql = sql.replace(a, b)
    return sql

sd = json.load(open(REF))

# remap dataset queries in place
for d in sd["datasets"]:
    d["queryLines"] = [remap(l) for l in d["queryLines"]]

# --- expose account_owner in the RR datasets so the Account Owner global filter can bind ---
# Both source objects (mv_advertiser_renewal / dash_advertiser_risk / gold_campaign_delivery)
# already carry account_owner; inject the column into each dataset's SELECT list.
def add_account_owner_columns(sd):
    # ds_adv reads the metric view with positional GROUP BY 1..7 — add Account Owner as the
    # 8th dimension (after Recommended Action) and extend the GROUP BY, so positions stay aligned.
    repl = {
        "ds_adv":          ("`Recommended Action` AS recommended_action,",
                            "`Recommended Action` AS recommended_action, `Account Owner` AS account_owner,"),
        "ds_camp":         ("SELECT advertiser_name AS advertiser,", "SELECT account_owner, advertiser_name AS advertiser,"),
        "ds_ml_risk":      ("SELECT advertiser_name,", "SELECT account_owner, advertiser_name,"),
        "ds_ml_campshort": ("SELECT s.campaign_id, c.advertiser_name,", "SELECT c.account_owner, s.campaign_id, c.advertiser_name,"),
        "ds_ml_decomp":    ("SELECT advertiser_name, p_churn,", "SELECT advertiser_name, account_owner, p_churn,"),
    }
    for d in sd["datasets"]:
        if d["name"] in repl:
            old, new = repl[d["name"]]
            q = "".join(d["queryLines"])
            assert old in q, f"account_owner anchor not found in {d['name']}: {q[:120]}"
            d["queryLines"] = [q.replace(old, new, 1)]
    for d in sd["datasets"]:
        q = "".join(d["queryLines"])
        if d["name"] == "ds_adv":
            q = q.replace("GROUP BY 1,2,3,4,5,6,7", "GROUP BY 1,2,3,4,5,6,7,8", 1)
        elif d["name"] == "ds_ml_decomp":
            # thread account_owner through the outer SELECT off the CTE
            q = q.replace("SELECT advertiser_name, driver, contribution FROM top",
                          "SELECT advertiser_name, account_owner, driver, contribution FROM top", 1)
        else:
            continue
        d["queryLines"] = [q]
add_account_owner_columns(sd)

# --- cascade the global filters onto the ML datasets (Risk Analytics / Delivery Risk) ---
# The reference binds each filter only to ds_adv/ds_camp, so the ML pages never get filtered.
# Add each filter's field to the ML datasets that carry the same column.
FILTER_EXTRA = {
    "advertiser":     [("ds_ml_risk", "advertiser_name"), ("ds_ml_campshort", "advertiser_name"), ("ds_ml_decomp", "advertiser_name")],
    "risk_tier":      [("ds_ml_risk", "risk_tier")],
    "renewal_window": [("ds_ml_risk", "renewal_window")],
    "category":       [("ds_ml_risk", "category"), ("ds_ml_campshort", "category")],
    "account_owner":  [("ds_ml_risk", "account_owner"), ("ds_ml_campshort", "account_owner"), ("ds_ml_decomp", "account_owner")],
}

# --- add an Account Owner global filter (binds ds_adv + ds_camp; cascades via FILTER_EXTRA) ---
def add_account_owner_filter(sd):
    widget = {"widget": {"name": "f_owner",
        "queries": [
            {"name": "fo1", "query": {"datasetName": "ds_adv",
                "fields": [{"name": "account_owner", "expression": "`account_owner`"}], "disaggregated": False}},
            {"name": "fo2", "query": {"datasetName": "ds_camp",
                "fields": [{"name": "account_owner", "expression": "`account_owner`"}], "disaggregated": False}}],
        "spec": {"version": 2, "widgetType": "filter-multi-select",
            "encodings": {"fields": [
                {"fieldName": "account_owner", "queryName": "fo1", "displayName": "Account Owner"},
                {"fieldName": "account_owner", "queryName": "fo2"}]},
            "frame": {"showTitle": True, "title": "Account Owner"}}},
        "position": {"x": 0, "y": 2, "width": 3, "height": 2}}
    for p in sd["pages"]:
        if p.get("name") == "filters":
            p["layout"].append(widget)
add_account_owner_filter(sd)
def wire_global_filters(sd):
    for p in sd["pages"]:
        if p.get("name") != "filters":
            continue
        for it in p["layout"]:
            w = it["widget"]; sp = w.get("spec", {})
            enc = sp.get("encodings", {}).get("fields")
            if not enc:
                continue
            primary = enc[0]["fieldName"]
            for j, (ds, col) in enumerate(FILTER_EXTRA.get(primary, [])):
                qn = f"{w['name']}_ml{j}"
                w.setdefault("queries", []).append(
                    {"name": qn, "query": {"datasetName": ds,
                        "fields": [{"name": col, "expression": f"`{col}`"}], "disaggregated": False}})
                enc.append({"fieldName": col, "queryName": qn})
wire_global_filters(sd)

# --- per-page filter customizations ---
def _filter_widget(name, ds, col, title, x, y, w=4, h=2):
    qn = f"{name}_q"
    return {"widget": {"name": name, "queries": [{"name": qn, "query": {"datasetName": ds,
                "fields": [{"name": col, "expression": f"`{col}`"},
                           {"name": f"{col}_associativity", "expression": "COUNT_IF(`associative_filter_predicate_group`)"}],
                "disaggregated": False}}],
            "spec": {"version": 2, "widgetType": "filter-multi-select",
                     "frame": {"showTitle": True, "title": title},
                     "encodings": {"fields": [{"fieldName": col, "queryName": qn}]}}},
            "position": {"x": x, "y": y, "width": w, "height": h}}

# --- currency formatting for every money/CPM widget field ---
# User requirement: money renders with a $ sign and thousand separators. In tables/charts,
# rounded to WHOLE dollars, no compact abbreviation (e.g. $45,600,000). In SUMMARY CARDS
# (the KPI counter tiles), keep it compact — millions/thousands as appropriate — at ONE
# decimal (e.g. $45.6M). Walk every widget encoding and stamp the right format by widget type.
CURRENCY_FMT = {"type": "number-currency", "currencyCode": "USD",
                "abbreviation": "none", "hideGroupSeparator": False,
                "decimalPlaces": {"type": "exact", "places": 0}}
# Summary-card (counter) format: compact K/M/B, one decimal place.
COMPACT_FMT = {"type": "number-currency", "currencyCode": "USD",
               "abbreviation": "compact", "hideGroupSeparator": False,
               "decimalPlaces": {"type": "exact", "places": 1}}
# Reach metric (efficiency / delivery ratio): plain number, two decimal places.
REACH_FMT = {"type": "number", "hideGroupSeparator": False,
             "decimalPlaces": {"type": "exact", "places": 2}}

def _is_reach_field(fieldname):
    if not fieldname:
        return False
    base = fieldname.lower().strip()
    for agg in ("sum(", "avg(", "min(", "max("):
        if base.startswith(agg) and base.endswith(")"):
            base = base[len(agg):-1]
            break
    base = base.strip("`")
    # ratio/efficiency reach metrics only — NOT raw reach counts (delivered_reach/planned_reach)
    return "reach" in base and ("ratio" in base or "efficiency" in base)

def _is_money_field(fieldname):
    if not fieldname:
        return False
    # strip an aggregate wrapper like sum(...)/avg(...) and backticks
    base = fieldname.lower().strip()
    for agg in ("sum(", "avg(", "min(", "max("):
        if base.startswith(agg) and base.endswith(")"):
            base = base[len(agg):-1]
            break
    base = base.strip("`")
    return (base in ("revenue_at_risk", "contract_value", "booked_spend")
            or "cpm" in base or base.endswith("_spend") or "revenue" in base)

def apply_number_formats(sd):
    def stamp(fo, wt):
        fn = fo.get("fieldName") or fo.get("name")
        if _is_money_field(fn):
            # summary cards (counters) get compact 1dp; everything else whole-dollar
            fo["format"] = dict(COMPACT_FMT if wt == "counter" else CURRENCY_FMT)
        elif _is_reach_field(fn):
            fo["format"] = dict(REACH_FMT)
    for p in sd["pages"]:
        for it in p.get("layout", []):
            spec = it.get("widget", {}).get("spec", {})
            wt = spec.get("widgetType")
            enc = spec.get("encodings", {})
            for k in ("value", "target"):
                if isinstance(enc.get(k), dict):
                    stamp(enc[k], wt)
            for c in enc.get("columns", []) or []:
                stamp(c, wt)
            for ax in ("x", "y", "color", "size", "angle", "label"):
                a = enc.get(ax)
                if isinstance(a, dict):
                    stamp(a, wt)
                elif isinstance(a, list):
                    for aa in a:
                        stamp(aa, wt)

def customize_pages(sd):
    for p in sd["pages"]:
        # Deals Explorer: replace the Advertiser ID filter with Advertiser Name
        if p.get("name") == "silver_deals":
            for it in p["layout"]:
                sp = it["widget"].get("spec", {})
                if sp.get("widgetType", "").startswith("filter") and (sp.get("frame") or {}).get("title") == "Advertiser ID":
                    for q in it["widget"]["queries"]:
                        for f in q["query"]["fields"]:
                            if f["name"] == "advertiser_id":
                                f["name"] = "advertiser_name"; f["expression"] = "`advertiser_name`"
                    sp["frame"]["title"] = "Advertiser"
                    for e in sp["encodings"]["fields"]:
                        if e["fieldName"] == "advertiser_id":
                            e["fieldName"] = "advertiser_name"
        # Ad Server Details: add an Advertiser filter (ds_camp.advertiser); shrink header to make room
        if p.get("name") == "ad_server_details":
            for it in p["layout"]:
                if it["widget"].get("name") == "header":
                    it["position"]["width"] = 8
            p["layout"].append(_filter_widget("f_adserver_advertiser", "ds_camp", "advertiser", "Advertiser", 8, 0))
customize_pages(sd)
apply_number_formats(sd)

# --- test every dataset query against the warehouse ---
def test_ds(d):
    sql = "".join(d["queryLines"])
    # supply catalog.schema for bare names (dashboard flags do this at runtime)
    test_sql = sql.replace("FROM ", f"FROM {CATALOG}.{SCHEMA}.").replace(f"{CATALOG}.{SCHEMA}.(", "(")
    # the naive replace also prefixes CTE refs; instead run with USE + bare — use a wrapper
    return sql

print("=== testing datasets ===")
import re
OBJECTS = ["mv_advertiser_renewal", "gold_campaign_delivery", "silver_accounts", "silver_deals",
           "dash_silver_nielsen", "dash_advertiser_risk", "dash_model_health",
           "ml_campaign_shortfall_scores"]
def qualify(sql):
    for o in OBJECTS:
        sql = re.sub(rf"(?<![\w.]){o}\b", f"{CATALOG}.{SCHEMA}.{o}", sql)
    return sql
fail = False
for d in sd["datasets"]:
    sql = qualify("".join(d["queryLines"]))
    r = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", sql,
                        "--profile", PROFILE], capture_output=True, text=True)
    ok = r.returncode == 0 and '"error"' not in r.stdout and "Error:" not in r.stdout[:60]
    print(f"  [{d['name']:20s}] {'OK' if ok else 'FAIL'}")
    if not ok:
        print("    ", (r.stdout or r.stderr)[:300]); fail = True

if fail:
    print("Some datasets failed — aborting update."); sys.exit(1)

def page_datasets(pg):
    s = set()
    for it in pg.get("layout", []):
        for qd in (it.get("widget", {}).get("queries", []) or []):
            dn = qd.get("query", {}).get("datasetName")
            if dn: s.add(dn)
    return s

def build(pages, with_genie):
    used = set()
    for p in pages: used |= page_datasets(p)
    ds = [dict(d, catalog=CATALOG, schema=SCHEMA) for d in sd["datasets"] if d["name"] in used]  # reference pins a stale catalog
    out = {"datasets": ds, "pages": pages}
    ui = dict(sd.get("uiSettings", {}))
    if with_genie:
        ui = {**ui, "genieSpace": {"isEnabled": True, "overrideId": GENIE, "enablementMode": "ENABLED"}}
    out["uiSettings"] = ui
    return out

rr_pages = [p for p in sd["pages"] if p["name"] in RR_PAGES]
as_pages = [p for p in sd["pages"] if p["name"] not in RR_PAGES]
print("RR pages:", [p["name"] for p in rr_pages])
print("AS pages:", [p["name"] for p in as_pages])

DISPLAY = {"renewal_risk": "Renewal & Risk Insights", "ad_sales": "Ad Sales Insights"}

def update(did, payload, title):
    open(f"/tmp/{title}.json", "w").write(json.dumps(payload))
    if not did:   # fresh build: CREATE (avoids the stale-schema issue of repeated in-place updates)
        r = subprocess.run(["databricks", "lakeview", "create", "--display-name", DISPLAY[title],
            "--warehouse-id", WAREHOUSE, "--dataset-catalog", CATALOG, "--dataset-schema", SCHEMA,
            "--serialized-dashboard", json.dumps(payload), "-p", PROFILE, "-o", "json"],
            capture_output=True, text=True)
        if r.returncode != 0 or '"dashboard_id"' not in r.stdout:
            print("CREATE FAILED", title); print(r.stdout[:600]); print(r.stderr[:600]); sys.exit(1)
        did = json.loads(r.stdout)["dashboard_id"]
        subprocess.run(["databricks", "lakeview", "publish", did, "--warehouse-id", WAREHOUSE, "-p", PROFILE],
                       capture_output=True, text=True)
        print(f"created+published {title}: {did}  (paste into RR_ID/AS_ID)")
        return did
    r = subprocess.run(["databricks", "lakeview", "update", did,
        "--dataset-catalog", CATALOG, "--dataset-schema", SCHEMA,
        "--serialized-dashboard", json.dumps(payload), "-p", PROFILE, "-o", "json"],
        capture_output=True, text=True)
    if r.returncode != 0 or '"dashboard_id"' not in r.stdout:
        print("UPDATE FAILED", title); print(r.stdout[:600]); print(r.stderr[:600]); sys.exit(1)
    subprocess.run(["databricks", "lakeview", "publish", did, "--warehouse-id", WAREHOUSE, "-p", PROFILE],
                   capture_output=True, text=True)
    print(f"updated+published {title}: {did}")

rr = build(rr_pages, True)
adm = build(as_pages, True)   # both link Ask Genie to THIS build's space (override reference's stale id)
open("dashboards/renewal_risk_insights.json", "w").write(json.dumps(rr, indent=1))
open("dashboards/ad_sales_insights.json", "w").write(json.dumps(adm, indent=1))
update(RR_ID, rr, "renewal_risk")
update(AS_ID, adm, "ad_sales")
print("DONE")

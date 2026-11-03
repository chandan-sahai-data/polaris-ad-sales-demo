"""Split the combined dashboard into TWO dashboards (one per app tab):
  - Renewal & Risk Insights : cockpit + filters + risk_analytics + delivery_risk + model_health
  - Ad Sales Insights       : everything else (silver_accounts/deals/nielsen, ad_server_details, …)
Pulls the LIVE dashboard, partitions pages + the datasets each set references, creates + publishes
both. Non-destructive: the original combined dashboard is left in place as a backup.
"""
import json, os, subprocess
os.environ["DATABRICKS_CONFIG_PROFILE"] = "ad-sales-demo"

P, SRC, WID = "ad-sales-demo", "01f1abe603c91ff7a62a63033e00d32e", "16f458cf207d4cf6"
PARENT = "/Workspace/Users/chandansahai@gmail.com/dashboards"
RR_PAGES = {"cockpit", "filters", "risk_analytics", "delivery_risk", "model_health"}

sd = json.loads(json.loads(subprocess.run(["databricks", "lakeview", "get", SRC, "-p", P, "-o", "json"],
                                          capture_output=True, text=True).stdout)["serialized_dashboard"])


def page_datasets(pg):
    s = set()
    for it in pg.get("layout", []):
        for qd in (it.get("widget", {}).get("queries", []) or []):
            dn = qd.get("query", {}).get("datasetName")
            if dn:
                s.add(dn)
    return s


def build(pages):
    used = set()
    for p in pages:
        used |= page_datasets(p)
    out = dict(sd)
    out["pages"] = pages
    out["datasets"] = [d for d in sd["datasets"] if d["name"] in used]
    return out


rr_pages = [p for p in sd["pages"] if p["name"] in RR_PAGES]
as_pages = [p for p in sd["pages"] if p["name"] not in RR_PAGES]  # everything else (incl. any new page)
print("Renewal & Risk pages:", [p["name"] for p in rr_pages])
print("Ad Sales pages:", [p["name"] for p in as_pages])


def create(title, payload):
    open(f"/tmp/{title}.json", "w").write(json.dumps(payload))
    out = subprocess.run(["databricks", "lakeview", "create", "--display-name", title, "--warehouse-id", WID,
                          "--dataset-catalog", "ad_sales_demo", "--dataset-schema", "ad_sales",
                          "--serialized-dashboard", json.dumps(payload),
                          "--json", json.dumps({"parent_path": PARENT}), "-p", P, "-o", "json"],
                         capture_output=True, text=True)
    did = json.loads(out.stdout)["dashboard_id"]
    subprocess.run(["databricks", "lakeview", "publish", did, "--warehouse-id", WID, "-p", P], capture_output=True, text=True)
    return did


as_id = create("Ad Sales Insights", build(as_pages))
rr_id = create("Renewal & Risk Insights", build(rr_pages))
print("AS_DASHBOARD_ID=" + as_id)
print("RR_DASHBOARD_ID=" + rr_id)

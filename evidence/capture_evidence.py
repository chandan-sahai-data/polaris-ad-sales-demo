"""Capture TEXT execution evidence for every stage of the deployed build.

Reads the LIVE workspace (nothing is mocked) and writes one markdown file per stage into
./evidence/. Re-run any time:  ../.venv/bin/python -I evidence/capture_evidence.py

Stages: Lakeflow ingest -> Unity Catalog governance -> ML -> Lakebase -> Genie -> dashboards
-> Databricks App -> Deal Memory (GenAI retrieval) -> "one number" proof.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

import psycopg2
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

PROFILE = "fe-vm-cs-genie-research"
CATALOG, SCHEMA = "cs_genie_research_catalog", "ad_sales"
FQ = f"{CATALOG}.{SCHEMA}"
WAREHOUSE = "69a77ede4fa03b41"
PIPELINE_ID = "42e57d29-404f-4c9d-a677-5c0b6d8fba90"
SYNC_PIPELINE_ID = "b99ed1a4-a38d-43bf-8de1-f667cfb6a9c9"
SYNCED_TABLE = f"{FQ}.lb_advertiser_risk_scores"
LB_ENDPOINT = "projects/renewal-actions/branches/production/endpoints/primary"
GENIE_SPACE = "01f1c80529421edaa5212423f9c65124"
DASHBOARDS = {"Renewal & Risk Insights": "01f1c805646d10c7bc4b13e6270abd37",
              "Ad Sales Insights": "01f1c805651b10ad9a2ffccdcc8219f0"}
APP = "ad-sales-renewal-cockpit"
OUT = os.path.dirname(os.path.abspath(__file__))

w = WorkspaceClient(profile=PROFILE)
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------- helpers
def sql(stmt, catalog=None, schema=None):
    """Run SQL on the warehouse; return (columns, rows)."""
    r = w.statement_execution.execute_statement(warehouse_id=WAREHOUSE, statement=stmt, wait_timeout="50s",
                                                catalog=catalog, schema=schema)
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"{r.status.state}: {r.status.error.message if r.status.error else ''}")
    cols = [c.name for c in r.manifest.schema.columns]
    return cols, (r.result.data_array or []) if r.result else []


def md_table(cols, rows, limit=30):
    def cell(v):
        s = "NULL" if v is None else str(v)
        return s.replace("|", "\\|").replace("\n", " ")[:160]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(cell(v) for v in row) + " |" for row in list(rows)[:limit]]
    if len(rows) > limit:
        out.append(f"\n_({len(rows)} rows total, first {limit} shown)_")
    return "\n".join(out)


def q(stmt, title=None, limit=30, **kw):
    """Run a query and return a markdown block showing the SQL and its result."""
    head = f"**{title}**\n\n" if title else ""
    try:
        cols, rows = sql(stmt, **kw)
        return f"{head}```sql\n{stmt.strip()}\n```\n\n{md_table(cols, rows, limit)}\n"
    except Exception as e:
        return f"{head}```sql\n{stmt.strip()}\n```\n\n> ERROR: {e}\n"


def code(obj, lang="json"):
    txt = obj if isinstance(obj, str) else json.dumps(obj, indent=2, default=str)
    return f"```{lang}\n{txt}\n```\n"


def write(name, title, body):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(f"# {title}\n\n_Captured live from `{w.config.host}` at {NOW} by `evidence/capture_evidence.py`._\n\n{body}")
    print("wrote", name)


def pg():
    host = w.postgres.get_endpoint(LB_ENDPOINT).status.hosts.host
    tok = w.postgres.generate_database_credential(LB_ENDPOINT).token
    user = w.current_user.me().user_name
    return psycopg2.connect(host=host, user=user, password=tok, dbname="databricks_postgres", sslmode="require")


def pg_q(cur, stmt, title):
    cur.execute(stmt)
    cols = [d.name for d in cur.description]
    return f"**{title}**\n\n```sql\n{stmt.strip()}\n```\n\n{md_table(cols, cur.fetchall())}\n"


# ---------------------------------------------------------------- 01 Lakeflow ingest
def lakeflow():
    b = ["## Landing (raw) tables — synthetic source systems\n"]
    b.append(q(f"""SELECT 'crm_accounts_raw' t, count(*) n, max(source_system) src, max(last_refresh) last_refresh FROM {FQ}.crm_accounts_raw
UNION ALL SELECT 'crm_deals_raw', count(*), max(source_system), max(last_refresh) FROM {FQ}.crm_deals_raw
UNION ALL SELECT 'ad_server_lineitems_raw', count(*), max(source_system), max(last_refresh) FROM {FQ}.ad_server_lineitems_raw
UNION ALL SELECT 'nielsen_measurement_raw', count(*), max(source_system), max(last_refresh) FROM {FQ}.nielsen_measurement_raw""",
               "Row counts + source system + freshness per landing table"))
    b.append(q(f"SELECT * FROM {FQ}.ad_server_lineitems_raw ORDER BY order_id LIMIT 5", "Sample: ad_server_lineitems_raw"))

    p = w.pipelines.get(PIPELINE_ID)
    b.append("\n## Lakeflow Spark Declarative Pipeline\n")
    b.append(code({"pipeline_id": p.pipeline_id, "name": p.name, "state": str(p.state),
                   "catalog": p.spec.catalog, "schema": p.spec.target or p.spec.schema,
                   "serverless": p.spec.serverless, "channel": p.spec.channel,
                   "libraries": [l.file.path for l in (p.spec.libraries or []) if l.file]}))
    ups = w.pipelines.list_updates(PIPELINE_ID, max_results=5).updates or []
    b.append("**Pipeline updates (most recent first)**\n\n" + md_table(
        ["update_id", "state", "full_refresh", "creation_time"],
        [[u.update_id, str(u.state).split(".")[-1], u.full_refresh,
          dt.datetime.fromtimestamp(u.creation_time / 1000, dt.timezone.utc)] for u in ups]) + "\n")

    b.append(q(f"""SELECT timestamp, origin.flow_name AS flow, details:flow_progress.status AS status,
details:flow_progress.metrics.num_output_rows AS num_output_rows
FROM event_log('{PIPELINE_ID}') WHERE event_type='flow_progress' AND details:flow_progress.status='COMPLETED'
ORDER BY timestamp""", "Event log — completed flows (bronze → silver → gold)", limit=40))
    b.append(q(f"""SELECT origin.flow_name AS flow, e.name AS expectation, e.dataset, e.passed_records, e.failed_records
FROM event_log('{PIPELINE_ID}'),
LATERAL explode(from_json(details:flow_progress.data_quality.expectations,
  'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS t(e)
WHERE event_type='flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL
ORDER BY flow, expectation""", "Event log — data-quality expectation results (SDP expectations)", limit=40))
    b.append("\n## Row counts at every medallion layer\n")
    layers = ["bronze_ad_server", "bronze_crm_accounts", "bronze_crm_deals", "bronze_nielsen",
              "silver_ad_server", "silver_crm_accounts", "silver_crm_deals", "silver_nielsen",
              "gold_campaign_advertiser", "gold_advertiser_book", "gold_advertiser_renewal_risk"]
    b.append(q(" UNION ALL ".join(f"SELECT '{t}' AS table_name, count(*) AS row_count FROM {FQ}.{t}" for t in layers)))
    b.append(q(f"""SELECT campaign_id, advertiser_name, category, sales_type, round(pacing_index,3) pacing_index,
round(effective_cpm,2) effective_cpm, round(reach_delivery_pct,3) reach_delivery_pct, adserver_last_refresh, nielsen_last_refresh
FROM {FQ}.gold_campaign_advertiser WHERE advertiser_id='ADV0062'""", "Gold unified campaign row (hero advertiser Meridian Retail)"))
    write("01_lakeflow_ingest.md", "Stage 1 — Lakeflow ingestion (raw → bronze → silver → gold)", "\n".join(b))


# ---------------------------------------------------------------- 02 Unity Catalog
def unity_catalog():
    b = [q(f"""SELECT table_name, table_type, data_source_format, comment FROM {CATALOG}.information_schema.tables
WHERE table_schema='{SCHEMA}' AND table_name NOT LIKE '\\_\\_%' ORDER BY table_type, table_name""", "All governed objects in the schema", limit=60)]
    b.append(q(f"SHOW GRANTS ON SCHEMA {FQ}", "Grants on the schema (app service principal has USE SCHEMA + SELECT)"))
    b.append(q(f"""SELECT source_table_full_name, target_table_full_name, entity_type, max(event_time) last_seen
FROM system.access.table_lineage WHERE target_table_catalog='{CATALOG}' AND target_table_schema='{SCHEMA}'
AND source_table_full_name IS NOT NULL GROUP BY ALL ORDER BY target_table_full_name""",
               "Unity Catalog lineage captured automatically (system.access.table_lineage)", limit=60))
    for mv in ["mv_campaign_metrics", "mv_advertiser_renewal"]:
        try:
            _, rows = sql(f"SHOW CREATE TABLE {FQ}.{mv}")
            b.append(f"**Metric view definition — `{mv}`** (single source of truth for KPIs)\n\n" + code(rows[0][0], "sql"))
        except Exception as e:
            b.append(f"> SHOW CREATE TABLE {mv} failed: {e}\n")
    b.append(q(f"""SELECT Category, MEASURE(`Campaigns`) campaigns, ROUND(MEASURE(`Effective CPM`),2) effective_cpm,
ROUND(MEASURE(`Delivery vs Commitment`),3) delivery_vs_commitment, ROUND(MEASURE(`Sellout Pct`),3) sellout_pct,
ROUND(MEASURE(`Reach Efficiency`),2) reach_efficiency FROM {FQ}.mv_campaign_metrics GROUP BY Category ORDER BY Category""",
               "Metric view query: governed KPIs by category"))
    b.append(q(f"""SELECT `Risk Tier`, `Renewal Window`, CAST(MEASURE(`Revenue at Risk`) AS DECIMAL(18,0)) revenue_at_risk, CAST(MEASURE(`Total Contract Value`) AS DECIMAL(18,0)) total_contract_value
FROM {FQ}.mv_advertiser_renewal GROUP BY ALL ORDER BY 1,2""", "Metric view query: revenue at risk by tier × renewal window"))
    write("02_unity_catalog_governance.md", "Stage 2 — Unity Catalog governance (objects, grants, lineage, metric views)", "\n".join(b))


# ---------------------------------------------------------------- 03 ML
def ml():
    import mlflow
    from mlflow.tracking import MlflowClient
    os.environ["DATABRICKS_CONFIG_PROFILE"] = PROFILE
    mlflow.set_tracking_uri("databricks")
    mc = MlflowClient(tracking_uri="databricks", registry_uri="databricks-uc")
    b = []
    exp = mc.get_experiment_by_name(f"/Users/{w.current_user.me().user_name}/{CATALOG}_ml_experiment")
    runs = mc.search_runs([exp.experiment_id], order_by=["start_time DESC"], max_results=10)
    b.append(f"**MLflow experiment** `{exp.name}` (id {exp.experiment_id})\n\n" + md_table(
        ["run_id", "run_name", "status", "start_time", "val_auc", "precision", "recall"],
        [[r.info.run_id, r.info.run_name, r.info.status,
          dt.datetime.fromtimestamp(r.info.start_time / 1000, dt.timezone.utc),
          round(r.data.metrics.get("val_auc", float("nan")), 4), round(r.data.metrics.get("precision", float("nan")), 4),
          round(r.data.metrics.get("recall", float("nan")), 4)] for r in runs]) + "\n")
    rows = []
    for m in ["delivery_shortfall_model", "renewal_risk_model"]:
        for v in mc.search_model_versions(f"name='{FQ}.{m}'"):
            rm = mc.get_registered_model(f"{FQ}.{m}")
            rows.append([f"{FQ}.{m}", v.version, v.status, v.run_id,
                         ",".join(a for a, ver in (rm.aliases or {}).items() if str(ver) == str(v.version)) if isinstance(rm.aliases, dict)
                         else ",".join(getattr(a, "alias", str(a)) for a in (rm.aliases or []))])
    b.append("\n**Unity Catalog registered model versions**\n\n" + md_table(["model", "version", "status", "run_id", "aliases"], rows) + "\n")
    b.append(q(f"SELECT * FROM {FQ}.ml_model_monitoring", "Model monitoring table (predicted vs actual)"))
    b.append(q(f"""SELECT campaign_id, advertiser_id, round(p_shortfall,3) p_shortfall FROM {FQ}.ml_campaign_shortfall_scores
ORDER BY p_shortfall DESC LIMIT 10""", "Model A batch scores — top 10 campaigns by p(shortfall)"))
    b.append(q(f"""SELECT risk_tier, count(*) advertisers, round(sum(revenue_at_risk),0) revenue_at_risk FROM {FQ}.advertiser_risk_scores
GROUP BY risk_tier ORDER BY revenue_at_risk DESC""", "Composite score tiers (advertiser_risk_scores)"))
    b.append(q(f"""SELECT advertiser_name, category, round(p_churn,3) p_churn, round(adv_p_shortfall,3) adv_p_shortfall, round(risk_score,1) risk_score,
risk_tier, round(revenue_at_risk,0) revenue_at_risk, renewal_window, contributing_factors FROM {FQ}.advertiser_risk_scores
ORDER BY revenue_at_risk DESC LIMIT 15""", "Top 15 advertisers by revenue at risk, with explainable drivers"))
    write("03_ml_models.md", "Stage 3 — ML: delivery-shortfall classifier + renewal-risk model → composite score", "\n".join(b))


# ---------------------------------------------------------------- 04 Lakebase
def lakebase():
    b = []
    proj = w.postgres.get_project("projects/renewal-actions")
    ep = w.postgres.get_endpoint(LB_ENDPOINT)
    b.append("**Lakebase Autoscaling project + endpoint**\n\n" + code({
        "project": proj.name, "display_name": proj.status.display_name if proj.status else None,
        "pg_version": proj.status.pg_version if proj.status else None,
        "endpoint": ep.name, "endpoint_state": str(ep.status.current_state) if ep.status else None}))
    st = w.postgres.get_synced_table(f"synced_tables/{SYNCED_TABLE}").as_dict()
    b.append("**Synced table (Delta → Postgres, CONTINUOUS)**\n\n" + code({
        "name": st.get("name"), "source": st.get("spec", {}).get("source_table_full_name"),
        "scheduling_policy": st.get("spec", {}).get("scheduling_policy"),
        "detailed_state": st.get("status", {}).get("detailed_state"),
        "last_sync": st.get("status", {}).get("last_sync")}))
    with pg() as c:
        c.autocommit = True
        cur = c.cursor()
        b.append(pg_q(cur, "SELECT risk_tier, count(*) advertisers, round(sum(revenue_at_risk)::numeric,0) revenue_at_risk FROM ad_sales.lb_advertiser_risk_scores GROUP BY risk_tier ORDER BY 3 DESC",
                      "Postgres read of the synced risk table"))
        cur.execute("INSERT INTO public.seller_actions (advertiser_id, action_type, note, next_connect_date, acted_by) "
                    "VALUES ('ADV0040','snoozed','evidence capture: transactional write-back test', current_date + 7, 'evidence-script') RETURNING action_id, acted_at")
        aid, at = cur.fetchone()
        b.append(f"**Transactional write-back** — inserted `seller_actions.action_id={aid}` at {at}\n\n")
        b.append(pg_q(cur, "SELECT action_id, advertiser_id, action_type, note, next_connect_date, acted_by, acted_at FROM public.seller_actions ORDER BY action_id",
                      "Read-back of seller_actions (rows written by the app and by this script)"))
    write("04_lakebase_serving.md", "Stage 4 — Lakebase operational serving (synced reads + transactional write-back)", "\n".join(b))


# ---------------------------------------------------------------- 05 Genie
def genie():
    b = []
    sp = w.genie.get_space(GENIE_SPACE)
    b.append(code({"space_id": sp.space_id, "title": sp.title, "description": sp.description}))
    qs = ["What's our track record with QSR campaigns over the last two quarters?",
          "Meridian Restaurants came up as elevated renewal risk — summarize their campaign performance and delivery against plan.",
          "Which audience segments delivered the best reach efficiency for QSR advertisers?",
          "Show the top 10 high-risk advertisers by revenue at risk with their contributing factors."]
    for i, question in enumerate(qs, 1):
        t0 = time.time()
        msg = w.genie.start_conversation_and_wait(GENIE_SPACE, question)
        secs = round(time.time() - t0, 1)
        b.append(f"\n## Q{i}. {question}\n\n_status={msg.status}, latency={secs}s, conversation_id={msg.conversation_id}_\n")
        for a in msg.attachments or []:
            if a.text and a.text.content:
                b.append("**Genie answer**\n\n> " + a.text.content.replace("\n", "\n> ") + "\n")
            if a.query:
                b.append("**Generated SQL**\n\n" + code(a.query.query, "sql"))
                try:
                    r = w.genie.get_message_attachment_query_result(GENIE_SPACE, msg.conversation_id, msg.id, a.attachment_id)
                    sr = r.statement_response
                    cols = [c.name for c in sr.manifest.schema.columns]
                    b.append("**Result rows**\n\n" + md_table(cols, sr.result.data_array or [], 15) + "\n")
                except Exception as e:
                    b.append(f"> result fetch failed: {e}\n")
    write("05_genie_agent.md", "Stage 5 — Genie Agent: natural-language questions answered over the governed data", "\n".join(b))


# ---------------------------------------------------------------- 06 dashboards
def dashboards():
    b = []
    for title, did in DASHBOARDS.items():
        d = w.lakeview.get(did)
        pub = w.lakeview.get_published(did)
        ser = json.loads(d.serialized_dashboard)
        b.append(f"\n## {title} (`{did}`)\n\n" + code({
            "display_name": d.display_name, "lifecycle_state": str(d.lifecycle_state), "published_warehouse": pub.warehouse_id,
            "published_revision": str(pub.revision_create_time), "pages": [p.get("displayName", p["name"]) for p in ser["pages"]],
            "widgets": sum(len(p.get("layout", [])) for p in ser["pages"]),
            "genie_space_linked": ser.get("uiSettings", {}).get("genieSpace", {}).get("overrideId")}))
        for ds in ser["datasets"]:
            stmt = "".join(ds.get("queryLines") or [ds.get("query", "")])
            b.append(q(stmt, f"Dataset `{ds['name']}` ({ds.get('displayName', '')}) — executed on the warehouse", limit=5,
                       catalog=ds.get("catalog", CATALOG), schema=ds.get("schema", SCHEMA)))
    write("06_aibi_dashboards.md", "Stage 6a — AI/BI dashboards (published; every dataset query executed)", "\n".join(b))


# ---------------------------------------------------------------- 07 app
def app():
    a = w.apps.get(APP)
    b = ["**App status**\n\n" + code({
        "name": a.name, "url": a.url, "app_status": str(a.app_status.state) if a.app_status else None,
        "compute_status": str(a.compute_status.state) if a.compute_status else None,
        "service_principal_client_id": a.service_principal_client_id,
        "active_deployment": a.active_deployment.deployment_id if a.active_deployment else None,
        "deployment_status": str(a.active_deployment.status.state) if a.active_deployment and a.active_deployment.status else None,
        "resources": [r.name for r in (a.resources or [])]})]
    headers = dict(w.config.authenticate())
    headers["Content-Type"] = "application/json"

    def call(method, path, body=None):
        req = urllib.request.Request(a.url + path, method=method, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, round(time.time() - t0, 2), json.loads(r.read())

    calls = [("GET", "/api/config", None),
             ("GET", "/api/risk?tier=High&window=renews_this_quarter", None),
             ("POST", "/api/action", {"advertiser_id": "ADV0062", "action_type": "contacted",
                                      "note": "evidence capture: app write-back", "next_connect_date": "2026-11-09", "acted_by": "evidence-script"}),
             ("GET", "/api/risk?advertiser=ADV0062", None),
             ("POST", "/api/deal_memory", {"query": "What did we promise Meridian in their last renewal?"}),
             ("POST", "/api/genie", {"question": "How many advertisers renew this quarter and how many of those are High risk?"})]
    for method, path, body in calls:
        try:
            status, secs, resp = call(method, path, body)
            if isinstance(resp, list):
                resp = {"rows_returned": len(resp), "first_rows": resp[:5]}
            if isinstance(resp, dict) and isinstance(resp.get("content"), str):
                resp["content"] = resp["content"][:200]
            b.append(f"\n### `{method} {path}` → HTTP {status} in {secs}s\n\n" + (f"Request body:\n{code(body)}" if body else "") + "Response:\n" + code(resp))
        except Exception as e:
            b.append(f"\n### `{method} {path}` → ERROR {e}\n")
    write("07_databricks_app.md", "Stage 7 — Databricks App (FastAPI) surfacing it to the business", "\n".join(b))


# ---------------------------------------------------------------- 08 GenAI deal memory
def deal_memory():
    b = [q(f"SELECT doc_id, advertiser_name, doc_type, source, effective_date, size(embedding) embedding_dim FROM {FQ}.deal_docs ORDER BY doc_id",
           "Deal Memory corpus (UC table; files also in Volume deal_memory)")]
    b.append(q(f"LIST '/Volumes/{CATALOG}/{SCHEMA}/deal_memory/'", "Files in the UC Volume", limit=20))
    try:
        emb = w.serving_endpoints.query(name="databricks-bge-large-en", input=["probe"]).data[0].embedding
        b.append(f"**Embedding endpoint `databricks-bge-large-en` live** — returned a {len(emb)}-dim vector.\n")
    except Exception as e:
        b.append(f"> embedding endpoint call failed: {e}\n")
    write("08_genai_deal_memory.md", "Stage 8 — GenAI: semantic retrieval over unstructured deal documents", "\n".join(b))


# ---------------------------------------------------------------- 09 one-number proof
def one_number():
    b = [q(f"""SELECT
 CAST((SELECT MEASURE(`Revenue at Risk`) FROM {FQ}.mv_advertiser_renewal WHERE `Risk Tier`='High') AS DECIMAL(18,0)) AS metric_view_high_rar,
 CAST((SELECT SUM(revenue_at_risk) FROM {FQ}.advertiser_risk_scores WHERE risk_tier='High') AS DECIMAL(18,0)) AS base_table_high_rar,
 CAST((SELECT SUM(revenue_at_risk) FROM {FQ}.dash_advertiser_risk WHERE risk_tier='High') AS DECIMAL(18,0)) AS dashboard_view_high_rar,
 (SELECT COUNT(*) FROM {FQ}.advertiser_risk_scores WHERE risk_tier='High') AS high_count,
 (SELECT ROUND(MEASURE(`Effective CPM`),2) FROM {FQ}.mv_campaign_metrics) AS overall_cpm""", "Lakehouse side")]
    with pg() as c:
        cur = c.cursor()
        b.append(pg_q(cur, "SELECT round(sum(revenue_at_risk)::numeric,0) lakebase_high_rar, count(*) high_count FROM ad_sales.lb_advertiser_risk_scores WHERE risk_tier='High'",
                      "Lakebase (operational) side — what the app reads"))
    write("09_one_number_proof.md", "Integration proof — the same number on every surface", "\n".join(b))


STAGES = {"lakeflow": lakeflow, "uc": unity_catalog, "ml": ml, "lakebase": lakebase, "genie": genie,
          "dashboards": dashboards, "app": app, "deal_memory": deal_memory, "one_number": one_number}

if __name__ == "__main__":
    for name in (sys.argv[1:] or STAGES):
        try:
            STAGES[name]()
        except Exception as e:
            print(f"STAGE {name} FAILED: {e}")

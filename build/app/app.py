"""Polaris — Ad Sales Intelligence Cockpit (Databricks App, FastAPI).

One seller surface: embeds the two AI/BI dashboards, a multi-turn Genie panel, and the
Lakebase write-back (mark contacted / snooze + note + next-connect date). Reads current
risk state from the Lakebase SYNCED table (low latency) and writes seller actions back to
Lakebase — the concrete reason Lakebase sits under the app.

FastAPI + a top-level HTML <iframe> (NOT Streamlit): Streamlit's sandboxed component layer
breaks the AI/BI embed's parent-frame auth handshake.
"""
import os, time, threading, uuid, math, json as _json
import urllib.request as _urlreq
from contextlib import contextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
import psycopg2
import psycopg2.extras
from databricks.sdk import WorkspaceClient

HERE = os.path.dirname(__file__)
HOST          = os.environ.get("DATABRICKS_HOST", "")
WORKSPACE_ID  = os.environ.get("WORKSPACE_ID", "")
GENIE_SPACE   = os.environ.get("GENIE_SPACE_ID", "")
DASH_AS       = os.environ.get("DASHBOARD_ID_AS", "")
DASH_RR       = os.environ.get("DASHBOARD_ID_RR", "")
LB_ENDPOINT   = os.environ.get("LAKEBASE_ENDPOINT", "projects/renewal-actions/branches/production/endpoints/primary")
PGHOST        = os.environ.get("PGHOST", "")
PGUSER        = os.environ.get("PGUSER", "")
PGDATABASE    = os.environ.get("PGDATABASE", "databricks_postgres")
PGPORT        = os.environ.get("PGPORT", "5432")
WAREHOUSE_ID  = os.environ.get("WAREHOUSE_ID", "")
EMBED_ENDPOINT = os.environ.get("EMBED_ENDPOINT", "databricks-bge-large-en")
FQ            = os.environ.get("FQ", "cs_genie_research_catalog.ad_sales")
RISK_TABLE    = os.environ.get("RISK_TABLE", "public.advertiser_risk_scores")   # Lakebase synced table (schema.table in Postgres)

app = FastAPI(title="Ad Sales Intelligence Cockpit")
_w = WorkspaceClient()
_tok = {"value": None, "exp": 0}
_tok_lock = threading.Lock()


def _db_token():
    with _tok_lock:
        if _tok["value"] and time.time() < _tok["exp"]:
            return _tok["value"]
        cred = _w.postgres.generate_database_credential(LB_ENDPOINT)
        _tok["value"] = cred.token
        _tok["exp"] = time.time() + 45 * 60   # refresh well before the 1h expiry
        return _tok["value"]


@contextmanager
def db():
    conn = psycopg2.connect(host=PGHOST, port=PGPORT, user=PGUSER, dbname=PGDATABASE,
                            password=_db_token(), sslmode="require",
                            cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


@app.on_event("startup")
def _startup():
    # ensure write-back table exists (idempotent); the synced risk table is created by the sync pipeline
    try:
        with db() as c, c.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.seller_actions (
                  action_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                  advertiser_id TEXT NOT NULL, action_type TEXT NOT NULL, note TEXT,
                  next_connect_date DATE, acted_by TEXT, acted_at TIMESTAMPTZ DEFAULT now());
                GRANT ALL ON public.seller_actions TO PUBLIC;
            """)
            c.commit()
    except Exception as e:
        print("startup seller_actions ensure:", e)


@app.get("/api/config")
def config():
    return {"host": HOST, "workspace_id": WORKSPACE_ID, "genie_space": GENIE_SPACE,
            "dashboard_as": DASH_AS, "dashboard_rr": DASH_RR}


@app.get("/api/risk")
def risk(tier: str = "", window: str = "", advertiser: str = ""):
    where, params = ["1=1"], []
    if tier:
        where.append("risk_tier = %s"); params.append(tier)
    if window:
        where.append("renewal_window = %s"); params.append(window)
    if advertiser:
        where.append("advertiser_id = %s"); params.append(advertiser)
    sql = f"""
      SELECT r.advertiser_id, r.advertiser_name, r.category, r.region, r.risk_score, r.risk_tier,
             r.revenue_at_risk, r.renewal_window, r.days_to_renewal, r.campaign_count, r.campaigns_behind,
             r.contributing_factors,
             a.action_type AS last_action, a.note AS last_note, a.next_connect_date, a.acted_at AS last_acted_at
      FROM {RISK_TABLE} r
      LEFT JOIN LATERAL (
        SELECT action_type, note, next_connect_date, acted_at FROM public.seller_actions s
        WHERE s.advertiser_id = r.advertiser_id ORDER BY s.acted_at DESC LIMIT 1) a ON true
      WHERE {' AND '.join(where)}
      ORDER BY (r.risk_tier='High') DESC, r.revenue_at_risk DESC LIMIT 200"""
    with db() as c, c.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    for r in rows:
        for k in ("next_connect_date", "last_acted_at"):
            if r.get(k) is not None:
                r[k] = str(r[k])
    return JSONResponse(rows)


@app.get("/api/advertisers")
def advertisers():
    with db() as c, c.cursor() as cur:
        cur.execute(f"SELECT advertiser_id, advertiser_name FROM {RISK_TABLE} ORDER BY advertiser_name")
        return JSONResponse(cur.fetchall())


@app.post("/api/action")
async def action(request: Request):
    b = await request.json()
    with db() as c, c.cursor() as cur:
        cur.execute("""INSERT INTO public.seller_actions (advertiser_id, action_type, note, next_connect_date, acted_by)
                       VALUES (%s,%s,%s,%s,%s) RETURNING action_id""",
                    (b["advertiser_id"], b["action_type"], b.get("note"),
                     b.get("next_connect_date") or None, b.get("acted_by", "app-user")))
        aid = cur.fetchone()["action_id"]; c.commit()
    return {"ok": True, "action_id": aid}


@app.post("/api/genie")
async def genie(request: Request):
    b = await request.json()
    q = b.get("question", "")
    conv = b.get("conversation_id")
    if conv:
        msg = _w.genie.create_message_and_wait(GENIE_SPACE, conv, q)
    else:
        msg = _w.genie.start_conversation_and_wait(GENIE_SPACE, q)
        conv = msg.conversation_id
    text, sql, rows = None, None, None
    for a in (msg.attachments or []):
        if a.text and a.text.content:
            text = a.text.content
        if a.query:
            sql = a.query.query
            try:
                qr = _w.genie.get_message_attachment_query_result(GENIE_SPACE, conv, msg.id, a.attachment_id)
                sr = qr.statement_response
                if sr and sr.result and sr.result.data_array:
                    cols = [c.name for c in sr.manifest.schema.columns]
                    rows = {"columns": cols, "data": sr.result.data_array[:50]}
            except Exception as e:
                print("genie query result:", e)
    return {"conversation_id": conv, "text": text, "sql": sql, "rows": rows}


# ---- Deal Memory (semantic search over deal_docs via bge embeddings + in-app cosine) ----
_docs = {"rows": None}
_docs_lock = threading.Lock()

def _load_docs():
    with _docs_lock:
        if _docs["rows"] is not None:
            return _docs["rows"]
        r = _w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID, wait_timeout="30s",
            statement=f"SELECT doc_id, advertiser_id, advertiser_name, doc_type, source, effective_date, content, embedding FROM {FQ}.deal_docs")
        rows = []
        for row in (r.result.data_array or []):
            emb = row[7]
            emb = _json.loads(emb) if isinstance(emb, str) else emb
            rows.append({"doc_id": row[0], "advertiser_id": row[1], "advertiser_name": row[2],
                         "doc_type": row[3], "source": row[4], "effective_date": row[5],
                         "content": row[6], "embedding": [float(x) for x in emb]})
        _docs["rows"] = rows
        return rows

def _cos(a, b):
    dot = sum(x*y for x, y in zip(a, b)); na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0.0

@app.post("/api/deal_memory")
async def deal_memory(request: Request):
    b = await request.json()
    q = (b.get("query") or "").strip()
    if not q:
        return JSONResponse([])
    docs = _load_docs()
    qv = [float(x) for x in _w.serving_endpoints.query(name=EMBED_ENDPOINT, input=[q]).data[0].embedding]
    scored = sorted(((_cos(qv, d["embedding"]), d) for d in docs), key=lambda t: -t[0])[:5]
    return JSONResponse([{"score": round(sc, 3), "advertiser_name": d["advertiser_name"],
                          "advertiser_id": d["advertiser_id"], "doc_type": d["doc_type"], "source": d["source"],
                          "effective_date": d["effective_date"], "content": d["content"]} for sc, d in scored])

# ---- Genie One (cross-data "onechat") — same backend as the Genie One MCP ----
def _ws_base():
    h = HOST or ""
    if not h.startswith("http"):
        h = "https://" + h
    return h.rstrip("/")

@app.post("/api/genie_one")
async def genie_one(request: Request):
    b = await request.json()
    q = (b.get("question") or "").strip()
    if not q:
        return JSONResponse({"text": "", "steps": [], "thoughts": []})
    url = _ws_base() + "/api/2.0/data-rooms/tools/onechat/responses"
    payload = _json.dumps({
        "enable_viz": False,
        "input": [{"type": "message", "role": "user",
                   "content": [{"type": "input_text", "text": q}]}],
        "source": "databricks_app",
    }).encode("utf-8")
    headers = dict(_w.config.authenticate() or {})
    headers["Content-Type"] = "application/json"
    items = {}      # output_index -> latest item (added/updated)
    conv = None
    try:
        req = _urlreq.Request(url, data=payload, headers=headers, method="POST")
        with _urlreq.urlopen(req, timeout=180) as resp:   # streaming NDJSON of response.output_item events
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if line.startswith("data:"):      # SSE-framed stream
                    line = line[5:].strip()
                if not line:
                    continue
                try:
                    ev = _json.loads(line)
                except Exception:
                    continue
                if ev.get("conversation_id"):
                    conv = ev["conversation_id"]
                if "item" in ev and ev.get("output_index") is not None:
                    items[ev["output_index"]] = ev["item"]
    except Exception as e:
        return JSONResponse({"text": f"Genie One is unavailable to this app: {e}", "steps": [], "thoughts": []})
    steps, texts = [], []
    for idx in sorted(items):
        it = items[idx] or {}
        if it.get("type") == "function_call" and it.get("name"):
            steps.append(it["name"])
        if it.get("type") == "message" and it.get("role") == "assistant":
            for c in (it.get("content") or []):
                if c.get("type") == "output_text" and (c.get("text") or "").strip():
                    texts.append(c["text"].strip())
    seen = set(); steps = [s for s in steps if not (s in seen or seen.add(s))]
    answer = texts[-1] if texts else "(no answer returned)"
    return JSONResponse({"text": answer, "steps": steps, "thoughts": texts[:-1], "conversation_id": conv})


# ---- Ontology graph: governed entities + relationships of the ad-sales data model ----
@app.get("/api/ontology")
def ontology():
    counts = {}
    try:
        r = _w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID, wait_timeout="30s",
            statement=f"""SELECT 'Advertiser' e, count(*) n FROM {FQ}.silver_crm_accounts
              UNION ALL SELECT 'Campaign', count(*) FROM {FQ}.gold_campaign_advertiser
              UNION ALL SELECT 'Deal', count(*) FROM {FQ}.silver_crm_deals
              UNION ALL SELECT 'AdServerLineItem', count(*) FROM {FQ}.silver_ad_server
              UNION ALL SELECT 'NielsenMeasurement', count(*) FROM {FQ}.silver_nielsen
              UNION ALL SELECT 'RenewalRiskScore', count(*) FROM {FQ}.advertiser_risk_scores
              UNION ALL SELECT 'DealDocument', count(*) FROM {FQ}.deal_docs""")
        for row in (r.result.data_array or []):
            counts[row[0]] = int(row[1])
    except Exception as e:
        print("ontology counts:", e)
    nodes = [
        {"id": "Advertiser", "label": "Advertiser", "table": "silver_crm_accounts", "key": "advertiser_id", "x": 180, "y": 250, "hub": True},
        {"id": "RenewalRiskScore", "label": "Renewal Risk Score", "table": "advertiser_risk_scores", "key": "advertiser_id", "x": 180, "y": 70},
        {"id": "DealDocument", "label": "Deal Document", "table": "deal_docs", "key": "advertiser_id", "x": 180, "y": 430},
        {"id": "Deal", "label": "Deal", "table": "silver_crm_deals", "key": "deal_id", "x": 480, "y": 370},
        {"id": "Campaign", "label": "Campaign", "table": "gold_campaign_advertiser", "key": "campaign_id", "x": 490, "y": 150},
        {"id": "AdServerLineItem", "label": "Ad Server Line Item", "table": "silver_ad_server", "key": "order_id", "x": 800, "y": 80},
        {"id": "NielsenMeasurement", "label": "Nielsen Measurement", "table": "silver_nielsen", "key": "campaign_id", "x": 810, "y": 250},
    ]
    for n in nodes:
        n["count"] = counts.get(n["id"])
    edges = [
        {"s": "Advertiser", "t": "Campaign", "via": "advertiser_id", "card": "1—∗"},
        {"s": "Advertiser", "t": "Deal", "via": "advertiser_id", "card": "1—∗"},
        {"s": "Advertiser", "t": "RenewalRiskScore", "via": "advertiser_id", "card": "1—1"},
        {"s": "Advertiser", "t": "DealDocument", "via": "advertiser_id", "card": "1—∗"},
        {"s": "Campaign", "t": "AdServerLineItem", "via": "campaign_id", "card": "1—∗"},
        {"s": "Campaign", "t": "NielsenMeasurement", "via": "campaign_id", "card": "1—1"},
    ]
    return {"nodes": nodes, "edges": edges, "catalog": FQ}


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("DATABRICKS_APP_PORT", 8000)))

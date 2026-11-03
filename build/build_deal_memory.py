"""Step 9 — Deal Memory (untapped knowledge, kept thin).

A ~15-doc corpus of ad-sales prose (recaps / contract & renewal terms / QBR notes) keyed to
REAL advertiser_ids (weighted to the high-risk heroes). Landed as files in a UC Volume + a
metadata table `deal_docs` that also stores a bge-large-en embedding per doc, so the app can
do in-app cosine retrieval with CITED results.

Managed Vector Search + a Knowledge Assistant is the documented production scale-out; at this
demo's doc scale, embeddings + in-app cosine is the lightweight, reliable path (managed VS
indexes don't provision in this FEVM).
"""
from pyspark.sql import types as T
from config import spark, wc, FQ, CATALOG, SCHEMA, EMBED_ENDPOINT

DOCS = [
    # ---- Meridian Retail (062) — the top high-risk hero: rich memory ----
    dict(doc_id="DM001", advertiser_id="ADV0062", advertiser_name="Meridian Retail (062)", campaign_id="CMP-MR-Q3",
         doc_type="contract", source="Renewal Insertion Order 2026", effective_date="2026-03-01",
         content="Meridian Retail renewal insertion order. We committed to a 95% delivered-impressions guarantee across primetime and sports inventory, with automatic make-good credits for any flight delivering below 95% of booked. Renewal includes a locked upfront CPM rate for four quarters, first-look on premium primetime holiday inventory, and a quarterly business review with audience-quality reporting. We promised added-value bonus weight in daytime if primetime under-delivers."),
    dict(doc_id="DM002", advertiser_id="ADV0062", advertiser_name="Meridian Retail (062)", campaign_id="CMP-MR-Q3",
         doc_type="recap", source="Q3 Campaign Wrap Report", effective_date="2026-08-20",
         content="Q3 wrap for Meridian Retail: campaign delivered 82% of booked impressions — an under-delivery driven by soft CTV supply and off-peak daypart pacing. Viewability on the CTV app placements came in below the 70% benchmark, and in-target audience delivery lagged plan. We flagged the under-delivery risk to the client and proposed a make-good plan ahead of the renewal conversation."),
    dict(doc_id="DM003", advertiser_id="ADV0062", advertiser_name="Meridian Retail (062)", campaign_id=None,
         doc_type="qbr", source="QBR Notes — Aug 2026", effective_date="2026-08-28",
         content="QBR with Meridian Retail. The client raised concerns about under-delivery and viewability on the current flight and asked what we would do before renewal. We promised a make-good in primetime plus a viewability guarantee written into the next insertion order, and committed to a renewal call within two weeks. Renewal is elevated risk given the delivery shortfall and the upcoming renewal date."),
    # ---- Meridian Restaurants (001) — original QSR hero ----
    dict(doc_id="DM004", advertiser_id="ADV0001", advertiser_name="Meridian Restaurants", campaign_id="CMP00028",
         doc_type="recap", source="Primetime QSR Wrap", effective_date="2026-08-15",
         content="Meridian Restaurants primetime QSR wrap: all active campaigns pacing behind plan at roughly 0.82x delivery. Under-delivery concentrated in scatter buys. We discussed a make-good and additional primetime weight to protect the renewal, which is due in ten days."),
    # ---- Ironwood Health (040) ----
    dict(doc_id="DM005", advertiser_id="ADV0040", advertiser_name="Ironwood Health (040)", campaign_id="CMP-IH-01",
         doc_type="contract", source="Pharma Guaranteed-GRP Agreement", effective_date="2026-02-10",
         content="Ironwood Health agreement guarantees gross rating points against an A25-54 target with compliant pharma placement and brand-safe adjacency. Make-good terms apply if delivered GRPs fall short. Renewal terms include an audience-quality floor and monthly measurement reconciliation."),
    dict(doc_id="DM006", advertiser_id="ADV0040", advertiser_name="Ironwood Health (040)", campaign_id="CMP-IH-01",
         doc_type="recap", source="Reach Wrap Report", effective_date="2026-08-18",
         content="Ironwood Health reach wrap: planned reach delivered but average frequency ran high, and viewability on daytime placements dipped below benchmark. Under-delivery on in-target impressions flagged for the renewal review; recommended shifting weight to higher-viewability primetime."),
    dict(doc_id="DM007", advertiser_id="ADV0040", advertiser_name="Ironwood Health (040)", campaign_id=None,
         doc_type="qbr", source="Renewal QBR", effective_date="2026-08-25",
         content="Ironwood Health renewal QBR. Client wants added value and stronger audience guarantees at renewal. We proposed a viewability SLA and a make-good structure tied to in-target delivery."),
    # ---- Halcyon Retail (061) ----
    dict(doc_id="DM008", advertiser_id="ADV0061", advertiser_name="Halcyon Retail (061)", campaign_id="CMP-HR-02",
         doc_type="recap", source="Late-Night Wrap", effective_date="2026-08-12",
         content="Halcyon Retail late-night wrap flagged under-delivery and viewability concerns on late-night inventory. Delivery finished behind booked impressions; we offered a make-good in daytime and primetime to recover the shortfall before renewal."),
    dict(doc_id="DM009", advertiser_id="ADV0061", advertiser_name="Halcyon Retail (061)", campaign_id=None,
         doc_type="qbr", source="Budget QBR", effective_date="2026-08-22",
         content="Halcyon Retail QBR: renewal at risk amid budget scrutiny. Client evaluating spend efficiency; we presented reach-efficiency gains and committed to a delivery guarantee for the renewal flight."),
    # ---- Atlas Retail (070) ----
    dict(doc_id="DM010", advertiser_id="ADV0070", advertiser_name="Atlas Retail (070)", campaign_id="CMP-AR-03",
         doc_type="recap", source="Scatter Wrap Report", effective_date="2026-08-10",
         content="Atlas Retail scatter wrap: under-delivery across scatter buys with pacing well below plan. We proactively offered make-good weight and flagged viewability softness on app inventory."),
    dict(doc_id="DM011", advertiser_id="ADV0070", advertiser_name="Atlas Retail (070)", campaign_id="CMP-AR-03",
         doc_type="contract", source="Renewal Terms w/ Viewability SLA", effective_date="2026-03-15",
         content="Atlas Retail renewal terms include a viewability SLA of 70% on all digital placements and a delivered-impressions guarantee, with make-good credits for shortfalls. We promised priority access to primetime sports at renewal."),
    # ---- Polaris Brands (045) ----
    dict(doc_id="DM012", advertiser_id="ADV0045", advertiser_name="Polaris Brands (045)", campaign_id="CMP-PB-01",
         doc_type="contract", source="Upfront Commitment", effective_date="2026-01-20",
         content="Polaris Brands upfront commitment with an audience-delivery guarantee against a P2+ target and a locked CPM. Make-good terms apply for any under-delivery below the guaranteed impression floor."),
    dict(doc_id="DM013", advertiser_id="ADV0045", advertiser_name="Polaris Brands (045)", campaign_id="CMP-PB-01",
         doc_type="recap", source="CPG Wrap Report", effective_date="2026-08-19",
         content="Polaris Brands CPG wrap: strong delivery on plan with healthy in-target audience quality and viewability above benchmark. No make-good required; positioned for a clean renewal."),
    # ---- Emberly Retail (126) ----
    dict(doc_id="DM014", advertiser_id="ADV0126", advertiser_name="Emberly Retail (126)", campaign_id="CMP-ER-04",
         doc_type="recap", source="Holiday Wrap", effective_date="2026-08-05",
         content="Emberly Retail holiday campaign under-delivered booked impressions as demand outstripped supply. We flagged the shortfall and proposed make-good inventory in the following quarter; viewability held at benchmark."),
    # ---- Pioneer Communications (134) ----
    dict(doc_id="DM015", advertiser_id="ADV0134", advertiser_name="Pioneer Communications (134)", campaign_id=None,
         doc_type="qbr", source="Telco Renewal QBR", effective_date="2026-08-26",
         content="Pioneer Communications renewal QBR under competitive pressure. Client comparing partners on delivery reliability; we emphasized our make-good track record and proposed a delivery guarantee to secure the renewal."),
]

s = spark()

# --- UC Volume + land files (governance: docs in a UC Volume) ---
s.sql(f"CREATE VOLUME IF NOT EXISTS {FQ}.deal_memory")
w = wc()
vol = f"/Volumes/{CATALOG}/{SCHEMA}/deal_memory"
import io
for d in DOCS:
    body = f"# {d['advertiser_name']} — {d['doc_type']} — {d['source']} ({d['effective_date']})\n\n{d['content']}\n".encode()
    try:
        w.files.upload(f"{vol}/{d['doc_id']}.txt", io.BytesIO(body), overwrite=True)
    except Exception as e:
        print("volume upload skipped for", d["doc_id"], ":", str(e)[:80])

# --- embed all docs in one batch call ---
emb = w.serving_endpoints.query(name=EMBED_ENDPOINT, input=[d["content"] for d in DOCS])
vecs = [list(map(float, e.embedding)) for e in emb.data]
for d, v in zip(DOCS, vecs):
    d["embedding"] = v

schema = T.StructType([
    T.StructField("doc_id", T.StringType()), T.StructField("advertiser_id", T.StringType()),
    T.StructField("advertiser_name", T.StringType()), T.StructField("campaign_id", T.StringType()),
    T.StructField("doc_type", T.StringType()), T.StructField("source", T.StringType()),
    T.StructField("effective_date", T.StringType()), T.StructField("content", T.StringType()),
    T.StructField("embedding", T.ArrayType(T.DoubleType())),
])
df = s.createDataFrame([tuple(d.get(k) for k in
      ["doc_id","advertiser_id","advertiser_name","campaign_id","doc_type","source","effective_date","content","embedding"])
      for d in DOCS], schema)
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.deal_docs")
print("deal_docs rows:", s.table(f"{FQ}.deal_docs").count(), "| volume:", vol)

# --- verify retrieval for the two narrative questions (in-Python cosine) ---
import math
def cos(a, b):
    dot = sum(x*y for x, y in zip(a, b)); na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0.0
def topk(q, k=3):
    qv = list(map(float, w.serving_endpoints.query(name=EMBED_ENDPOINT, input=[q]).data[0].embedding))
    scored = sorted(((cos(qv, d["embedding"]), d) for d in DOCS), key=lambda t: -t[0])
    return [(round(sc,3), d["advertiser_name"], d["doc_type"], d["source"]) for sc, d in scored[:k]]
print("\nQ: What did we promise Meridian in their last renewal?")
for r in topk("What did we promise Meridian in their last renewal?"): print("  ", r)
print("\nQ: Which recaps flagged viewability or under-delivery concerns?")
for r in topk("Which recaps flagged viewability or under-delivery concerns?"): print("  ", r)

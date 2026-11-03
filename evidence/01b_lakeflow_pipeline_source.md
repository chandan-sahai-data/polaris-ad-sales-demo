# Stage 1b — Lakeflow pipeline source code (deployed = repo)

_Captured live from `https://fevm-cs-genie-research.cloud.databricks.com` at 2026-11-03 07:10:53 UTC by `evidence/capture_evidence.py`._

This is the transformation code the deployed Lakeflow Spark Declarative Pipeline executes, exported from the workspace via `GET /api/2.0/workspace/export` for pipeline `42e57d29-404f-4c9d-a677-5c0b6d8fba90` and compared (SHA-256) against the repo copy.

**Deployed pipeline libraries vs. repo**

| deployed workspace file | repo file | sha256 deployed | sha256 repo | match |
|---|---|---|---|---|
| /Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/bronze.py | build/dabs/src/bronze.py | e4f4490d339be1ac | e4f4490d339be1ac | IDENTICAL |
| /Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/silver.py | build/dabs/src/silver.py | 340f2cf496acb698 | 340f2cf496acb698 | IDENTICAL |
| /Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/gold.py | build/dabs/src/gold.py | be3e18b820accfec | be3e18b820accfec | IDENTICAL |
| /Workspace/Users/chandan.sahai@databricks.com/.bundle/ad_sales_renewal_intelligence/dev/files/src/gold_risk.py | build/dabs/src/gold_risk.py | 24d920708589734b | 24d920708589734b | IDENTICAL |

**Pipeline definition (Declarative Automation Bundle)** — `build/dabs/resources/ad_sales_ingestion.pipeline.yml`

```yaml
resources:
  pipelines:
    ad_sales_ingestion:
      name: "Ad Sales Ingestion (${var.catalog}.${var.schema})"
      catalog: ${var.catalog}
      schema: ${var.schema}
      serverless: true
      channel: CURRENT
      photon: true
      development: true
      libraries:
        - file:
            path: ../src/bronze.py
        - file:
            path: ../src/silver.py
        - file:
            path: ../src/gold.py
        - file:
            path: ../src/gold_risk.py
      configuration:
        source_catalog: ${var.catalog}
        source_schema: ${var.schema}

```

**Bundle root** — `build/dabs/databricks.yml`

```yaml
bundle:
  name: ad_sales_renewal_intelligence

variables:
  catalog:
    default: cs_genie_research_catalog
  schema:
    default: ad_sales

targets:
  dev:
    default: true
    mode: development
    workspace:
      host: https://fevm-cs-genie-research.cloud.databricks.com

include:
  - resources/*.yml

```


Layer map: `bronze.py` = 4 streaming tables reading the raw landing tables (`spark.readStream`, ingest timestamp); `silver.py` = 4 materialized views with `@dp.expect_all_or_drop` data-quality expectations + dedup on natural keys; `gold.py` = `gold_campaign_advertiser` (ad server + CRM + Nielsen joined at campaign grain) and `gold_advertiser_book`; `gold_risk.py` = rules-based v0 risk score (superseded by the ML score in stage 3). Execution of exactly these flows is shown in [01_lakeflow_ingest.md](01_lakeflow_ingest.md).


## `build/dabs/src/bronze.py`

```python
"""Bronze — ingest the three source systems as streaming tables.

Models the production ingestion path this stands in for:
  ad-server  -> live CDC-style signal (near-current last_refresh)
  CRM        -> operational feed
  Nielsen    -> LAGGED batch measurement feed (3-7d stale)
Each bronze table preserves source_system + last_refresh and stamps an ingest timestamp.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

CAT = spark.conf.get("source_catalog")
SCH = spark.conf.get("source_schema")

def _src(name):
    return f"{CAT}.{SCH}.{name}"

def _bronze(target, raw):
    @dp.table(name=target, comment=f"Bronze ingest of {raw}")
    def _fn():
        return (spark.readStream
                .option("skipChangeCommits", "true")
                .table(_src(raw))
                .withColumn("_ingested_at", F.current_timestamp()))
    return _fn

bronze_ad_server     = _bronze("bronze_ad_server",     "ad_server_lineitems_raw")
bronze_crm_accounts  = _bronze("bronze_crm_accounts",  "crm_accounts_raw")
bronze_crm_deals     = _bronze("bronze_crm_deals",     "crm_deals_raw")
bronze_nielsen       = _bronze("bronze_nielsen",       "nielsen_measurement_raw")

```


## `build/dabs/src/silver.py`

```python
"""Silver — clean & conform each source with data-quality EXPECTATIONS.

Materialized views (batch read of the bronze streaming tables) so dedup on natural
keys is trivial and expectation results are visible in the pipeline UI.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# ---- silver_ad_server (line-item grain) ----
@dp.materialized_view(name="silver_ad_server", comment="Conformed ad-server line items")
@dp.expect_all_or_drop({
    "valid_campaign": "campaign_id IS NOT NULL",
    "valid_advertiser": "advertiser_id IS NOT NULL",
    "valid_sales_type": "sales_type IN ('upfront','scatter')",
    "positive_booked": "booked_impressions > 0",
    "delivered_in_bounds": "delivered_impressions BETWEEN 0 AND booked_impressions * 1.5",
})
def silver_ad_server():
    df = spark.read.table("bronze_ad_server")
    w = Window.partitionBy("order_id").orderBy(F.col("_ingested_at").desc())
    return (df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
        .withColumn("pacing_ratio", F.round(F.col("delivered_impressions") / F.col("booked_impressions"), 4))
        .withColumn("under_delivered", (F.col("delivered_impressions") < 0.95 * F.col("booked_impressions")).cast("int"))
        .withColumn("pct_flight_elapsed", F.round(F.least(F.lit(1.0), F.greatest(F.lit(0.0),
            F.datediff(F.current_date(), F.col("flight_start")) /
            F.greatest(F.lit(1), F.datediff(F.col("flight_end"), F.col("flight_start"))))), 3))
        .withColumnRenamed("last_refresh", "adserver_last_refresh"))

# ---- silver_crm_accounts ----
@dp.materialized_view(name="silver_crm_accounts", comment="Conformed CRM accounts")
@dp.expect_all_or_drop({
    "valid_advertiser": "advertiser_id IS NOT NULL",
    "valid_category": "category IS NOT NULL",
})
def silver_crm_accounts():
    df = spark.read.table("bronze_crm_accounts")
    w = Window.partitionBy("advertiser_id").orderBy(F.col("_ingested_at").desc())
    return (df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
        .withColumnRenamed("last_refresh", "crm_last_refresh"))

# ---- silver_crm_deals ----
@dp.materialized_view(name="silver_crm_deals", comment="Conformed CRM deals (current + historical)")
@dp.expect_all_or_drop({
    "valid_deal": "deal_id IS NOT NULL",
    "valid_advertiser": "advertiser_id IS NOT NULL",
    "positive_value": "contract_value > 0",
})
def silver_crm_deals():
    df = spark.read.table("bronze_crm_deals")
    w = Window.partitionBy("deal_id").orderBy(F.col("_ingested_at").desc())
    return (df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
        .withColumn("days_to_renewal", F.datediff(F.col("renewal_date"), F.current_date())))

# ---- silver_nielsen ----
@dp.materialized_view(name="silver_nielsen", comment="Conformed Nielsen measurement (lagged feed)")
@dp.expect_all_or_drop({
    "valid_campaign": "campaign_id IS NOT NULL",
    "in_target_bounds": "in_target_pct BETWEEN 0 AND 1",
})
def silver_nielsen():
    df = spark.read.table("bronze_nielsen")
    w = Window.partitionBy("campaign_id").orderBy(F.col("_ingested_at").desc())
    return (df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
        .withColumn("reach_delivery_pct", F.round(F.col("delivered_reach") / F.col("planned_reach"), 4))
        .withColumnRenamed("last_refresh", "nielsen_last_refresh"))

```


## `build/dabs/src/gold.py`

```python
"""Gold — unified business tables.

gold_campaign_advertiser : one row per campaign (ad-server + CRM + Nielsen), the canonical
                           table the metric views / risk model / Genie / dashboard read.
gold_advertiser_book     : advertiser grain rollup with the current deal.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.materialized_view(
    name="gold_campaign_advertiser",
    comment="One row per campaign joining ad-server delivery, CRM deal/account, and Nielsen reach.")
def gold_campaign_advertiser():
    # aggregate line items -> campaign
    ad = spark.read.table("silver_ad_server")
    camp = (ad.groupBy("campaign_id", "advertiser_id").agg(
        F.sum("booked_impressions").alias("booked_impressions"),
        F.sum("delivered_impressions").alias("delivered_impressions"),
        F.sum("booked_spend").alias("booked_spend"),
        F.sum("inventory_units_booked").alias("inventory_units_booked"),
        F.sum("inventory_units_available").alias("inventory_units_available"),
        F.expr("mode(daypart)").alias("daypart"),
        F.expr("mode(sales_type)").alias("sales_type"),
        F.expr("mode(network)").alias("network"),
        F.avg("pct_flight_elapsed").alias("pct_flight_elapsed"),
        F.count("*").alias("line_item_count"),
        F.max("adserver_last_refresh").alias("adserver_last_refresh"),
    )
    .withColumn("pacing_index", F.round(F.col("delivered_impressions") / F.col("booked_impressions"), 4))
    .withColumn("delivery_vs_commitment", F.round(F.col("delivered_impressions") / F.col("booked_impressions"), 4))
    .withColumn("effective_cpm", F.round(F.col("booked_spend") / (F.col("delivered_impressions") / 1000.0), 2))
    .withColumn("cpm_booked", F.round(F.col("booked_spend") / (F.col("booked_impressions") / 1000.0), 2))
    .withColumn("sellout_pct", F.round(F.col("inventory_units_booked") / F.col("inventory_units_available"), 4))
    .withColumn("under_delivered", (F.col("delivered_impressions") < 0.95 * F.col("booked_impressions")).cast("int")))

    acct = spark.read.table("silver_crm_accounts").select(
        "advertiser_id", "advertiser_name", "category", "region", "account_owner", "crm_last_refresh")

    deal = (spark.read.table("silver_crm_deals").filter("is_historical = false")
        .select("advertiser_id", "deal_id", "stage", "contract_value", "renewal_date",
                "renewal_window", "upfront_commit_flag", "days_to_renewal"))

    niel = spark.read.table("silver_nielsen").select(
        "campaign_id", "target_demo", "planned_reach", "delivered_reach", "reach_delivery_pct",
        "gross_rating_points", "target_audience_impressions", "in_target_pct", "avg_frequency",
        "audience_quality_score", "nielsen_last_refresh")

    return (camp
        .join(acct, "advertiser_id", "left")
        .join(deal, "advertiser_id", "left")
        .join(niel, "campaign_id", "left")
        .withColumn("reach_efficiency", F.round(F.col("target_audience_impressions") / F.col("booked_spend"), 2)))


@dp.materialized_view(
    name="gold_advertiser_book",
    comment="Advertiser-grain rollup of campaign delivery + the current renewal deal.")
def gold_advertiser_book():
    g = spark.read.table("gold_campaign_advertiser")
    rollup = (g.groupBy("advertiser_id", "advertiser_name", "category", "region", "account_owner",
                        "contract_value", "renewal_date", "renewal_window", "upfront_commit_flag",
                        "days_to_renewal", "stage")
        .agg(
            F.count("*").alias("campaign_count"),
            F.sum("under_delivered").alias("campaigns_behind"),
            F.round(F.avg("pacing_index"), 4).alias("avg_pacing_index"),
            F.round(F.avg("delivery_vs_commitment"), 4).alias("avg_delivery_vs_commitment"),
            F.round(F.avg("in_target_pct"), 4).alias("avg_in_target_pct"),
            F.round(F.avg("reach_delivery_pct"), 4).alias("avg_reach_delivery_pct"),
            F.round(F.avg("audience_quality_score"), 2).alias("avg_audience_quality"),
            F.sum("booked_spend").alias("total_booked_spend"),
            F.sum("booked_impressions").alias("total_booked_impressions"),
            F.sum("delivered_impressions").alias("total_delivered_impressions"),
        )
        .withColumn("shortfall_rate", F.round(F.col("campaigns_behind") / F.col("campaign_count"), 4)))
    return rollup

```


## `build/dabs/src/gold_risk.py`

```python
"""Gold risk — rules-based composite renewal-risk score (v0).

This is the v0 the pipeline computes from ingested data. Step 4 TRAINS two models
(delivery-shortfall classifier + renewal-risk) and writes advertiser_risk_scores, which
the metric view / dashboard / Genie / app then read instead. Kept here so the pipeline
produces an end-to-end risk table even before ML runs.

composite = 0.40*delivery + 0.25*audience + 0.35*urgency  (each 0-100)
tiers calibrated High>=52 / Med>=40.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

def _clip01(c):
    return F.least(F.lit(1.0), F.greatest(F.lit(0.0), c))

@dp.materialized_view(
    name="gold_advertiser_renewal_risk",
    comment="Rules-based composite renewal-risk score per advertiser (v0; superseded by advertiser_risk_scores in step 4).")
def gold_advertiser_renewal_risk():
    b = spark.read.table("gold_advertiser_book")

    delivery = 100 * _clip01(0.6 * F.col("shortfall_rate") + 0.4 * (1 - F.least(F.lit(1.0), F.col("avg_pacing_index"))))
    audience = 100 * _clip01(0.5 * (1 - F.coalesce(F.col("avg_in_target_pct"), F.lit(0.7)))
                             + 0.5 * (1 - F.least(F.lit(1.0), F.coalesce(F.col("avg_reach_delivery_pct"), F.lit(0.85)))))
    urgency = F.when(F.col("renewal_window") == "renews_this_quarter",
                     100 * _clip01(1 - F.col("days_to_renewal") / F.lit(120.0))) \
               .when(F.col("renewal_window") == "renews_next_quarter", F.lit(45.0)) \
               .otherwise(F.lit(15.0))

    df = (b
        .withColumn("delivery_risk", F.round(delivery, 1))
        .withColumn("audience_risk", F.round(audience, 1))
        .withColumn("urgency_risk", F.round(urgency, 1))
        .withColumn("risk_score", F.round(0.40 * delivery + 0.25 * audience + 0.35 * urgency, 1))
        .withColumn("risk_tier", F.when(F.col("risk_score") >= 52, "High")
                                  .when(F.col("risk_score") >= 40, "Medium").otherwise("Low"))
        .withColumn("revenue_at_risk", F.round(F.col("contract_value") * F.col("risk_score") / 100.0, 0))
        .withColumn("contributing_factors", F.concat_ws(" | ",
            F.when(F.col("shortfall_rate") > 0.3, F.concat(F.lit("Delivery shortfall on "),
                   F.format_string("%.0f%%", F.col("shortfall_rate") * 100), F.lit(" of campaigns"))),
            F.when(F.col("avg_in_target_pct") < 0.7, F.lit("Low in-target audience delivery")),
            F.when((F.col("renewal_window") == "renews_this_quarter") & (F.col("days_to_renewal") <= 30),
                   F.concat(F.lit("Renews in "), F.col("days_to_renewal").cast("string"), F.lit(" days"))),
            F.when(F.col("upfront_commit_flag"), F.lit("Upfront commitment at stake")))))
    return df.select(
        "advertiser_id", "advertiser_name", "category", "region", "account_owner",
        "contract_value", "renewal_date", "renewal_window", "days_to_renewal", "upfront_commit_flag",
        "campaign_count", "campaigns_behind", "shortfall_rate", "avg_pacing_index",
        "avg_in_target_pct", "avg_reach_delivery_pct", "avg_audience_quality",
        "delivery_risk", "audience_risk", "urgency_risk",
        "risk_score", "risk_tier", "revenue_at_risk", "contributing_factors")

```


## Raw landing-data generator — `build/generate_landing_data.py`

Produces the four `_raw` tables the bronze layer ingests.

```python
"""Step 1 — Landing data: three source systems (native Spark, no pandas UDFs).

Produces the _raw tables the SDP pipeline ingests in step 2:
  crm_accounts_raw        (~150)  mimics Salesforce accounts
  crm_deals_raw           (~300)  mimics Salesforce deals (current + historical-with-outcome)
  ad_server_lineitems_raw (~770)  mimics GAM/FreeWheel ad server (line-item grain)
  nielsen_measurement_raw (~600)  mimics a LAGGED Nielsen feed (3-7d stale)

Design that feeds later steps:
  * Every row carries source_system + last_refresh (ad-server near-current; CRM ~1d; Nielsen 3-7d stale).
  * Under-delivery is DRIVER-DEPENDENT (scatter / off-peak daypart / CTV) so Model A (step 4) has signal.
  * Historical deals carry a resolved renewed/lapsed outcome so Model B (step 4) has churn labels.
  * Deterministic: all randomness via pmod(hash(id,'salt'), N) so re-runs reproduce.
  * Advertiser 1 is forced to the hero: Meridian Restaurants (QSR), renews in 10 days, mostly behind.
"""
from pyspark.sql import functions as F
from config import spark, FQ, N_ADVERTISERS, N_CAMPAIGNS, ANCHOR_TODAY

s = spark()

def U(idcol, salt, n=100000):
    """Deterministic uniform [0,1) from an id column + salt."""
    return (F.pmod(F.hash(F.col(idcol), F.lit(salt)), F.lit(n)) / F.lit(float(n)))

def PICK(idcol, salt, arr):
    """Deterministic pick from a python list."""
    idx = F.pmod(F.hash(F.col(idcol), F.lit(salt)), F.lit(len(arr)))
    return F.element_at(F.array(*[F.lit(x) for x in arr]), idx + F.lit(1))

CATEGORIES = ["Auto", "QSR", "CPG", "Retail", "Telco", "Pharma"]
REGIONS    = ["Northeast", "Southeast", "Midwest", "West", "National"]
OWNERS     = ["A. Rivera", "B. Chen", "C. Okafor", "D. Novak", "E. Santos", "F. Kim", "G. Patel", "H. Larsson"]
NETWORKS   = ["Flagship Broadcast", "Sports Net", "News 24", "Lifestyle", "CTV App", "Kids"]
DAYPARTS   = ["Morning", "Daytime", "Primetime", "LateNight"]
DEMOS      = ["A18-49", "A25-54", "W18-34", "M18-49", "P2+"]
PREFIXES   = ["Meridian", "Pioneer", "Summit", "Atlas", "Vertex", "Beacon", "Cascade", "Harbor",
              "Ironwood", "Northstar", "Cobalt", "Emberly", "Falcon", "Granite", "Halcyon",
              "Juniper", "Keystone", "Lumen", "Monarch", "Nimbus", "Onyx", "Polaris", "Quill",
              "Riverstone", "Solace", "Tundra", "Umbra", "Vantage", "Willow", "Zephyr"]
SUFFIX = {"Auto": "Motors", "QSR": "Restaurants", "CPG": "Brands", "Retail": "Retail",
          "Telco": "Communications", "Pharma": "Health"}

# ---------------------------------------------------------------- accounts
adv = s.range(1, N_ADVERTISERS + 1).withColumnRenamed("id", "n")
adv = (adv
    .withColumn("advertiser_id", F.format_string("ADV%04d", F.col("n")))
    .withColumn("category", PICK("advertiser_id", "cat", CATEGORIES))
    .withColumn("region",   PICK("advertiser_id", "reg", REGIONS))
    .withColumn("account_owner", PICK("advertiser_id", "own", OWNERS))
    .withColumn("_pfx", PICK("advertiser_id", "pfx", PREFIXES))
    .withColumn("_suf", F.element_at(F.map_from_arrays(
        F.array(*[F.lit(k) for k in SUFFIX]), F.array(*[F.lit(v) for v in SUFFIX.values()])), F.col("category")))
    .withColumn("advertiser_name", F.concat_ws(" ", F.col("_pfx"), F.col("_suf"), F.format_string("(%03d)", F.col("n"))))
)
# Force the hero
adv = adv.withColumn("category",        F.when(F.col("n") == 1, F.lit("QSR")).otherwise(F.col("category"))) \
         .withColumn("advertiser_name", F.when(F.col("n") == 1, F.lit("Meridian Restaurants")).otherwise(F.col("advertiser_name"))) \
         .withColumn("region",          F.when(F.col("n") == 1, F.lit("National")).otherwise(F.col("region")))
accounts = (adv.select("advertiser_id", "advertiser_name", "category", "region", "account_owner")
    .withColumn("source_system", F.lit("Salesforce_CRM"))
    .withColumn("last_refresh", F.expr("current_timestamp() - INTERVAL 8 HOURS")))
accounts.write.mode("overwrite").saveAsTable(f"{FQ}.crm_accounts_raw")

# ---------------------------------------------------------------- deals (current + historical)
anchor = F.to_date(F.lit(ANCHOR_TODAY))
# advertiser-level "health" latent (0=healthy .. 1=troubled), drives both delivery & churn
adv_health = adv.select("advertiser_id", "category", U("advertiser_id", "health").alias("health"))

# CURRENT deals — one per advertiser, up for renewal
cur = (adv.select("advertiser_id", "n")
    .withColumn("deal_id", F.format_string("DL%04d-C", F.col("n")))
    .withColumn("is_historical", F.lit(False))
    .withColumn("stage", PICK("deal_id", "stg", ["Renewal Pending", "Negotiation", "Proposal Sent"]))
    .withColumn("contract_value", F.round(F.lit(200000) + U("deal_id", "cv") * F.lit(3800000), 0))
    .withColumn("_rw_u", U("deal_id", "rw"))
    .withColumn("renewal_window", F.when(F.col("_rw_u") < 0.42, "renews_this_quarter")
                                   .when(F.col("_rw_u") < 0.78, "renews_next_quarter")
                                   .otherwise("already_in_scatter"))
    .withColumn("_days", F.when(F.col("renewal_window") == "renews_this_quarter", (U("deal_id", "d") * 85 + 3).cast("int"))
                          .when(F.col("renewal_window") == "renews_next_quarter", (U("deal_id", "d") * 85 + 95).cast("int"))
                          .otherwise((U("deal_id", "d") * 60 - 90).cast("int")))
    .withColumn("renewal_date", F.date_add(anchor, F.col("_days")))
    .withColumn("deal_start", F.date_add(F.col("renewal_date"), -365))
    .withColumn("deal_end", F.col("renewal_date"))
    .withColumn("upfront_commit_flag", (U("deal_id", "uf") < 0.6))
    .withColumn("renewed", F.lit(None).cast("int")))
# Force hero: renews in 10 days, this quarter, upfront, $2.2M
cur = (cur.withColumn("renewal_window", F.when(F.col("n") == 1, F.lit("renews_this_quarter")).otherwise(F.col("renewal_window")))
          .withColumn("renewal_date", F.when(F.col("n") == 1, F.date_add(anchor, 10)).otherwise(F.col("renewal_date")))
          .withColumn("deal_end", F.when(F.col("n") == 1, F.date_add(anchor, 10)).otherwise(F.col("deal_end")))
          .withColumn("contract_value", F.when(F.col("n") == 1, F.lit(2200000.0)).otherwise(F.col("contract_value")))
          .withColumn("upfront_commit_flag", F.when(F.col("n") == 1, F.lit(True)).otherwise(F.col("upfront_commit_flag"))))

# HISTORICAL deals — prior renewal cycle with a resolved outcome (renewed/lapsed) => Model B labels.
# Churn correlated with advertiser health so the model can learn.
hist = (adv_health.join(adv.select("advertiser_id", "n"), "advertiser_id")
    .withColumn("deal_id", F.format_string("DL%04d-H", F.col("n")))
    .withColumn("is_historical", F.lit(True))
    .withColumn("_churn_p", F.least(F.lit(0.92), F.greatest(F.lit(0.03), F.col("health") * 0.8 + U("deal_id", "nz") * 0.2 - 0.1)))
    .withColumn("renewed", (U("deal_id", "out") > F.col("_churn_p")).cast("int"))
    .withColumn("stage", F.when(F.col("renewed") == 1, F.lit("Renewed")).otherwise(F.lit("Lapsed")))
    .withColumn("contract_value", F.round(F.lit(180000) + U("deal_id", "cv") * F.lit(3600000), 0))
    .withColumn("renewal_date", F.date_add(anchor, -(180 + (U("deal_id", "d") * 90).cast("int"))))
    .withColumn("deal_start", F.date_add(F.col("renewal_date"), -365))
    .withColumn("deal_end", F.col("renewal_date"))
    .withColumn("renewal_window", F.lit("already_in_scatter"))
    .withColumn("upfront_commit_flag", (U("deal_id", "uf") < 0.5)))

deal_cols = ["deal_id", "advertiser_id", "stage", "contract_value", "deal_start", "deal_end",
             "renewal_date", "upfront_commit_flag", "renewal_window", "is_historical", "renewed"]
deals = (cur.select(*deal_cols).unionByName(hist.select(*deal_cols))
    .withColumn("source_system", F.lit("Salesforce_CRM"))
    .withColumn("last_refresh", F.expr("current_timestamp() - INTERVAL 20 HOURS")))
deals.write.mode("overwrite").saveAsTable(f"{FQ}.crm_deals_raw")

# ---------------------------------------------------------------- ad server line items (~770)
# 600 campaigns; ~28% get a 2nd line item. campaign->advertiser via modulo mapping.
camp = s.range(1, N_CAMPAIGNS + 1).withColumnRenamed("id", "c")
camp = (camp
    .withColumn("campaign_id", F.format_string("CMP%05d", F.col("c")))
    .withColumn("advertiser_id", F.format_string("ADV%04d", F.pmod(F.hash(F.col("campaign_id"), F.lit("amap")), F.lit(N_ADVERTISERS)) + F.lit(1)))
    .withColumn("_extra", (U("campaign_id", "extra") < 0.28)))
li_extra = camp.filter(F.col("_extra")).withColumn("li", F.lit(2))
li = camp.withColumn("li", F.lit(1)).unionByName(li_extra)
li = (li.join(adv_health.select("advertiser_id", "health"), "advertiser_id", "left")
    .withColumn("order_id", F.format_string("ORD-%s-%d", F.col("campaign_id"), F.col("li")))
    .withColumn("_lisalt", F.concat(F.col("campaign_id"), F.lit("-"), F.col("li")))
    .withColumn("network", PICK("_lisalt", "net", NETWORKS))
    .withColumn("daypart", PICK("_lisalt", "dp", DAYPARTS))
    .withColumn("_st_u", U("_lisalt", "st"))
    .withColumn("sales_type", F.when(F.col("_st_u") < 0.55, "upfront").otherwise("scatter"))
    .withColumn("booked_impressions", F.round(F.lit(500000) + U("_lisalt", "bi") * F.lit(9500000), 0))
    .withColumn("cpm_booked", F.round(F.lit(8) + U("_lisalt", "cpm") * F.lit(37), 2))
    .withColumn("booked_spend", F.round(F.col("booked_impressions") / 1000 * F.col("cpm_booked"), 2))
    .withColumn("inventory_units_booked", F.round(F.lit(50) + U("_lisalt", "iub") * F.lit(450), 0))
    # inventory tightness: available only modestly above booked when scarce
    .withColumn("inventory_units_available", F.round(F.col("inventory_units_booked") * (F.lit(1.02) + U("_lisalt", "iua") * F.lit(0.9)), 0))
    # flight window straddles anchor; some completed, some active
    .withColumn("_fs_off", (U("_lisalt", "fs") * 70 - 45).cast("int"))
    .withColumn("flight_start", F.date_add(F.to_date(F.lit(ANCHOR_TODAY)), F.col("_fs_off")))
    .withColumn("flight_end", F.date_add(F.col("flight_start"), (F.lit(20) + U("_lisalt", "fl") * F.lit(45)).cast("int")))
    # DRIVER-DEPENDENT pacing: base ~1.0 minus penalties for scatter / off-peak / CTV / troubled advertiser
    .withColumn("_pen", (F.when(F.col("sales_type") == "scatter", 0.12).otherwise(0.0)
                       + F.when(F.col("daypart").isin("LateNight", "Daytime"), 0.10).otherwise(0.0)
                       + F.when(F.col("network") == "CTV App", 0.09).otherwise(0.0)
                       + F.coalesce(F.col("health"), F.lit(0.4)) * 0.18))
    .withColumn("_pacing", F.greatest(F.lit(0.45), F.least(F.lit(1.15),
                 F.lit(1.06) - F.col("_pen") + (U("_lisalt", "noise") - 0.5) * 0.16)))
    .withColumn("delivered_impressions", F.round(F.col("booked_impressions") * F.col("_pacing"), 0)))
# Force hero campaigns mostly behind (2 of ~3): advertiser ADV0001 line items get depressed pacing
li = li.withColumn("delivered_impressions",
        F.when(F.col("advertiser_id") == "ADV0001",
               F.round(F.col("booked_impressions") * F.lit(0.82), 0)).otherwise(F.col("delivered_impressions")))
li_out = (li.select("campaign_id", "advertiser_id", "order_id", "network", "daypart", "sales_type",
                    "flight_start", "flight_end", "booked_impressions", "delivered_impressions",
                    "booked_spend", "cpm_booked", "inventory_units_booked", "inventory_units_available")
    .withColumn("source_system", F.lit("GAM_AdServer"))
    .withColumn("last_refresh", F.expr("current_timestamp() - INTERVAL 12 MINUTES")))
li_out.write.mode("overwrite").saveAsTable(f"{FQ}.ad_server_lineitems_raw")

# ---------------------------------------------------------------- nielsen (~600, lagged)
niel = (camp.select("campaign_id", "advertiser_id")
    .join(adv_health.select("advertiser_id", "health"), "advertiser_id", "left")
    .withColumn("target_demo", PICK("campaign_id", "demo", DEMOS))
    .withColumn("planned_reach", F.round(F.lit(1000000) + U("campaign_id", "pr") * F.lit(14000000), 0))
    .withColumn("_reach_eff", F.greatest(F.lit(0.55), F.least(F.lit(1.05), F.lit(0.98) - F.coalesce(F.col("health"), F.lit(0.4)) * 0.22 + (U("campaign_id", "rn") - 0.5) * 0.14)))
    .withColumn("delivered_reach", F.round(F.col("planned_reach") * F.col("_reach_eff"), 0))
    .withColumn("gross_rating_points", F.round(F.lit(50) + U("campaign_id", "grp") * F.lit(250), 1))
    .withColumn("target_audience_impressions", F.round(F.col("delivered_reach") * (F.lit(2) + U("campaign_id", "tai") * F.lit(4)), 0))
    .withColumn("in_target_pct", F.round(F.lit(0.55) + F.col("_reach_eff") * F.lit(0.35), 3))
    .withColumn("avg_frequency", F.round(F.lit(1.5) + U("campaign_id", "freq") * F.lit(4), 2))
    .withColumn("audience_quality_score", F.round(F.lit(50) + F.col("_reach_eff") * F.lit(45), 1))
    .withColumn("source_system", F.lit("Nielsen_ONE"))
    # LAGGED feed: 3-7 days stale
    .withColumn("last_refresh", F.expr("current_timestamp() - make_interval(0,0,0, cast(3 + pmod(hash(campaign_id,'lag'),5) as int),0,0,0)"))
    .select("campaign_id", "advertiser_id", "target_demo", "planned_reach", "delivered_reach",
            "gross_rating_points", "target_audience_impressions", "in_target_pct", "avg_frequency",
            "audience_quality_score", "source_system", "last_refresh"))
niel.write.mode("overwrite").saveAsTable(f"{FQ}.nielsen_measurement_raw")

# ---------------------------------------------------------------- report
print("=== ROW COUNTS ===")
for t in ["crm_accounts_raw", "crm_deals_raw", "ad_server_lineitems_raw", "nielsen_measurement_raw"]:
    print(f"{t:28s}", s.table(f"{FQ}.{t}").count())
print("\n=== deals: current vs historical, churn balance ===")
s.sql(f"SELECT is_historical, count(*) n, sum(coalesce(renewed,0)) renewed FROM {FQ}.crm_deals_raw GROUP BY is_historical ORDER BY is_historical").show()
print("=== ad_server pacing distribution ===")
s.sql(f"SELECT round(delivered_impressions/booked_impressions,1) pace, count(*) n FROM {FQ}.ad_server_lineitems_raw GROUP BY 1 ORDER BY 1").show(30, False)
print("=== hero (Meridian) ===")
s.sql(f"""SELECT a.advertiser_name, d.contract_value, d.renewal_date, d.renewal_window,
          (SELECT count(*) FROM {FQ}.ad_server_lineitems_raw l WHERE l.advertiser_id='ADV0001') li,
          (SELECT count(*) FROM {FQ}.ad_server_lineitems_raw l WHERE l.advertiser_id='ADV0001' AND l.delivered_impressions < 0.95*l.booked_impressions) behind
          FROM {FQ}.crm_accounts_raw a JOIN {FQ}.crm_deals_raw d ON a.advertiser_id=d.advertiser_id
          WHERE a.advertiser_id='ADV0001' AND d.is_historical=false""").show(truncate=False)
print("=== samples ===")
for t in ["crm_accounts_raw", "crm_deals_raw", "ad_server_lineitems_raw", "nielsen_measurement_raw"]:
    print("---", t); s.table(f"{FQ}.{t}").show(5, truncate=False)

```

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

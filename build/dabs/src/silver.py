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

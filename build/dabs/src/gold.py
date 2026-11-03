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

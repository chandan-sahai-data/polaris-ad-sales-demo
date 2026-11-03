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

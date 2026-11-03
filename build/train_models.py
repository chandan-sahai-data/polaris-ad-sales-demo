# Databricks notebook source
# MAGIC %md
# MAGIC # Ad Sales Predictive ML — delivery-shortfall classifier + renewal-risk model
# MAGIC Two models trained on the ingested gold/silver data, registered in Unity Catalog,
# MAGIC feeding an explainable composite renewal-risk score (`advertiser_risk_scores`).

# COMMAND ----------
import json
import numpy as np
import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from pyspark.sql import functions as F

# --- run locally via Databricks Connect (adapted from the notebook form) ---
import os
from config import spark as _make_spark, CATALOG, SCHEMA, FQ, PROFILE
os.environ.setdefault("DATABRICKS_CONFIG_PROFILE", PROFILE)
spark = _make_spark()
EXPERIMENT = f"/Users/chandan.sahai@databricks.com/{CATALOG}_ml_experiment"

mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(EXPERIMENT)
client = MlflowClient(registry_uri="databricks-uc")

# COMMAND ----------
# MAGIC %md ## Model A — delivery-shortfall classifier (line-item grain, real labels)

# COMMAND ----------
# advertiser historical delivery (avg pacing) as a feature
adv_hist = (spark.table(f"{FQ}.silver_ad_server")
            .groupBy("advertiser_id").agg(F.avg("pacing_ratio").alias("adv_hist_pacing")))

li = (spark.table(f"{FQ}.silver_ad_server").alias("l")
      .join(spark.table(f"{FQ}.silver_crm_accounts").select("advertiser_id", "category", "region"), "advertiser_id", "left")
      .join(spark.table(f"{FQ}.silver_nielsen").select("campaign_id", "in_target_pct", "avg_frequency", "audience_quality_score"), "campaign_id", "left")
      .join(adv_hist, "advertiser_id", "left")
      .withColumn("inv_tightness", F.col("inventory_units_booked") / F.col("inventory_units_available"))
      .select("order_id", "advertiser_id", "campaign_id", "under_delivered",
              "booked_impressions", "cpm_booked", "pct_flight_elapsed", "inv_tightness",
              F.coalesce("in_target_pct", F.lit(0.7)).alias("in_target_pct"),
              F.coalesce("avg_frequency", F.lit(3.0)).alias("avg_frequency"),
              F.coalesce("audience_quality_score", F.lit(80.0)).alias("audience_quality_score"),
              F.coalesce("adv_hist_pacing", F.lit(0.9)).alias("adv_hist_pacing"),
              "daypart", "sales_type", "network", "category", "region"))
pdf = li.toPandas()

numA = ["booked_impressions", "cpm_booked", "pct_flight_elapsed", "inv_tightness",
        "in_target_pct", "avg_frequency", "audience_quality_score", "adv_hist_pacing"]
catA = ["daypart", "sales_type", "network", "category", "region"]
XA, yA = pdf[numA + catA], pdf["under_delivered"].astype(int)
Xtr, Xte, ytr, yte = train_test_split(XA, yA, test_size=0.25, random_state=42, stratify=yA)

preA = ColumnTransformer([("num", StandardScaler(), numA),
                          ("cat", OneHotEncoder(handle_unknown="ignore"), catA)])
pipeA = Pipeline([("pre", preA), ("clf", GradientBoostingClassifier(random_state=42))])

mlflow.sklearn.autolog(log_models=False, silent=True)
with mlflow.start_run(run_name="delivery_shortfall") as runA:
    pipeA.fit(Xtr, ytr)
    pA = pipeA.predict_proba(Xte)[:, 1]
    aucA = roc_auc_score(yte, pA)
    predA = (pA >= 0.5).astype(int)
    mlflow.log_metrics({"val_auc": aucA,
                        "precision": precision_score(yte, predA, zero_division=0),
                        "recall": recall_score(yte, predA, zero_division=0)})
    infoA = mlflow.sklearn.log_model(pipeA, name="model", input_example=Xtr.head(3),
                                     registered_model_name=f"{FQ}.delivery_shortfall_model")
client.set_registered_model_alias(f"{FQ}.delivery_shortfall_model", "prod", infoA.registered_model_version)
print("Model A AUC:", round(aucA, 3), "version", infoA.registered_model_version)

# score all line items
pdf["p_shortfall"] = pipeA.predict_proba(XA)[:, 1]
scoredA = spark.createDataFrame(pdf[["order_id", "advertiser_id", "campaign_id", "p_shortfall", "under_delivered"]])
scoredA.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.ml_campaign_shortfall_scores")
adv_shortfall = pdf.groupby("advertiser_id")["p_shortfall"].mean().rename("adv_p_shortfall").reset_index()

# COMMAND ----------
# MAGIC %md ## Model B — renewal-risk model (advertiser grain, historical churn labels)

# COMMAND ----------
# labels from historical deals (renewed -> churn=0, lapsed -> churn=1)
labels = (spark.table(f"{FQ}.crm_deals_raw").filter("is_historical = true")
          .select("advertiser_id", (1 - F.col("renewed")).alias("churn")).toPandas())

book = spark.table(f"{FQ}.gold_advertiser_book").toPandas()
book = book.merge(adv_shortfall, on="advertiser_id", how="left")
train_b = book.merge(labels, on="advertiser_id", how="inner")

numB = ["avg_pacing_index", "shortfall_rate", "avg_in_target_pct", "avg_reach_delivery_pct",
        "avg_audience_quality", "days_to_renewal", "contract_value", "adv_p_shortfall", "campaigns_behind"]
catB = ["category", "region", "renewal_window"]
for c in numB:
    train_b[c] = pd.to_numeric(train_b[c], errors="coerce").fillna(train_b[c].astype(float).median() if train_b[c].notna().any() else 0)
XB, yB = train_b[numB + catB], train_b["churn"].astype(int)
XBtr, XBte, yBtr, yBte = train_test_split(XB, yB, test_size=0.25, random_state=42, stratify=yB)

preB = ColumnTransformer([("num", StandardScaler(), numB),
                          ("cat", OneHotEncoder(handle_unknown="ignore"), catB)])
pipeB = Pipeline([("pre", preB), ("clf", GradientBoostingClassifier(random_state=42))])
with mlflow.start_run(run_name="renewal_risk") as runB:
    pipeB.fit(XBtr, yBtr)
    pB = pipeB.predict_proba(XBte)[:, 1]
    aucB = roc_auc_score(yBte, pB)
    predB = (pB >= 0.5).astype(int)
    mlflow.log_metrics({"val_auc": aucB,
                        "precision": precision_score(yBte, predB, zero_division=0),
                        "recall": recall_score(yBte, predB, zero_division=0),
                        "n_labels": len(yB)})
    infoB = mlflow.sklearn.log_model(pipeB, name="model", input_example=XBtr.head(3),
                                     registered_model_name=f"{FQ}.renewal_risk_model")
client.set_registered_model_alias(f"{FQ}.renewal_risk_model", "prod", infoB.registered_model_version)
print("Model B AUC:", round(aucB, 3), "version", infoB.registered_model_version, "labels", len(yB))

# score ALL advertisers
for c in numB:
    book[c] = pd.to_numeric(book[c], errors="coerce").fillna(0)
book["p_churn"] = pipeB.predict_proba(book[numB + catB])[:, 1]

# COMMAND ----------
# MAGIC %md ## Composite renewal-risk score (explainable) -> advertiser_risk_scores

# COMMAND ----------
b = book.copy()
b["days_to_renewal"] = pd.to_numeric(b["days_to_renewal"], errors="coerce").fillna(180)
# urgency in [0,1]
def urg(row):
    if row["renewal_window"] == "renews_this_quarter":
        return float(np.clip(1 - row["days_to_renewal"] / 120.0, 0, 1))
    if row["renewal_window"] == "renews_next_quarter":
        return 0.45
    return 0.15
b["urgency"] = b.apply(urg, axis=1)
b["adv_p_shortfall"] = pd.to_numeric(b["adv_p_shortfall"], errors="coerce").fillna(0.3)

# blended, explainable composite (0-100). Delivery shortfall + urgency weighted for the
# near-term renewal book (a failing account renewing soon is at risk even if it renewed before).
b["risk_score"] = (100 * (0.35 * b["p_churn"] + 0.40 * b["adv_p_shortfall"] + 0.25 * b["urgency"])).round(1)

# calibrate tiers to ~22 High for demo continuity, with an explicit "act-today" override:
# any account renewing this quarter with materially failing delivery is High regardless of score.
hi_thr = float(np.quantile(b["risk_score"], 1 - 20/len(b)))
md_thr = float(np.quantile(b["risk_score"], 1 - 65/len(b)))
act_today = ((b["renewal_window"] == "renews_this_quarter") & (b["adv_p_shortfall"] >= 0.9)
             & (b["days_to_renewal"] <= 21))
b["risk_tier"] = np.where((b["risk_score"] >= hi_thr) | act_today, "High",
                  np.where(b["risk_score"] >= md_thr, "Medium", "Low"))
b["contract_value"] = pd.to_numeric(b["contract_value"], errors="coerce").fillna(0)
b["revenue_at_risk"] = (b["contract_value"] * b["risk_score"] / 100.0).round(0)

def factors(r):
    out = []
    if r["p_churn"] >= 0.5: out.append(f"Churn model p={r['p_churn']:.0%}")
    if r["adv_p_shortfall"] >= 0.4: out.append(f"Delivery shortfall risk {r['adv_p_shortfall']:.0%}")
    if r["renewal_window"] == "renews_this_quarter" and r["days_to_renewal"] <= 30:
        out.append(f"Renews in {int(r['days_to_renewal'])} days")
    if str(r.get("upfront_commit_flag")) in ("True", "true", "1"): out.append("Upfront commitment at stake")
    return " | ".join(out) if out else "Stable — monitor"
b["contributing_factors"] = b.apply(factors, axis=1)

out_cols = ["advertiser_id", "advertiser_name", "category", "region", "account_owner",
            "contract_value", "renewal_date", "renewal_window", "days_to_renewal",
            "campaign_count", "campaigns_behind", "shortfall_rate", "avg_pacing_index",
            "avg_in_target_pct", "adv_p_shortfall", "p_churn",
            "risk_score", "risk_tier", "revenue_at_risk", "contributing_factors"]
out = b[out_cols].copy()
out["p_churn"] = out["p_churn"].round(4)
out["adv_p_shortfall"] = out["adv_p_shortfall"].round(4)
(spark.createDataFrame(out).write.mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{FQ}.advertiser_risk_scores"))

# monitoring table (predicted vs actual, Model A on completed line items)
mon = spark.sql(f"""
  SELECT 'delivery_shortfall_model' AS model, current_timestamp() AS scored_at,
         count(*) AS n, round(avg(p_shortfall),4) AS avg_pred,
         round(avg(under_delivered),4) AS actual_rate
  FROM {FQ}.ml_campaign_shortfall_scores""")
mon.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.ml_model_monitoring")

# COMMAND ----------
summary = spark.sql(f"""
  SELECT risk_tier, count(*) n, round(sum(revenue_at_risk)/1e6,1) rev_M
  FROM {FQ}.advertiser_risk_scores GROUP BY risk_tier""").toPandas().to_dict("records")
high = int(spark.sql(f"SELECT count(*) c FROM {FQ}.advertiser_risk_scores WHERE risk_tier='High'").collect()[0]["c"])
rev = float(spark.sql(f"SELECT sum(revenue_at_risk) s FROM {FQ}.advertiser_risk_scores WHERE risk_tier='High'").collect()[0]["s"])
result = {"model_a_auc": round(aucA, 3), "model_a_version": infoA.registered_model_version,
          "model_b_auc": round(aucB, 3), "model_b_version": infoB.registered_model_version,
          "b_labels": len(yB), "high_count": high, "high_rev_at_risk_M": round(rev/1e6, 1),
          "tiers": summary}
print("RESULT:", json.dumps(result, indent=2))

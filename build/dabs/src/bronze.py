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

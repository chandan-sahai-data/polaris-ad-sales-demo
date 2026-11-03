"""Shared config + Spark/SDK helpers for the Ad Sales Renewal Intelligence build.

FRESH BUILD — fill in the four values below for the NEW workspace before running anything.
  HOST      = https://<workspace>.cloud.databricks.com
  PROFILE   = <cli profile>   (verify: databricks current-user me --profile <PROFILE>)
  CATALOG   = <writable catalog in the new workspace>
  SCHEMA    = ad_sales
  WAREHOUSE = <serverless SQL warehouse id>   (databricks warehouses list --profile <PROFILE>)
"""
import os

PROFILE   = "fe-vm-cs-genie-research"
HOST      = "https://fevm-cs-genie-research.cloud.databricks.com"
CATALOG   = "cs_genie_research_catalog"
SCHEMA    = "ad_sales"
WAREHOUSE = "69a77ede4fa03b41"
FQ        = f"{CATALOG}.{SCHEMA}"

# Demo narrative constants
COMPANY      = "Polaris"
ANCHOR_TODAY = "2026-10-14"   # renewal-window anchor
N_ADVERTISERS = 150
N_CAMPAIGNS   = 600

EMBED_ENDPOINT = "databricks-bge-large-en"
LLM_ENDPOINT   = "databricks-claude-sonnet-5"


def spark():
    """Serverless Databricks Connect session bound to the profile."""
    from databricks.connect import DatabricksSession
    from databricks.sdk.core import Config
    cfg = Config(profile=PROFILE, serverless_compute_id="auto")
    s = DatabricksSession.builder.sdkConfig(cfg).getOrCreate()
    s.sql(f"USE CATALOG {CATALOG}")
    s.sql(f"USE SCHEMA {SCHEMA}")
    return s


def wc():
    """WorkspaceClient bound to the profile."""
    from databricks.sdk import WorkspaceClient
    return WorkspaceClient(profile=PROFILE)

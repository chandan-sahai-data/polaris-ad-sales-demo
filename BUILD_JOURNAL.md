# Build journal — how the AI-assisted build actually iterated

The build agent was Claude Code (Claude Opus), driving the Databricks CLI, the Python SDK and
Databricks Connect, with Databricks AI Dev Kit skills loaded per product. Each step in
`runbook.md` is a prompt. The entries below are the concrete problems hit, what the agent
observed, and what changed in the prompt or code as a result. Most of these fixes now live in
the runbook's "Fast-path gotchas" so later builds avoid them.

## Earlier iterations (folded into the runbook)

| Attempt | Observed | Change made |
|---|---|---|
| Landing data used Faker / pandas UDFs | Serverless failed with `ISOLATION_STARTUP_FAILURE.SANDBOX_STARTUP … exec format error` | Prompt and code changed to generate strings natively in Spark (`hash()`-indexed arrays). This also made the data deterministic across rebuilds |
| Model A trained at campaign grain | AUC ≈ 0.57, barely better than random | Retrained at line-item grain. The generator was changed so under-delivery depends on real drivers (scatter, off-peak dayparts, CTV, advertiser health). AUC rose to 0.938 |
| Metric-view `.sql` files sat inside the pipeline's source glob | Pipeline update failed: "CREATE OR REPLACE VIEW … not supported in a DLT pipeline" | Moved the DDL to `dabs/ddl/` and deploy it via SDK statement execution (`deploy_mv.py`). Passing it as a CLI argument also mangled the YAML indentation |
| App built in Streamlit | Embedded AI/BI dashboard was blank ("must be embedded in an iframe") | Rebuilt as FastAPI with a top-level `<iframe>` |
| Dashboards iterated with repeated `lakeview update` | Queries finished, but widgets rendered blank because of a stale dataset schema | Rule changed to: always create fresh, and match the reference JSON |
| Managed Vector Search index for Deal Memory | Index stuck in "pending endpoint provisioning" in the workspace | Switched to `bge-large-en` embeddings with in-app cosine search for 15 docs. Vector Search + Knowledge Assistant documented as the scale-out |
| Genie text instructions sent as separate list items | Concatenated into run-on text | Instructions written as one newline-delimited string, with a `NUMBER FORMATTING` block |

## Fresh rebuild in `fevm-cs-genie-research` (2026-10-14)

| Step | Observed | Change made |
|---|---|---|
| 5 Lakebase | `create-catalog` failed: no CREATE CATALOG on the metastore | Created the synced table directly in the existing catalog; it landed in Postgres as `ad_sales.lb_advertiser_risk_scores`. Added a `RISK_TABLE` env var to the app instead of hard-coding `public.…` |
| 5 Lakebase | App service principal couldn't create `seller_actions` (`public` is owned by `pg_database_owner`) | Project owner creates the table and grants the SP `ALL`. SP gets `USAGE`/`SELECT` on the synced schema |
| 7 Dashboards | GOLDEN parity diff showed every dataset pinned to `catalog: ad_sales_demo` from the reference, which would break at runtime | `rebuild_dashboards_from_ref.py` now overrides catalog/schema per dataset and creates fresh when no IDs are set. The two broken dashboards were trashed and recreated; datasets now match GOLDEN exactly |
| 8 App | AI/BI embedding allowlist was empty | Not auto-applied (it's a workspace-wide security setting in a shared workspace). Documented for an admin in `DEPLOYED.md` |

## Evidence capture (2026-11-03)

| Observed | Change made |
|---|---|
| SDK `list_pipeline_events` returned no flow rows | Switched to SQL `event_log('<pipeline_id>')` with `LATERAL explode` over the expectations JSON. That surfaced all 12 expectations with 0 failed records |
| Genie Q4 ("top 10 by revenue at risk") ranked `$702,245` above `$3,586,879` | Root cause: the seeded example SQL ordered by a `$`-formatted string alias. Renamed the alias to `revenue_at_risk_usd`, ordered by the raw column, added a SORTING rule to the instructions, updated the space, re-ran it and confirmed the correct order |
| Assessor couldn't see the Lakeflow transformation code | Added `evidence/01b_lakeflow_pipeline_source.md`: source exported from the deployed pipeline, SHA-256 matched to the repo, and inlined. Linked from the README |

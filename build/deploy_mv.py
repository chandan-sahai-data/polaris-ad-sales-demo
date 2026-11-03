"""Deploy a metric view via SDK statement-execution (preserves YAML indentation).

Passing the WITH METRICS ... LANGUAGE YAML DDL through the CLI as an arg mangles the
YAML indentation, so we execute the file content directly on the warehouse.
"""
import sys, time
from config import wc, WAREHOUSE

path = sys.argv[1] if len(sys.argv) > 1 else "dabs/ddl/mv_campaign_metrics.metric_view.sql"
sql = open(path).read()

w = wc()
r = w.statement_execution.execute_statement(warehouse_id=WAREHOUSE, statement=sql, wait_timeout="30s")
st = r.status.state.value
print("state:", st)
if st != "SUCCEEDED":
    print("error:", r.status.error)
    sys.exit(1)
print("deployed:", path)

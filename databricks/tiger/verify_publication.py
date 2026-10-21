# Databricks notebook source
"""Final read-only task; a mismatch fails the managed job and its failure alert."""
# COMMAND ----------
# MAGIC %pip install "psycopg[binary]>=3.2,<4"
# COMMAND ----------
dbutils.library.restartPython()
# COMMAND ----------
import json
import sys

import psycopg
from pyspark.sql import functions as F

for name, default in {
    "session_id": "", "expected_model": "", "tiger_host": "", "tiger_port": "5432",
    "project_root": "", "secret_scope": "se-project-2", "tiger_database": "tsdb",
    "sslrootcert": "", "expected_windows": "",
}.items():
    dbutils.widgets.text(name, default)
p = {name: dbutils.widgets.get(name) for name in (
    "session_id", "expected_model", "tiger_host", "tiger_port", "project_root",
    "secret_scope", "tiger_database", "sslrootcert", "expected_windows")}
sys.path.insert(0, p["project_root"])
from publication_parity import LIMIT, METRICS, compare

spark.conf.set("spark.sql.session.timeZone", "UTC")
pins = (spark.table("workspace.gluco_demo.replay_risk_models")
        .where(F.col("session_id") == p["session_id"]).limit(2).collect())
if len(pins) != 1 or pins[0].model_version != p["expected_model"]:
    raise ValueError("Unexpected session model pin")
frame = spark.table("workspace.gluco_demo.dashboard_windows").where(
    F.col("session_id") == p["session_id"])
rows = frame.select("participant_key", F.unix_micros("window_end"),
                    F.lit(p["expected_model"]), *METRICS).limit(LIMIT + 1).collect()
delta = [list(row) for row in rows]
options = {"sslmode": "verify-full"}
if p["sslrootcert"]:
    options["sslrootcert"] = p["sslrootcert"]
try:
    with psycopg.connect(host=p["tiger_host"], port=int(p["tiger_port"]),
            dbname=p["tiger_database"], user=dbutils.secrets.get(p["secret_scope"], "tiger-user"),
            password=dbutils.secrets.get(p["secret_scope"], "tiger-password"),
            connect_timeout=15, options="-c default_transaction_read_only=on -c statement_timeout=30000",
            **options) as connection:
        fields = ",".join(f"(payload->>'{name}')::double precision" for name in METRICS)
        tiger = connection.execute(f"""SELECT participant_key,
            (extract(epoch FROM window_end)*1000000)::bigint,
            payload->>'risk_model_version',{fields}
            FROM gold.dashboard_windows WHERE session_id=%s LIMIT {LIMIT + 1}""",
            (p["session_id"],)).fetchall()
except psycopg.Error:
    raise RuntimeError("Tiger read-only verification connection/query failed") from None
report = compare(delta, tiger, int(p["expected_windows"]), p["expected_model"])
if report["status"] != "pass":
    raise ValueError("Publication verification failed: " + ",".join(report["failures"]))
dbutils.notebook.exit(json.dumps(report, allow_nan=False))

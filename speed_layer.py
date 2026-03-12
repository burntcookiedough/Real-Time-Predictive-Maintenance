import logging
import sys
import time as _graph_cache_time
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, DoubleType, StringType, ArrayType, IntegerType
import config

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(levelname)s [speed_layer] %(message)s'
)
logger = logging.getLogger("speed_layer")

# Define Schema of incoming Kafka JSON
schema = StructType([
    StructField("Product ID", StringType(), True),
    StructField("Type", StringType(), True),
    StructField("Air temperature [K]", DoubleType(), True),
    StructField("Process temperature [K]", DoubleType(), True),
    StructField("Rotational speed [rpm]", DoubleType(), True),
    StructField("Torque [Nm]", DoubleType(), True),
    StructField("Tool wear [min]", IntegerType(), True),
    StructField("Machine failure", IntegerType(), True),
    StructField("timestamp", DoubleType(), True),
    StructField("connected_to", ArrayType(StringType()), True)
])

# ── Graph Context Cache ─────────────────────────────────────────
# We cache graph context DataFrames and refresh every 60s to avoid
# hammering Cassandra on every micro-batch.
_graph_cache = {"pr": None, "comm": None, "risk": None, "ts": 0}
GRAPH_CACHE_TTL = 60  # seconds


def _refresh_graph_cache(spark):
    """Refresh graph context from Cassandra if cache is stale."""
    now = _graph_cache_time.time()
    if _graph_cache["pr"] is not None and (now - _graph_cache["ts"]) < GRAPH_CACHE_TTL:
        return  # Cache still fresh

    try:
        pr_df = spark.read.format("org.apache.spark.sql.cassandra") \
            .options(table="pagerank_scores", keyspace="pdm").load() \
            .select(F.col("machine_id").alias("pr_machine_id"),
                    F.col("pagerank").alias("pr_score"))

        comm_df = spark.read.format("org.apache.spark.sql.cassandra") \
            .options(table="failure_communities", keyspace="pdm").load() \
            .select("community_id", F.col("machine_id").alias("comm_machine_id"))

        risk_df = spark.read.format("org.apache.spark.sql.cassandra") \
            .options(table="community_risk", keyspace="pdm").load() \
            .select(F.col("community_id").alias("risk_community_id"),
                    "risk_score")

        _graph_cache["pr"] = pr_df
        _graph_cache["comm"] = comm_df
        _graph_cache["risk"] = risk_df
        _graph_cache["ts"] = now
        logger.info("Graph context cache refreshed (%d PR, %d communities, %d risk scores)",
                     pr_df.count(), comm_df.count(), risk_df.count())
    except Exception as e:
        logger.warning("Could not load graph context (graph analytics may not have run yet): %s", e)
        # Keep stale cache if it exists, otherwise scoring falls back to base thresholds


def main():
    logger.info("Initializing Speed Layer (PySpark Streaming) with Graph-Augmented Scoring...")

    spark = SparkSession.builder \
        .appName("PdMSpeedLayer") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1") \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Read from Kafka
    logger.info("Connecting to Kafka at %s...", config.KAFKA_BROKER)
    df_kafka = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BROKER) \
        .option("subscribe", config.TOPIC_RAW) \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON
    df_parsed = df_kafka.select(
        F.from_json(F.col("value").cast("string"), schema).alias("data")
    ).select("data.*")

    # ── Graph-Augmented Anomaly Scoring via foreachBatch ─────────────
    # Instead of a static heuristic, each micro-batch is enriched with
    # graph context (PageRank centrality + community risk) from Cassandra.
    # Machines in high-risk communities get LOWER thresholds (more sensitive).
    #
    # Formula:
    #   graph_adjustment = coalesce(risk_score * α + pr_score * β, 0.0)
    #   adjusted_tw_threshold = BASE_TW - graph_adjustment * BASE_TW
    #   adjusted_rpm_threshold = BASE_RPM + graph_adjustment * 200
    #
    # This creates the feedback loop:
    #   Graph Analytics (batch) → community_risk + pagerank (Cassandra)
    #   → Speed Layer reads and adjusts thresholds per machine
    #   → More/fewer alerts → affects edge routing → affects cloud training

    ALPHA = config.GRAPH_SCORE_ALPHA
    BETA = config.GRAPH_SCORE_BETA
    BASE_TW = config.BASE_TOOL_WEAR_THRESHOLD
    BASE_RPM = config.BASE_RPM_THRESHOLD

    def process_with_graph_context(batch_df, batch_id):
        """Process each micro-batch with graph-augmented anomaly scoring."""
        count = batch_df.count()
        if count == 0:
            return

        # Refresh graph context cache if stale
        _refresh_graph_cache(spark)

        pr_df = _graph_cache["pr"]
        comm_df = _graph_cache["comm"]
        risk_df = _graph_cache["risk"]

        # If graph context is available, enrich the batch
        if pr_df is not None and comm_df is not None and risk_df is not None:
            # Join: batch → pagerank
            enriched = batch_df.join(
                pr_df,
                batch_df["Product ID"] == pr_df["pr_machine_id"],
                "left"
            ).drop("pr_machine_id")

            # Join: enriched → communities (to get community_id)
            enriched = enriched.join(
                comm_df,
                enriched["Product ID"] == comm_df["comm_machine_id"],
                "left"
            ).drop("comm_machine_id")

            # Join: enriched → community_risk (to get risk_score)
            enriched = enriched.join(
                risk_df,
                enriched["community_id"] == risk_df["risk_community_id"],
                "left"
            ).drop("risk_community_id")

            # Compute graph adjustment factor
            enriched = enriched.withColumn(
                "graph_adjustment",
                F.coalesce(
                    F.col("risk_score") * F.lit(ALPHA) + F.col("pr_score") * F.lit(BETA),
                    F.lit(0.0)
                )
            )

            # Log graph scoring stats for observability
            adj_stats = enriched.agg(
                F.avg("graph_adjustment").alias("avg_adj"),
                F.max("graph_adjustment").alias("max_adj"),
                F.sum(F.when(F.col("graph_adjustment") > 0, 1).otherwise(0)).alias("enriched_count")
            ).collect()[0]
            logger.info(
                "batch=%d records=%d graph_enriched=%d avg_adjustment=%.4f max_adjustment=%.4f",
                batch_id, count,
                int(adj_stats["enriched_count"] or 0),
                float(adj_stats["avg_adj"] or 0),
                float(adj_stats["max_adj"] or 0)
            )
        else:
            # No graph context yet — fall back to base thresholds (adjustment = 0)
            enriched = batch_df.withColumn("graph_adjustment", F.lit(0.0)) \
                               .withColumn("community_id", F.lit(None).cast("string")) \
                               .withColumn("risk_score", F.lit(None).cast("double")) \
                               .withColumn("pr_score", F.lit(None).cast("double"))
            logger.info("batch=%d records=%d (no graph context — using base thresholds)", batch_id, count)

        # ── Apply Graph-Augmented Scoring ───────────────────────────
        scored = enriched.withColumn(
            "prediction_score",
            F.when(
                (F.col("Tool wear [min]") > (F.lit(BASE_TW) - F.col("graph_adjustment") * F.lit(BASE_TW))) |
                (F.col("Rotational speed [rpm]") < (F.lit(BASE_RPM) + F.col("graph_adjustment") * F.lit(200))),
                F.lit(-1.0)
            ).otherwise(F.lit(1.0))
        )

        # ── Write Alerts to Cassandra ───────────────────────────────
        alerts = scored.filter(F.col("prediction_score") == -1.0).select(
            F.col("Product ID").alias("machine_id"),
            F.current_timestamp().alias("alert_time"),
            F.lit(0).alias("latency_ms"),
            F.col("Air temperature [K]").alias("air_temp"),
            F.col("Process temperature [K]").alias("process_temp"),
            F.col("Rotational speed [rpm]").alias("rotational_speed"),
            F.col("Torque [Nm]").alias("torque"),
            F.col("Tool wear [min]").alias("tool_wear"),
            F.col("prediction_score")
        )

        alert_count = alerts.count()
        if alert_count > 0:
            alerts.write \
                .format("org.apache.spark.sql.cassandra") \
                .option("keyspace", "pdm") \
                .option("table", "realtime_alerts") \
                .mode("append") \
                .save()
            logger.info("  → alerts written: %d", alert_count)

        # ── Write Machine States to Cassandra ───────────────────────
        states = scored.select(
            F.col("Product ID").alias("machine_id"),
            F.current_timestamp().alias("last_update"),
            F.when(F.col("prediction_score") == -1.0, F.lit("CRITICAL"))
             .otherwise(F.lit("HEALTHY")).alias("status"),
            F.col("Air temperature [K]").alias("air_temp"),
            F.col("Torque [Nm]").alias("torque")
        )

        states.write \
            .format("org.apache.spark.sql.cassandra") \
            .option("keyspace", "pdm") \
            .option("table", "machine_states") \
            .mode("append") \
            .save()

    # ── Start unified foreachBatch stream ────────────────────────────
    # Using a single foreachBatch handles both alerts + states in one pass,
    # avoiding the overhead of two separate streaming queries.
    df_parsed.writeStream \
        .foreachBatch(process_with_graph_context) \
        .option("checkpointLocation", "./checkpoints/graph_scored") \
        .outputMode("append") \
        .start()

    logger.info("Speed layer stream active (graph-augmented scoring). Awaiting data...")
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    import time as _time

    MAX_BACKOFF = 60  # seconds
    backoff = 5

    while True:
        try:
            main()
            logger.warning("awaitAnyTermination() returned. Restarting in %ds...", backoff)
        except KeyboardInterrupt:
            logger.info("Speed layer stopped by user.")
            break
        except Exception as e:
            logger.error("Speed layer crashed: %s. Restarting in %ds...", e, backoff, exc_info=True)

        _time.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF)

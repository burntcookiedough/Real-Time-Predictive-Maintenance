import logging
import sys
import os
import threading
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

def main():
    logger.info("Initializing Speed Layer (PySpark Streaming)...")
    
    # Include kafka, cassandra, AND graphframes connectors in one session
    spark = SparkSession.builder \
        .appName("PdMSpeedLayer") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1,graphframes:graphframes:0.8.3-spark3.5-s_2.12") \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # ─── Background Graph Analytics (PageRank + Communities) ─────────
    # Runs every 5 min inside this same SparkSession — no second JVM needed.
    GRAPH_INTERVAL_SEC = 300  # 5 minutes
    HDFS_PATH = "./hdfs_temp/*"

    def run_graph_analytics():
        """Periodic batch: PageRank + Connected Components on historical data."""
        import time as _t
        while True:
            _t.sleep(GRAPH_INTERVAL_SEC)
            try:
                from graphframes import GraphFrame

                logger.info("[graph] Starting periodic graph analytics...")
                df = spark.read.json(HDFS_PATH)
                if df.rdd.isEmpty():
                    logger.warning("[graph] No historical data found. Skipping.")
                    continue

                # Nodes
                nodes = df.select(F.col("Product ID").alias("id")).distinct()
                # Edges
                edges_df = df.select(
                    F.col("Product ID").alias("src"),
                    F.explode("connected_to").alias("dst")
                ).distinct()

                if edges_df.rdd.isEmpty():
                    logger.warning("[graph] No edges found. Skipping.")
                    continue

                g = GraphFrame(nodes, edges_df)

                # PageRank
                logger.info("[graph] Running PageRank (maxIter=10)...")
                pr = g.pageRank(resetProbability=0.15, maxIter=10)
                pr_scores = pr.vertices.select(
                    F.col("id").alias("machine_id"),
                    F.col("pagerank"),
                    F.current_timestamp().alias("last_computed")
                )
                pr_scores.write \
                    .format("org.apache.spark.sql.cassandra") \
                    .mode("append") \
                    .options(table="pagerank_scores", keyspace="pdm") \
                    .save()
                logger.info("[graph] PageRank saved to Cassandra (%d nodes)", pr_scores.count())

                # Connected Components
                logger.info("[graph] Running Connected Components...")
                os.makedirs("./checkpoints/graph", exist_ok=True)
                spark.sparkContext.setCheckpointDir("./checkpoints/graph")
                cc = g.connectedComponents()
                communities = cc.select(
                    F.col("component").cast("string").alias("community_id"),
                    F.col("id").alias("machine_id")
                )
                communities.write \
                    .format("org.apache.spark.sql.cassandra") \
                    .mode("append") \
                    .options(table="failure_communities", keyspace="pdm") \
                    .save()
                logger.info("[graph] Communities saved to Cassandra (%d rows)", communities.count())

            except Exception as e:
                logger.error("[graph] Graph analytics failed (non-fatal): %s", e, exc_info=True)
    # ─── End Graph Analytics ─────────────────────────────────────────

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

    # For the speed layer, we want to capture anomalies immediately.
    # While the Batch Layer trains the heavy Random Forest, the Speed Layer
    # can use a fast, lightweight heuristic (or a broadcasted PMML/ONNX model).
    # Here, we simulate the "prediction" by flagging if Tool wear > 200 or Rotational speed < 1300
    df_with_predictions = df_parsed.withColumn(
        "prediction_score", 
        F.when((F.col("Tool wear [min]") > 200) | (F.col("Rotational speed [rpm]") < 1300), F.lit(-1.0)).otherwise(F.lit(1.0))
    )

    # 1. Write Alerts to Cassandra
    df_alerts = df_with_predictions.filter(F.col("prediction_score") == -1.0)
    
    # Map to Cassandra schema for realtime_alerts
    df_cassandra_alerts = df_alerts.select(
        F.col("Product ID").alias("machine_id"),
        F.current_timestamp().alias("alert_time"),
        F.lit(0).alias("latency_ms"), # Simulated
        F.col("Air temperature [K]").alias("air_temp"),
        F.col("Process temperature [K]").alias("process_temp"),
        F.col("Rotational speed [rpm]").alias("rotational_speed"),
        F.col("Torque [Nm]").alias("torque"),
        F.col("Tool wear [min]").alias("tool_wear"),
        F.col("prediction_score")
    )

    # Sink to Cassandra — with foreachBatch logging for observability
    def log_alerts_batch(batch_df, batch_id):
        count = batch_df.count()
        logger.info("alerts.batch_id=%d records=%d", batch_id, count)
        if count > 0:
            batch_df.write \
                .format("org.apache.spark.sql.cassandra") \
                .option("keyspace", "pdm") \
                .option("table", "realtime_alerts") \
                .mode("append") \
                .save()

    df_cassandra_alerts.writeStream \
        .foreachBatch(log_alerts_batch) \
        .option("checkpointLocation", "./checkpoints/alerts") \
        .outputMode("append") \
        .start()

    # 2. Write Current States to Cassandra
    df_cassandra_states = df_with_predictions.select(
        F.col("Product ID").alias("machine_id"),
        F.current_timestamp().alias("last_update"),
        F.when(F.col("prediction_score") == -1.0, F.lit("CRITICAL")).otherwise(F.lit("HEALTHY")).alias("status"),
        F.col("Air temperature [K]").alias("air_temp"),
        F.col("Torque [Nm]").alias("torque")
    )

    df_cassandra_states.writeStream \
        .format("org.apache.spark.sql.cassandra") \
        .option("keyspace", "pdm") \
        .option("table", "machine_states") \
        .option("checkpointLocation", "./checkpoints/states") \
        .outputMode("append") \
        .start()

    # Start the graph analytics background thread (daemon = dies with main process)
    graph_thread = threading.Thread(target=run_graph_analytics, daemon=True, name="GraphAnalytics")
    graph_thread.start()
    logger.info("Graph analytics scheduler started (runs every %ds)", GRAPH_INTERVAL_SEC)

    logger.info("Speed layer streams active. Awaiting data...")
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    import time as _time

    MAX_BACKOFF = 60  # seconds
    backoff = 5

    while True:
        try:
            main()
            # If main() returns normally (shouldn't in steady state), restart
            logger.warning("awaitAnyTermination() returned. Restarting in %ds...", backoff)
        except KeyboardInterrupt:
            logger.info("Speed layer stopped by user.")
            break
        except Exception as e:
            logger.error("Speed layer crashed: %s. Restarting in %ds...", e, backoff, exc_info=True)

        _time.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF)

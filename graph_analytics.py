import os
import glob
import logging
import sys
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from graphframes import GraphFrame
import config

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(levelname)s [graph_analytics] %(message)s'
)
logger = logging.getLogger("graph_analytics")

HDFS_PATH = "./hdfs_temp/*"
SNAPSHOT_DIR = "./graph_snapshot"

def main():
    # Pre-flight: snapshot data files to avoid race conditions with hdfs_writer
    # (hdfs_writer deletes files from hdfs_temp/ after uploading to HDFS,
    #  which causes SparkFileNotFoundException if we read them concurrently)
    import shutil
    data_files = glob.glob(os.path.join(".", "hdfs_temp", "*.json"))
    if not data_files:
        logger.warning("No data files found in ./hdfs_temp/ — graph analytics skipped. "
                        "Wait for hdfs_writer.py to accumulate batches first.")
        return

    # Copy to a stable snapshot directory
    if os.path.exists(SNAPSHOT_DIR):
        shutil.rmtree(SNAPSHOT_DIR)
    os.makedirs(SNAPSHOT_DIR)
    for f in data_files:
        shutil.copy2(f, SNAPSHOT_DIR)
    logger.info("Snapshotted %d data files to %s", len(data_files), SNAPSHOT_DIR)

    # Fix for Windows JVM/Py4J collision: force a separate temp dir and explicit driver/UI ports
    os.environ["SPARK_LOCAL_DIRS"] = os.path.abspath("./spark_temp_graph")
    os.makedirs("./spark_temp_graph", exist_ok=True)
    
    logger.info("Initializing Spark Graph Analytics...")
    
    # We must include the graphframes package
    spark = SparkSession.builder \
        .appName("PdPGraphAnalytics") \
        .config("spark.driver.port", "0") \
        .config("spark.driver.blockManager.port", "0") \
        .config("spark.ui.port", "0") \
        .config("spark.jars.packages", "graphframes:graphframes:0.8.3-spark3.5-s_2.12,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1") \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .config("spark.sql.catalogImplementation", "in-memory") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    snapshot_path = os.path.join(SNAPSHOT_DIR, "*")
    logger.info("Reading historical records from %s to construct graph...", snapshot_path)
    try:
        df = spark.read.json(snapshot_path)
    except Exception as e:
        logger.error("Failed to read data for graph analytics: %s", e, exc_info=True)
        return

    # Limit to 100 records to prevent local GraphFrames StackOverflow in ConnectedComponents
    # since the simulated graph connects every machine randomly.
    df = df.limit(100)

    # Extract Nodes (unique machines)
    nodes = df.select(F.col("Product ID").alias("id")).distinct()
    
    # Extract Edges
    # 'connected_to' is an array of machine IDs. We explode it to get individual edge rows.
    edges_df = df.select(
        F.col("Product ID").alias("src"), 
        F.explode("connected_to").alias("dst")
    ).distinct()

    if edges_df.count() == 0:
        logger.warning("No network connections found in dataset. Graph is empty.")
        return

    logger.info("Constructing GraphFrame...")
    g = GraphFrame(nodes, edges_df)

    logger.info("Running PageRank (Finding Critical Bottleneck Machines)...")
    # PageRank identifies the most "important" or central nodes in the graph
    results = g.pageRank(resetProbability=0.15, maxIter=10)
    
    # Select id and pagerank score
    pr_scores = results.vertices.select(
        F.col("id").alias("machine_id"),
        F.col("pagerank"),
        F.current_timestamp().alias("last_computed")
    )
    
    pr_scores.show(5)
    
    logger.info("Saving PageRank scores to Cassandra...")
    pr_scores.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table="pagerank_scores", keyspace="pdm") \
        .save()

    logger.info("Running Label Propagation (Finding Fault Cascade Communities)...")
    # Label Propagation is much lighter than Connected Components and doesn't
    # require checkpointing — ideal for local development machines.
    lpa_results = g.labelPropagation(maxIter=5)
    
    # Map label to 'community_id' string
    communities = lpa_results.select(
        F.col("label").cast("string").alias("community_id"),
        F.col("id").alias("machine_id")
    )
    
    communities.show(5)

    logger.info("Saving Communities to Cassandra...")
    communities.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table="failure_communities", keyspace="pdm") \
        .save()

    logger.info("Graph Analytics Complete!")
    spark.stop()

if __name__ == "__main__":
    main()

import os
import logging
import sys
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from graphframes import GraphFrame

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(levelname)s [graph_analytics] %(message)s'
)
logger = logging.getLogger("graph_analytics")

HDFS_PATH = "./hdfs_temp/*"

def main():
    logger.info("Initializing Spark Graph Analytics...")
    
    # We must include the graphframes package
    spark = SparkSession.builder \
        .appName("PdPGraphAnalytics") \
        .config("spark.jars.packages", "graphframes:graphframes:0.8.3-spark3.5-s_2.12,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1") \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    logger.info("Reading historical records from %s to construct graph...", HDFS_PATH)
    try:
        df = spark.read.json(HDFS_PATH)
    except Exception as e:
        logger.error("Failed to read HDFS data for graph analytics: %s", e, exc_info=True)
        return

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

    logger.info("Running Connected Components (Finding Fault Cascades)...")
    # Groups machines into isolated "sub-networks" or communities
    os.makedirs("./checkpoints/graph", exist_ok=True)
    spark.sparkContext.setCheckpointDir("./checkpoints/graph")
    cc_results = g.connectedComponents()
    
    # Map component ID to 'community_id' string
    communities = cc_results.select(
        F.col("component").cast("string").alias("community_id"),
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

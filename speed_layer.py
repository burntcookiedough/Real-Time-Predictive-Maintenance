import os
import pyspark.sql.functions as F
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, DoubleType, StringType, ArrayType, LongType, IntegerType
import config

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
    print("Initializing Speed Layer (PySpark Streaming)...")
    
    # We must include the kafka and cassandra connectors
    # Depending on your PySpark version, these coordinates might change. 
    # Assumes Spark 3.x and Scala 2.12
    spark = SparkSession.builder \
        .appName("PdMSpeedLayer") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1") \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Read from Kafka
    print(f"Connecting to Kafka at {config.KAFKA_BROKER}...")
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

    # Sink to Cassandra
    query_alerts = df_cassandra_alerts.writeStream \
        .format("org.apache.spark.sql.cassandra") \
        .option("keyspace", "pdm") \
        .option("table", "realtime_alerts") \
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

    query_states = df_cassandra_states.writeStream \
        .format("org.apache.spark.sql.cassandra") \
        .option("keyspace", "pdm") \
        .option("table", "machine_states") \
        .option("checkpointLocation", "./checkpoints/states") \
        .outputMode("append") \
        .start()

    print("Speed layer streams active. Awaiting data...")
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()

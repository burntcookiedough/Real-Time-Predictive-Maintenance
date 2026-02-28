import logging
import sys
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(levelname)s [batch_ml] %(message)s'
)
logger = logging.getLogger("batch_ml")

# Simulating reading from HDFS. 
# During real dev, HDFS_PATH = "hdfs://namenode:9000/user/hadoop/pdm_data/*"
HDFS_PATH = "./hdfs_temp/*"

def main():
    logger.info("Initializing Batch ML Pipeline...")

    spark = SparkSession.builder \
        .appName("PdMBatchTraining") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")
    
    logger.info("Reading historical data from %s...", HDFS_PATH)
    
    # Read all historical JSON files dumped by hdfs_writer.py
    try:
        df = spark.read.json(HDFS_PATH)
    except Exception as e:
        logger.error("Failed to read HDFS data: %s", e, exc_info=True)
        return
        
    # Cache count to avoid triggering two full Spark jobs (CR-4)
    record_count = df.count()
    if record_count < 100:
        logger.warning("Not enough data (%d records). Need at least 100 to train.", record_count)
        return

    logger.info("Loaded %d historical records. Preparing Random Forest...", record_count)

    # Data Preparation
    # Features mentioned in Syllabus Unit 6
    feature_cols = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
    
    # Assemble features into a vector
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features", handleInvalid="skip")
    
    # Random Forest Classifier
    # We predict the 'Machine failure' column (0 or 1)
    rf = RandomForestClassifier(labelCol="Machine failure", featuresCol="features", numTrees=50, maxDepth=5)
    
    # Build the Pipeline
    pipeline = Pipeline(stages=[assembler, rf])
    
    # Split data
    train_data, test_data = df.randomSplit([0.8, 0.2], seed=42)
    
    logger.info("Training Random Forest model...")
    model = pipeline.fit(train_data)
    
    logger.info("Evaluating model...")
    predictions = model.transform(test_data)
    
    evaluator = MulticlassClassificationEvaluator(labelCol="Machine failure", predictionCol="prediction", metricName="f1")
    f1_score = evaluator.evaluate(predictions)
    
    logger.info("Random Forest Training Complete! F1 Score: %.4f", f1_score)
    
    # Save Model (Overwrite previous)
    model_save_path = "./models/pdm_rf_model"
    model.write().overwrite().save(model_save_path)
    logger.info("Model saved to %s", model_save_path)
    
    spark.stop()

if __name__ == "__main__":
    main()

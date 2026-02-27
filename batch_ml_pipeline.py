import os
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import config

# Simulating reading from HDFS. 
# During real dev, HDFS_PATH = "hdfs://namenode:9000/user/hadoop/pdm_data/*"
HDFS_PATH = "./hdfs_temp/*"

def main():
    print("Initializing Batch ML Pipeline...")

    spark = SparkSession.builder \
        .appName("PdMBatchTraining") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"Reading historical data from {HDFS_PATH}...")
    
    # Read all historical JSON files dumped by hdfs_writer.py
    try:
        df = spark.read.json(HDFS_PATH)
    except Exception as e:
        print("No historical data found to train on yet.")
        return
        
    if df.count() < 100:
        print("Not enough data to train a robust Random Forest. Exiting.")
        return

    print(f"Loaded {df.count()} historical records. Preparing for Random Forest...")

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
    
    print("Training Random Forest model...")
    model = pipeline.fit(train_data)
    
    print("Evaluating model...")
    predictions = model.transform(test_data)
    
    evaluator = MulticlassClassificationEvaluator(labelCol="Machine failure", predictionCol="prediction", metricName="f1")
    f1_score = evaluator.evaluate(predictions)
    
    print(f"Random Forest Training Complete! F1 Score: {f1_score:.4f}")
    
    # Save Model (Overwrite previous)
    model_save_path = "./models/pdm_rf_model"
    model.write().overwrite().save(model_save_path)
    print(f"Model saved to {model_save_path}")
    
    spark.stop()

if __name__ == "__main__":
    main()

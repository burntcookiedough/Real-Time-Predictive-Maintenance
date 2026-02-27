import json
import time
import os
import subprocess
from kafka import KafkaConsumer
import config

BATCH_SIZE = 500
LOCAL_TEMP_DIR = "./hdfs_temp"
HDFS_DIR = "/user/hadoop/pdm_data"

def json_deserializer(data):
    return json.loads(data.decode('utf-8'))

def ensure_hdfs_dir():
    # Make sure HDFS directory exists
    print(f"Ensuring HDFS directory {HDFS_DIR} exists...")
    try:
        # The docker exec command expects the namenode container.
        subprocess.run(["docker", "exec", "namenode", "hdfs", "dfs", "-mkdir", "-p", HDFS_DIR], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not create HDFS directory. Is the namenode running? {e}")

def sink_to_hdfs(file_path, filename):
    print(f"Sinking batch {filename} to HDFS...")
    hdfs_path = f"{HDFS_DIR}/{filename}"
    try:
        # Copy to container first
        subprocess.run(["docker", "cp", file_path, f"namenode:/tmp/{filename}"], check=True)
        # Put into HDFS
        subprocess.run(["docker", "exec", "namenode", "hdfs", "dfs", "-put", f"/tmp/{filename}", hdfs_path], check=True)
        print(f"Successfully sunk {filename} to HDFS.")
        os.remove(file_path)
    except subprocess.CalledProcessError as e:
         print(f"Failed to sink to HDFS: {e}")

def main():
    print("Starting Kafka to HDFS Writer...")
    
    if not os.path.exists(LOCAL_TEMP_DIR):
        os.makedirs(LOCAL_TEMP_DIR)

    ensure_hdfs_dir()

    consumer = KafkaConsumer(
        config.TOPIC_RAW,
        bootstrap_servers=[config.KAFKA_BROKER],
        auto_offset_reset='earliest',
        group_id='hdfs_sink_group',
        value_deserializer=json_deserializer
    )

    print(f"Listening on topic: {config.TOPIC_RAW} for batch sinking...")
    
    batch = []
    batch_count = 0
    
    try:
        for message in consumer:
            batch.append(message.value)
            
            if len(batch) >= BATCH_SIZE:
                batch_count += 1
                filename = f"batch_{int(time.time())}_{batch_count}.json"
                file_path = os.path.join(LOCAL_TEMP_DIR, filename)
                
                # Write to local file first
                with open(file_path, 'w') as f:
                    for record in batch:
                        f.write(json.dumps(record) + "\n")
                
                # Upload to HDFS
                sink_to_hdfs(file_path, filename)
                batch = [] # Reset batch

    except KeyboardInterrupt:
        print("\nHDFS Writer stopped by user.")
    finally:
        consumer.close()

if __name__ == "__main__":
    main()

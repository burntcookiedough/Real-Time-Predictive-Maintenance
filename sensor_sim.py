import time
import json
import logging
import sys
import pandas as pd
from kafka import KafkaProducer
import config

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s %(levelname)s [sensor_sim] %(message)s'
)
logger = logging.getLogger("sensor_sim")

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

def main():
    logger.info("Initializing Sensor Simulator...")
    # Load AI4I 2020 dataset
    try:
        df = pd.read_csv('ai4i2020.csv')
    except FileNotFoundError:
        logger.error("Dataset ai4i2020.csv not found. Please ensure it is in the same directory.")
        return

    # Initialize Kafka Producer
    producer = KafkaProducer(
        bootstrap_servers=[config.KAFKA_BROKER],
        value_serializer=json_serializer
    )

    logger.info("Connected to Kafka broker at %s", config.KAFKA_BROKER)
    logger.info("Starting to stream data to topic: %s", config.TOPIC_RAW)

    # Generate static graph relationships for machines
    unique_machines = df['Product ID'].unique()
    import random
    machine_graph = {}
    for process in unique_machines:
        # Each machine connects to 1-3 other random machines
        connections = random.sample(list(unique_machines), random.randint(1, 3))
        # Prevent self-loop in this simple simulation
        connections = [m for m in connections if m != process]
        machine_graph[process] = connections

    # Stream data continuously, cycling through the dataset indefinitely
    total_sent = 0
    cycle = 0
    try:
        while True:
            cycle += 1
            logger.info("Starting dataset cycle #%d", cycle)
            for index, row in df.iterrows():
                # Convert row to dictionary
                message = row.to_dict()
                # Add a real-time timestamp so every message is "fresh"
                message['timestamp'] = time.time()

                # Add Graph Edge Metadata
                machine_id = message['Product ID']
                message['connected_to'] = machine_graph.get(machine_id, [])

                # Send message to Kafka
                producer.send(config.TOPIC_RAW, value=message)

                total_sent += 1
                if total_sent % 100 == 0:
                    logger.info("Sent %d messages total (cycle %d)", total_sent, cycle)

                # ~100 msgs/sec — PySpark will always find fresh data
                time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Streaming stopped by user.")
    finally:
        producer.flush()
        producer.close()
        logger.info("Producer closed. Total messages sent: %d", total_sent)

if __name__ == "__main__":
    main()

import time
import json
import pandas as pd
from kafka import KafkaProducer
import config

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

def main():
    print("Initializing Sensor Simulator...")
    # Load AI4I 2020 dataset
    try:
        df = pd.read_csv('ai4i2020.csv')
    except FileNotFoundError:
        print("Dataset ai4i2020.csv not found. Please ensure it is in the same directory.")
        return

    # Initialize Kafka Producer
    producer = KafkaProducer(
        bootstrap_servers=[config.KAFKA_BROKER],
        value_serializer=json_serializer
    )

    print(f"Connected to Kafka broker at {config.KAFKA_BROKER}")
    print(f"Starting to stream data to topic: {config.TOPIC_RAW}")

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
            print(f"Starting dataset cycle #{cycle}...")
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
                    print(f"Sent {total_sent} messages total (cycle {cycle})...")

                # ~100 msgs/sec — PySpark will always find fresh data
                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStreaming stopped by user.")
    finally:
        producer.flush()
        producer.close()
        print(f"Producer closed. Total messages sent: {total_sent}")

if __name__ == "__main__":
    main()

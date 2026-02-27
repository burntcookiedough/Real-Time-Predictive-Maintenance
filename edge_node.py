import json
import time
import random
import joblib
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
import config

def json_deserializer(data):
    return json.loads(data.decode('utf-8'))

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

def get_simulated_latency():
    """Generates a random network RTT between min and max config values."""
    return random.randint(config.SIMULATED_LATENCY_MIN, config.SIMULATED_LATENCY_MAX)

def main():
    print("Starting Edge Node Simulator...")

    # Load baseline model
    try:
        model = joblib.load(config.MODEL_PATH)
        print(f"Loaded edge model from {config.MODEL_PATH}")
    except FileNotFoundError:
        print(f"Edge model not found at {config.MODEL_PATH}. Please run train_initial_edge_model.py first.")
        return

    # Setup Kafka Consumer and Producer
    consumer = KafkaConsumer(
        config.TOPIC_RAW,
        bootstrap_servers=[config.KAFKA_BROKER],
        auto_offset_reset='latest',
        group_id='edge_processing_group',
        value_deserializer=json_deserializer
    )

    producer = KafkaProducer(
        bootstrap_servers=[config.KAFKA_BROKER],
        value_serializer=json_serializer
    )

    print(f"Listening on topic: {config.TOPIC_RAW}")
    
    features = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
    
    total_messages = 0
    messages_to_cloud = 0
    anomalies_detected = 0

    try:
        for message in consumer:
            total_messages += 1
            data = message.value
            
            # Extract features for model
            try:
                X = pd.DataFrame([data], columns=features)
            except KeyError as e:
                print(f"Missing feature in data: {e}")
                continue

            latency = get_simulated_latency()
            
            # --- Latency-Aware Scheduler Logic ---
            if latency < config.LATENCY_ROUTE_THRESHOLD:
                # FAST NETWORK: Offload raw/filtered data to cloud
                messages_to_cloud += 1
                data['routing'] = 'cloud_offload'
                data['latency_ms'] = latency
                producer.send(config.TOPIC_CLOUD, value=data)
            else:
                # SLOW NETWORK: Process locally at edge
                # Model returns 1 for inliers, -1 for outliers
                prediction = model.predict(X)[0]
                
                if prediction == -1:
                    anomalies_detected += 1
                    alert = {
                        'timestamp': data.get('timestamp', time.time()),
                        'original_data': data,
                        'latency_ms': latency,
                        'alert_type': 'edge_anomaly',
                        'product_id': data.get('Product ID', 'UNKNOWN')
                    }
                    producer.send(config.TOPIC_ALERTS, value=alert)
            
            # Log periodic stats
            if total_messages % 100 == 0:
                cloud_reduction = (1 - (messages_to_cloud / total_messages)) * 100
                print(f"Processed: {total_messages} | Anomalies: {anomalies_detected} | Data Reduced: {cloud_reduction:.1f}%")

    except KeyboardInterrupt:
        print("\nEdge Node stopped by user.")
    finally:
        consumer.close()
        producer.close()
        print("Kafka clients closed.")

if __name__ == "__main__":
    main()

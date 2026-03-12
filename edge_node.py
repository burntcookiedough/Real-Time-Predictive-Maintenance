import json
import time
import random
import joblib
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
import config

# Cassandra driver is optional — Python 3.12+ removed asyncore which
# breaks older cassandra-driver versions; controller will skip persistence
# if import fails.
try:
    from cassandra.cluster import Cluster
    _CASSANDRA_AVAILABLE = True
except Exception:
    _CASSANDRA_AVAILABLE = False
    print("[controller] WARNING: cassandra-driver not available (possible asyncore issue on Python 3.12+). "
          "Controller will run without Cassandra state persistence.")

def json_deserializer(data):
    return json.loads(data.decode('utf-8'))

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

def get_simulated_latency():
    """Generates a random network RTT between min and max config values."""
    return random.randint(config.SIMULATED_LATENCY_MIN, config.SIMULATED_LATENCY_MAX)


class AdaptiveController:
    """
    Closed-Loop Adaptive Edge-Cloud Controller.

    Replaces fixed latency threshold with a self-optimizing multi-objective
    controller that monitors system metrics and dynamically adjusts:
      - latency_threshold: when to route to cloud vs edge
      - cloud_sample_rate: probabilistic sampling even on high-latency
      - retrain_interval: how often to trigger cloud model retraining

    Control policy runs every CONTROLLER_WINDOW_SIZE messages and uses
    exponential moving averages for stability.
    """

    def __init__(self):
        # Current controller state — starts from config defaults
        self.latency_threshold = float(config.LATENCY_ROUTE_THRESHOLD)
        self.cloud_sample_rate = 0.2  # Start at 20% sampling
        self.retrain_interval = 500   # Start at 500 records

        # Rolling metric accumulators
        self._window_total = 0
        self._window_anomalies = 0
        self._window_rtt_sum = 0.0
        self._cloud_backlog = 0

        # EMA-smoothed metrics
        self.edge_anomaly_rate = 0.0
        self.avg_rtt = 250.0  # Initial estimate

        # Controller step sizes
        self._threshold_step = 20.0   # ms per adjustment
        self._threshold_fine = 5.0    # ms for fine-tuning
        self._prev_avg_rtt = 250.0    # For trend detection

        # Cassandra connection for persisting state
        self._cass_session = None
        self._init_cassandra()

    def _init_cassandra(self):
        """Connect to Cassandra for persisting controller state."""
        if not _CASSANDRA_AVAILABLE:
            print("[controller] Cassandra driver not available — skipping state persistence.")
            return
        try:
            cluster = Cluster(['localhost'], port=9042)
            self._cass_session = cluster.connect('pdm')
            print("[controller] Connected to Cassandra for state persistence.")
        except Exception as e:
            print(f"[controller] WARNING: Could not connect to Cassandra: {e}")
            print("[controller] Controller will operate without state persistence.")

    def record_message(self, latency, is_anomaly, routed_to_cloud):
        """Record metrics for a single processed message."""
        self._window_total += 1
        self._window_rtt_sum += latency
        if is_anomaly:
            self._window_anomalies += 1
        if routed_to_cloud:
            self._cloud_backlog += 1

        # Run optimization step every WINDOW_SIZE messages
        if self._window_total >= config.CONTROLLER_WINDOW_SIZE:
            self._optimize()

    def record_retrain(self):
        """Called when cloud reports retraining complete."""
        self._cloud_backlog = 0

    def should_route_to_cloud(self, latency):
        """
        Adaptive routing decision:
          1. If latency < threshold → always route to cloud
          2. Else if random < cloud_sample_rate → probabilistic sampling
          3. Else → process at edge
        """
        if latency < self.latency_threshold:
            return True
        elif random.random() < self.cloud_sample_rate:
            return True
        return False

    def _optimize(self):
        """
        Multi-objective optimization step.

        Adjusts controller parameters based on observed window metrics.
        Runs every CONTROLLER_WINDOW_SIZE messages.
        """
        if self._window_total == 0:
            return

        # Compute window metrics
        window_anomaly_rate = self._window_anomalies / self._window_total
        window_avg_rtt = self._window_rtt_sum / self._window_total

        # Apply EMA smoothing for stability
        alpha = config.CONTROLLER_ALPHA
        beta = config.CONTROLLER_BETA
        self.edge_anomaly_rate = alpha * window_anomaly_rate + (1 - alpha) * self.edge_anomaly_rate
        self._prev_avg_rtt = self.avg_rtt
        self.avg_rtt = beta * window_avg_rtt + (1 - beta) * self.avg_rtt

        # ── Control Policy ──────────────────────────────────────────
        if self.edge_anomaly_rate > 0.15:
            # HIGH ANOMALY RATE: Edge model is struggling.
            # Send more data to cloud for better model training.
            self.latency_threshold += self._threshold_step
            self.cloud_sample_rate = min(
                self.cloud_sample_rate + 0.05,
                config.CLOUD_SAMPLE_MAX
            )
            self.retrain_interval = max(
                self.retrain_interval - 50,
                config.RETRAIN_INTERVAL_MIN
            )
            action = "EXPAND_CLOUD (high anomaly rate)"

        elif self.edge_anomaly_rate < 0.02:
            # LOW ANOMALY RATE: Edge is handling well.
            # Save bandwidth by processing more at edge.
            self.latency_threshold -= self._threshold_step
            self.cloud_sample_rate = max(
                self.cloud_sample_rate - 0.05,
                config.CLOUD_SAMPLE_MIN
            )
            self.retrain_interval = min(
                self.retrain_interval + 100,
                config.RETRAIN_INTERVAL_MAX
            )
            action = "REDUCE_CLOUD (low anomaly rate)"

        else:
            # STABLE: Fine-tune based on RTT trend
            rtt_trend = self.avg_rtt - self._prev_avg_rtt
            if rtt_trend > 5:
                # RTT increasing → network degrading → lean toward edge
                self.latency_threshold -= self._threshold_fine
                action = "FINE_TUNE_EDGE (RTT rising)"
            elif rtt_trend < -5:
                # RTT decreasing → network improving → lean toward cloud
                self.latency_threshold += self._threshold_fine
                action = "FINE_TUNE_CLOUD (RTT falling)"
            else:
                action = "HOLD (stable)"

        # Clamp all values to configured bounds
        self.latency_threshold = max(
            config.LATENCY_THRESHOLD_MIN,
            min(config.LATENCY_THRESHOLD_MAX, self.latency_threshold)
        )

        print(f"[controller] {action} | threshold={self.latency_threshold:.0f}ms "
              f"sample_rate={self.cloud_sample_rate:.2f} retrain_every={self.retrain_interval} "
              f"anomaly_rate={self.edge_anomaly_rate:.3f} avg_rtt={self.avg_rtt:.0f}ms "
              f"cloud_backlog={self._cloud_backlog}")

        # Persist state to Cassandra
        self._persist_state()

        # Reset window accumulators
        self._window_total = 0
        self._window_anomalies = 0
        self._window_rtt_sum = 0.0

    def _persist_state(self):
        """Write current controller state to Cassandra for dashboard visibility."""
        if self._cass_session is None:
            return
        try:
            self._cass_session.execute(
                """INSERT INTO controller_state
                   (controller_id, latency_threshold, cloud_sample_rate, retrain_interval,
                    edge_anomaly_rate, cloud_backlog, avg_rtt, last_updated)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, toTimestamp(now()))""",
                (
                    config.CONTROLLER_ID,
                    self.latency_threshold,
                    self.cloud_sample_rate,
                    self.retrain_interval,
                    self.edge_anomaly_rate,
                    self._cloud_backlog,
                    self.avg_rtt
                )
            )
        except Exception as e:
            print(f"[controller] Failed to persist state: {e}")


def main():
    print("Starting Edge Node with Adaptive Controller...")

    # Load baseline Isolation Forest model
    try:
        model = joblib.load(config.MODEL_PATH)
        print(f"Loaded edge model from {config.MODEL_PATH}")
    except FileNotFoundError:
        print(f"Edge model not found at {config.MODEL_PATH}. Please run train_initial_edge_model.py first.")
        return

    # Initialize the adaptive controller
    controller = AdaptiveController()

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

    # Also consume controller-metrics for retrain feedback from cloud
    controller_consumer = None
    try:
        controller_consumer = KafkaConsumer(
            config.TOPIC_CONTROLLER,
            bootstrap_servers=[config.KAFKA_BROKER],
            auto_offset_reset='latest',
            group_id='controller_feedback_group',
            value_deserializer=json_deserializer,
            consumer_timeout_ms=100  # Non-blocking
        )
    except Exception as e:
        print(f"[controller] Could not subscribe to controller-metrics: {e}")

    print(f"Listening on topic: {config.TOPIC_RAW}")

    features = ['Air temperature [K]', 'Process temperature [K]',
                'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']

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

            # ── Adaptive Routing Decision ───────────────────────────
            routed_to_cloud = controller.should_route_to_cloud(latency)
            is_anomaly = False

            if routed_to_cloud:
                # Route to cloud (deterministic or probabilistic sampling)
                messages_to_cloud += 1
                data['routing'] = 'cloud_offload'
                data['latency_ms'] = latency
                producer.send(config.TOPIC_CLOUD, value=data)
            else:
                # Process locally at edge with Isolation Forest
                prediction = model.predict(X)[0]

                if prediction == -1:
                    is_anomaly = True
                    anomalies_detected += 1
                    alert = {
                        'timestamp': data.get('timestamp', time.time()),
                        'original_data': data,
                        'latency_ms': latency,
                        'alert_type': 'edge_anomaly',
                        'product_id': data.get('Product ID', 'UNKNOWN')
                    }
                    producer.send(config.TOPIC_ALERTS, value=alert)

            # Record metrics in controller
            controller.record_message(latency, is_anomaly, routed_to_cloud)

            # Check for retrain feedback from cloud (non-blocking)
            if controller_consumer:
                try:
                    for ctrl_msg in controller_consumer:
                        ctrl_data = ctrl_msg.value
                        if ctrl_data.get('type') == 'retrain_complete':
                            controller.record_retrain()
                            print(f"[controller] Cloud retrain complete — "
                                  f"loss={ctrl_data.get('training_loss', '?')}")
                except Exception:
                    pass  # No messages or timeout — fine

            # Log periodic stats
            if total_messages % 100 == 0:
                cloud_pct = (messages_to_cloud / total_messages) * 100
                print(f"Stats: processed={total_messages} anomalies={anomalies_detected} "
                      f"cloud={cloud_pct:.1f}% threshold={controller.latency_threshold:.0f}ms "
                      f"sample_rate={controller.cloud_sample_rate:.2f}")

    except KeyboardInterrupt:
        print("\nEdge Node stopped by user.")
    finally:
        consumer.close()
        producer.close()
        if controller_consumer:
            controller_consumer.close()
        print("Kafka clients closed.")

if __name__ == "__main__":
    main()

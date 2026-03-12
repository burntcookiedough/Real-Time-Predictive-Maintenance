import os

# Ensure JAVA_HOME is set for PySpark on this local machine
if "JAVA_HOME" not in os.environ:
    # Use the portable JDK 17 we just downloaded
    local_jdk = os.path.abspath(os.path.join(os.path.dirname(__file__), "jdk-17.0.18+8"))
    if os.path.exists(local_jdk):
        os.environ["JAVA_HOME"] = local_jdk

# Ensure HADOOP_HOME is set to load winutils.exe
if "HADOOP_HOME" not in os.environ:
    local_hadoop = os.path.abspath(os.path.join(os.path.dirname(__file__), "hadoop"))
    if os.path.exists(local_hadoop):
        os.environ["HADOOP_HOME"] = local_hadoop
        
        # Add to PATH so hadoop.dll can be found
        hadoop_bin = os.path.join(local_hadoop, "bin")
        if hadoop_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = hadoop_bin + os.pathsep + os.environ.get("PATH", "")

# Shared configurations

KAFKA_BROKER = 'localhost:9092'
TOPIC_RAW = 'raw-sensor-data'
TOPIC_ALERTS = 'edge-alerts'
TOPIC_CLOUD = 'cloud-data'

# Latency Simulation
SIMULATED_LATENCY_MIN = 50
SIMULATED_LATENCY_MAX = 500
LATENCY_ROUTE_THRESHOLD = 200  # default initial value; controller overrides dynamically

# Data Paths
MODEL_PATH = './edge_model.pkl'
CLOUD_DATA_PATH = './historical_data.csv'

# ── Adaptive Edge-Cloud Controller ──────────────────────────────
CONTROLLER_ID = 'edge_controller_v1'
TOPIC_CONTROLLER = 'controller-metrics'

# Controller optimization bounds
LATENCY_THRESHOLD_MIN = 100    # Never route below 100ms to edge
LATENCY_THRESHOLD_MAX = 400    # Never route above 400ms to cloud
CLOUD_SAMPLE_MIN = 0.1         # Always send at least 10% to cloud
CLOUD_SAMPLE_MAX = 0.9         # Never send more than 90% to cloud
RETRAIN_INTERVAL_MIN = 200     # Minimum records before retrain
RETRAIN_INTERVAL_MAX = 2000    # Maximum records before retrain

# Controller tuning
CONTROLLER_WINDOW_SIZE = 200   # Evaluate every N messages
CONTROLLER_ALPHA = 0.3         # EMA smoothing for anomaly rate
CONTROLLER_BETA = 0.2          # EMA smoothing for RTT

# ── Graph-Augmented Anomaly Scoring ─────────────────────────────
GRAPH_SCORE_ALPHA = 0.4        # Weight for community risk in scoring
GRAPH_SCORE_BETA = 0.3         # Weight for PageRank centrality in scoring
BASE_TOOL_WEAR_THRESHOLD = 200 # Base tool wear threshold (mins)
BASE_RPM_THRESHOLD = 1300      # Base RPM threshold

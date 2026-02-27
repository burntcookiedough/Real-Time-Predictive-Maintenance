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
LATENCY_ROUTE_THRESHOLD = 200 # under this goes to cloud, over this stays at edge

# Data Paths
MODEL_PATH = './edge_model.pkl'
CLOUD_DATA_PATH = './historical_data.csv'

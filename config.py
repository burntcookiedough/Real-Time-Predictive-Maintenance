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

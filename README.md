# Real-Time Predictive Maintenance

A Lambda Architecture platform demonstrating real-time streaning analytics and batch machine learning for predictive maintenance on a simulated factory floor.

## Architecture

![Lambda Architecture](/docs/architecture.png) *Assuming an architecture diagram exists*

1. **Edge Node / Sensor Simulator (`sensor_sim.py`)**: Continuously simulates high-frequency telemetry data for 10,000 industrial machines (temperature, torque, vibration) and streams it to Kafka.
2. **Speed Layer (`speed_layer.py`)**: A PySpark Structured Streaming job that consumes the Kafka topic in real-time, calculates rolling averages, runs an edge ML model (to predict immediate failures), and writes states and alerts to Cassandra.
3. **Batch Layer (`hdfs_writer.py`)**: Another PySpark stream that sinks raw Kafka data into an HDFS datalake for historical persistence.
4. **Analytic layer (`graph_analytics.py`)**: A periodic batch PySpark job utilizing GraphFrames to calculate PageRank (identifying critical systemic bottlenecks) and Connected Components (identifying cascading failure domains) over the historical data. Writes findings to Cassandra.
5. **Serving Layer (Cassandra)**: The `pdm` keyspace houses `machine_states`, `realtime_alerts`, `pagerank_scores`, and `failure_communities`.
6. **Next.js Dashboard (`frontend/`)**: A modern web UI polling Cassandra via direct connections and Server-Sent Events (SSE) to visualize the factory floor, ticker tape alerts, and graph analytic insights in real-time.

## One-Click Startup (Windows)

To start the entire platform—including all Docker infrastructure, Python streams, scheduled batch jobs, and the web frontend—run the unified startup script from PowerShell:

```powershell
.\start_all.ps1
```

**What the script does:**
1. Spins up Cassandra, Kafka, Zookeeper, and HDFS via `docker-compose`.
2. Starts the continuous sensor simulator (`sensor_sim.py`).
3. Starts the real-time speed layer (`speed_layer.py`).
4. Starts the HDFS batch writer (`hdfs_writer.py`).
5. Initiates a background scheduler to run `graph_analytics.py` every 5 minutes.
6. Starts the Next.js development server.

All logs stream directly to the single terminal window.

**To safely shut down the system:**
Press `Ctrl+C` in the terminal running `start_all.ps1`. The script traps the interrupt and gracefully cleans up all child process trees (Python, Node.js) and turns off the Docker containers.

## Manual Execution

If you prefer to run services manually (e.g. for debugging):

1. **Infrastructure**: `docker-compose up -d`
2. **Simulation**: `python sensor_sim.py`
3. **Real-time Pipeline**: `python speed_layer.py`
4. **HDFS Archiving**: `python hdfs_writer.py`
5. **Graph Analytics**: `python graph_analytics.py` (Run this periodically as desired)
6. **Frontend**: `cd frontend; npm run dev`

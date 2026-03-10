# Real-Time Predictive Maintenance: Startup Guide

This document outlines the procedure to start the Real-Time Predictive Maintenance system. There are two ways to launch the platform: using the **Automated One-Click Script** (Recommended) or by **Manually Executing Services** (useful for debugging and individual component testing).

---

## Method 1: Automated One-Click Startup (Windows)

The repository includes a PowerShell script (`start_all.ps1`) designed to seamlessly spin up the entire infrastructure, start the microservices, and boot the frontend dashboard from a single command line.

### Prerequisites:
- Ensure **Docker Desktop** is currently running on your machine.
- Open **PowerShell** as an Administrator (or a user with permissions to execute Docker commands).

### Steps:
1. Navigate to the root directory of the project:
   ```powershell
   cd "C:\Users\anshu\Desktop\Real-Time Predictive Maintenance"
   ```
2. Execute the unified startup script:
   ```powershell
   .\start_all.ps1
   ```

### What happens behind the scenes?
Once you hit enter, the script sequentially orchestrates the following:
1. **Docker Infrastructure:** Spins up Kafka, Zookeeper, Cassandra, and HDFS in detached mode using `docker-compose`.
2. **Health Checks + Schema Init:** Actively polls Cassandra and Kafka until they accept connections (up to 60s), then auto-applies `cassandra_schema.cql` to create the `pdm` keyspace and all tables.
3. **Checkpoint Cleanup:** Removes any stale PySpark checkpoints from previous runs to prevent `OffsetOutOfRange` crashes.
4. **Sensor Simulation + Data Pipelines:**
   - Starts `sensor_sim.py` to continuously generate telemetry data.
   - Starts `speed_layer.py` (PySpark streaming job for real-time anomaly detection).
   - Starts `hdfs_writer.py` (sinks telemetry into the historical datalake).
5. **Graph Analytics Scheduler:** Runs `graph_analytics.py` once immediately after a 90-second data collection window, then periodically every 5 minutes.
6. **Frontend Application:** Starts the Next.js development server (`npm run dev`).

### Accessing the Dashboard:
Once all 6 steps complete, the terminal will display:
```
Dashboard:  http://localhost:3000
```
Open your browser to **http://localhost:3000** to view the live factory metrics. The **Batch Analytics** panels (PageRank + Fault Cascades) will populate within ~2 minutes of first startup.

### Graceful Shutdown:
To safely spin down the entire platform:
1. Click into the terminal window running `start_all.ps1`.
2. Press **`Ctrl + C`**.
3. The script will gracefully kill all child process trees (Python, Java, Node.js) and issue a `docker-compose down` to stop the containers.

---

## Method 2: Manual Execution

If you need to debug a specific component, restart a failed microservice, or just want to run the pipeline manually, you can start the components individually. You will likely want to open multiple terminal tabs for this approach.

### 1. Boot Infrastructure (Terminal 1)
Make sure Docker Desktop is open.
```powershell
docker-compose up -d
```
Wait about 20–30 seconds to ensure Zookeeper, Kafka, and Cassandra are fully initialized.

### 2. Start Sensor Simulation (Terminal 2)
```powershell
python sensor_sim.py
```

### 3. Start Streaming ML Inference (Terminal 3)
*Note: Wait a few seconds after starting the simulation so Kafka topics exist.*
```powershell
python speed_layer.py
```

### 4. Start Datalake Ingestion (Terminal 4)
```powershell
python hdfs_writer.py
```

### 5. Run Batch Analytics (Terminal 5)
You can run this script periodically whenever you want to detect failure domains and perform PageRank networking calculations over historical sensor data.
```powershell
python graph_analytics.py
```

### 6. Start the Dashboard (Terminal 6)
```powershell
cd frontend
npm run dev
```

### Manual Teardown:
To tear down the stack manually:
1. Press `Ctrl + C` in all Python and Node.js terminal windows.
2. Run `docker-compose down` to turn off and remove the backend containers.

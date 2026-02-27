-- Cassandra Schema for Real-Time Predictive Maintenance

-- Create Keyspace
CREATE KEYSPACE IF NOT EXISTS pdm
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE pdm;

-- Table for real-time anomalous events (Speed Layer)
CREATE TABLE IF NOT EXISTS realtime_alerts (
    machine_id text,
    alert_time timestamp,
    latency_ms int,
    air_temp double,
    process_temp double,
    rotational_speed double,
    torque double,
    tool_wear int,
    prediction_score double,
    PRIMARY KEY (machine_id, alert_time)
) WITH CLUSTERING ORDER BY (alert_time DESC);

-- Table for the current state of all machines (Serving Layer - Dashboard)
CREATE TABLE IF NOT EXISTS machine_states (
    machine_id text PRIMARY KEY,
    last_update timestamp,
    status text, -- e.g., 'HEALTHY', 'WARNING', 'CRITICAL'
    air_temp double,
    torque double
);

-- Table for Global Graph Analytics (Batch Layer - Network Centrality)
-- PageRank helps identify which machine is the most critical chokepoint
CREATE TABLE IF NOT EXISTS pagerank_scores (
    machine_id text PRIMARY KEY,
    pagerank double,
    last_computed timestamp
);

-- Table for Community Discovery (Batch Layer)
-- Helps group machines into interconnected "fault cascades"
CREATE TABLE IF NOT EXISTS failure_communities (
    community_id text,
    machine_id text,
    PRIMARY KEY (community_id, machine_id)
);

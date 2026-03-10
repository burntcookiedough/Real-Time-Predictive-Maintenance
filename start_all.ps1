<#
.SYNOPSIS
Starts the Real-Time Predictive Maintenance system and stops it gracefully on exit.

.DESCRIPTION
This script orchestrates the entire Lambda Architecture platform:
  1. Docker infrastructure (Kafka, Zookeeper, Cassandra, HDFS)
  2. Cassandra schema initialization
  3. Sensor simulation + streaming pipelines (Speed Layer, HDFS Writer)
  4. Graph analytics (immediate first run + periodic 5-minute schedule)
  5. Next.js dashboard frontend

Press Ctrl+C for a clean shutdown of all services.
#>

$ErrorActionPreference = "Stop"
$script:processList = @()
$ROOT = $PSScriptRoot
if (-not $ROOT) { $ROOT = (Get-Location).Path }

# ─────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║   Real-Time Predictive Maintenance — Startup Script     ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────
function Write-Step($step, $total, $msg) {
    Write-Host "`n[$step/$total] $msg" -ForegroundColor Yellow
}

function Write-OK($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-Info($msg) {
    Write-Host "  → $msg" -ForegroundColor DarkGray
}

function Write-Warn($msg) {
    Write-Host "  ⚠ $msg" -ForegroundColor DarkYellow
}

function Start-ServiceProcess($executable, $arguments, $workingDir, $name) {
    Write-Host "  => Starting $name..." -ForegroundColor Green
    $proc = Start-Process -FilePath $executable -ArgumentList $arguments `
        -WorkingDirectory $workingDir -NoNewWindow -PassThru
    $script:processList += $proc
    return $proc
}

# ─────────────────────────────────────────────────────────────────
# Health Checks
# ─────────────────────────────────────────────────────────────────
function Wait-ForCassandra {
    param([int]$TimeoutSeconds = 60)
    Write-Info "Waiting for Cassandra to accept CQL connections (up to ${TimeoutSeconds}s)..."
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $result = docker exec cassandra cqlsh -e "DESCRIBE KEYSPACES;" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Cassandra is ready."
            return $true
        }
        Start-Sleep -Seconds 3
        $elapsed += 3
        Write-Host "." -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Warn "Cassandra NOT ready after ${TimeoutSeconds}s — proceeding anyway."
    return $false
}

function Wait-ForKafka {
    param([int]$TimeoutSeconds = 30)
    Write-Info "Waiting for Kafka broker to be reachable (up to ${TimeoutSeconds}s)..."
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $result = docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Kafka broker is ready."
            return $true
        }
        Start-Sleep -Seconds 3
        $elapsed += 3
        Write-Host "." -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Warn "Kafka NOT ready after ${TimeoutSeconds}s — proceeding anyway."
    return $false
}

# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
Show-Banner

try {
    # ── Step 1: Docker Infrastructure ────────────────────────────
    Write-Step 1 6 "Starting Docker infrastructure (Kafka, Cassandra, HDFS, Zookeeper)..."
    docker-compose up -d 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start Docker containers. Is Docker Desktop running?"
        exit 1
    }
    Write-OK "Docker containers launched."

    # ── Step 2: Health Checks + Schema Init ──────────────────────
    Write-Step 2 6 "Running health checks and initializing Cassandra schema..."

    Wait-ForCassandra -TimeoutSeconds 60
    Wait-ForKafka -TimeoutSeconds 30

    # Always apply the schema (IF NOT EXISTS makes it idempotent)
    Write-Info "Applying cassandra_schema.cql..."
    $schemaPath = Join-Path $ROOT "cassandra_schema.cql"
    if (Test-Path $schemaPath) {
        Get-Content $schemaPath | docker exec -i cassandra cqlsh 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Cassandra schema initialized (keyspace 'pdm' + all tables)."
        } else {
            Write-Warn "Schema apply returned a non-zero exit code. Check CQL file."
        }
    } else {
        Write-Warn "cassandra_schema.cql not found at $schemaPath — skipping."
    }

    # ── Step 3: Clear stale checkpoints ──────────────────────────
    Write-Step 3 6 "Cleaning stale PySpark checkpoints..."
    $checkpointDir = Join-Path $ROOT "checkpoints"
    if (Test-Path $checkpointDir) {
        Remove-Item -Recurse -Force $checkpointDir -ErrorAction SilentlyContinue
        Write-OK "Removed old checkpoints (prevents OffsetOutOfRange errors)."
    } else {
        Write-Info "No stale checkpoints found — clean slate."
    }

    # ── Step 4: Start Python Microservices ───────────────────────
    Write-Step 4 6 "Starting Python microservices..."

    Start-ServiceProcess "python" "-u sensor_sim.py" $ROOT "Sensor Simulator"

    # Give Kafka a moment to create topics from the first batch of messages
    Write-Info "Waiting 5s for Kafka topic auto-creation..."
    Start-Sleep -Seconds 5

    Start-ServiceProcess "python" "-u speed_layer.py" $ROOT "Speed Layer (PySpark Streaming)"
    Start-ServiceProcess "python" "-u hdfs_writer.py" $ROOT "HDFS Writer"

    # ── Step 5: Graph Analytics ──────────────────────────────────
    Write-Step 5 6 "Scheduling Graph Analytics..."

    # Run an immediate first graph analytics job after a brief data collection window (90s),
    # then repeat every 5 minutes. This ensures the dashboard's batch panels populate quickly.
    $graphCmd = @"
        Start-Sleep -Seconds 90
        Write-Host '[graph_scheduler] Running initial graph analytics...' -ForegroundColor Magenta
        python -u graph_analytics.py
        while (`$true) {
            Start-Sleep -Seconds 300
            Write-Host '[graph_scheduler] Running periodic graph analytics...' -ForegroundColor Magenta
            python -u graph_analytics.py
        }
"@
    Start-ServiceProcess "powershell" "-Command `"$graphCmd`"" $ROOT "Graph Analytics Scheduler"
    Write-OK "Graph analytics will run in 90s (then every 5 min)."

    # ── Step 6: Next.js Frontend ─────────────────────────────────
    Write-Step 6 6 "Starting Next.js Frontend..."
    $frontendDir = Join-Path $ROOT "frontend"
    Start-ServiceProcess "npm.cmd" "run dev" $frontendDir "Next.js Dev Server"

    # ── Ready ────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║             All services started successfully!          ║" -ForegroundColor Green
    Write-Host "  ║                                                        ║" -ForegroundColor Green
    Write-Host "  ║   Dashboard:  http://localhost:3000                     ║" -ForegroundColor Green
    Write-Host "  ║   Press Ctrl+C to shut down all services               ║" -ForegroundColor Green
    Write-Host "  ╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    # Wait indefinitely until the user presses Ctrl+C
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    # ── Graceful Shutdown ────────────────────────────────────────
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "  ║                   SHUTTING DOWN...                      ║" -ForegroundColor Red
    Write-Host "  ╚══════════════════════════════════════════════════════════╝" -ForegroundColor Red

    foreach ($p in $script:processList) {
        if ($p -and -not $p.HasExited) {
            Write-Info "Stopping process tree PID $($p.Id)..."
            # taskkill /T kills the process and all child processes
            Start-Process -FilePath "taskkill" -ArgumentList "/F /T /PID $($p.Id)" `
                -NoNewWindow -Wait -ErrorAction SilentlyContinue
        }
    }

    Write-Info "Stopping Docker containers..."
    docker-compose down 2>&1 | Out-Null

    Write-Host ""
    Write-OK "Shutdown complete. Have a great day!"
    Write-Host ""
}

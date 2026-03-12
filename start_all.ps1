<#
.SYNOPSIS
Starts the Real-Time Predictive Maintenance system and stops it gracefully on exit.

.DESCRIPTION
This script orchestrates the entire Lambda Architecture platform:
  1. Prerequisite validation (Docker, Python, Node.js, Java)
  2. Docker infrastructure (Kafka, Zookeeper, Cassandra, HDFS)
  3. Cassandra schema initialization
  4. Sensor simulation + streaming pipelines (Speed Layer, HDFS Writer)
  5. Graph analytics (immediate first run + periodic 5-minute schedule)
  6. Next.js dashboard frontend

Usage:
  .\start_all.ps1              # Normal startup
  .\start_all.ps1 -Clean       # Full teardown: stop containers, delete temp data
  .\start_all.ps1 -SkipDocker  # Skip Docker startup (containers already running)

Press Ctrl+C for a clean shutdown of all services.
#>

param(
    [switch]$Clean,
    [switch]$SkipDocker
)

$ErrorActionPreference = "Continue"
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

function Write-Fail($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
}

function Start-ServiceProcess($executable, $arguments, $workingDir, $name) {
    Write-Host "  => Starting $name..." -ForegroundColor Green
    $proc = Start-Process -FilePath $executable -ArgumentList $arguments `
        -WorkingDirectory $workingDir -NoNewWindow -PassThru
    $script:processList += $proc
    return $proc
}

# ─────────────────────────────────────────────────────────────────
# Clean Mode — Full Teardown
# ─────────────────────────────────────────────────────────────────
if ($Clean) {
    Show-Banner
    Write-Host "  CLEANUP MODE — Tearing down all resources..." -ForegroundColor Red
    Write-Host ""

    # Kill any running Python/Node processes related to this project
    Write-Info "Stopping any running Python processes..."
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

    # Stop Docker containers
    Write-Info "Stopping Docker containers..."
    docker-compose -f (Join-Path $ROOT "docker-compose.yml") down 2>&1 | Out-Null

    # Clean temp directories
    Write-Info "Removing temporary directories..."
    $tempDirs = @("checkpoints", "hdfs_temp", "spark_temp_graph", "graph_snapshot", "spark-warehouse", "metastore_db")
    foreach ($dir in $tempDirs) {
        $path = Join-Path $ROOT $dir
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path -ErrorAction SilentlyContinue
            Write-OK "Removed $dir/"
        }
    }

    # Clean log files
    Write-Info "Removing log files..."
    Get-ChildItem -Path $ROOT -Filter "*.log" -File | Remove-Item -Force -ErrorAction SilentlyContinue
    Write-OK "Removed all .log files."

    # Clean Python caches
    Write-Info "Removing Python cache files..."
    $cacheDirs = @("__pycache__", ".mypy_cache", ".ruff_cache")
    foreach ($dir in $cacheDirs) {
        $path = Join-Path $ROOT $dir
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path -ErrorAction SilentlyContinue
            Write-OK "Removed $dir/"
        }
    }

    # Clean Next.js build cache
    $nextCache = Join-Path $ROOT "frontend\.next"
    if (Test-Path $nextCache) {
        Remove-Item -Recurse -Force $nextCache -ErrorAction SilentlyContinue
        Write-OK "Removed frontend/.next/"
    }

    Write-Host ""
    Write-OK "Cleanup complete. All temporary data removed."
    Write-Host ""
    exit 0
}

# ─────────────────────────────────────────────────────────────────
# Prerequisite Checks
# ─────────────────────────────────────────────────────────────────
function Test-Prerequisites {
    Write-Step 0 7 "Checking prerequisites..."
    $allGood = $true

    # Docker
    $dockerRunning = $false
    try {
        $dockerInfo = docker info 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            $dockerRunning = $true
            Write-OK "Docker Desktop is running."
        }
    } catch { }
    if (-not $dockerRunning) {
        Write-Fail "Docker Desktop is NOT running. Please start it first."
        $allGood = $false
    }

    # Python
    try {
        $pyVer = python --version 2>&1 | Out-String
        if ($pyVer -match "Python (\d+\.\d+)") {
            Write-OK "Python found: $($pyVer.Trim())"
        } else {
            Write-Fail "Python not found on PATH."
            $allGood = $false
        }
    } catch {
        Write-Fail "Python not found on PATH."
        $allGood = $false
    }

    # Node.js
    try {
        $nodeVer = node --version 2>&1 | Out-String
        Write-OK "Node.js found: $($nodeVer.Trim())"
    } catch {
        Write-Fail "Node.js not found on PATH."
        $allGood = $false
    }

    # Java (bundled JDK)
    $jdkPath = Join-Path $ROOT "jdk-17.0.18+8"
    if (Test-Path $jdkPath) {
        Write-OK "Bundled JDK 17 found."
    } else {
        Write-Warn "Bundled JDK not found at $jdkPath — Spark may fail."
    }

    # Hadoop winutils
    $winutilsPath = Join-Path $ROOT "hadoop\bin\winutils.exe"
    if (Test-Path $winutilsPath) {
        Write-OK "winutils.exe found (Hadoop Windows support)."
    } else {
        Write-Warn "winutils.exe not found — HDFS operations may fail on Windows."
    }

    # Edge model
    $modelPath = Join-Path $ROOT "edge_model.pkl"
    if (Test-Path $modelPath) {
        Write-OK "Edge ML model (edge_model.pkl) found."
    } else {
        Write-Warn "edge_model.pkl not found. Run: python train_initial_edge_model.py"
    }

    # Frontend node_modules
    $nodeModules = Join-Path $ROOT "frontend\node_modules"
    if (Test-Path $nodeModules) {
        Write-OK "Frontend dependencies installed."
    } else {
        Write-Warn "frontend/node_modules missing. Run: cd frontend && npm install"
    }

    # Port checks
    $portsToCheck = @(
        @{Port=9092; Name="Kafka"},
        @{Port=9042; Name="Cassandra"},
        @{Port=3000; Name="Next.js Dashboard"}
    )
    foreach ($p in $portsToCheck) {
        $inUse = netstat -ano 2>$null | Select-String ":$($p.Port)\s.*LISTENING"
        if ($inUse) {
            $pid = ($inUse -split '\s+')[-1]
            # Check if it's a Docker process (expected for infra ports)
            if ($p.Port -in @(9092, 9042) -and $SkipDocker) {
                Write-OK "Port $($p.Port) ($($p.Name)) — already in use (expected with -SkipDocker)."
            } elseif ($p.Port -eq 3000) {
                Write-Warn "Port $($p.Port) ($($p.Name)) already in use by PID $pid. Kill it: taskkill /F /PID $pid"
            }
        }
    }

    if (-not $allGood) {
        Write-Host ""
        Write-Fail "CRITICAL prerequisites missing. Fix the issues above before proceeding."
        exit 1
    }

    Write-Host ""
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
Test-Prerequisites

try {
    # ── Step 1: Docker Infrastructure ────────────────────────────
    if ($SkipDocker) {
        Write-Step 1 7 "Skipping Docker startup (-SkipDocker flag)..."
        Write-OK "Assuming containers are already running."
    } else {
        Write-Step 1 7 "Starting Docker infrastructure (Kafka, Cassandra, HDFS, Zookeeper)..."
        $composeOutput = docker-compose up -d 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            Write-Host $composeOutput -ForegroundColor Red
            Write-Fail "Failed to start Docker containers. Is Docker Desktop running?"
            exit 1
        }
        Write-OK "Docker containers launched."
    }

    # ── Step 2: Health Checks + Schema Init ──────────────────────
    Write-Step 2 7 "Running health checks and initializing Cassandra schema..."

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
    Write-Step 3 7 "Cleaning stale PySpark checkpoints..."
    $checkpointDir = Join-Path $ROOT "checkpoints"
    if (Test-Path $checkpointDir) {
        Remove-Item -Recurse -Force $checkpointDir -ErrorAction SilentlyContinue
        Write-OK "Removed old checkpoints (prevents OffsetOutOfRange errors)."
    } else {
        Write-Info "No stale checkpoints found — clean slate."
    }

    # Also clean spark temp if present
    $sparkTemp = Join-Path $ROOT "spark_temp_graph"
    if (Test-Path $sparkTemp) {
        Remove-Item -Recurse -Force $sparkTemp -ErrorAction SilentlyContinue
        Write-Info "Cleaned spark_temp_graph directory."
    }

    # ── Step 4: Train edge model if missing ──────────────────────
    Write-Step 4 7 "Checking edge ML model..."
    $modelPath = Join-Path $ROOT "edge_model.pkl"
    if (Test-Path $modelPath) {
        Write-OK "edge_model.pkl exists — skipping training."
    } else {
        Write-Info "Training initial edge model..."
        $trainScript = Join-Path $ROOT "train_initial_edge_model.py"
        if (Test-Path $trainScript) {
            python $trainScript 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-OK "Edge model trained successfully."
            } else {
                Write-Warn "Edge model training failed. Check train_initial_edge_model.py."
            }
        } else {
            Write-Warn "train_initial_edge_model.py not found."
        }
    }

    # ── Step 5: Start Python Microservices ───────────────────────
    Write-Step 5 7 "Starting Python microservices..."

    Start-ServiceProcess "python" "-u sensor_sim.py" $ROOT "Sensor Simulator"

    # Give Kafka a moment to create topics from the first batch of messages
    Write-Info "Waiting 5s for Kafka topic auto-creation..."
    Start-Sleep -Seconds 5

    Start-ServiceProcess "python" "-u speed_layer.py" $ROOT "Speed Layer (PySpark Streaming)"
    Start-ServiceProcess "python" "-u hdfs_writer.py" $ROOT "HDFS Writer"

    # ── Step 6: Graph Analytics ──────────────────────────────────
    Write-Step 6 7 "Scheduling Graph Analytics..."

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

    # ── Step 7: Next.js Frontend ─────────────────────────────────
    Write-Step 7 7 "Starting Next.js Frontend..."
    $frontendDir = Join-Path $ROOT "frontend"
    Start-ServiceProcess "npm.cmd" "run dev" $frontendDir "Next.js Dev Server"

    # ── Ready ────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║             All services started successfully!          ║" -ForegroundColor Green
    Write-Host "  ║                                                        ║" -ForegroundColor Green
    Write-Host "  ║   Dashboard:  http://localhost:3000                     ║" -ForegroundColor Green
    Write-Host "  ║   HDFS UI:   http://localhost:9870                     ║" -ForegroundColor Green
    Write-Host "  ║                                                        ║" -ForegroundColor Green
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

    if (-not $SkipDocker) {
        Write-Info "Stopping Docker containers..."
        docker-compose down 2>&1 | Out-Null
    }

    Write-Host ""
    Write-OK "Shutdown complete. Have a great day!"
    Write-Host ""
}

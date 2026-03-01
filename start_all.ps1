<#
.SYNOPSIS
Starts the Real-Time Predictive Maintenance system and stops it gracefully on exit.
#>

$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  Real-Time Predictive Maintenance - Startup Script" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Start Docker Containers
Write-Host "`n[1/4] Starting Docker infrastructure (Kafka, Cassandra, HDFS, Zookeeper)..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to start Docker containers. Is Docker Desktop running?"
    exit 1
}

Write-Host "Waiting 30 seconds for services to initialize..." -ForegroundColor DarkGray
Start-Sleep -Seconds 30

$script:processList = @()

function Start-ServiceProcess($executable, $args, $workingDir=".", $name="") {
    Write-Host " => Starting $name..." -ForegroundColor Green
    $proc = Start-Process -FilePath $executable -ArgumentList $args -WorkingDirectory $workingDir -NoNewWindow -PassThru
    $script:processList += $proc
    return $proc
}

try {
    # 2. Start Python Microservices
    # -u ensures Python output is unbuffered and prints immediately to this console
    Write-Host "`n[2/4] Starting Python microservices..." -ForegroundColor Yellow
    Start-ServiceProcess "python" "-u sensor_sim.py" "." "Sensor Simulator"
    
    # Give Kafka a moment to create topics if not already created
    Start-Sleep -Seconds 5
    
    Start-ServiceProcess "python" "-u speed_layer.py" "." "Speed Layer"
    Start-ServiceProcess "python" "-u hdfs_writer.py" "." "HDFS Writer"
    
    # 3. Start Graph Analytics loop
    Write-Host "`n[3/4] Starting periodic Graph Analytics job (runs every 5 mins)..." -ForegroundColor Yellow
    $loopCmd = 'while ($true) { Start-Sleep -Seconds 300; Write-Host "`n[graph_scheduler] Starting periodic graph analytics run..." -ForegroundColor Magenta; python -u graph_analytics.py }'
    Start-ServiceProcess "powershell" "-Command `"$loopCmd`"" "." "Graph Analytics Scheduler"
    
    # 4. Start Next.js Frontend
    Write-Host "`n[4/4] Starting Next.js Frontend..." -ForegroundColor Yellow
    Start-ServiceProcess "npm.cmd" "run dev" ".\frontend" "Next.js Dev Server"
    
    Write-Host "`n=======================================================" -ForegroundColor Cyan
    Write-Host " All services started successfully!" -ForegroundColor Green
    Write-Host " Frontend is accessible at: http://localhost:3000 (or 3006)" -ForegroundColor Green
    Write-Host " Output from all services will appear below." -ForegroundColor DarkGray
    Write-Host " PRESS CTRL+C TO STOP ALL SERVICES CAREFULLY." -ForegroundColor Red
    Write-Host "=======================================================`n" -ForegroundColor Cyan

    # Wait indefinitely until the user presses Ctrl+C
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`n`n[SHUTDOWN] Ctrl+C detected. Cleaning up all services gracefully..." -ForegroundColor Red
    
    foreach ($p in $script:processList) {
        if ($p -and -not $p.HasExited) {
            Write-Host " => Stopping process tree PID $($p.Id)..." -ForegroundColor DarkGray
            # taskkill /T kills the process and all child processes (like node.exe from npm or java.exe from pyspark)
            Start-Process -FilePath "taskkill" -ArgumentList "/F /T /PID $($p.Id)" -NoNewWindow -Wait -ErrorAction SilentlyContinue
        }
    }
    
    Write-Host " => Stopping Docker containers..." -ForegroundColor DarkGray
    docker-compose down
    
    Write-Host "`n[SHUTDOWN] Complete. Have a great day!" -ForegroundColor Green
}

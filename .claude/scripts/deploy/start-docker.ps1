# Start Docker Desktop if not running, then start docker-compose stack
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProcess) {
    Write-Host "[startup] Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker.exe"
    Start-Sleep -Seconds 15
}

# Navigate to repo and start compose
$repoPath = "D:\GitHub\BoredBot"
Write-Host "[startup] Starting docker-compose from $repoPath"
cd $repoPath
docker-compose up -d

Write-Host "[startup] Vesper stack started (backend, frontend, scheduler)"

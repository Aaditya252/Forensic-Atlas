param([int]$Port = 8100, [switch]$SkipModel)
$ErrorActionPreference = 'Stop'
$ForensicRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$ForensicOutput = Join-Path $ForensicRoot 'output'
New-Item -ItemType Directory -Path $ForensicOutput -Force | Out-Null
$ForensicDocker = (Get-Command docker -ErrorAction Stop).Source
function Test-ForensicDocker {
    # Windows PowerShell turns native stderr into a terminating error under Stop.
    $ErrorActionPreference = 'Continue'
    & $ForensicDocker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}
$ForensicDockerReady = Test-ForensicDocker
if (-not $ForensicDockerReady) {
    $ForensicDesktop = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $ForensicDocker -Parent) '..\..\Docker Desktop.exe'))
    if (-not (Test-Path -LiteralPath $ForensicDesktop)) { throw 'Start Docker Desktop, then run this script again.' }
    Start-Process -FilePath $ForensicDesktop -WindowStyle Hidden
    $ForensicDeadline = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Seconds 2
        $ForensicDockerReady = Test-ForensicDocker
        if ($ForensicDockerReady) { break }
    } while ((Get-Date) -lt $ForensicDeadline)
    if (-not $ForensicDockerReady) { throw 'Docker did not become ready within 60 seconds.' }
}
$ForensicContainer = 'forensic-atlas-local-graph'
$ForensicGraphPath = Join-Path $ForensicRoot 'cases\graph-data'
New-Item -ItemType Directory -Path $ForensicGraphPath -Force | Out-Null
$ForensicExisting = @(& $ForensicDocker ps -a --format '{{.Names}}')
if ($ForensicContainer -notin $ForensicExisting) {
    $ForensicImage = 'falkordb/falkordb@sha256:107455e862a824e45e8e9f5a7fbfdf5e00a08b14e13eae2577c72fd9e3f59ba6'
    & $ForensicDocker run --name $ForensicContainer --restart unless-stopped -d -p '127.0.0.1:6380:6379' -p '127.0.0.1:3001:3000' --mount "type=bind,source=$ForensicGraphPath,target=/var/lib/falkordb/data" -e 'REDIS_ARGS=--appendonly yes --appendfsync everysec --dir /var/lib/falkordb/data' $ForensicImage | Out-Null
} else {
    & $ForensicDocker start $ForensicContainer | Out-Null
}
if ($LASTEXITCODE -ne 0) { throw 'Could not start the project graph container.' }
$env:FALKORDB_URL = 'redis://127.0.0.1:6380'
if (-not $SkipModel -and (Test-Path -LiteralPath (Join-Path $ForensicRoot 'models\phase2\manifest.json'))) {
    & (Join-Path $PSScriptRoot 'start_phase2_model.ps1')
}
$ForensicHealthUrl = "http://127.0.0.1:$Port/health"
$ForensicHealth = $null
function Assert-ForensicHealth($Health) {
    if (-not $Health.storage.sqlite) { throw 'The case database is unavailable. Inspect output/api.stderr.log.' }
    if (-not $Health.graph.connected) { throw 'The API cannot reach FalkorDB. Inspect the project graph container.' }
    if (-not $SkipModel -and -not $Health.models.localLLM.ready) { throw 'Qwen is not ready. Inspect output/llm.stderr.log.' }
}
try { $ForensicHealth = Invoke-RestMethod -Uri $ForensicHealthUrl -TimeoutSec 3 } catch {}
if ($ForensicHealth) {
    if ([System.IO.Path]::GetFullPath($ForensicHealth.storage.path) -ne (Join-Path $ForensicRoot 'cases\storage\sutram.sqlite3')) { throw 'Port is serving another case database; it was left running.' }
    if ($ForensicHealth.service -ne 'forensic-atlas') { throw "Port $Port is occupied by another service; it was left running." }
    Assert-ForensicHealth $ForensicHealth
    Write-Output "Forensic Atlas is already running: http://127.0.0.1:$Port/"
    return
}
$ForensicPython = (Get-Command python -ErrorAction Stop).Source
$env:SUTRAM_API_PORT = "$Port"
$ForensicServer = Start-Process -FilePath $ForensicPython -ArgumentList @('-m','backend.app','--seed-demo','--sync-demo-graph') -WorkingDirectory $ForensicRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $ForensicOutput 'api.stdout.log') -RedirectStandardError (Join-Path $ForensicOutput 'api.stderr.log') -PassThru
$ForensicServer.Id | Set-Content -LiteralPath (Join-Path $ForensicOutput 'api.pid')
$ForensicDeadline = (Get-Date).AddSeconds(30)
do {
    Start-Sleep -Seconds 1
    try { $ForensicHealth = Invoke-RestMethod -Uri $ForensicHealthUrl -TimeoutSec 2 } catch { $ForensicHealth = $null }
    if ($ForensicHealth -and $ForensicHealth.service -eq 'forensic-atlas') { break }
    if ($ForensicServer.HasExited) { throw 'The API exited. Inspect output/api.stderr.log.' }
} while ((Get-Date) -lt $ForensicDeadline)
if (-not $ForensicHealth -or $ForensicHealth.service -ne 'forensic-atlas') { throw 'The API did not become ready; inspect output/api.stderr.log.' }
Assert-ForensicHealth $ForensicHealth
Write-Output "Forensic Atlas ready: http://127.0.0.1:$Port/"
Write-Output "Graph container: $ForensicContainer"

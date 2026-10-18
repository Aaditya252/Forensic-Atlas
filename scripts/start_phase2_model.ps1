$ErrorActionPreference = 'Stop'
$Phase2Root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Phase2Manifest = Join-Path $Phase2Root 'models\phase2\manifest.json'
if (-not (Test-Path -LiteralPath $Phase2Manifest)) { throw 'Run python scripts/setup_phase2_model.py first.' }
$Phase2Config = Get-Content -LiteralPath $Phase2Manifest -Raw | ConvertFrom-Json
$Phase2Url = [Uri]$Phase2Config.baseUrl
if ($Phase2Url.Scheme -ne 'http' -or $Phase2Url.Host -notin @('127.0.0.1','localhost','::1')) { throw 'Model endpoint must be loopback only.' }
$Phase2Model = [System.IO.Path]::GetFullPath((Join-Path $Phase2Root $Phase2Config.modelPath))
$Phase2Server = [System.IO.Path]::GetFullPath((Join-Path $Phase2Root $Phase2Config.runtimePath))
foreach ($Phase2Path in @($Phase2Model,$Phase2Server)) {
    if (-not $Phase2Path.StartsWith($Phase2Root + [System.IO.Path]::DirectorySeparatorChar) -or -not (Test-Path -LiteralPath $Phase2Path)) { throw 'Model/runtime path is missing or outside the project.' }
}
$Phase2Models = $null
try { $Phase2Models = Invoke-RestMethod -Uri ($Phase2Config.baseUrl + '/models') -TimeoutSec 3 } catch {}
if ($Phase2Models) {
    if ($Phase2Config.modelId -notin $Phase2Models.data.id) { throw 'The model port is occupied by a different model service; it was left running.' }
    Write-Output "Local model already ready: $($Phase2Config.upstreamModel)"
    return
}
if ((Get-FileHash -LiteralPath $Phase2Model -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Phase2Config.modelSha256) { throw 'Model checksum no longer matches the pinned source.' }
$Phase2Output = Join-Path $Phase2Root 'output'
New-Item -ItemType Directory -Force -Path $Phase2Output | Out-Null
$Phase2Process = Start-Process -FilePath $Phase2Server -ArgumentList @('-m',('"' + $Phase2Model + '"'),'--alias',$Phase2Config.modelId,'--host','127.0.0.1','--port',"$($Phase2Url.Port)",'-c','4096','-np','1','-t','4','-tb','4','-ngl','0','--jinja','--no-webui') -WorkingDirectory (Split-Path $Phase2Server -Parent) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Phase2Output 'llm.stdout.log') -RedirectStandardError (Join-Path $Phase2Output 'llm.stderr.log') -PassThru
$Phase2Process.Id | Set-Content -LiteralPath (Join-Path $Phase2Output 'llm.pid')
$Phase2Deadline = (Get-Date).AddSeconds(60)
do {
    Start-Sleep -Seconds 1
    try { $Phase2Models = Invoke-RestMethod -Uri ($Phase2Config.baseUrl + '/models') -TimeoutSec 2 } catch { $Phase2Models = $null }
    if ($Phase2Models -and $Phase2Config.modelId -in $Phase2Models.data.id) { break }
    if ($Phase2Process.HasExited) { throw 'The local model exited; inspect output/llm.stderr.log.' }
} while ((Get-Date) -lt $Phase2Deadline)
if (-not $Phase2Models) { throw 'Local model did not become ready; inspect output/llm.stderr.log.' }
Write-Output "Local model ready: $($Phase2Config.upstreamModel) $($Phase2Config.quantization) on $($Phase2Config.baseUrl)"

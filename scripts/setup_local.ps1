param([switch]$Start)
$ErrorActionPreference = 'Stop'
$SetupRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $SetupRoot
foreach ($SetupTool in @('python', 'docker', 'ffmpeg', 'ffprobe')) {
    if (-not (Get-Command $SetupTool -ErrorAction SilentlyContinue)) {
        throw "Missing $SetupTool. Install the prerequisites in docs/GETTING_STARTED.md, reopen PowerShell, then retry."
    }
}
& python -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or later is required.' }
function Test-SetupDocker {
    $ErrorActionPreference = 'Continue'
    & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}
if (-not (Test-SetupDocker)) { throw 'Open Docker Desktop, wait for the Linux container engine to be running, then retry.' }
$SetupPython = Join-Path $SetupRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $SetupPython)) {
    Write-Output 'Creating a project Python environment...'
    & python -m venv (Join-Path $SetupRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
}
Write-Output 'Installing application and audio dependencies. This may take several minutes...'
& $SetupPython -m pip install -r (Join-Path $SetupRoot 'backend\requirements-full.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the pip error above and retry.' }
Write-Output 'Downloading/verifying pinned Qwen weights and llama.cpp runtime (Qwen weights: approximately 1.28 GB)...'
& $SetupPython (Join-Path $SetupRoot 'scripts\setup_phase2_model.py')
if ($LASTEXITCODE -ne 0) { throw 'Qwen setup failed. Check the download error above and retry.' }
Write-Output 'Downloading/verifying AASIST-L research audio assets...'
& $SetupPython (Join-Path $SetupRoot 'scripts\setup_audio_screen.py')
if ($LASTEXITCODE -ne 0) { throw 'Audio model setup failed. Check the download error above and retry.' }
Write-Output 'Setup finished. Models are downloaded, not trained.'
if ($Start) {
    & (Join-Path $SetupRoot 'scripts\start_forensic_atlas.ps1')
    & $SetupPython (Join-Path $SetupRoot 'scripts\deployment_preflight.py')
    if ($LASTEXITCODE -ne 0) { throw 'Readiness checks failed. Review the FAIL lines above.' }
} else {
    Write-Output 'Start: powershell -ExecutionPolicy Bypass -File scripts/start_forensic_atlas.ps1'
}

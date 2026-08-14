<#
.SYNOPSIS
    Dependency-checked launcher for yt-mp3-agent.py

.DESCRIPTION
    Verifies Python, required pip packages, ffmpeg, and a JS runtime
    (Node.js or Deno) are available before running yt-mp3-agent.py.
    Any missing pip packages are offered for install automatically.

    DEFAULT BEHAVIOR (no arguments passed):
      Runs  --url-file channels.txt <DefaultDestination> --skip-existing
      i.e. it reads channels.txt from this script's folder and downloads
      into $DefaultDestination below, automatically skipping any file
      that already exists on disk (no interactive prompts).

    Passing any arguments of your own overrides the default entirely and
    forwards exactly what you typed to the Python script, unchanged.

.EXAMPLE
    .\Run-YtMp3Agent.ps1
    (uses channels.txt + skip-existing + $DefaultDestination automatically)

.EXAMPLE
    .\Run-YtMp3Agent.ps1 https://www.youtube.com/@mkbhd "E:\Users\itama\OneDrive\Music\Fake Music"

.EXAMPLE
    .\Run-YtMp3Agent.ps1 --url-file channels.txt "E:\Users\itama\OneDrive\Music\Fake Music" -q 320 -w 5

.NOTES
    Place this file in the same folder as yt-mp3-agent.py and channels.txt,
    or edit $ScriptPath / $ChannelsFile below to point at them.
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

$ScriptPath         = Join-Path $PSScriptRoot "yt-mp3-agent.py"
$ChannelsFile       = Join-Path $PSScriptRoot "channels.txt"
$DefaultDestination = $PSScriptRoot   # edit this if you want a different default download folder
$RequiredModules = @(
    @{ Import = "yt_dlp";   Pip = "yt-dlp[default]" },
    @{ Import = "requests"; Pip = "requests" },
    @{ Import = "tqdm";     Pip = "tqdm" },
    @{ Import = "mutagen";  Pip = "mutagen" },
    @{ Import = "PIL";      Pip = "pillow" }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Ok    ($msg) { Write-Host "  [OK]   $msg" -ForegroundColor Green }
function Write-Warn2 ($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err2  ($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Step  ($msg) { Write-Host "`n$msg" -ForegroundColor Cyan }

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-PythonCommand {
    # Prefer 'py' launcher on Windows, fall back to 'python' / 'python3'
    foreach ($cand in @("py", "python", "python3")) {
        if (Test-Command $cand) {
            try {
                $verOutput = & $cand --version 2>&1
                if ($LASTEXITCODE -eq 0) { return $cand }
            } catch {}
        }
    }
    return $null
}

# ---------------------------------------------------------------------------
# 1. Locate the target script
# ---------------------------------------------------------------------------

Write-Step "Checking for yt-mp3-agent.py..."

if (-not (Test-Path $ScriptPath)) {
    Write-Err2 "yt-mp3-agent.py not found next to this PS1 file: $ScriptPath"
    Write-Host "  Update `$ScriptPath at the top of this file, or place the .py file alongside it." -ForegroundColor Yellow
    exit 1
}
Write-Ok "Found script: $ScriptPath"

# ---------------------------------------------------------------------------
# 2. Python
# ---------------------------------------------------------------------------

Write-Step "Checking for Python..."

$PythonCmd = Get-PythonCommand
if (-not $PythonCmd) {
    Write-Err2 "Python was not found on PATH."
    Write-Host "  Install Python 3.9+ from https://python.org and ensure it's added to PATH." -ForegroundColor Yellow
    exit 1
}
$pyVersion = (& $PythonCmd --version 2>&1)
Write-Ok "$pyVersion (using '$PythonCmd')"

# ---------------------------------------------------------------------------
# 3. Required pip packages
# ---------------------------------------------------------------------------

Write-Step "Checking required Python packages..."

$missing = @()
foreach ($mod in $RequiredModules) {
    $checkCmd = "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('$($mod.Import)') else 1)"
    & $PythonCmd -c $checkCmd 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "$($mod.Import)"
    } else {
        Write-Warn2 "$($mod.Import) - missing"
        $missing += $mod.Pip
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Warn2 "Missing packages: $($missing -join ', ')"
    $answer = Read-Host "  Install them now with pip? (y/N)"
    if ($answer -match '^[Yy]') {
        Write-Host "  Installing..." -ForegroundColor Cyan
        & $PythonCmd -m pip install -U @missing
        if ($LASTEXITCODE -ne 0) {
            Write-Err2 "pip install failed. Install manually:"
            Write-Host "    $PythonCmd -m pip install -U $($missing -join ' ')" -ForegroundColor Yellow
            exit 1
        }
        Write-Ok "Packages installed."
    } else {
        Write-Err2 "Cannot continue without required packages."
        Write-Host "  Install manually with:" -ForegroundColor Yellow
        Write-Host "    $PythonCmd -m pip install -U $($missing -join ' ')" -ForegroundColor Yellow
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 4. ffmpeg
# ---------------------------------------------------------------------------

Write-Step "Checking for ffmpeg..."

if (Test-Command "ffmpeg") {
    Write-Ok "ffmpeg found on PATH."
} else {
    $localAppData = $env:LOCALAPPDATA
    $autoFfmpeg   = Join-Path $localAppData "ffmpeg-yt-dlp\ffmpeg.exe"
    if (Test-Path $autoFfmpeg) {
        Write-Ok "ffmpeg found (auto-downloaded build): $autoFfmpeg"
    } else {
        Write-Warn2 "ffmpeg not found. The Python script will attempt to auto-download"
        Write-Warn2 "a static build on first run (Windows only). This may take a minute."
    }
}

# ---------------------------------------------------------------------------
# 5. JS runtime (Node.js or Deno) - required by yt-dlp for YouTube
# ---------------------------------------------------------------------------

Write-Step "Checking for a JS runtime (required by yt-dlp)..."

$hasNode = Test-Command "node"
$hasDeno = Test-Command "deno"

if ($hasNode) {
    $nodeVer = (& node --version 2>&1)
    Write-Ok "Node.js found ($nodeVer)"
} elseif ($hasDeno) {
    $denoVer = (& deno --version 2>&1 | Select-Object -First 1)
    Write-Ok "Deno found ($denoVer)"
} else {
    Write-Warn2 "Neither Node.js nor Deno was found on PATH."
    Write-Warn2 "yt-dlp needs one of these to download from YouTube reliably."
    Write-Host "    Node.js: https://nodejs.org  (20+ recommended)" -ForegroundColor Yellow
    Write-Host "    Deno:    https://deno.com" -ForegroundColor Yellow
    $answer = Read-Host "  Continue anyway? (y/N)"
    if ($answer -notmatch '^[Yy]') {
        exit 1
    }
}

# ---------------------------------------------------------------------------
# 6. Build arguments (default to channels.txt + skip-existing if none given)
# ---------------------------------------------------------------------------

if (-not $Args -or $Args.Count -eq 0) {
    Write-Step "No arguments given - using default: channels.txt + skip-existing"

    if (-not (Test-Path $ChannelsFile)) {
        Write-Err2 "channels.txt not found: $ChannelsFile"
        Write-Host "  Create it with one channel URL per line, or pass arguments" -ForegroundColor Yellow
        Write-Host "  explicitly, e.g.:" -ForegroundColor Yellow
        Write-Host "    .\Run-YtMp3Agent.ps1 <channel_url> <destination>" -ForegroundColor Yellow
        exit 1
    }

    $Args = @("--url-file", $ChannelsFile, $DefaultDestination, "--skip-existing")
    Write-Ok "Channels file : $ChannelsFile"
    Write-Ok "Destination   : $DefaultDestination"
    Write-Ok "Skip existing : enabled"
}

# ---------------------------------------------------------------------------
# 7. Run the script
# ---------------------------------------------------------------------------

Write-Step "All checks passed. Running yt-mp3-agent.py..."
Write-Host ""

& $PythonCmd $ScriptPath @Args
exit $LASTEXITCODE

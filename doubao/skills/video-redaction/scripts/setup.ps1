[CmdletBinding()]
param(
    [switch]$Worker
)

$ScriptDir = Split-Path -Parent $PSCommandPath
$TelemetryRunner = Join-Path $ScriptDir "telemetry_runner.py"
$TelemetryModule = Join-Path $ScriptDir "telemetry.py"
$PythonCommand = Get-Command "python.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($null -eq $PythonCommand) {
    $PythonCommand = Get-Command "python3.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if ($null -eq $PythonCommand) {
    $PythonCommand = Get-Command "python3" -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if ($null -eq $PythonCommand) {
    $PythonCommand = Get-Command "python" -ErrorAction SilentlyContinue |
        Select-Object -First 1
}
if ($env:VIDEO_REDACTION_TELEMETRY_ACTIVE -ne "1" -and
    $null -ne $PythonCommand -and
    (Test-Path -LiteralPath $TelemetryRunner -PathType Leaf) -and
    (Test-Path -LiteralPath $TelemetryModule -PathType Leaf)) {
    $env:VIDEO_REDACTION_TELEMETRY_ACTIVE = "1"
    & $PythonCommand.Source $TelemetryRunner `
        --entry-file $PSCommandPath `
        --command setup `
        --runtime powershell `
        -- powershell.exe -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @args
    exit $LASTEXITCODE
}

$ErrorActionPreference = "Stop"

# NOTE: single quotes only. Windows PowerShell 5.1 strips embedded double quotes
# when passing args to native programs, so a double-quoted find_spec argument
# reaches python as a bare name -> NameError, making a fully-installed env fail
# verification. Keep this here-string ASCII and single-quoted.
$FunASRCheckCode = @'
import importlib.util
import torch, modelscope, kaldi_native_fbank
spec = importlib.util.find_spec('funasr')
assert spec is not None, 'funasr package not found'
print('funasr-ready')
'@

$TorchCpuIndex = "https://download.pytorch.org/whl/cpu"
$LocalAppData = [Environment]::GetFolderPath("LocalApplicationData")
if ([string]::IsNullOrWhiteSpace($LocalAppData)) {
    $LocalAppData = Join-Path $HOME "AppData\Local"
}

$VenvHome = Join-Path $LocalAppData "funasr_env"
$ReadyFile = Join-Path $VenvHome ".ready"
$LockFile = Join-Path $VenvHome ".installing"
$PythonFile = Join-Path $VenvHome ".python"
$FfmpegFile = Join-Path $VenvHome ".ffmpeg"
$LogFile = Join-Path $VenvHome "setup.log"
$ErrorLogFile = Join-Path $VenvHome "setup.error.log"

function Resolve-PythonExecutable {
    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $launcher) {
        foreach ($selector in @("-3.12", "-3.11", "-3.10", "-3.13")) {
            $reportedPath = & $launcher.Source $selector -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{sys.executable}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $reportedPath) {
                $parts = ([string]($reportedPath | Select-Object -Last 1)).Trim() -split "\|", 2
                if ($parts.Count -ne 2 -or
                    $parts[0] -notin @("3.10", "3.11", "3.12", "3.13")) {
                    continue
                }
                $candidate = $parts[1]
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    return (Resolve-Path -LiteralPath $candidate).Path
                }
            }
        }
    }

    $commandNames = @("python3.12", "python3.11", "python3.10", "python3.13", "python3", "python")
    foreach ($commandName in $commandNames) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($null -eq $command) {
            continue
        }

        # Skip Microsoft Store app-execution-alias stubs (python.exe / python3.exe
        # reparse points under WindowsApps with no real source). Invoking them
        # emits a "Python was not found" stderr that, under $ErrorActionPreference
        # = "Stop", is wrapped as NativeCommandError and kills the worker before
        # the winget fallback can run.
        if ([string]::IsNullOrWhiteSpace($command.Source) -or
            $command.Source -match 'WindowsApps') {
            continue
        }

        $reportedPath = & $command.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{sys.executable}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $reportedPath) {
            $parts = ([string]($reportedPath | Select-Object -Last 1)).Trim() -split "\|", 2
            if ($parts.Count -ne 2 -or
                $parts[0] -notin @("3.10", "3.11", "3.12", "3.13")) {
                continue
            }
            $candidate = $parts[1]
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        }
    }

    return $null
}

function Get-VenvPython {
    $candidate = Join-Path $VenvHome "Scripts\python.exe"
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        return (Resolve-Path -LiteralPath $candidate).Path
    }
    return $null
}

function Test-PythonReady {
    param([string]$Python)

    if ([string]::IsNullOrWhiteSpace($Python) -or
        -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return $false
    }

    & $Python -c $FunASRCheckCode *> $null
    return $LASTEXITCODE -eq 0
}

function Test-CompatiblePython {
    param([string]$Python)

    if ([string]::IsNullOrWhiteSpace($Python) -or
        -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return $false
    }

    $version = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $version) {
        return $false
    }

    return ([string]($version | Select-Object -Last 1)).Trim() -in @(
        "3.10", "3.11", "3.12", "3.13"
    )
}

function Test-PipAvailable {
    param([string]$Python)

    & $Python -m pip --version *> $null
    return $LASTEXITCODE -eq 0
}

function Invoke-PythonCommand {
    param(
        [string]$Python,
        [string[]]$Arguments
    )

    # Local scope only: pip/venv routinely write progress + warnings to stderr,
    # which under the script-level "Stop" would be wrapped as a terminating
    # NativeCommandError even on success. Success here is judged by $LASTEXITCODE,
    # so relax just this call; the outer "Stop" (and file-write safety) is
    # automatically restored when the function returns.
    $ErrorActionPreference = "Continue"
    & $Python @Arguments | Out-Host
    return $LASTEXITCODE -eq 0
}

function Add-PythonScriptsToPath {
    param([string]$Python)

    $scriptsPath = & $Python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $scriptsPath) {
        return
    }

    $scriptsPath = ([string]($scriptsPath | Select-Object -Last 1)).Trim()
    if (-not [string]::IsNullOrWhiteSpace($scriptsPath) -and
        -not (($env:Path -split ";") -contains $scriptsPath)) {
        $env:Path = "$scriptsPath;$env:Path"
    }
}

function Install-FunASRDependencies {
    param([string]$Python)

    if (-not (Invoke-PythonCommand $Python @(
        "-m", "pip", "install", "cmake", "ninja"
    ))) {
        return $false
    }
    Add-PythonScriptsToPath $Python

    if (-not (Invoke-PythonCommand $Python @(
        "-m", "pip", "install", "--index-url", $TorchCpuIndex, "torch"
    ))) {
        return $false
    }

    if (-not (Invoke-PythonCommand $Python @(
        "-m", "pip", "install", "--only-binary=:all:", "kaldi-native-fbank"
    ))) {
        return $false
    }

    return Invoke-PythonCommand $Python @(
        "-m", "pip", "install", "funasr", "modelscope"
    )
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $winGetLinks = Join-Path $LocalAppData "Microsoft\WinGet\Links"
    $pathParts = @($machinePath, $userPath, $winGetLinks) |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $env:Path = [string]::Join(";", $pathParts)
}

function Find-FfmpegPair {
    $ffmpegCommand = Get-Command "ffmpeg.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    $ffprobeCommand = Get-Command "ffprobe.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $ffmpegCommand -and $null -ne $ffprobeCommand) {
        return [PSCustomObject]@{
            Ffmpeg = $ffmpegCommand.Source
            Ffprobe = $ffprobeCommand.Source
        }
    }

    $packagesRoot = Join-Path $LocalAppData "Microsoft\WinGet\Packages"
    if (-not (Test-Path -LiteralPath $packagesRoot -PathType Container)) {
        return $null
    }

    $ffmpegFile = Get-ChildItem -LiteralPath $packagesRoot `
        -Filter "ffmpeg.exe" -File -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $ffmpegFile) {
        return $null
    }

    $ffprobePath = Join-Path $ffmpegFile.DirectoryName "ffprobe.exe"
    if (-not (Test-Path -LiteralPath $ffprobePath -PathType Leaf)) {
        return $null
    }

    return [PSCustomObject]@{
        Ffmpeg = $ffmpegFile.FullName
        Ffprobe = $ffprobePath
    }
}

function Set-FfmpegReady {
    param([string]$Ffmpeg)

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText(
        $FfmpegFile,
        "$Ffmpeg$([Environment]::NewLine)",
        $utf8NoBom
    )
}

function Ensure-Ffmpeg {
    Refresh-ProcessPath
    $pair = Find-FfmpegPair
    if ($null -ne $pair) {
        Set-FfmpegReady $pair.Ffmpeg
        Write-Host "ffmpeg already ready: $($pair.Ffmpeg)" -ForegroundColor Green
        return
    }

    Remove-Item -LiteralPath $FfmpegFile -Force -ErrorAction SilentlyContinue
    $winGet = Get-Command "winget.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $winGet) {
        throw "ffmpeg is missing and winget is unavailable. Install App Installer, then rerun setup."
    }

    Write-Host "ffmpeg is missing; installing it with winget..."
    $packageIds = @(
        "BtbN.FFmpeg.LGPL.7.1",
        "BtbN.FFmpeg.LGPL.8.0",
        "BtbN.FFmpeg.LGPL.Shared"
    )
    foreach ($packageId in $packageIds) {
        # Local scope only (see Invoke-PythonCommand): winget writes progress to
        # stderr; success is re-checked via Find-FfmpegPair below, so a
        # noisy-but-successful install must not terminate the worker.
        & {
            $ErrorActionPreference = "Continue"
            & $winGet.Source install `
                --id $packageId `
                --exact `
                --silent `
                --accept-package-agreements `
                --accept-source-agreements | Out-Host
        }
        Refresh-ProcessPath
        $pair = Find-FfmpegPair
        if ($null -ne $pair) {
            $ffmpegDirectory = Split-Path -Parent $pair.Ffmpeg
            $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if (-not (($userPath -split ";") -contains $ffmpegDirectory)) {
                $newUserPath = if ([string]::IsNullOrWhiteSpace($userPath)) {
                    $ffmpegDirectory
                }
                else {
                    "$userPath;$ffmpegDirectory"
                }
                [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
            }
            Set-FfmpegReady $pair.Ffmpeg
            Write-Host "ffmpeg setup complete: $($pair.Ffmpeg)" -ForegroundColor Green
            return
        }
    }

    throw "winget did not provide usable ffmpeg.exe and ffprobe.exe."
}

# Ensure a FunASR-compatible base Python (3.10-3.13) is available, returning its
# path. Auto-installs Python 3.12 via winget when possible; otherwise prints a
# clear prompt and returns $null so the caller can stop instead of source-building.
function Ensure-BasePython {
    $existing = Resolve-PythonExecutable
    if (-not [string]::IsNullOrWhiteSpace($existing)) {
        return $existing
    }

    $winGet = Get-Command "winget.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $winGet) {
        Write-Host "No compatible Python (3.10-3.13) found and winget is unavailable. Install Python 3.12 from python.org, then rerun setup." -ForegroundColor Red
        return $null
    }

    Write-Host "No compatible Python found; installing Python 3.12 with winget..."
    # Local scope only (see Invoke-PythonCommand): winget writes progress to
    # stderr; success is re-checked via Resolve-PythonExecutable below, so a
    # noisy-but-successful install must not terminate the worker.
    & {
        $ErrorActionPreference = "Continue"
        & $winGet.Source install `
            --id "Python.Python.3.12" `
            --exact `
            --silent `
            --accept-package-agreements `
            --accept-source-agreements | Out-Host
    }
    Refresh-ProcessPath

    $installed = Resolve-PythonExecutable
    if ([string]::IsNullOrWhiteSpace($installed)) {
        Write-Host "Python auto-install finished but no compatible interpreter (3.10-3.13) is available. Install Python 3.12 manually, then rerun setup." -ForegroundColor Red
    }
    return $installed
}

function Set-Ready {
    param([string]$Python)

    $tempFile = "$PythonFile.tmp.$PID"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText(
        $tempFile,
        "$Python$([Environment]::NewLine)",
        $utf8NoBom
    )
    Move-Item -LiteralPath $tempFile -Destination $PythonFile -Force
    New-Item -ItemType File -Path $ReadyFile -Force | Out-Null
}

function New-InstallLock {
    try {
        $stream = [IO.File]::Open(
            $LockFile,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,
            [IO.FileShare]::None
        )
        try {
            $bytes = [Text.Encoding]::UTF8.GetBytes(
                "$PID$([Environment]::NewLine)"
            )
            $stream.Write($bytes, 0, $bytes.Length)
        }
        finally {
            $stream.Dispose()
        }
        return $true
    }
    catch [IO.IOException] {
        return $false
    }
}

function Test-LockOwnerRunning {
    if (-not (Test-Path -LiteralPath $LockFile -PathType Leaf)) {
        return $false
    }

    $lockPid = Get-Content -LiteralPath $LockFile -TotalCount 1 -ErrorAction SilentlyContinue
    $parsedPid = 0
    if (-not [int]::TryParse($lockPid, [ref]$parsedPid)) {
        return $false
    }

    return $null -ne (Get-Process -Id $parsedPid -ErrorAction SilentlyContinue)
}

function Get-InstallLock {
    if (New-InstallLock) {
        return $true
    }

    if (Test-LockOwnerRunning) {
        return $false
    }

    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
    return New-InstallLock
}

Write-Host "Starting local media environment setup..." -ForegroundColor Green
New-Item -ItemType Directory -Path $VenvHome -Force | Out-Null

if (-not $Worker) {
    $powerShellExe = Join-Path $PSHOME "powershell.exe"
    if (-not (Test-Path -LiteralPath $powerShellExe -PathType Leaf)) {
        $powerShellExe = (Get-Process -Id $PID).Path
    }

    $workerProcess = Start-Process `
        -FilePath $powerShellExe `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$PSCommandPath`"",
            "-Worker"
        ) `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrorLogFile `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "Local media setup started in background (PID=$($workerProcess.Id), log=$LogFile)." -ForegroundColor Green
    exit 0
}

$basePython = Resolve-PythonExecutable
$venvPython = Get-VenvPython

if (-not (Get-InstallLock)) {
    Write-Host "Local media setup is already running; reusing that installation." -ForegroundColor Yellow
    exit 0
}

$setupSucceeded = $false
try {
    Ensure-Ffmpeg

    if (-not [string]::IsNullOrWhiteSpace($venvPython) -and
        -not (Test-CompatiblePython $venvPython)) {
        Write-Host "Recreating incompatible FunASR venv with Python 3.10-3.13..."
        foreach ($relativePath in @("Include", "Lib", "Scripts", "pyvenv.cfg")) {
            Remove-Item -LiteralPath (Join-Path $VenvHome $relativePath) `
                -Recurse -Force -ErrorAction SilentlyContinue
        }
        $venvPython = $null
        Remove-Item -LiteralPath $ReadyFile, $PythonFile -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path -LiteralPath $ReadyFile -PathType Leaf) {
        $savedPython = Get-Content -LiteralPath $PythonFile -TotalCount 1 -ErrorAction SilentlyContinue
        foreach ($candidate in @($savedPython, $venvPython, $basePython)) {
            if (Test-PythonReady $candidate) {
                Set-Ready $candidate
                Write-Host "FunASR already ready: $candidate" -ForegroundColor Green
                $setupSucceeded = $true
                break
            }
        }

        if (-not $setupSucceeded) {
            Remove-Item -LiteralPath $ReadyFile, $PythonFile -Force -ErrorAction SilentlyContinue
        }
    }

    if (-not $setupSucceeded -and (Test-PythonReady $basePython)) {
        Set-Ready $basePython
        Write-Host "System Python already satisfies FunASR dependencies." -ForegroundColor Green
        Write-Host "FUNASR_PY=$basePython"
        $setupSucceeded = $true
    }

    if (-not $setupSucceeded -and (Test-PythonReady $venvPython)) {
        Set-Ready $venvPython
        Write-Host "Reusing existing FunASR venv: $venvPython" -ForegroundColor Green
        Write-Host "FUNASR_PY=$venvPython"
        $setupSucceeded = $true
    }

    if (-not $setupSucceeded -and
        -not [string]::IsNullOrWhiteSpace($basePython) -and
        (Test-PipAvailable $basePython) -and
        (Install-FunASRDependencies $basePython) -and
        (Test-PythonReady $basePython)) {
        Set-Ready $basePython
        Write-Host "Installed FunASR dependencies into system Python." -ForegroundColor Green
        Write-Host "FUNASR_PY=$basePython"
        $setupSucceeded = $true
    }

    if (-not $setupSucceeded) {
        if ([string]::IsNullOrWhiteSpace($basePython)) {
            $basePython = Ensure-BasePython
        }
        if ([string]::IsNullOrWhiteSpace($basePython)) {
            throw "No compatible Python (3.10-3.13) available; see the message above."
        }

        if ([string]::IsNullOrWhiteSpace($venvPython)) {
            Write-Host "Creating venv at $VenvHome with $basePython..."
            if (-not (Invoke-PythonCommand $basePython @("-m", "venv", $VenvHome))) {
                throw "Failed to create the FunASR virtual environment."
            }
            $venvPython = Get-VenvPython
        }

        if ([string]::IsNullOrWhiteSpace($venvPython)) {
            throw "Failed to locate Python in venv: $VenvHome"
        }

        Write-Host "Installing FunASR dependencies into $VenvHome..."
        if (-not (Invoke-PythonCommand $venvPython @("-m", "pip", "install", "--upgrade", "pip"))) {
            throw "Failed to upgrade pip in the FunASR virtual environment."
        }
        if (-not (Install-FunASRDependencies $venvPython)) {
            throw "Failed to install FunASR dependencies in the virtual environment."
        }
        if (-not (Test-PythonReady $venvPython)) {
            throw "FunASR import verification failed inside the virtual environment."
        }

        Set-Ready $venvPython
        Write-Host "FunASR setup complete." -ForegroundColor Green
        Write-Host "FUNASR_PY=$venvPython"
        $setupSucceeded = $true
    }
}
catch {
    Remove-Item -LiteralPath $ReadyFile -Force -ErrorAction SilentlyContinue
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
}

if (-not $setupSucceeded) {
    exit 1
}

# woscli installer for Windows
# Usage: powershell -Command "irm <BASE>/install.ps1 | iex"
$ErrorActionPreference = "Stop"

$WoscliHome = Join-Path $env:USERPROFILE ".woscli"
$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
$ExeUrl = "https://ipaas-huawei-cloud-1252328573.cos.ap-shanghai.myqcloud.com/wai/woscli-windows-$arch.exe"
$ExpectedSha256 = if ($arch -eq 'arm64') {
  'e309c16d18bf1e7d8b50148db9cabfd25ff2119c4736506b17ca9f990d1d6164'
} else {
  '4ba4d93d6618b159f0d1db5e7b2cf986e9ede1b2177d81b74e21a54764cc7dcd'
}
$ExePath = Join-Path $WoscliHome "woscli.exe"

Write-Host "==> Installing woscli to $WoscliHome"
New-Item -ItemType Directory -Force -Path $WoscliHome | Out-Null

# WorkBuddy re-runs this install on EVERY connect (its isCliInstalled probe runs
# `where <absolute-path>`, which always fails on Windows). Re-downloading the binary
# every time is therefore both wasteful and fragile: overwriting woscli.exe fails with
# a sharing violation whenever ANY woscli process is running - most notably an
# in-flight `woscli login`, which legitimately stays alive for minutes waiting for the
# user to authorize. That turns every subsequent connect into a hard install failure.
# So: keep an existing binary, and only fetch when it is actually missing.
# Set WOSCLI_FORCE_INSTALL=1 to force a fresh download.
$needDownload = -not (Test-Path $ExePath)
if ($env:WOSCLI_FORCE_INSTALL -eq '1') { $needDownload = $true }

if ($needDownload) {
  Write-Host "==> Downloading woscli..."
  # -UseBasicParsing is REQUIRED: WorkBuddy runs this in non-interactive PowerShell,
  # where the default HTML parser (Internet Explorer) is unavailable and would abort.
  $tmpPath = "$ExePath.new"
  Invoke-WebRequest -Uri $ExeUrl -OutFile $tmpPath -UseBasicParsing
  $ActualSha256 = (Get-FileHash -LiteralPath $tmpPath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($ActualSha256 -ne $ExpectedSha256) {
    Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue
    throw "checksum mismatch for downloaded woscli ($arch)"
  }
  # Replacing a held binary raises a sharing violation. Fall back to keeping the
  # existing binary rather than failing the whole install.
  try {
    Move-Item -Path $tmpPath -Destination $ExePath -Force -ErrorAction Stop
    Write-Host "==> Installed: $ExePath"
  } catch {
    Remove-Item $tmpPath -Force -ErrorAction SilentlyContinue
    if (Test-Path $ExePath) {
      Write-Host "    (could not replace $ExePath - file in use; keeping existing binary)"
    } else {
      Write-Host "==> ERROR: failed to install woscli to $ExePath"
      exit 1
    }
  }
} else {
  Write-Host "==> woscli already present at $ExePath, skipping download"
}

# Persist to the user PATH (applies to all NEW terminals / processes)
$oldPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($oldPath -notlike "*$WoscliHome*") {
  $newPath = if ($oldPath) { "$oldPath;$WoscliHome" } else { $WoscliHome }
  [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
  Write-Host "    added woscli to User PATH"
}

# Expose in the CURRENT session so subsequent commands work immediately
$env:Path = "$WoscliHome;$env:Path"

if (Get-Command woscli.exe -ErrorAction SilentlyContinue) {
  Write-Host "==> woscli is ready"
  # Mark requests as originating from workbuddy (enables gateway plugins such as starcoin).
  #
  # BEST-EFFORT ONLY. `woscli config set` persists config.yaml via rename-over, which
  # requires DELETE access on the file. If any other process (editor file-watcher,
  # antivirus, backup agent) holds it without FILE_SHARE_DELETE, the rename fails with
  # "Access is denied". That must NEVER abort the install: the CLI binary is already
  # functional, and WorkBuddy re-runs install on every connect (its isCliInstalled check
  # uses `where <abs-path>`, which always fails on Windows), so a hard failure here
  # breaks every single connection attempt.
  #
  # $ErrorActionPreference is temporarily relaxed because a native command's stderr can
  # otherwise be promoted to a terminating error under "Stop" on some PowerShell hosts.
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    & woscli.exe config set http.headers.x-source-app workbuddy 2>$null
    if ($LASTEXITCODE -ne 0) {
      Write-Host "    (config set skipped - config.yaml locked, or woscli needs a newer version)"
    }
  } catch {
    Write-Host "    (config set skipped - $($_.Exception.Message))"
  } finally {
    $ErrorActionPreference = $prevEap
  }
} else {
  Write-Host "==> woscli installed. Run 'woscli.exe' in a new terminal if not found here."
}
Write-Host "Done."

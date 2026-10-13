# Set-ShortcutIcon.ps1
# Update a Windows shortcut (.lnk) IconLocation and refresh the shell icon cache.
#
# Usage (PowerShell 5.1+ on Windows):
#   powershell -ExecutionPolicy Bypass -File Set-ShortcutIcon.ps1 `
#       -ShortcutPath "$env:USERPROFILE\Desktop\QwenWork.lnk" `
#       -IconPath    "C:\path\to\qwenwork-app-icon\assets\default-icon.ico" `
#       [-IconIndex  0] `
#       [-Backup]
#
# Notes:
#   * The .ico file must exist at IconPath BEFORE running this script; the icon
#     is referenced by absolute path, not embedded in the .lnk. Keep the .ico
#     file where it is (do not delete it after running).
#   * Windows caches shell icons aggressively. This script clears the current
#     user's IconCache.db and restarts explorer.exe to force a refresh. Any
#     unsaved File Explorer state (open windows, selections) will reset.
#   * For a pinned-taskbar item, the underlying .lnk lives at
#     %APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\<App>.lnk
#     — you may need to unpin and re-pin after running for the taskbar to pick
#     up the new icon.

param(
    [Parameter(Mandatory = $true)]
    [string]$ShortcutPath,

    [Parameter(Mandatory = $true)]
    [string]$IconPath,

    [int]$IconIndex = 0,

    [switch]$Backup
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ShortcutPath)) {
    throw "Shortcut not found: $ShortcutPath"
}
if (-not (Test-Path -LiteralPath $IconPath)) {
    throw "Icon file not found: $IconPath"
}

# Absolute paths — WScript.Shell chokes on relative paths.
$ShortcutPath = (Resolve-Path -LiteralPath $ShortcutPath).ProviderPath
$IconPath     = (Resolve-Path -LiteralPath $IconPath).ProviderPath

if ($Backup) {
    $stamp    = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupTo = "$ShortcutPath.bak_$stamp"
    Copy-Item -LiteralPath $ShortcutPath -Destination $backupTo -Force
    Write-Host "Backup: $backupTo"
}

$shell    = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)

$oldIcon = $shortcut.IconLocation
Write-Host "Old IconLocation: $oldIcon"

$shortcut.IconLocation = "$IconPath,$IconIndex"
$shortcut.Save()

Write-Host "New IconLocation: $($shortcut.IconLocation)"

# Force refresh: clear the per-user icon cache and restart explorer.
$iconCache = Join-Path $env:LOCALAPPDATA "IconCache.db"
if (Test-Path -LiteralPath $iconCache) {
    try {
        Remove-Item -LiteralPath $iconCache -Force -ErrorAction Stop
        Write-Host "Removed: $iconCache"
    } catch {
        Write-Warning "Could not remove IconCache.db (may be locked): $_"
    }
}

# Modern Windows 10/11 stores per-DPI icon caches under Explorer\
$explorerCache = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Explorer"
if (Test-Path -LiteralPath $explorerCache) {
    Get-ChildItem -LiteralPath $explorerCache -Filter "iconcache_*.db" -ErrorAction SilentlyContinue |
        ForEach-Object {
            try { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop; Write-Host "Removed: $($_.FullName)" }
            catch { Write-Warning "Could not remove $($_.FullName): $_" }
        }
}

Write-Host "Restarting explorer.exe to refresh icon cache..."
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Process explorer.exe

Write-Host "Done. If the taskbar still shows the old icon, unpin and re-pin the shortcut."

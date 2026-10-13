#!/bin/bash
# macos_install_icon.sh — Robust macOS app icon replacement.
#
# Handles the three ways macOS ships icons in a .app bundle:
#   1. Legacy `.icns` under Contents/Resources/ (CFBundleIconFile)
#   2. Modern Xcode-compiled `Assets.car` referenced by CFBundleIconName
#   3. Both (Xcode 26+ / newer Electron packagers)
#
# When CFBundleIconName is present, macOS reads the icon from Assets.car and
# IGNORES the .icns file. This script strips CFBundleIconName so the .icns
# path wins, ad-hoc re-signs the bundle (required after Info.plist edit,
# otherwise Gatekeeper flags it), and force-refreshes every macOS icon
# cache layer (LaunchServices, IconServices, Dock, Finder). This is the
# only reliable path — earlier versions of this skill only replaced .icns
# and the Dock kept showing the old artwork.
#
# Usage: macos_install_icon.sh <app_path> <new_icns_path> <backup_dir>
set -euo pipefail

APP="${1:?usage: macos_install_icon.sh <app_path> <new_icns> <backup_dir>}"
NEW_ICNS="${2:?}"
BACKUP_DIR="${3:?}"

if [ ! -d "$APP" ]; then echo "ERROR: app not found: $APP" >&2; exit 1; fi
if [ ! -f "$NEW_ICNS" ]; then echo "ERROR: icns not found: $NEW_ICNS" >&2; exit 1; fi
mkdir -p "$BACKUP_DIR"

APP_NAME=$(basename "$APP" .app)
TS=$(date +%Y%m%d_%H%M%S)
INFO="$APP/Contents/Info.plist"

# 1. Determine the icns filename (CFBundleIconFile). Fallback to icon.icns.
ICN_FILE=$(/usr/libexec/PlistBuddy -c "Print :CFBundleIconFile" "$INFO" 2>/dev/null || echo "icon.icns")
case "$ICN_FILE" in
    *.icns) ;;
    *) ICN_FILE="${ICN_FILE}.icns" ;;
esac
ICN_PATH="$APP/Contents/Resources/$ICN_FILE"

echo "app        = $APP"
echo "icns file  = $ICN_FILE"
echo "icns path  = $ICN_PATH"

# 2. Back up the ORIGINAL icns (if exists) and Info.plist.
if [ -f "$ICN_PATH" ]; then
    cp "$ICN_PATH" "$BACKUP_DIR/icon_backup_${APP_NAME}_${TS}.icns"
    echo "backup icns → $BACKUP_DIR/icon_backup_${APP_NAME}_${TS}.icns"
fi
cp "$INFO" "$BACKUP_DIR/Info_backup_${APP_NAME}_${TS}.plist"
echo "backup plist → $BACKUP_DIR/Info_backup_${APP_NAME}_${TS}.plist"

# 3. Replace the .icns.
cp "$NEW_ICNS" "$ICN_PATH"
echo "wrote new icns"

# 4. Detect & neutralize CFBundleIconName (Xcode-compiled Assets.car override).
#    When present, macOS reads from Assets.car and ignores our .icns.
if /usr/libexec/PlistBuddy -c "Print :CFBundleIconName" "$INFO" >/dev/null 2>&1; then
    echo "detected CFBundleIconName — deleting so .icns wins"
    /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$INFO"
fi

# 5. Ad-hoc re-sign — Info.plist edits invalidate the existing signature.
#    Without this, Gatekeeper may refuse to launch the app, and IconServices
#    may cache the old signed icon. `-` = ad-hoc identity.
if command -v codesign >/dev/null 2>&1; then
    codesign --force --deep --sign - "$APP" 2>&1 | tail -3 || true
fi

# 6. Touch bundle & register with LaunchServices.
touch "$APP" "$ICN_PATH" "$INFO"
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
if [ -x "$LSREGISTER" ]; then
    "$LSREGISTER" -f "$APP" >/dev/null 2>&1 || true
fi

# 7. Nuke the IconServices caches — this is the layer that stubbornly holds
#    the old icon even after everything else is updated.
rm -rf "$HOME/Library/Caches/com.apple.iconservices.store" 2>/dev/null || true
sudo -n rm -rf /Library/Caches/com.apple.iconservices.store 2>/dev/null || true
find /private/var/folders/ -name com.apple.dock.iconcache -delete 2>/dev/null || true
find /private/var/folders/ -name com.apple.iconservices -type d -exec rm -rf {} + 2>/dev/null || true
killall -HUP iconservicesagent 2>/dev/null || true
killall -HUP iconservicesd 2>/dev/null || true

# 8. Refresh Dock & Finder.
killall Dock 2>/dev/null || true
killall Finder 2>/dev/null || true

echo "OK"

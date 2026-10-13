---
name: qwenwork-app-icon
description: Cross-platform (macOS + Windows) app icon replacement centered on the official QwenWork mascot "千仔" (Qianzai) — a flat-vector waving green octopus with two big round eyes. Auto-detects platform and routes accordingly. macOS branch replaces the icon inside any .app bundle (produces .icns, handles Assets.car / CFBundleIconName override, ad-hoc re-signs, force-refreshes IconServices + Dock cache). Windows branch retargets desktop / Start-menu shortcut (.lnk) IconLocation to a new .ico (produces multi-size .ico, backs up the .lnk, refreshes icon cache). Three source modes on both platforms — (1) user-uploaded PNG/JPG/ICNS/ICO, (2) AI-generated remix of the bundled Qianzai mascot (asks the user for costume / expression / scene every time), (3) bundled mascot default (pre-baked .icns + .ico). Explicitly does NOT modify PE resources inside .exe files, and explicitly does NOT support HarmonyOS. Use when the user wants to change an app icon, replace a dock icon, rebrand a shortcut, customize application icons, or says "换图标", "替换图标", "换千问办公图标", "千仔图标", "改造千仔", "改造章鱼", "章鱼图标", "换 dock 图标", "换快捷方式图标", "replace icon", "change app icon".
version: 1.4.0
install_method: download
install_source: official
skill_id: official_FNMbWWWA
enabled_at: 1791893810487
name_zh: 千问办公客户端图标替换
---

# QwenWork App Icon Replacement (macOS + Windows)

Replace the visible icon of a macOS `.app` bundle or a Windows `.lnk` shortcut with the official QwenWork mascot **千仔 (Qianzai)** — a flat-vector waving green octopus (`#41D87E`) with two round white eyes, big pupils, and one raised tentacle — or with a user-supplied image. Ships with the official mascot SVG (`assets/qianzai-mascot.svg`) plus pre-baked composites (`default-icon.png/.icns/.ico`, mascot centered on a soft-white rounded-square background). The whole community customizes around Qianzai — costumes, seasons, moods, side objects — so treat the mascot itself as the anchor and change what surrounds it.

## Platform matrix — read first

| Platform | Supported | Mechanism | Notes |
|---|---|---|---|
| macOS | ✅ full | Replace `.icns` inside `.app/Contents/Resources/`; `killall Dock`. | Any `.app`. Needs `sudo` for `/Applications/`. |
| Windows | ✅ shortcuts only | Set `.lnk` `IconLocation` via PowerShell WScript.Shell; clear IconCache; restart Explorer. | Desktop + Start Menu + Taskbar-pinned `.lnk`. |
| Windows PE / .exe internals | ❌ not supported | Would require ResourceHacker-style PE surgery; breaks signature; Defender risk. Do NOT attempt. |
| Windows UWP / Microsoft Store apps | ❌ not supported | Manifest editing + repackage + resigning required. Out of scope. |
| HarmonyOS (phone/tablet/PC) | ❌ not supported | No public API to swap third-party app icons; only official theme store accepts full theme packs. Refuse and explain. |

If the user's target does not fall into ✅, refuse the automation part, explain why, and offer to just produce the branded icon asset for them to install manually.

## Prerequisites

- **macOS**: `iconutil` (built-in), `qlmanage` (built-in), `Pillow` (`pip3 install --break-system-packages Pillow`); optional `cairosvg` as SVG-render fallback.
- **Windows**: PowerShell 5.1+ (built into Windows 10/11), Python 3 + Pillow to run `png_to_ico.py`. If Python isn't installed on the target machine, generate the `.ico` from macOS first and copy it over.

## Bundled assets

- `assets/qianzai-mascot.svg` — **canonical source**. Official 千仔 mascot vector: flat green (`#41D87E`) octopus body, two round white eyes with black pupils and small eyebrow strokes, one tentacle raised in a wave, transparent background. This is the file you feed into `ImageGen` as reference and the file you rasterize for compositing.
- `assets/qianzai-icon.svg` — alternate official mascot pose (in-app icon variant). Reference only.
- `assets/default-icon.png` — 2048×2048 pre-composed default: Qianzai centered on a soft white → very-light-green vertical gradient inside a Big Sur squircle. High contrast, mascot pops.
- `assets/default-icon.icns` — pre-baked macOS icon derived from `default-icon.png`.
- `assets/default-icon.ico` — pre-baked Windows multi-resolution icon (16/24/32/48/64/128/256) derived from `default-icon.png`.

**Non-goals**: this skill no longer bundles the abstract 3-brick QwenWork logo — that logo is a *product mark*, not the mascot. Community convention here is "改造千仔 / 改造章鱼" (customize Qianzai), not "put the product logo somewhere". If a user explicitly wants the abstract logo, direct them to `brand-skill-work/official-assets/logo-3d.svg` in the brand kit, not this skill.

## Source options — always ask before doing anything

Use the AskUserQuestion tool with a 3-way choice:

1. **Upload own image** — user provides PNG / JPG / ICNS (macOS) / ICO (Windows). Square, ≥1024×1024 recommended for macOS, ≥256×256 for Windows.
2. **AI-generated remix of 千仔** — call `ImageGen` with `assets/qianzai-mascot.svg` (or the pre-rendered `default-icon.png`) as the reference image. **Ask the user for the style every time** — costume, expression, season, mood, side prop, scene, etc. Rules:
    - Keep the octopus recognisable: flat vector, brand green `#41D87E`, two big round white eyes with black pupils, waving tentacle.
    - Change what surrounds it (outfit, background, accessories, seasonal theme, cyberpunk / cottagecore / holiday / anime style, etc.).
    - Do NOT swap the mascot for a totally different character. If the user asks for a non-Qianzai icon, that's Source Option 1 (upload) or a fully custom `ImageGen` prompt — say so.
3. **Bundled default** — use `assets/default-icon.icns` (macOS) or `assets/default-icon.ico` (Windows) as-is. Fastest path, zero conversion.

## Platform detection

Detect the runtime OS first — do not assume:

```bash
uname   # macOS returns "Darwin"; Linux returns "Linux"
```

On Windows the skill runs from either WSL/Git-Bash or PowerShell; if `uname` returns `MINGW*` / `MSYS*` / `CYGWIN*`, or `%OS%` env var equals `Windows_NT`, take the Windows branch.

---

## Branch A · macOS workflow

### A1. Identify target `.app`

```bash
ls /Applications/ | grep -i "<name>"
# or
mdfind "kMDItemFSName == '<Name>.app'"
```
If not specified, ask.

### A2. Read the icon filename

```bash
/usr/libexec/PlistBuddy -c "Print :CFBundleIconFile" "/Applications/<App>.app/Contents/Info.plist"
```
Icon path: `/Applications/<App>.app/Contents/Resources/<iconfile>`. If no extension, append `.icns`.

### A3. Produce `.icns`

**Bundled default, default background** → use `~/.qwenworkcn/skills/qwenwork-app-icon/assets/default-icon.icns` directly. Skip conversion.

**Bundled default, custom background**:
```bash
python3 ~/.qwenworkcn/skills/qwenwork-app-icon/scripts/compose_qwenwork_icon.py \
    /tmp/qwenwork-custom.png \
    --bg-style soft-white    # soft-white (default) | dark | white | custom  (avoid brand-green with the green mascot)
python3 ~/.qwenworkcn/skills/qwenwork-app-icon/scripts/png_to_icns.py \
    /tmp/qwenwork-custom.png /tmp/qwenwork-custom.icns
```

**AI-generated**: after getting the style answer, call `ImageGen` with `assets/qianzai-mascot.svg` (or the pre-rendered PNG) as the reference image. **`ImageGen` adds an "AI 生成" watermark strip along the bottom ~90 px of the output.** Crop it before compositing:

```python
from PIL import Image
img = Image.open('/tmp/qianzai-<style>.png').convert('RGBA')
w, h = img.size
img.crop((0, 0, w, h - 90)).save('/tmp/qianzai-<style>-cropped.png')
```

Then feed the cropped PNG into `compose_qwenwork_icon.py` (usually `--bg-style dark` or `--bg-style soft-white` — pick whichever contrasts with the mascot's costume/scene) and finally run `png_to_icns.py`.

**User-uploaded**: run `png_to_icns.py` directly on the supplied file.

### A4. Install — ALWAYS use `macos_install_icon.sh`

Never do a bare `cp` + `killall Dock` — modern macOS apps (Xcode 26 / newer
Electron builds) ship a compiled `Assets.car` referenced by
`CFBundleIconName`, which OVERRIDES `Contents/Resources/icon.icns`. Just
replacing the .icns will produce a silent no-op: file is on disk, Dock still
shows the old icon. The install script handles all of this in one shot.

```bash
bash ~/.qwenworkcn/skills/qwenwork-app-icon/scripts/macos_install_icon.sh \
     "/Applications/<App>.app" \
     "<new.icns>" \
     "/Users/rollin/.qwenworkcn/workspace/mspk8h7m0zr0kz2n"
```

The script:
1. Reads `CFBundleIconFile` from Info.plist (fallback `icon.icns`).
2. Backs up the original `.icns` and Info.plist to the workspace with timestamps.
3. Writes the new `.icns`.
4. If `CFBundleIconName` exists, deletes it so `.icns` wins over Assets.car.
5. Ad-hoc re-signs the bundle (`codesign --force --deep --sign -`) — required
   after Info.plist edits, otherwise Gatekeeper flags the app and IconServices
   keeps caching the old signed icon.
6. Registers with LaunchServices (`lsregister -f`).
7. Wipes IconServices caches (`~/Library/Caches/com.apple.iconservices.store`,
   `/private/var/folders/**/com.apple.iconservices`,
   `/private/var/folders/**/com.apple.dock.iconcache`).
8. HUPs `iconservicesagent` + `iconservicesd`, then restarts Dock and Finder.

### A5. Verify

```bash
sips -s format png "/Applications/<App>.app/Contents/Resources/<iconfile>" \
     --out /tmp/icon_preview.png --resampleWidth 512
```
Read the preview image back and confirm. If the Dock still shows the old
icon after step A4, the app is still running — tell the user to Cmd+Q the
app and reopen it (Dock caches the running app's icon separately). If it's
still wrong, log out and back in (fully rebuilds all icon caches).

---

## Branch B · Windows workflow

### B1. Identify target shortcut

Ask the user which `.lnk` to retarget. Common locations:

- Desktop (current user): `%USERPROFILE%\Desktop\<Name>.lnk`
- Desktop (all users): `C:\Users\Public\Desktop\<Name>.lnk`
- Start Menu (current user): `%APPDATA%\Microsoft\Windows\Start Menu\Programs\<Name>.lnk`
- Start Menu (all users): `%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\<Name>.lnk`
- Taskbar-pinned: `%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\<Name>.lnk`

Search by name:
```powershell
Get-ChildItem "$env:USERPROFILE\Desktop","$env:APPDATA\Microsoft\Windows\Start Menu\Programs","$env:PROGRAMDATA\Microsoft\Windows\Start Menu\Programs" -Recurse -Filter "*<Name>*.lnk"
```

### B2. Produce `.ico`

**Bundled default** → use `assets/default-icon.ico` directly.

**Bundled default, custom background** or **AI-generated** or **User-uploaded**:
```bash
python3 scripts/compose_qwenwork_icon.py C:\Temp\qwenwork.png --bg-style soft-white    # optional
python3 scripts/png_to_ico.py C:\Temp\qwenwork.png C:\Temp\qwenwork.ico
```
`png_to_ico.py` emits a multi-resolution ICO (16/24/32/48/64/128/256) — this is what Explorer & the taskbar consume.

### B3. Put the `.ico` in a stable location

The `.ico` file is referenced by absolute path from the `.lnk`. Do NOT delete it after the operation. Recommended location:
```
%LOCALAPPDATA%\QwenWork\Icons\<name>.ico
```
Create the folder if it doesn't exist and copy the `.ico` there.

### B4. Retarget the shortcut + refresh icon cache

```powershell
powershell -ExecutionPolicy Bypass -File "<skill_dir>\scripts\Set-ShortcutIcon.ps1" `
    -ShortcutPath "$env:USERPROFILE\Desktop\<Name>.lnk" `
    -IconPath    "$env:LOCALAPPDATA\QwenWork\Icons\<name>.ico" `
    -Backup
```
The script:
1. Backs up the original `.lnk` (with `-Backup`) → `.lnk.bak_<timestamp>`.
2. Sets `IconLocation = "<abs path>,0"` via WScript.Shell.
3. Deletes `%LOCALAPPDATA%\IconCache.db` and `iconcache_*.db` under `Microsoft\Windows\Explorer\`.
4. Restarts `explorer.exe`.

### B5. Verify

- Open the folder containing the `.lnk`; the tile should now show the new icon.
- If the taskbar-pinned icon still shows the old artwork, tell the user to unpin the shortcut and re-pin it (Windows caches taskbar icons separately).

---

## `compose_qwenwork_icon.py` — quick reference

Composites Qianzai (or any RGBA logo) onto a themed rounded-square background and writes a PNG.

```
python3 compose_qwenwork_icon.py <output.png> [options]
  --logo <path>           Logo SVG or PNG (default: assets/qianzai-mascot.svg)
  --bg-style <name>       soft-white | dark | brand-green | gradient-green | white | custom
                          Default is `soft-white` — the mascot is green, so light
                          backgrounds give it the best contrast.
  --bg-color <hex>        Solid color for `custom` style, e.g. #161616
  --bg-gradient <a,b>     Two-stop gradient for `custom`, e.g. #FFFFFF,#E8FAF0
  --scale <float>         Mascot width as fraction of canvas (default 0.62; 0.72 works well for Qianzai)
  --size <int>            Output pixel size (default 2048)
  --corner <float>        Rounded-corner ratio (default 0.225 = Big Sur squircle)
  --no-shadow             Skip drop shadow
```

**Do NOT use `--bg-style brand-green`** — Qianzai is `#41D87E` on `#41D87E` = invisible. Only pick brand-green if the logo passed via `--logo` is not green.

## `png_to_icns.py` — macOS

```
python3 png_to_icns.py <source_image> <output.icns>
```
Emits all 10 required macOS iconset sizes (16/32/128/256/512 + @2x) via `iconutil -c icns`.

## `png_to_ico.py` — Windows

```
python3 png_to_ico.py <source_image> <output.ico>
```
Emits 16/24/32/48/64/128/256 in one multi-resolution ICO.

## `Set-ShortcutIcon.ps1` — Windows

```
Set-ShortcutIcon.ps1 -ShortcutPath <path.lnk> -IconPath <path.ico> [-IconIndex 0] [-Backup]
```

## Pitfalls

**macOS**
- **NEVER do a bare `cp` + `killall Dock`.** Always run `macos_install_icon.sh`. Modern Xcode-built apps (Xcode 26+ / newer Electron) ship a compiled `Assets.car` referenced by `CFBundleIconName` — this OVERRIDES `Contents/Resources/icon.icns` and your replaced .icns will silently be ignored. Detection: `PlistBuddy -c "Print :CFBundleIconName"` returns a value. The install script strips it and re-signs; nothing else works reliably.
- After Info.plist edits you MUST ad-hoc re-sign (`codesign --force --deep --sign -`) — otherwise Gatekeeper flags the app AND IconServices keeps caching the pre-edit signed icon indefinitely.
- IconServices caches at BOTH `~/Library/Caches/com.apple.iconservices.store` AND `/private/var/folders/**/com.apple.iconservices`. Kill both, plus HUP `iconservicesagent` and `iconservicesd`.
- `killall Dock` alone is insufficient on macOS 13+; also `killall Finder` and if the target app is running tell the user to Cmd+Q and reopen. If icon is still wrong after all of that, log out and back in — that fully rebuilds the icon cache.
- `/Applications/` writes may require `sudo` on some setups — ask the user first.
- `Info.plist` icon filename varies (`icon.icns`, `AppIcon.icns`, `Electron.icns`, etc.) — the install script reads it dynamically.

**Windows**
- **Do not** edit exe internals — always retarget the `.lnk`. Modifying PE resources risks breaking code signatures and triggering SmartScreen/Defender.
- The `.ico` file must remain at its absolute path — deleting it will make the shortcut fall back to the default icon.
- Icon cache is aggressive. Even after restarting `explorer.exe`, taskbar-pinned items may still show the old icon; unpin and re-pin fixes it.
- UAC / permission: writing under `%PROGRAMDATA%` or `C:\Users\Public\` requires an elevated PowerShell.
- WSL path handling: convert `/mnt/c/...` paths to `C:\...` before passing into PowerShell.

**Both**
- **AI-generated images have an "AI 生成" watermark on the bottom ~90 px.** Crop it before compositing (see step A3 `AI-generated`), otherwise the watermark bleeds into the icon corner.
- **Do not redraw Qianzai from scratch.** When AI-generating, always feed `assets/qianzai-mascot.svg` (or the pre-rendered `default-icon.png`) into `ImageGen` as the reference image so the mascot stays on-model. Never hand-code an approximation SVG.
- **Green mascot needs a light or dark background.** Do not composite Qianzai onto brand-green — the mascot disappears. Prefer `soft-white` (default), `white`, `dark`, or a `custom` non-green gradient. For heavily-recolored AI remixes (e.g. cyberpunk metal), `dark` gives the best contrast.
- Source image should be ≥1024×1024 for macOS, ≥256×256 for Windows.

## HarmonyOS

The skill explicitly refuses HarmonyOS icon replacement requests. If asked, explain: "HarmonyOS 上单独替换第三方应用图标没有公开接口，只有华为主题商店的整套 `.hwt` 主题包才能改，覆盖面是整个系统而不是单个 app。这个能力这个 skill 不提供。"

## File safety

- macOS: every `.icns` replacement is preceded by a timestamped backup to the workspace: `icon_backup_<AppName>_<timestamp>.icns`.
- Windows: `Set-ShortcutIcon.ps1 -Backup` writes `<Name>.lnk.bak_<timestamp>` next to the original.
- Never `rm` an original icon or shortcut — always move-to-backup first.
- Never delete `.app` bundles or `.lnk` shortcuts as part of icon work.

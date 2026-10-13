#Requires -Version 5.1
# 一键安装 Node.js LTS + UTP CLI（Windows 原生 PowerShell 版）
# 无需管理员权限，解压到用户目录并写入用户级 PATH
param([switch]$Reset)

$ErrorActionPreference = 'Stop'

$INSTALL_DIR = Join-Path $env:USERPROFILE 'nodejs'
$TEMP_DIR    = Join-Path $env:USERPROFILE 'nodejs-install'

# 包源可覆盖（默认国内镜像，可通过 UTP_NPM_REGISTRY / UTP_NPM_PACKAGE 覆盖）
$NPM_PACKAGE = if ($env:UTP_NPM_PACKAGE) { $env:UTP_NPM_PACKAGE } else { '@ut-protocol/utp' }
$NPM_REGISTRY = if ($env:UTP_NPM_REGISTRY) { $env:UTP_NPM_REGISTRY } else { 'https://registry.npmmirror.com' }

# Node.js 二进制下载走国内镜像（华为云，与 nodejs.org/dist 路径同构）
$NODE_MIRROR = 'https://mirrors.huaweicloud.com/nodejs'

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Get-LatestNodeVersion($major) {
    try {
        $html = Invoke-WebRequest -Uri "$NODE_MIRROR/latest-v$major.x/" -UseBasicParsing -TimeoutSec 15
        if ($html.Content -match 'node-v(\d+\.\d+\.\d+)') {
            return $Matches[1]
        }
    } catch {}
    return $null
}

# ── 0. reset 模式：清除 ~/.utp 和本地 skill/MCP 配置 ──
if ($Reset) {
    Write-Host '[0/7] reset 模式：清理本地 UTP 数据...'
    $utpDir = Join-Path $env:USERPROFILE '.utp'
    if (Test-Path $utpDir) {
        Remove-Item $utpDir -Recurse -Force
        Write-Host "      已移除 $utpDir"
    }
}

# ── 1. 检查/安装 Node.js ──
if (Test-Command node) {
    Write-Host "[1/7] 检测到 Node.js: $(node --version)，将覆盖/校验安装"
}

Write-Host '[1/7] 查询最新 Node.js LTS 版本...'
$version = Get-LatestNodeVersion 24
if (-not $version) { $version = Get-LatestNodeVersion 22 }
if (-not $version) { throw '无法获取 Node.js 版本号，请检查网络连接。' }
Write-Host "[OK] 目标版本: v$version"

$zipName = "node-v${version}-win-x64.zip"
$downloadUrl = "$NODE_MIRROR/v$version/$zipName"
$tempZip = Join-Path $TEMP_DIR $zipName
New-Item -ItemType Directory -Force $TEMP_DIR | Out-Null

if (Test-Path $tempZip) {
    Write-Host "[2/7] 安装包已存在，跳过下载: $tempZip"
} else {
    Write-Host "[2/7] 下载 Node.js v$version ..."
    Write-Host "       $downloadUrl"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $tempZip -UseBasicParsing
    Write-Host "[OK] 下载完成 ($((Get-Item $tempZip).Length / 1MB -as [int]) MB)"
}

Write-Host "[3/7] 解压到 $INSTALL_DIR ..."
$extractedDir = Join-Path $env:USERPROFILE "node-v${version}-win-x64"
if (Test-Path $extractedDir) { Remove-Item $extractedDir -Recurse -Force }
Expand-Archive -Path $tempZip -DestinationPath $env:USERPROFILE -Force

if (Test-Path $INSTALL_DIR) {
    $backup = "$INSTALL_DIR-backup-$(Get-Date -Format 'yyyyMMddHHmmss')"
    Write-Host "      备份旧版本到 $backup"
    Rename-Item $INSTALL_DIR $backup
}
Rename-Item $extractedDir $INSTALL_DIR
Write-Host '[OK] 解压完成'

# ── 4. 写入用户级 PATH ──
Write-Host '[4/7] 配置 PATH ...'
$pathItem = Get-ItemProperty -Path 'HKCU:\Environment' -Name 'Path' -ErrorAction SilentlyContinue
$currentPath = if ($pathItem) { $pathItem.Path } else { '' }
if ($currentPath -notlike "*$INSTALL_DIR*") {
    Set-ItemProperty -Path 'HKCU:\Environment' -Name 'Path' -Value "$currentPath;$INSTALL_DIR" -Force
    Write-Host "[OK] 已写入用户 PATH: $INSTALL_DIR"
} else {
    Write-Host '[INFO] PATH 中已有 nodejs 目录，跳过 setx'
}

# 当前进程临时生效
$env:Path = "$INSTALL_DIR;$env:Path"

# ── 5. 验证 ──
Write-Host '[5/7] 验证安装...'
if ((Test-Command node) -and (Test-Command npm.cmd)) {
    Write-Host "========================================="
    Write-Host "  Node.js 安装成功！"
    Write-Host "  node: $(node --version) ($INSTALL_DIR\node.exe)"
    Write-Host "  npm:  $((& npm.cmd --version) 2>$null)"
    Write-Host "========================================="
} else {
    Write-Warning '安装完成，但当前进程未检测到 node/npm。请关闭并重新打开终端。'
}

# 清理临时文件
Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue

# ── 6. 安装 utp CLI ──
Write-Host '[6/7] 安装 utp CLI ...'
# Windows 需要同时安装平台二进制包，否则 utp.cmd 指向的 bin/utp 无 .exe 后缀无法执行
& npm.cmd install -g "$NPM_PACKAGE@latest" "${NPM_PACKAGE}-win32-x64@latest" --registry "$NPM_REGISTRY" --silent 2>$null

# 定位真实可执行文件（优先 utp-win32-x64/utp.exe，其次 utp.cmd，兜底 utp/bin/utp）
$UTP_EXE = $null
$candidates = @(
    "$INSTALL_DIR\node_modules\$NPM_PACKAGE-win32-x64\utp.exe",
    "$INSTALL_DIR\node_modules\$NPM_PACKAGE-win32-x64\utp",
    "$INSTALL_DIR\utp.cmd",
    "$INSTALL_DIR\node_modules\$NPM_PACKAGE\bin\utp",
    "$INSTALL_DIR\node_modules\$NPM_PACKAGE\bin\utp.exe"
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $UTP_EXE = $c; break }
}
if (-not $UTP_EXE) {
    throw "utp 安装失败，未找到可执行文件。可稍后手动运行：npm install -g $NPM_PACKAGE ${NPM_PACKAGE}-win32-x64 --registry $NPM_REGISTRY"
}
Write-Host "[OK] utp CLI 已安装: $UTP_EXE"

# ── 7. 探测 Host 并执行 utp install ──
Write-Host '[7/7] 探测 Host 并执行 utp install ...'

# 优先按脚本自身所在路径反推「用户此刻正在用的 Host」（Skill 总是从当前
# Host 的 skills\ 目录被拉起）；推不出来才回退到按优先级探测已安装目录
$target = ''
$hostFound = ''
$selfDir = $PSScriptRoot
$hostMap = @(
    @{ Dir = '.qwenworkcn';  Target = 'qwenwork-cn';  Label = '千问 Work 中国版' },
    @{ Dir = '.qwenwork';    Target = 'qwenwork';     Label = '千问 Work' },
    @{ Dir = '.qoderworkcn'; Target = 'qoderwork-cn'; Label = 'QoderWork 中国版' },
    @{ Dir = '.qoderwork';   Target = 'qoderwork';    Label = 'QoderWork' }
)

if ($selfDir) {
    foreach ($h in $hostMap) {
        $hostRoot = Join-Path $env:USERPROFILE $h.Dir
        if ($selfDir.StartsWith($hostRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            $target = $h.Target; $hostFound = "$($h.Label)（按 Skill 所在路径识别）"
            break
        }
    }
}

if (-not $target) {
    foreach ($h in $hostMap) {
        if (Test-Path (Join-Path $env:USERPROFILE $h.Dir)) {
            $target = $h.Target; $hostFound = $h.Label
            break
        }
    }
}

if ($target) {
    Write-Host "      检测到 $hostFound，执行: utp install --target $target"
    & "$UTP_EXE" install --target $target
} else {
    Write-Host '      未检测到已知 Host，尝试自动探测...'
    & "$UTP_EXE" install
}

Write-Host '[OK] utp install 完成'
Write-Host ''
Write-Host '完成！'

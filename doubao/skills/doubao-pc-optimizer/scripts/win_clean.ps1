# win_clean.ps1 — 安全清理(L1,只删可再生的缓存/临时文件,绝不碰个人文件)
# 用法:
#   预演(只统计不删除): powershell -ExecutionPolicy Bypass -File win_clean.ps1 -DryRun
#   实际清理(建议管理员): Start-Process powershell -Verb RunAs -Wait -ArgumentList '-ExecutionPolicy Bypass -File "此文件完整路径" -LogPath "C:\Users\Public\clean_log.txt"'
# 参数: -DryRun 预演 | -IncludeRecycleBin 清空回收站(默认不清!仅在用户明确提出或单项确认后传入)
#       | -SkipBrowser 跳过浏览器缓存 | -LogPath 日志路径(提权运行时必传,agent 靠日志读取结果)
# 回收站默认不清: 它是用户误删文件的唯一自助恢复渠道,笼统的"清理垃圾"授权不包含它
# 注意: 本脚本无 pause、无任何交互等待,可被 agent 直接调用;确认动作应在调用前由 agent 与用户完成
param(
  [switch]$DryRun,
  [switch]$IncludeRecycleBin,
  [switch]$SkipBrowser,
  [string]$LogPath = ""
)
$ErrorActionPreference = "SilentlyContinue"
$script:freed = 0
$script:report = @()

function Log($msg) {
  Write-Output $msg
  if ($LogPath) { Add-Content -Path $LogPath -Value $msg -Encoding UTF8 }
}
function CleanDir($label, $path) {
  if (-not (Test-Path $path)) { return }
  $size = (Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
  if (-not $size) { $size = 0 }
  if ($DryRun) {
    Log ("[预演] {0}: 可清理 {1} MB ({2})" -f $label, [math]::Round($size/1MB), $path)
  } else {
    # 只删目录内容,不删目录本身;被占用的文件自动跳过,不强制解锁
    Get-ChildItem $path -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $after = (Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if (-not $after) { $after = 0 }
    $delta = $size - $after
    $script:freed += $delta
    Log ("[完成] {0}: 释放 {1} MB(被占用文件已自动跳过)" -f $label, [math]::Round($delta/1MB))
  }
}

Log ("=== C盘安全清理 {0} 开始 {1} ===" -f $(if($DryRun){"(预演模式)"}else{""}), (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
$before = (Get-PSDrive C).Free

# --- 白名单清理项(与 references/windows-cleanup.md 一致,不要在此列表外添加路径)---
# 注意: 清理目标与 win_scan.ps1 的预估清单一一对应,修改任一侧必须同步另一侧
CleanDir "用户临时文件" $env:TEMP
CleanDir "系统临时文件" "C:\Windows\Temp"

# Windows 更新缓存: 先停服务再清;只有服务原本在运行时才重新启动,不改变系统原有状态
$wuWasRunning = (Get-Service wuauserv -ErrorAction SilentlyContinue).Status -eq "Running"
if (-not $DryRun) { Stop-Service wuauserv -Force -ErrorAction SilentlyContinue }
CleanDir "Windows更新缓存" "C:\Windows\SoftwareDistribution\Download"
if (-not $DryRun -and $wuWasRunning) { Start-Service wuauserv -ErrorAction SilentlyContinue }

CleanDir "DirectX着色器缓存" "$env:LOCALAPPDATA\D3DSCache"
CleanDir "NVIDIA着色器缓存" "$env:LOCALAPPDATA\NVIDIA\DXCache"
CleanDir "NVIDIA GL着色器缓存" "$env:LOCALAPPDATA\NVIDIA\GLCache"

# 日志与错误转储: 对普通用户只占空间没有用处,默认清理
# (例外: 若本次会话正在排查蓝屏/故障,调用前 agent 应保留转储,跳过下面三行相关项)
CleanDir "系统日志" "C:\Windows\Logs"
CleanDir "错误报告(WER)" "$env:ProgramData\Microsoft\Windows\WER"
CleanDir "蓝屏小转储" "C:\Windows\Minidump"
if (Test-Path "C:\Windows\MEMORY.DMP") {
  $dmp = (Get-Item "C:\Windows\MEMORY.DMP").Length
  if ($DryRun) { Log ("[预演] 内存转储 MEMORY.DMP: 可清理 {0} MB" -f [math]::Round($dmp/1MB)) }
  else {
    Remove-Item "C:\Windows\MEMORY.DMP" -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path "C:\Windows\MEMORY.DMP")) { $script:freed += $dmp; Log ("[完成] 内存转储 MEMORY.DMP: 释放 {0} MB" -f [math]::Round($dmp/1MB)) }
    else { Log "[跳过] MEMORY.DMP 删除失败(可能被占用),未计入释放量" }
  }
}

# 缩略图缓存: 只删 thumbcache 文件,同目录其他文件不动;删除后重测,只计入实际删掉的部分
$thumbDir = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
$tsize = (Get-ChildItem $thumbDir -Filter "thumbcache_*" -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
if (-not $tsize) { $tsize = 0 }
if ($DryRun) { Log ("[预演] 缩略图缓存: 可清理 {0} MB" -f [math]::Round($tsize/1MB)) }
else {
  Get-ChildItem $thumbDir -Filter "thumbcache_*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
  $tafter = (Get-ChildItem $thumbDir -Filter "thumbcache_*" -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
  if (-not $tafter) { $tafter = 0 }
  $script:freed += ($tsize - $tafter)
  Log ("[完成] 缩略图缓存: 释放 {0} MB(被占用文件已跳过)" -f [math]::Round(($tsize-$tafter)/1MB))
}

if (-not $SkipBrowser) {
  # 浏览器: 枚举 Default 与所有 Profile *,但每个配置里只删 Cache/Code Cache 目录,
  # 绝不碰 History/Login Data/Bookmarks/Cookies 等同级文件
  foreach ($ud in @("$env:LOCALAPPDATA\Google\Chrome\User Data", "$env:LOCALAPPDATA\Microsoft\Edge\User Data")) {
    if (-not (Test-Path $ud)) { continue }
    $browser = if ($ud -match "Chrome") { "Chrome" } else { "Edge" }
    $profiles = Get-ChildItem $ud -Directory -ErrorAction SilentlyContinue
    foreach ($profile in $profiles) {
      if ($profile.Name -ne "Default" -and $profile.Name -notlike "Profile *") { continue }
      CleanDir ("{0}缓存({1})" -f $browser, $profile.Name) (Join-Path $profile.FullName "Cache")
      CleanDir ("{0}代码缓存({1})" -f $browser, $profile.Name) (Join-Path $profile.FullName "Code Cache")
    }
  }
}

$rb = (New-Object -ComObject Shell.Application).NameSpace(0xA).Items() | Measure-Object -Property Size -Sum
$rbSize = $rb.Sum; if (-not $rbSize) { $rbSize = 0 }
if ($IncludeRecycleBin) {
  if ($DryRun) { Log ("[预演] 回收站: 可清空 {0} MB(清空后不可恢复)" -f [math]::Round($rbSize/1MB)) }
  else {
    Clear-RecycleBin -Force -ErrorAction SilentlyContinue
    # 清空后重测,只计入实际清掉的部分
    $rbAfter = ((New-Object -ComObject Shell.Application).NameSpace(0xA).Items() | Measure-Object -Property Size -Sum).Sum
    if (-not $rbAfter) { $rbAfter = 0 }
    $script:freed += ($rbSize - $rbAfter)
    Log ("[完成] 回收站: 清空 {0} MB" -f [math]::Round(($rbSize-$rbAfter)/1MB))
  }
} else {
  Log ("[跳过] 回收站({0} MB)— 默认不清空(用户误删文件的恢复渠道);用户单项确认后加 -IncludeRecycleBin 执行" -f [math]::Round($rbSize/1MB))
}

if ($DryRun) {
  Log "=== 预演结束,未删除任何文件。确认后去掉 -DryRun 参数执行实际清理 ==="
} else {
  $after = (Get-PSDrive C).Free
  Log ("=== 清理完成: 共释放约 {0} GB (C盘剩余 {1} GB -> {2} GB) ===" -f [math]::Round($script:freed/1GB,2), [math]::Round($before/1GB,1), [math]::Round($after/1GB,1))
  Log "未触碰: 个人文件(桌面/文档/下载/图片/视频)、已安装软件、系统文件"
}

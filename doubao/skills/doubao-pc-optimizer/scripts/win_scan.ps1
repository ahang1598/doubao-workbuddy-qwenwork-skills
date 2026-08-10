# win_scan.ps1 — 只读系统扫描(L0,无需管理员,不修改任何内容)
# 用法: powershell -ExecutionPolicy Bypass -File win_scan.ps1 [-BigFiles]
# 输出系统信息、磁盘占用、可清理空间预估、内存/启动项概况
param([switch]$BigFiles)
$ErrorActionPreference = "SilentlyContinue"
function MB($bytes) { [math]::Round($bytes/1MB) }
function GB($bytes) { [math]::Round($bytes/1GB, 1) }
function DirSize($path) { if (Test-Path $path) { (Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } else { 0 } }

Write-Output "=== 系统信息 ==="
$os = Get-CimInstance Win32_OperatingSystem
Write-Output ("OS: {0} (Build {1}, {2})" -f $os.Caption, $os.BuildNumber, $os.OSArchitecture)
if ([int]$os.BuildNumber -ge 22000) { Write-Output "判定: Windows 11" } else { Write-Output "判定: Windows 10" }
if ($os.Caption -match "家庭|Home") { Write-Output "版本: 家庭版(无组策略 gpedit)" }
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output ("机型: {0} {1} | 内存: {2} GB" -f $cs.Manufacturer, $cs.Model, (GB $cs.TotalPhysicalMemory))
$cpu = Get-CimInstance Win32_Processor
Write-Output ("CPU: {0} ({1}核{2}线程)" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
Get-CimInstance Win32_VideoController | ForEach-Object { Write-Output ("GPU: {0} (驱动 {1})" -f $_.Name, $_.DriverVersion) }
$nv = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null
if ($nv) { Write-Output "NVIDIA(准确显存): $nv" }

Write-Output "`n=== 磁盘空间 ==="
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
  Write-Output ("{0} 总 {1} GB / 剩余 {2} GB ({3}%)" -f $_.DeviceID, (GB $_.Size), (GB $_.FreeSpace), [math]::Round($_.FreeSpace/$_.Size*100))
}

Write-Output "`n=== 可清理空间预估(只统计,未删除)==="
# 注意: 此清单与 win_clean.ps1 的实际清理目标一一对应,修改任一侧必须同步另一侧,
# 否则用户看到的"预计释放"与实际释放会不一致
function BrowserCacheSize($userData) {
  $sum = 0
  if (-not (Test-Path $userData)) { return $sum }
  $profiles = Get-ChildItem $userData -Directory -ErrorAction SilentlyContinue
  foreach ($profile in $profiles) {
    if ($profile.Name -eq "Default" -or $profile.Name -like "Profile *") {
      $sum += DirSize (Join-Path $profile.FullName "Cache")
      $sum += DirSize (Join-Path $profile.FullName "Code Cache")
    }
  }
  return $sum
}
$thumbSize = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Windows\Explorer" -Filter "thumbcache_*" -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
if (-not $thumbSize) { $thumbSize = 0 }
$items = [ordered]@{
  "用户临时文件 %TEMP%"        = DirSize $env:TEMP
  "系统临时文件 Windows\Temp"  = DirSize "C:\Windows\Temp"
  "Windows更新缓存"            = DirSize "C:\Windows\SoftwareDistribution\Download"
  "缩略图缓存(thumbcache)"     = $thumbSize
  "着色器缓存(D3D/NV DX/GL)"   = (DirSize "$env:LOCALAPPDATA\D3DSCache") + (DirSize "$env:LOCALAPPDATA\NVIDIA\DXCache") + (DirSize "$env:LOCALAPPDATA\NVIDIA\GLCache")
  "Chrome缓存(全部配置)"       = BrowserCacheSize "$env:LOCALAPPDATA\Google\Chrome\User Data"
  "Edge缓存(全部配置)"         = BrowserCacheSize "$env:LOCALAPPDATA\Microsoft\Edge\User Data"
  "系统日志"                   = DirSize "C:\Windows\Logs"
  "错误报告WER"                = DirSize "$env:ProgramData\Microsoft\Windows\WER"
  "蓝屏转储"                   = (DirSize "C:\Windows\Minidump") + $(if (Test-Path "C:\Windows\MEMORY.DMP") { (Get-Item "C:\Windows\MEMORY.DMP").Length } else { 0 })
}
$total = 0
foreach ($k in $items.Keys) { $total += $items[$k]; Write-Output ("{0}: {1} MB" -f $k, (MB $items[$k])) }
$rb = (New-Object -ComObject Shell.Application).NameSpace(0xA).Items() | Measure-Object -Property Size -Sum
Write-Output ("回收站: {0} MB(默认不清空,清空不可恢复,需用户单项确认)" -f (MB $rb.Sum))
if (Test-Path "C:\Windows.old") {
  Write-Output ("Windows.old: {0} MB(旧系统回退途径,默认不删,需用户单项确认,删除走 cleanmgr/存储设置)" -f (MB (DirSize "C:\Windows.old")))
}
Write-Output ("合计约可释放: {0} GB(不含回收站/Windows.old 等需单独确认项)" -f (GB $total))

Write-Output "`n=== 系统还原点占用(需管理员,失败则跳过)==="
$vss = vssadmin list shadowstorage 2>$null | Select-String "已使用|Used"
if ($vss) { $vss | ForEach-Object { Write-Output $_.Line.Trim() } ; Write-Output "(如占用较大,可询问用户是否删除旧还原点,保留最新一个,见 windows-cleanup.md 进阶方案)" }
else { Write-Output "(无权限或无还原点)" }

Write-Output "`n=== 内存占用 Top 10 ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 |
  ForEach-Object { Write-Output ("{0}: {1} MB" -f $_.Name, (MB $_.WorkingSet64)) }

Write-Output "`n=== 开机启动项 ==="
Get-CimInstance Win32_StartupCommand | ForEach-Object { Write-Output ("[{0}] {1}" -f $_.Location, $_.Name) }

if ($BigFiles) {
  Write-Output "`n=== 用户目录大文件 >500MB(仅报告,请用户自行决定)==="
  foreach ($d in @("$env:USERPROFILE\Downloads","$env:USERPROFILE\Desktop","$env:USERPROFILE\Documents","$env:USERPROFILE\Videos")) {
    Get-ChildItem $d -Recurse -File -ErrorAction SilentlyContinue | Where-Object Length -gt 500MB |
      Sort-Object Length -Descending | Select-Object -First 20 |
      ForEach-Object { Write-Output ("{0} MB`t{1}`t(修改于 {2:yyyy-MM-dd})" -f (MB $_.Length), $_.FullName, $_.LastWriteTime) }
  }
}
Write-Output "`n扫描完成(未做任何修改)"

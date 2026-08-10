# win_game_boost.ps1 — 游戏优化系统层设置(L2,全部可逆,逐值快照+自动生成撤销脚本)
# 用法(需管理员): Start-Process powershell -Verb RunAs -Wait -ArgumentList '-ExecutionPolicy Bypass -File "此文件完整路径" -LogPath "C:\Users\Public\boost_log.txt"'
# 参数: -SkipRestorePoint 跳过还原点 | -EnableHAGS 开启硬件加速GPU计划(需独显+Build>=19041,改后需重启) | -LogPath 日志
# 执行前 agent 必须已向用户逐项说明改动并获得同意(SKILL.md L2 规范)
# 可逆性设计:
#   - 备份目录带时间戳,多次执行互不覆盖
#   - 每个注册表值在修改前记录"是否存在/类型/原值":原来存在 -> 撤销时 reg add 写回原值;
#     原来不存在 -> 撤销时 reg delete 删除(reg import 只回写旧值、不会删新值,不能用作状态恢复)
#   - reg.exe 每次调用检查退出码,失败如实报告
# 本脚本刻意不包含: bcdedit、服务禁用、页面文件、Defender、内存压缩 —— L3 黑名单或收益存疑,不要往里加
param(
  [switch]$SkipRestorePoint,
  [switch]$EnableHAGS,
  [string]$LogPath = ""
)
$ErrorActionPreference = "SilentlyContinue"
function Log($msg) { Write-Output $msg; if ($LogPath) { Add-Content $LogPath -Value $msg -Encoding UTF8 } }

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $env:USERPROFILE "Desktop\游戏优化备份\$stamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$undoScript = Join-Path $backupDir "撤销游戏优化.ps1"
$undoLines = @("# 撤销游戏优化($stamp)— 以管理员身份运行即可恢复本次全部更改", "`$ErrorActionPreference='SilentlyContinue'")

# 修改前快照一个注册表值,返回对应的撤销命令
function UndoLineFor($psPath, $regPath, $name, $type) {
  $cur = (Get-ItemProperty -Path $psPath -Name $name -ErrorAction SilentlyContinue).$name
  if ($null -ne $cur) { return "reg add `"$regPath`" /v $name /t $type /d $cur /f | Out-Null  # 原值: $cur" }
  else { return "reg delete `"$regPath`" /v $name /f 2>`$null | Out-Null  # 原来不存在,撤销即删除" }
}
# 设置一个注册表值:先记撤销行,再写入,并检查退出码
function SetRegValue($psPath, $regPath, $name, $type, $value, $label) {
  $script:undoLines += UndoLineFor $psPath $regPath $name $type
  reg add $regPath /v $name /t $type /d $value /f | Out-Null
  if ($LASTEXITCODE -eq 0) { Log "[完成] $label"; return $true }
  else { Log "[失败] $label (reg 退出码 $LASTEXITCODE),已跳过"; return $false }
}

Log ("=== 游戏优化开始 {0} ===" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Log ("备份目录: {0}" -f $backupDir)

# 0) 系统还原点(失败不阻塞;注意 Win8+ 默认 24 小时内只允许创建一次,当日已建过会被系统跳过,属正常现象而非异常)
if (-not $SkipRestorePoint) {
  Enable-ComputerRestore -Drive "C:\" -ErrorAction SilentlyContinue
  Checkpoint-Computer -Description "游戏优化前备份" -RestorePointType MODIFY_SETTINGS -ErrorAction SilentlyContinue
  if ($?) { Log "[完成] 已创建系统还原点「游戏优化前备份」" }
  else { Log "[提示] 未新建还原点(常见原因: 24小时内已创建过一次,系统限制,属正常;逐值注册表快照仍然完整)" }
}

# 1) reg export 整键备份(额外保险,逐条检查退出码;精确恢复依赖上面的逐值快照)
$exportOk = $true
foreach ($k in @(
  @{Path="HKCU\System\GameConfigStore"; File="GameConfigStore.reg"},
  @{Path="HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"; File="GameDVR.reg"},
  @{Path="HKCU\SOFTWARE\Microsoft\GameBar"; File="GameBar.reg"},
  @{Path="HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"; File="GraphicsDrivers.reg"}
)) {
  reg export $k.Path (Join-Path $backupDir $k.File) /y 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { $exportOk = $false; Log ("[警告] 备份 {0} 失败(键可能不存在),依赖逐值快照撤销" -f $k.Path) }
}
if ($exportOk) { Log "[完成] 注册表整键备份完成" }

# 2) 电源计划 -> 高性能(记录原计划供撤销)
$m = [regex]::Match((powercfg /getactivescheme | Out-String), '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})')
if ($m.Success) { $undoLines += "powercfg /setactive $($m.Groups[1].Value)  # 恢复原电源计划" }
else { Log "[警告] 未能解析当前电源计划 GUID,撤销脚本将不含电源计划恢复项(可在 控制面板→电源选项 手动切回)" }
$high = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
powercfg /setactive $high 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { Log "[完成] 电源计划已切换为「高性能」" }
else {
  # 高性能计划不存在: duplicatescheme 会生成一个【新 GUID】,必须解析并启用新 GUID,而不是旧的
  $dup = powercfg /duplicatescheme $high 2>$null | Out-String
  $dm = [regex]::Match($dup, '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})')
  if ($dm.Success) {
    powercfg /setactive $dm.Groups[1].Value 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { Log "[完成] 已创建并启用「高性能」电源计划 (GUID $($dm.Groups[1].Value))" }
    else { Log "[失败] 高性能计划已创建但启用失败,电源计划未改动" }
  } else { Log "[失败] 无法创建高性能电源计划,电源计划未改动" }
}

# 3) 开启游戏模式 + 关闭 Xbox 后台录制(Game DVR)— 逐值快照后写入
SetRegValue "HKCU:\SOFTWARE\Microsoft\GameBar" "HKCU\SOFTWARE\Microsoft\GameBar" "AutoGameModeEnabled" "REG_DWORD" 1 "开启游戏模式" | Out-Null
SetRegValue "HKCU:\System\GameConfigStore" "HKCU\System\GameConfigStore" "GameDVR_Enabled" "REG_DWORD" 0 "关闭 GameDVR" | Out-Null
SetRegValue "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR" "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR" "AppCaptureEnabled" "REG_DWORD" 0 "关闭 Xbox 后台录制" | Out-Null

# 4) HAGS 硬件加速GPU计划(仅显式要求时;需 Build>=19041,改后重启生效)
if ($EnableHAGS) {
  $build = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber
  if ($build -ge 19041) {
    if (SetRegValue "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" "HwSchMode" "REG_DWORD" 2 "开启硬件加速GPU计划") {
      Log "[提示] HAGS 需重启后生效"
    }
  } else { Log "[跳过] 系统版本过低(Build $build < 19041),不支持 HAGS" }
}

# 5) 写出撤销脚本
$undoLines += 'Write-Output "已恢复本次游戏优化的全部更改(原有值已写回,新增值已删除,电源计划已切回)。部分设置重启后完全生效。"'
$utf8Bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllLines($undoScript, [string[]]$undoLines, $utf8Bom)
Log ("=== 优化完成。撤销脚本: {0} (右键以管理员身份用 PowerShell 运行即可全部恢复) ===" -f $undoScript)

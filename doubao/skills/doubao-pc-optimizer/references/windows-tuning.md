# Windows 系统调优参考(卡顿/内存/启动项/进程)

用户典型诉求:"电脑卡顿帮我优化"、"释放内存"、"关闭占内存的后台程序"、"禁用开机自启动"。

## 先诊断,再动手

"卡"有很多种,盲目优化常无效。先用 `scripts/win_scan.ps1` + 以下只读检查定位:

| 症状 | 检查 | 常见原因 |
|------|------|---------|
| 开机后好几分钟才能用 | 启动项数量、任务管理器"启动"页的影响评级 | 自启动软件太多 |
| 一直很卡 | 内存占用率、C盘剩余空间(<10% 会显著变慢)、磁盘是否 HDD | 内存不足/系统盘满/机械硬盘 |
| 间歇性卡死 | 磁盘 100% 占用的进程、Windows 更新是否在后台下载 | 后台更新/杀毒扫描/HDD |
| 越用越卡,重启就好 | 内存泄漏的进程(占用只增不减) | 某个软件的问题 |
| 风扇狂转+卡 | CPU 占用 top 进程、温度 | 挖矿木马/失控进程/散热 |

诊断命令(L0):

```powershell
# 内存占用 Top 15
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 Name, @{n='内存MB';e={[math]::Round($_.WorkingSet64/1MB)}}
# CPU 占用 Top(取两次采样更准)
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Name, CPU
# 启动项(三个来源都要查)
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
```

## 进程管理(L2:结束进程需确认)

**永不结束**(结束即蓝屏/黑屏/注销):`csrss`、`wininit`、`winlogon`、`services`、`lsass`、`smss`、`svchost`(宿主,里面是什么服务不看就杀等于开盲盒)、`dwm`、`MsMpEng`(Defender)、`audiodg`、`fontdrvhost`、`RuntimeBroker`、`sihost`、`ctfmon`(杀了输入法失灵)。`explorer` 只能"重启"(`Stop-Process -Name explorer` 后它会自动重启或手动 `start explorer`),不要单纯结束。

**可以安全结束的典型**(仍需列清单让用户确认,用户可能正在用):浏览器、网盘同步、音乐/视频App、办公软件的常驻更新器(如 `*Update*.exe`)、游戏平台常驻(Steam 不在游戏时),以及经准确识别、确认属于普通第三方应用且不涉及安全防护、驱动、远程管理、同步备份、身份认证或硬件管理的后台进程。

结束进程用 `Stop-Process -Name xxx -ErrorAction SilentlyContinue`,一次性列出将结束的清单征得同意,别逐个问。

"释放内存"类需求的正确姿势:关掉高占用的用户进程 + 建议重启,**不要**用"内存整理/压缩工具"或 `EmptyStandbyList` 类偏方(标准待机列表本来就是缓存,清了反而变慢)。内存长期 >85% 的根本解法是加内存或少开软件,如实告知。

## 启动项管理(L2)

原则:**禁用而不是删除/卸载**,禁用可随时在任务管理器"启动"页恢复,这是天然可回滚的操作。

- **保留**:杀毒/安全软件、显卡面板(NVIDIA/AMD)、声卡管理器、输入法、云同步(用户日常依赖的话)、厂商电源管理(笔记本)
- **建议禁用**:办公软件预加载(WPS/Office 加速启动项)、视频/音乐/购物类App自启、游戏平台自启、更新器(软件用时会自己查更新),以及经准确识别、确认属于普通第三方应用的“助手”“管家”等自启动项。安全软件、驱动、远程管理、同步备份、身份认证和 OEM 硬件管理组件必须保留;无法确认用途时保持原样
- **拿不准的**:列出名字和厂商让用户决定,或保持原样

禁用方式:引导用户在 任务管理器→启动应用 里关(最直观、最可逆);或用注册表 `StartupApproved` 项(win_scan 输出会给出对应项)。不要直接删 Run 键值——那是"删除"不是"禁用"。

服务(Services)层面:**默认不动任何服务**。网上"禁用XX服务提速"清单里,SysMain/Windows Search 在 SSD 机器上确实可关(L2,`Set-Service -StartupType Disabled` 前记录原值),但收益很小;其余服务一律不碰。绝不禁用 SKILL.md 黑名单里的关键服务。

## 系统整体加速清单(按收益排序)

1. C盘保持 >15% 剩余空间(不足先走清理流程,见 windows-cleanup.md)
2. 减少自启动(见上)
3. 结束当前不用的高占用进程(见上)
4. 视觉效果调"最佳性能"(用户同意后;界面会变朴素):`SystemPropertiesPerformance.exe` 引导用户选,或注册表 VisualFXSetting=2
5. 检查 Windows 更新是否卡在失败重试循环(设置→Windows 更新),失败的更新反复下载会持续占用磁盘和网络
6. 机械硬盘:碎片整理 `defrag C: /O`(SSD 上不要做传统碎片整理,系统会自动 TRIM)
7. 硬件建议(软件解决不了时):HDD→SSD 是老机器最大提升;8GB→16GB 内存;笔记本清灰换硅脂

## 弹窗广告治理(用户常连带提出)

- 先定位来源:弹窗出现时打开任务管理器,右键弹窗进程→打开文件所在位置,即知是哪家软件
- 处理顺序:软件设置里关推送 → 确认弹窗所属软件 → 普通第三方软件可在用户明确确认后禁用对应启动项或计划任务,也可按 L2 流程卸载。不得仅凭文件名删除、移动或改名安装目录组件;安全软件和重要系统软件一律不处理
- 不要建议用户安装"弹窗拦截大师"类软件(很多本身就是广告源);不要用防火墙全域封禁(可能影响软件正常功能)

## L2 撤销速查(执行 L2 时把对应撤销命令写进撤销脚本)

每做一项 L2 修改,先记录原值,并把下表对应的撤销命令(带上记录的原值)追加进用户可见的撤销脚本——不要执行完才临场回忆怎么撤:

| L2 操作 | 修改前记录 | 撤销命令 |
|---------|-----------|---------|
| 禁用启动项(StartupApproved) | `reg export "HKCU\...\Explorer\StartupApproved\Run" 备份.reg` | `reg import 备份.reg`(或告知用户:任务管理器→启动应用→重新启用) |
| 修改服务启动类型 | `(Get-Service 名).StartType` 原值 | `Set-Service 名 -StartupType 原值` |
| 关闭休眠 | 无需记录 | `powercfg /h on` |
| 切换电源计划 | `powercfg /getactivescheme` 的原 GUID | `powercfg /setactive 原GUID` |
| 视觉效果改性能优先 | `reg export "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" 备份.reg` | `reg import 备份.reg` |
| 结束用户进程 | 无需记录 | 无需撤销(重开软件即可),但要在汇报里列出关了哪些 |
| 游戏相关注册表(GameDVR/GameBar/HAGS) | win_game_boost.ps1 自动备份 | 其生成的"撤销游戏优化.ps1" |

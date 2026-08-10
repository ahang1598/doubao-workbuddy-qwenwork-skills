# macOS 清理与优化参考

Mac 用户提出"清理垃圾/电脑卡/优化"时使用。macOS 与 Windows 的思路差异很大,不要把 Windows 方案翻译过来:没有C盘和注册表、系统自带内存压缩和维护机制、大部分"清理软件"在 Mac 上弊大于利。

## 识别(L0)

```bash
sw_vers                                    # ProductVersion: 14.x=Sonoma 15.x=Sequoia 26.x=Tahoe
sysctl -n machdep.cpu.brand_string         # 含 "Apple M" 即 Apple Silicon,否则 Intel
system_profiler SPHardwareDataType | grep -E "Memory|Model"
df -h /                                    # 注意 APFS 下"可用"含可清除空间,数字会波动
```

注意:你的命令工具在 Mac 上是真正的 bash/zsh,`&&`、常规 Unix 命令均可用,与 Windows 的 PowerShell 环境不同。

## 磁盘清理

**首选引导用户用系统自带工具**:苹果菜单→系统设置→通用→存储,那里有安全的分类清理建议(大文件、iOS 备份、废纸篓自动清倒),比命令行删除更安全直观。

命令行白名单(L1,用 `scripts/mac_clean.sh`——**默认即预演模式**,只统计不删除;确认后加 `--execute` 才实际清理,废纸篓需再加 `--trash`):

| 位置 | 内容 | 注意 |
|------|------|------|
| `~/Library/Caches/*` | 用户级应用缓存 | 只删缓存目录的**内容**,不删目录本身;跳过 CloudKit/FamilyCircle 相关 |
| `~/Library/Logs/*` | 用户日志 | 安全(系统级 /private/var/log 不碰,脚本也不涉及) |
| `废纸篓 ~/.Trash` | 已删除文件 | **默认不清空**(用户误删文件的恢复渠道):报告大小、单项确认后才清(脚本需 `--execute --trash` 双参数);笼统的"清理垃圾"授权不包含它 |
| `~/Library/Developer/Xcode/DerivedData` | Xcode 编译缓存 | 仅装了 Xcode 的用户,常有几十GB |
| `~/Library/Application Support/*/Cache*` | 各App缓存 | 微信缓存可达上百GB:微信自带"设置→通用→存储空间"清理最安全,聊天文件属个人资料不要碰 |
| 浏览器缓存 | Chrome/Safari | Safari 用 开发菜单→清空缓存 引导;Chrome 同 Windows 只删 Cache 目录 |

**黑名单(L3)**:`/System`、`/Library`(系统级,动了可能起不来)、`/private/var/db`、`~/Library/Keychains`、任何需要 `sudo rm -rf` 的系统路径、关闭 SIP、删除 `.app` 内部文件("给应用瘦身")。`/System/Library/Caches` 和 `/Library/Caches` 由系统管理,不要手动清。

时间机器本地快照占空间(`df` 与实际不符的常见原因):`tmutil listlocalsnapshots /` 查看,可用 `tmutil deletelocalsnapshots 日期` 删除(L2,告知用户这会失去对应时间点的本地恢复能力;系统空间不足时也会自动清)。

大文件报告(L0):`du -sh ~/Downloads ~/Movies ~/Documents 2>/dev/null`、`find ~ -size +500M -not -path "*/Library/*" 2>/dev/null` ——只报告,让用户自己删。

## 性能优化

Mac"卡"的常见原因和处理:

1. **磁盘快满**(剩余 <10%):先清理,APFS 满盘性能下降明显
2. **内存压力**:活动监视器(或 `top -l 1 | head -15`)看内存压力是否黄/红;高占用常见是 Chrome 多标签、微信、虚拟机。处理=关应用,Mac 不需要"内存清理软件",`sudo purge` 只在测试场景有意义,日常用会更慢
3. **登录项**:系统设置→通用→登录项与扩展,引导用户关闭不需要的(等价 Windows 启动项,天然可逆)
4. **Spotlight 重建索引**(风扇狂转+ mds 进程高占用):等它跑完即可,通常一次性
5. **Intel 老 Mac**:重置 SMC/NVRAM 可解决部分电源和风扇问题(引导用户按官方组合键操作);Apple Silicon 无此需求
6. **降级建议不要给**:不要建议用户关闭透明效果之外的系统动画 hack、不要装"清理/加速"类软件(CleanMyMac 之类由用户自己决定,你不主动推荐)

## Mac 上的游戏帧率

Mac 游戏优化空间小,如实告知:主要手段是游戏内降分辨率/画质(优先降分辨率到 1080p)、开 MetalFX 缩放(游戏支持的话)、关闭其他占内存应用、插电+高功率模式(系统设置→电池,部分机型)。不存在驱动面板和系统级"游戏模式"可调。

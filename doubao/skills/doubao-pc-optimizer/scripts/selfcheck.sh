#!/bin/bash
# selfcheck.sh — skill 静态自检(在任意 Linux/macOS 上可跑,不需要 Windows)
# 检查: 1) 脚本不含危险/禁止模式(不区分大小写)  2) shell 脚本语法  3) PowerShell 编码与语法  4) 关键文件齐全
cd "$(dirname "$0")/.." || exit 1
fail=0

echo "== 1. 危险模式检查(scripts/ 中不允许出现,忽略大小写)=="
# pause 会挂起 agent 执行工具; bcdedit 写操作在 L3 黑名单; Win32_Product 会触发 MSI 重配置;
# rm -rf 系统目录、全删卷影副本、关 SIP 均为 L3
PATTERNS=(
  '^[[:space:]]*pause[[:space:]]*$'
  'bcdedit[[:space:]]+/(set|deletevalue|delete)'
  'Win32_Product'
  'vssadmin[[:space:]]+delete[[:space:]]+shadows[[:space:]].*(/all|-all)'
  'rm[[:space:]]+-rf?[[:space:]]+["'"'"']?/(System|Library|Users|usr|etc|var|private|bin)'
  'csrutil[[:space:]]+disable'
  'pnputil(\.exe)?[[:space:]]+/delete-driver'
  'sc(\.exe)?[[:space:]]+delete'
  'Remove-Service'
  'Set-MpPreference.*DisableRealtimeMonitoring'
  'Disable-WindowsOptionalFeature'
  'Uninstall-WindowsFeature'
  '(Move-Item|Rename-Item|Remove-Item).*(System32|DriverStore|WindowsApps|Program Files)'
)
for pat in "${PATTERNS[@]}"; do
  hits=$(grep -riEn "$pat" scripts/ --include='*.ps1' --include='*.bat' --include='*.sh' | grep -v selfcheck)
  if [ -n "$hits" ]; then echo "[FAIL] 匹配到禁止模式 '$pat':"; echo "$hits"; fail=1; fi
done
[ $fail -eq 0 ] && echo "[OK] 未发现禁止模式"

if grep -Fq '核心隔离关闭' references/windows-game-fps.md; then
  echo "[FAIL] windows-game-fps.md 仍存在主动关闭核心隔离的建议"
  fail=1
fi
if grep -Eq '安装目录.*组件改名' references/windows-tuning.md; then
  echo "[FAIL] windows-tuning.md 仍存在改名安装目录组件的建议"
  fail=1
fi
if grep -Eq '主动要求卸载.*不在此列' SKILL.md; then
  echo "[FAIL] SKILL.md 的安全软件卸载仍存在例外"
  fail=1
fi

echo "== 2. shell 脚本语法检查 =="
for f in scripts/*.sh; do
  if bash -n "$f"; then echo "[OK] $f"; else echo "[FAIL] $f 语法错误"; fail=1; fi
done

echo "== 3. PowerShell 编码与语法检查 =="
for f in scripts/*.ps1; do
  bom=$(od -An -tx1 -N3 "$f" | tr -d ' \n')
  if [ "$bom" = "efbbbf" ]; then
    echo "[OK] $f 使用 UTF-8 BOM"
  else
    echo "[FAIL] $f 缺少 UTF-8 BOM,Windows PowerShell 5.1 可能误按本地代码页解析"
    fail=1
  fi
done

if ! grep -q '内置脚本解析或执行失败时' SKILL.md; then
  echo "[FAIL] SKILL.md 缺少内置脚本失败后的安全停止规则"
  fail=1
fi

if grep -Fq 'Where-Object { $_.Name -eq "Default"' scripts/win_clean.ps1; then
  echo "[FAIL] win_clean.ps1 浏览器配置枚举仍使用易受解析上下文影响的嵌套管道"
  fail=1
fi

if ! grep -Fq 'UTF8Encoding($true)' scripts/win_game_boost.ps1; then
  echo "[FAIL] win_game_boost.ps1 未明确保证生成的撤销脚本带 UTF-8 BOM"
  fail=1
fi

echo "-- PowerShell 语法解析(检测到 pwsh 时执行,否则跳过)--"
if command -v pwsh >/dev/null 2>&1; then
  for f in scripts/*.ps1; do
    if pwsh -NoProfile -Command "\$t=\$null;\$e=\$null;[void][System.Management.Automation.Language.Parser]::ParseFile('$PWD/$f',[ref]\$t,[ref]\$e); if(\$e.Count){exit 1}"; then
      echo "[OK] $f"
    else echo "[FAIL] $f 存在语法错误"; fail=1; fi
  done
else
  echo "[跳过] 本机无 pwsh,PowerShell 脚本请在 Windows 测试机上用 -DryRun 验证"
fi

echo "== 4. 关键文件齐全性 =="
for f in SKILL.md references/windows-cleanup.md references/windows-game-fps.md references/windows-tuning.md references/macos.md scripts/win_scan.ps1 scripts/win_clean.ps1 scripts/win_game_boost.ps1 scripts/mac_clean.sh; do
  [ -f "$f" ] || { echo "[FAIL] 缺少 $f"; fail=1; }
done
[ $fail -eq 0 ] && echo "[OK] 文件齐全"

echo; [ $fail -eq 0 ] && echo "自检全部通过" || echo "自检存在失败项"
exit $fail

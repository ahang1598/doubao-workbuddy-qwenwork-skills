#!/usr/bin/env bash
# check-init.sh - 检查 vlog 技能是否已初始化
# 用法：check-init.sh
# 返回值：
#   0 = 已初始化，无需操作
#   1 = 未初始化或 skill 已更新，需要执行 docs/setup.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$SKILL_DIR/.runtime/template"
SKEL_DIR="$SKILL_DIR/assets/template-skeleton"

# ─── 检查1：模板目录是否存在 ───
if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "❌ 模板目录不存在，需要执行 docs/setup.md"
  exit 1
fi

# ─── 检查2：依赖是否已安装 ───
if [ ! -f "$SKILL_DIR/node_modules/remotion/package.json" ]; then
  echo "❌ 依赖未就绪，请等待小艺 Work 后台安装或在技能页重试"
  exit 1
fi

# ─── 检查3：核心文件是否存在 ───
CORE_FILES=(
  "src/MainComposition.tsx"
  "package.json"
)
for f in "${CORE_FILES[@]}"; do
  if [ ! -f "$TEMPLATE_DIR/$f" ]; then
    echo "❌ 核心文件缺失: $f，需要执行 docs/setup.md"
    exit 1
  fi
done

# ─── 检查4：skill 更新检测（对比骨架与模板） ───
if [ -d "$SKEL_DIR" ]; then
  CHECK_FILES=(
    "package.json"
    "src/MainComposition.tsx"
    "src/Root.tsx"
  )
  for f in "${CHECK_FILES[@]}"; do
    skel_file="$SKEL_DIR/$f"
    tmpl_file="$TEMPLATE_DIR/$f"
    [ ! -f "$skel_file" ] && continue
    if [ ! -f "$tmpl_file" ] || ! diff -q "$skel_file" "$tmpl_file" &>/dev/null; then
      echo "⚠️  skill 已更新，文件与骨架不一致: $f，需要执行 docs/setup.md"
      exit 1
    fi
  done
fi

# ─── 全部通过 ───
echo "✅ 已初始化，无需操作"
exit 0

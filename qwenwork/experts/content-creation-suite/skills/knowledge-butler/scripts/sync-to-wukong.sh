#!/bin/bash
# sync-to-wukong.sh — 把源码同步到悟空已装 skill 目录 + 打压缩包
#
# 用法：
#   bash scripts/sync-to-wukong.sh                                # 交互式询问 message
#   bash scripts/sync-to-wukong.sh -m "v6.1 加 UI 缓存提示"        # 直接传 message
#   bash scripts/sync-to-wukong.sh --message "..."                # 同上
#   bash scripts/sync-to-wukong.sh --dry                          # 只看 diff 不执行
#
# 设计：
#   - 源码目录是权威，rsync --delete 让已装目录精确等于源码
#   - dist/ 保留**所有历史版本**（带时间戳）+ 维护 知识管家.zip 指向最新副本
#   - 每次部署自动写一条记录到 dist/CHANGELOG.md（最新在上）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$SCRIPT_DIR/.." && pwd)"            # 悟空skill开发/
KB_ROOT="$(cd "$SRC/.." && pwd)"               # 知识管家/
DIST="$KB_ROOT/dist"
SKILL_NAME="knowledge-butler"

# ─── 参数解析（--dry / --message） ───────────────────────────
DRY_RUN=""
CHANGELOG_MSG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry)
            DRY_RUN="--dry"
            shift
            ;;
        -m|--message)
            CHANGELOG_MSG="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# 没传 --message 且不是 --dry → 进交互模式询问
if [ -z "$CHANGELOG_MSG" ] && [ "$DRY_RUN" != "--dry" ]; then
    echo "📝 本次更新说明（一句话，可留空回车跳过）："
    read -r CHANGELOG_MSG </dev/tty 2>/dev/null || CHANGELOG_MSG=""
    [ -z "$CHANGELOG_MSG" ] && CHANGELOG_MSG="（无说明）"
fi

# rsync 排除项（源码中的本地产物不同步到已装目录）
EXCLUDES=(
    --exclude=.venv
    --exclude=.DS_Store
    --exclude=__pycache__
    --exclude='*.pyc'
    --exclude=dist
    --exclude=.git
    --exclude='*.log'
)

# ─── Step 1. 探测已装位置 ──────────────────────────────────────
TARGETS=$(grep -l "^name: $SKILL_NAME" ~/.real/users/user-*/.skills/*/SKILL.md 2>/dev/null || true)
if [ -z "$TARGETS" ]; then
    echo "❌ 未找到已装的 $SKILL_NAME skill。" >&2
    echo "   请先在钉钉客户端'技能中心 → 上传技能'走一次 initial install。" >&2
    exit 1
fi

TARGET_COUNT=$(echo "$TARGETS" | wc -l | tr -d ' ')
echo "🔍 发现 $TARGET_COUNT 个已装位置："
for T in $TARGETS; do
    echo "   $(dirname "$T")"
done
echo ""

# ─── Step 2. 同步（rsync --delete 保证精确镜像）────────────────
if [ "$DRY_RUN" = "--dry" ]; then
    echo "🧪 DRY RUN：只显示 diff，不实际同步"
    for SKILL_MD in $TARGETS; do
        TARGET_DIR="$(dirname "$SKILL_MD")"
        echo "---- $TARGET_DIR ----"
        rsync -avn --delete "${EXCLUDES[@]}" "$SRC/" "$TARGET_DIR/" | grep -v '^$' | head -30
    done
    exit 0
fi

SYNCED=0
for SKILL_MD in $TARGETS; do
    TARGET_DIR="$(dirname "$SKILL_MD")"
    echo "→ 同步到 $TARGET_DIR"
    rsync -a --delete "${EXCLUDES[@]}" "$SRC/" "$TARGET_DIR/"
    # 时间戳对齐，便于后续核对
    touch "$TARGET_DIR/SKILL.md"
    SYNCED=$((SYNCED + 1))
done
echo "✅ 已同步到 $SYNCED 个已装位置"
echo ""

# ─── Step 3. 打 zip 压缩包到 dist/（保留历史版本 + 维护 latest 副本）──
mkdir -p "$DIST"

TIMESTAMP=$(date +%Y%m%d-%H%M)
VERSIONED_ZIP="$DIST/知识管家-v$TIMESTAMP.zip"
LATEST_ZIP="$DIST/知识管家.zip"

# 仅清旧的 .tar.gz（已废弃格式）和 knowledge-butler-* 命名（旧的英文命名）
# **不再删** 知识管家-vX.zip — 保留所有历史版本
rm -f "$DIST"/*.tar.gz 2>/dev/null
rm -f "$DIST"/$SKILL_NAME-*.zip 2>/dev/null

# 实际打包目标：versioned zip
ZIPBALL="$VERSIONED_ZIP"

# 打包策略：先 rsync 源码到临时目录（过滤掉不想打包的），再用 Python zipfile 打成 zip
# - 包内顶层目录固定为 knowledge-butler/，避免中文目录名在部分解压器里乱码
# - Python zipfile 会给非 ASCII 文件名设置 UTF-8 flag，中文 references/templates 文件名可正常读取
TMP_STAGE=$(mktemp -d)
trap 'rm -rf "$TMP_STAGE"' EXIT

STAGE_ROOT="$TMP_STAGE/$SKILL_NAME"
mkdir -p "$STAGE_ROOT"
rsync -a \
    --exclude='.venv' \
    --exclude='.DS_Store' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='dist' \
    --exclude='.git' \
    --exclude='*.log' \
    "$SRC/" "$STAGE_ROOT/"

python3 - "$STAGE_ROOT" "$ZIPBALL" <<'PY'
import os
import sys
import zipfile
from pathlib import Path

stage_root = Path(sys.argv[1]).resolve()
zipball = Path(sys.argv[2]).resolve()
base = stage_root.name

with zipfile.ZipFile(zipball, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(stage_root):
        dirs[:] = sorted(dirs)
        files = sorted(files)
        root_path = Path(root)
        rel_root = root_path.relative_to(stage_root)
        if rel_root == Path("."):
            dir_arc = base + "/"
        else:
            dir_arc = str(Path(base) / rel_root).replace(os.sep, "/") + "/"
        zf.writestr(dir_arc, b"")
        for filename in files:
            path = root_path / filename
            rel = path.relative_to(stage_root)
            arcname = str(Path(base) / rel).replace(os.sep, "/")
            zf.write(path, arcname)
PY

ZB_SIZE=$(du -h "$ZIPBALL" | cut -f1)
echo "📦 已打包：$ZIPBALL ($ZB_SIZE)"

# 复制为 latest 副本（用户分发用——固定文件名稳定可分享）
cp -f "$VERSIONED_ZIP" "$LATEST_ZIP"
echo "📦 已更新 latest：$LATEST_ZIP"
echo ""

# ─── 写 CHANGELOG.md（最新在上 · 自动追加）─────────────────
CHANGELOG="$DIST/CHANGELOG.md"
python3 - "$CHANGELOG" "$TIMESTAMP" "$CHANGELOG_MSG" "$ZB_SIZE" <<'PY'
import sys
from pathlib import Path
from datetime import datetime

p = Path(sys.argv[1])
ts = sys.argv[2]
msg = sys.argv[3]
size = sys.argv[4]

now = datetime.now().strftime("%Y-%m-%d %H:%M")
new_entry = f"""## v{ts} — {now}

**zip**: `知识管家-v{ts}.zip` ({size})  ·  也复制为 `知识管家.zip`（latest）

**改动**：
{msg}

---
"""

if not p.exists():
    p.write_text(f"""# 知识管家分发包更新日记

每次跑 `sync-to-wukong.sh` 部署时自动追加一条记录。**最新在上**。

每次部署都会保留 `知识管家-vYYYYMMDD-HHMM.zip` 历史版本 + 同步更新 `知识管家.zip`（指向最新）。

<!-- LATEST -->

{new_entry}
""", encoding="utf-8")
    print(f"📓 已创建 CHANGELOG.md")
else:
    text = p.read_text(encoding="utf-8")
    if "<!-- LATEST -->" in text:
        text = text.replace("<!-- LATEST -->", f"<!-- LATEST -->\n\n{new_entry}", 1)
    else:
        # 没有标记位 → 加在文件开头第一段后
        text = text + "\n\n" + new_entry
    p.write_text(text, encoding="utf-8")
    print(f"📓 已追加到 CHANGELOG.md（v{ts}）")
PY
echo ""

# ─── Step 5. 提示 ────────────────────────────────────────────
echo "⚠️  重要：完全退出钉钉再重启，skill 索引才会刷新"
echo "    Mac：右键任务栏钉钉 → 退出；不是关闭窗口"

#!/usr/bin/env bash
# render-video.sh - vlog 技能第5+6步：预览帧检查 + 渲染输出
# 用法：render-video.sh <output_dir> <video_name> [--timeout <seconds>]
# 示例：render-video.sh ~/.openclaw/workspace/generated-vlog/20260506_090200 travel-landscape
#       render-video.sh ~/.openclaw/workspace/generated-vlog/20260506_090200 travel-landscape --timeout 3600
#
# 功能：
#   1. 预览帧检查（标题帧 + 场景帧，验证 script.json / 组件 / 图片无误）
#   2. 全部通过后渲染为 MP4
#   3. 验证输出文件

set -euo pipefail

# ─── 常量 ───
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$SKILL_DIR/.runtime/template"
REMOTION_BIN="$SKILL_DIR/node_modules/.bin/remotion"

# ─── 参数解析 ───
if [ $# -lt 2 ]; then
  echo "用法: render-video.sh <output_dir> <video_name> [--timeout <seconds>]"
  echo ""
  echo "参数："
  echo "  output_dir    第4步创建的输出目录路径"
  echo "  video_name    输出视频文件名（不含 .mp4，全小写短横线连接）"
  echo ""
  echo "选项："
  echo "  --timeout <sec>   渲染超时秒数（默认 1800）"
  exit 1
fi

OUTPUT_DIR="$1"; shift
VIDEO_NAME="$1"; shift

TIMEOUT=1800

while [ $# -gt 0 ]; do
  case "$1" in
    --timeout)
      shift
      if [ $# -eq 0 ]; then
        echo "❌ --timeout 需要指定秒数"
        exit 1
      fi
      TIMEOUT="$1"; shift
      ;;
    *)
      echo "❌ 未知参数: $1"
      exit 1
      ;;
  esac
done

# ─── 验证 ───
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "❌ 输出目录不存在: $OUTPUT_DIR"
  exit 1
fi

SCRIPT_JSON="$OUTPUT_DIR/script.json"
if [ ! -f "$SCRIPT_JSON" ]; then
  echo "❌ script.json 不存在: $SCRIPT_JSON"
  exit 1
fi

CHECK_SCRIPT="$SKILL_DIR/scripts/check-init.sh"
if [ -f "$CHECK_SCRIPT" ]; then
  bash "$CHECK_SCRIPT" || { echo "❌ 初始化检查未通过，请先执行 docs/setup.md"; exit 1; }
else
  if [ ! -f "$SKILL_DIR/node_modules/remotion/package.json" ]; then
    echo "❌ Vlog 依赖未就绪！"
    exit 1
  fi
fi

if [ ! -f "$REMOTION_BIN" ]; then
  echo "❌ Remotion 命令未就绪，请等待小艺 Work 后台安装或在技能页重试"
  exit 1
fi

# 验证视频名格式
if [[ "$VIDEO_NAME" =~ [^a-z0-9\-] ]]; then
  echo "❌ 视频名只能包含小写字母、数字和短横线: $VIDEO_NAME"
  exit 1
fi

OUT_DIR="$OUTPUT_DIR/out"
MP4_PATH="$OUT_DIR/${VIDEO_NAME}.mp4"

cd "$TEMPLATE_DIR"

# ─── 预览帧检查 ───
echo ""
echo "━━━ 预览帧检查 ━━━"
echo ""

PREVIEW_OK=true

# 标题帧（frame=0）
# P2-9：scale 0.25→0.5——180p 只能看构图，文字错别字/画面偏色看不清
echo "🔍 检查标题帧 (frame=0)..."
if "$REMOTION_BIN" still src/index.ts MainComposition "$OUT_DIR/preview-title.png" \
  --frame=0 --scale=0.5 --props="$SCRIPT_JSON" 2>&1; then
  echo "✅ 标题帧正常"
else
  echo "❌ 标题帧失败"
  PREVIEW_OK=false
fi

# P2-9：场景帧动态定位——取首场景中点帧，避免写死 frame 恰好落在转场上
# （旧版写死 138 是 TITLE_FRAMES=90 时代的值，标题改 72 帧后 138 已偏离首场景中点；
#  若首场景较短，写死值甚至可能落在转场帧上，预览检查意义打折）
# 首场景全局起始帧 = TITLE_FRAMES(72) - 片头转场(18)
# ⚠️ 72/18 与模板 MainComposition.tsx 常量 TITLE_FRAMES/TRANSITION_FRAMES 联动，改模板常量需同步此处
SCENE_MID_FRAME=$(node -e "
  const d = require('$SCRIPT_JSON');
  const sd = (Array.isArray(d.sceneDurations) && d.sceneDurations[0]) || 135;
  console.log(72 - 18 + Math.floor(sd / 2));
")
echo ""
echo "🔍 检查场景帧 (frame=${SCENE_MID_FRAME}，首场景中点)..."
if "$REMOTION_BIN" still src/index.ts MainComposition "$OUT_DIR/preview-mid.png" \
  --frame=${SCENE_MID_FRAME} --scale=0.5 --props="$SCRIPT_JSON" 2>&1; then
  echo "✅ 场景帧正常"
else
  echo "❌ 场景帧失败"
  PREVIEW_OK=false
fi

if [ "$PREVIEW_OK" = false ]; then
  echo ""
  echo "❌ 预览帧检查未通过，请修复 script.json 或图片后重试"
  echo "   提示：检查图片文件名是否与 script.json 中的 scene.image 一致"
  exit 1
fi

echo ""
echo "✅ 预览帧检查全部通过，开始渲染..."

# ─── 步骤6：渲染输出 ───
echo ""
echo "━━━ 渲染输出 ━━━"
echo "  输出: $MP4_PATH"
echo "  超时: ${TIMEOUT}s"
echo ""

# 渲染并发度：nproc 的一半，至少为 1（单核环境下 $(($(nproc) / 2)) 会算成 0，导致 remotion 报错）
CONCURRENCY=$(( $(nproc) / 2 ))
[ "$CONCURRENCY" -lt 1 ] && CONCURRENCY=1

START_TIME=$(date +%s)

# 使用 timeout 控制渲染时间
RENDER_EXIT=0
if command -v timeout &>/dev/null; then
  timeout "${TIMEOUT}" "$REMOTION_BIN" render src/index.ts MainComposition "$MP4_PATH" \
    --codec h264 --crf 23 --concurrency="$CONCURRENCY" --props="$SCRIPT_JSON" 2>&1 || RENDER_EXIT=$?
else
  # 没有 timeout 命令则直接跑
  "$REMOTION_BIN" render src/index.ts MainComposition "$MP4_PATH" \
    --codec h264 --crf 23 --concurrency="$CONCURRENCY" --props="$SCRIPT_JSON" 2>&1 || RENDER_EXIT=$?
fi

if [ "$RENDER_EXIT" -ne 0 ]; then
  echo ""
  echo "❌ 渲染失败（退出码: ${RENDER_EXIT}）"
  exit 1
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# ─── 验证输出 ───
echo ""
if [ -f "$MP4_PATH" ]; then
  FILE_SIZE=$(stat -c%s "$MP4_PATH" 2>/dev/null || stat -f%z "$MP4_PATH" 2>/dev/null || echo "unknown")
  if [ "$FILE_SIZE" = "unknown" ] || [ "$FILE_SIZE" -eq 0 ]; then
    echo "❌ 渲染输出文件异常（大小: ${FILE_SIZE} bytes）"
    exit 1
  fi

  # 人类可读的文件大小
  if [ "$FILE_SIZE" != "unknown" ]; then
    if [ "$FILE_SIZE" -gt 1048576 ]; then
      HUMAN_SIZE="$(echo "scale=1; $FILE_SIZE / 1048576" | bc)MB"
    elif [ "$FILE_SIZE" -gt 1024 ]; then
      HUMAN_SIZE="$(echo "scale=1; $FILE_SIZE / 1024" | bc)KB"
    else
      HUMAN_SIZE="${FILE_SIZE}B"
    fi
  fi

  echo "═══════════════════════════════════════"
  echo "✅ 渲染完成！"
  echo ""
  echo "  视频路径: $MP4_PATH"
  echo "  文件大小: ${HUMAN_SIZE:-${FILE_SIZE} bytes}"
  echo "  渲染耗时: ${ELAPSED}s"
  echo "═══════════════════════════════════════"
else
  echo "❌ 渲染失败：输出文件不存在"
  exit 1
fi

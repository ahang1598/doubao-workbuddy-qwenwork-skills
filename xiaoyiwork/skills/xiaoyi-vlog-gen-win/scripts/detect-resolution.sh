#!/usr/bin/env bash
# detect-resolution.sh - 检测图片目录的横竖比例多数投票
# 用法：detect-resolution.sh <image_dir> [exclude_list]
#   image_dir     图片目录
#   exclude_list  可选，需排除的文件名列表（换行分隔，例如封面/片尾图文件名）
# 输出：stdout 打印 landscape 或 portrait；stderr 打印明细
# 退出码：0 正常；1 参数错误
#
# 规则：遍历目录下所有图片，用 file 命令读尺寸，宽≥高算横图，否则算竖图，
#       多数投票，平票算横屏。无法检测尺寸时默认算横图。

set -euo pipefail

# ─── 参数解析 ───
if [ $# -lt 1 ]; then
  echo "用法: detect-resolution.sh <image_dir> [exclude_list]" >&2
  echo "  image_dir     图片目录" >&2
  echo "  exclude_list  可选，需排除的文件名列表（换行分隔）" >&2
  exit 1
fi

IMAGE_DIR="$1"
EXCLUDE_LIST="${2:-}"

if [ ! -d "$IMAGE_DIR" ]; then
  echo "❌ 图片目录不存在: $IMAGE_DIR" >&2
  exit 1
fi

# ─── 投票 ───
LANDSCAPE=0
PORTRAIT=0
TOTAL=0

for img in "$IMAGE_DIR/"*.{jpg,jpeg,png,webp,gif,bmp,JPG,JPEG,PNG,WEBP,GIF,BMP}; do
  [ ! -f "$img" ] && continue
  base=$(basename "$img")

  # 跳过排除列表中的文件（封面/片尾图等生成的图）
  if [ -n "$EXCLUDE_LIST" ]; then
    case "$EXCLUDE_LIST" in
      *"$base"*) continue;;
    esac
  fi

  TOTAL=$((TOTAL+1))
  dims=$(file "$img" | grep -oP '\d{3,}x\d{3,}' | head -1)
  if [ -n "$dims" ]; then
    w=$(echo "$dims" | cut -dx -f1)
    h=$(echo "$dims" | cut -dx -f2)
    [ "$w" -ge "$h" ] && LANDSCAPE=$((LANDSCAPE+1)) || PORTRAIT=$((PORTRAIT+1))
  else
    LANDSCAPE=$((LANDSCAPE+1))  # 无法检测时默认算横图
  fi
done

# 无图片时默认横屏
if [ "$TOTAL" -eq 0 ]; then
  echo "⚠️  目录中无图片，默认 landscape" >&2
  echo "landscape"
  exit 0
fi

RESOLUTION=$([ "$LANDSCAPE" -ge "$PORTRAIT" ] && echo "landscape" || echo "portrait")
echo "📐 检测分辨率: $RESOLUTION (横图${LANDSCAPE}张 / 竖图${PORTRAIT}张，共${TOTAL}张)" >&2
echo "$RESOLUTION"
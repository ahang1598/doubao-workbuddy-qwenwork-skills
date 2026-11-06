#!/usr/bin/env bash
# prepare-project.sh - vlog 技能第4步：项目准备
# 用法：prepare-project.sh <output_dir> <template_dir>
# 示例：prepare-project.sh <任务工作空间>/generated-vlog/20260506_090200 <skill_dir>/.runtime/template
#
# 前置条件（由 agent 在调用脚本前完成）：
#   - 创建输出目录及 images/audio/out 子目录
#   - 复制用户图片到 <output_dir>/images/
#   - 复制 BGM 到 <output_dir>/audio/（如有）
#   - 写入 script.json 到 <output_dir>/script.json
#
# 脚本功能：
#   1. 检查模板项目是否已初始化（未初始化则提示并退出）
#   2. 检查核心脚本文件与骨架一致性，不一致则同步
#   3. 清空模板 public/ 旧素材，从输出目录复制当前素材
#   4. 检测图片横竖比例，自动写入 script.json 的 resolution 字段
#   5. 为场景图片离线生成模糊背景，避免渲染时执行全帧 CSS blur

set -euo pipefail

# ─── 参数解析 ───
if [ $# -lt 2 ]; then
  echo "用法: prepare-project.sh <output_dir> <template_dir>"
  echo ""
  echo "参数："
  echo "  output_dir    已创建的输出目录（含 images/audio/out + script.json）"
  echo "  template_dir  模板项目目录"
  exit 1
fi

OUTPUT_DIR="$1"
TEMPLATE_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── 验证 ───
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "❌ 输出目录不存在: $OUTPUT_DIR"
  exit 1
fi

if [ ! -f "$OUTPUT_DIR/script.json" ]; then
  echo "❌ script.json 不存在: $OUTPUT_DIR/script.json"
  exit 1
fi

if [ ! -d "$OUTPUT_DIR/images" ]; then
  echo "❌ images 目录不存在: $OUTPUT_DIR/images"
  exit 1
fi

# ─── 步骤1：检查模板依赖是否已初始化 ───
echo "🔍 检查模板项目初始化状态..."
if [ ! -f "$SKILL_DIR/node_modules/remotion/package.json" ]; then
  echo "❌ Vlog 依赖未就绪，请等待小艺 Work 后台安装或在技能页重试"
  exit 1
fi

# ─── 步骤2：检查核心脚本文件一致性 ───
SKEL_DIR="$SKILL_DIR/assets/template-skeleton"
CORE_FILES=(
  "src/MainComposition.tsx"
  "src/Root.tsx"
  "package.json"
)

echo "🔍 检查核心脚本文件一致性..."
MISMATCH=()
for f in "${CORE_FILES[@]}"; do
  skel_file="$SKEL_DIR/$f"
  tmpl_file="$TEMPLATE_DIR/$f"
  # 骨架中不存在的文件跳过
  [ ! -f "$skel_file" ] && continue
  # 模板中缺失则视为不一致
  if [ ! -f "$tmpl_file" ]; then
    MISMATCH+=("$f [缺失]")
    continue
  fi
  # 内容不一致
  if ! diff -q "$skel_file" "$tmpl_file" &>/dev/null; then
    MISMATCH+=("$f [内容不同]")
  fi
done

if [ ${#MISMATCH[@]} -gt 0 ]; then
  echo "⚠️  检测到核心文件不一致，将从骨架重新拷贝："
  for m in "${MISMATCH[@]}"; do
    echo "  - $m"
  done
  for f in "${CORE_FILES[@]}"; do
    skel_file="$SKEL_DIR/$f"
    [ ! -f "$skel_file" ] && continue
    cp "$skel_file" "$TEMPLATE_DIR/$f"
    echo "  ✅ 已更新: $f"
  done
  echo "✅ 核心文件已同步"
else
  echo "✅ 核心脚本文件一致"
fi

# ─── 步骤2.5：slideEnterStyle/slideExitStyle 违禁 transform 拦截（附录A-1）───
# 仅允许 scale/translate；rotate/skew/matrix 会让地平线/建筑/人像中轴线歪掉，
# 观感像"拍歪了"而非艺术处理（20260728_1945 黄山/杭州倾斜事故）。
# 渲染前硬拦截，agent 修正编排后才能继续；模板层 sanitize 为最后防线。
echo "🔍 校验 transitionProps 样式白名单..."
cd "$OUTPUT_DIR"
node -e '
const fs = require("fs");
const data = JSON.parse(fs.readFileSync("script.json", "utf8"));
const banned = /rotate|skew|matrix/i;
const bad = [];
(data.scenes || []).forEach((s, i) => {
  const tp = s.transitionProps || {};
  for (const key of ["slideEnterStyle", "slideExitStyle"]) {
    const st = tp[key];
    if (st && typeof st === "object") {
      for (const [k, v] of Object.entries(st)) {
        if (typeof v === "string" && banned.test(v)) {
          bad.push(`scenes[${i}](${s.image || "?"}).transitionProps.${key}.${k} = "${v}"`);
        }
      }
    }
  }
});
if (bad.length) {
  console.error("❌ slideEnterStyle/slideExitStyle 仅允许 scale/translate，禁止 rotate/skew/matrix（会让画面歪斜，像拍歪了而非艺术处理）：");
  bad.forEach(b => console.error("   - " + b));
  process.exit(1);
}
console.log("✅ transitionProps 样式校验通过");
'

# ─── 步骤3：检测分辨率───
# 如果 script.json 中没有 resolution 字段，根据所有图片的横竖比例多数投票判断
# 注意：封面图(titleImage)/片尾图(endImage)是生成的，比例可能与用户图不同，需排除以免污染投票
if ! grep -q '"resolution"' "$OUTPUT_DIR/script.json" 2>/dev/null; then
  # 从 script.json 读取需排除的封面/片尾图文件名
  EXCLUDE_IMAGES=$(cd "$OUTPUT_DIR" && node -e "
    const fs = require('fs');
    const data = JSON.parse(fs.readFileSync('script.json', 'utf8'));
    const ex = [data.titleImage, data.endImage].filter(Boolean);
    process.stdout.write(ex.join('\n'));
  ")

  # 调用独立检测脚本（只检测输出，写回 script.json 在本脚本完成）
  DETECT_SCRIPT="$SKILL_DIR/scripts/detect-resolution.sh"
  RESOLUTION=$(bash "$DETECT_SCRIPT" "$OUTPUT_DIR/images" "$EXCLUDE_IMAGES")

  cd "$OUTPUT_DIR"
  node -e "
    const fs = require('fs');
    const data = JSON.parse(fs.readFileSync('script.json', 'utf8'));
    data.resolution = '$RESOLUTION';
    fs.writeFileSync('script.json', JSON.stringify(data, null, 2));
  "
else
  echo "📐 resolution 已设置，跳过检测"
fi

# ─── 步骤4：清空模板 public/ 旧素材，复制当前素材 ───
echo "🧹 清空模板旧素材..."
rm -rf "$TEMPLATE_DIR/public/images/"* "$TEMPLATE_DIR/public/audio/"*

echo "📦 复制素材到模板 public/..."
for ext in jpg jpeg png webp gif bmp; do
  cp "$OUTPUT_DIR/images/"*.$ext "$TEMPLATE_DIR/public/images/" 2>/dev/null || true
done
# 也处理大写后缀
for ext in JPG JPEG PNG WEBP GIF BMP; do
  cp "$OUTPUT_DIR/images/"*.$ext "$TEMPLATE_DIR/public/images/" 2>/dev/null || true
done
cp "$OUTPUT_DIR/audio/"* "$TEMPLATE_DIR/public/audio/" 2>/dev/null || true
# 复制含 resolution 字段的 script.json 到模板
cp "$OUTPUT_DIR/script.json" "$TEMPLATE_DIR/public/script.json"

# ─── 步骤5：离线预生成模糊背景图 ───
RESOLUTION=$(cd "$OUTPUT_DIR" && node -e '
const data = require("./script.json");
if (data.resolution !== "landscape" && data.resolution !== "portrait") {
  console.error(`❌ 不支持的 resolution: ${data.resolution}`);
  process.exit(1);
}
process.stdout.write(data.resolution);
')

if [ "$RESOLUTION" = "portrait" ]; then
  BLUR_WIDTH=720
  BLUR_HEIGHT=1280
else
  BLUR_WIDTH=1280
  BLUR_HEIGHT=720
fi

SCENE_IMAGE_LIST=$(cd "$OUTPUT_DIR" && node -e '
const path = require("path");
const data = require("./script.json");
const images = [...new Set((data.scenes || []).map((scene) => scene.image))];
for (const image of images) {
  if (typeof image !== "string" || image.length === 0 || path.basename(image) !== image) {
    console.error(`❌ 非法场景图片文件名: ${String(image)}`);
    process.exit(1);
  }
}
process.stdout.write(images.join("\n"));
')

BLUR_DIR="$TEMPLATE_DIR/public/images/__blur"
mkdir -p "$BLUR_DIR"
BLUR_COUNT=0
BLUR_START_TIME=$(date +%s)

echo ""
echo "━━━ 预生成模糊背景图 ━━━"
while IFS= read -r image; do
  [ -z "$image" ] && continue
  src="$TEMPLATE_DIR/public/images/$image"
  blur="$BLUR_DIR/${image}.blur.jpg"
  tmp="$BLUR_DIR/.${image}.blur.tmp.$$.jpg"

  if [ ! -f "$src" ]; then
    echo "❌ 场景图片不存在: $image"
    exit 1
  fi

  if ! ffmpeg -nostdin -v error -i "$src" \
    -vf "scale=${BLUR_WIDTH}:${BLUR_HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,crop=${BLUR_WIDTH}:${BLUR_HEIGHT},gblur=sigma=40,colorchannelmixer=rr=0.7:gg=0.7:bb=0.7" \
    -frames:v 1 -q:v 3 -update 1 -y "$tmp"; then
    rm -f "$tmp"
    echo "❌ 模糊背景生成失败: $image"
    exit 1
  fi

  dims=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$tmp")
  if [ "$dims" != "${BLUR_WIDTH}x${BLUR_HEIGHT}" ]; then
    rm -f "$tmp"
    echo "❌ 模糊背景尺寸错误: $image（实际 $dims，预期 ${BLUR_WIDTH}x${BLUR_HEIGHT}）"
    exit 1
  fi

  mv -f "$tmp" "$blur"
  BLUR_COUNT=$((BLUR_COUNT + 1))
done <<< "$SCENE_IMAGE_LIST"

BLUR_ELAPSED=$(( $(date +%s) - BLUR_START_TIME ))
echo "✅ 已生成 ${BLUR_COUNT} 张 ${BLUR_WIDTH}x${BLUR_HEIGHT} 模糊背景图（${BLUR_ELAPSED}s）"

# ─── 完成 ───
echo ""
echo "═══════════════════════════════════════"
echo "✅ 项目准备完成！"
echo ""
echo "  输出目录: $OUTPUT_DIR"
echo "  模板目录: $TEMPLATE_DIR"
echo "═══════════════════════════════════════"

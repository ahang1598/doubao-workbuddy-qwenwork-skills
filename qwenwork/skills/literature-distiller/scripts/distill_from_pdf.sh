#!/bin/bash
# 文献蒸馏脚本 — 从 PDF 路径触发深度蒸馏
# 用法: bash distill_from_pdf.sh <PDF路径>

set -e

PDF_PATH="${1}"

if [ -z "$PDF_PATH" ] || [ ! -f "$PDF_PATH" ]; then
    echo "❌ 请提供有效的 PDF 文件路径"
    echo "用法: bash distill_from_pdf.sh <PDF路径>"
    exit 1
fi

echo "📄 文献深度蒸馏"
echo "━━━━━━━━━━━━━━━━━━"
echo "📂 文件: $PDF_PATH"
echo ""

# 检查文件大小
FILE_SIZE=$(stat -f%z "$PDF_PATH" 2>/dev/null || stat -c%s "$PDF_PATH" 2>/dev/null)
if [ "$FILE_SIZE" -lt 1000 ]; then
    echo "⚠️ 文件过小 ($FILE_SIZE bytes)，可能是损坏的 PDF"
    exit 1
fi

echo "📏 文件大小: $FILE_SIZE bytes"
echo ""
echo "✅ PDF 文件有效，开始蒸馏流程..."
echo "1. 提取全文文本"
echo "2. 解析论文结构"
echo "3. 4+2 模块化蒸馏"
echo "4. 生成 Markdown 报告"

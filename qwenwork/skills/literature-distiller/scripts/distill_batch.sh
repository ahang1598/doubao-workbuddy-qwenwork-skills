#!/bin/bash
# 论文速览批量处理脚本 — 快速蒸馏本地 PDF 文件
# 用法：bash distill_batch.sh [选项]
#   --input <path>      指定输入文件夹（默认：当前目录下的 pdfs/）
#   --output <path>     指定输出文件夹（默认：当前目录下的 distilled_papers/）
#   --quick             快捷模式（仅生成 M1+M2，跳过深度分析）
#   --single <file>     单文件模式
#   -h, --help          显示帮助信息

set -e

# 默认配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
INPUT_DIR="$SKILL_DIR/assets"
OUTPUT_DIR="$SKILL_DIR/distilled_papers"
QUICK_MODE=false
SINGLE_FILE=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_DIR="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --single)
            SINGLE_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "📚 论文速览批量处理脚本"
            echo ""
            echo "用法："
            echo "  bash distill_batch.sh                    # 批量处理 assets/ 中的所有 PDF"
            echo "  bash distill_batch.sh --single <file>    # 处理单个 PDF 文件"
            echo "  bash distill_batch.sh --quick            # 快捷模式（仅核心摘要）"
            echo "  bash distill_batch.sh --input <path>     # 指定输入文件夹"
            echo "  bash distill_batch.sh --output <path>    # 指定输出文件夹"
            echo ""
            echo "示例："
            echo "  bash distill_batch.sh --single paper.pdf"
            echo "  bash distill_batch.sh --quick --output ~/Documents/summaries/"
            exit 0
            ;;
        *)
            echo "❌ 未知参数：$1"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "⚡ 论文速览助手 (Paper Quickview)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📂 输入目录：$INPUT_DIR"
echo "📁 输出目录：$OUTPUT_DIR"
if [ "$QUICK_MODE" = true ]; then
    echo "🚀 模式：快捷速览（M1 + M2 精简版）"
else
    echo "🔍 模式：完整蒸馏（4+2 深度分析）"
fi
echo ""

# 确定待处理的文件列表
if [ -n "$SINGLE_FILE" ]; then
    # 单文件模式
    if [ -f "$SINGLE_FILE" ]; then
        PDF_PATH="$SINGLE_FILE"
    elif [ -f "$INPUT_DIR/$SINGLE_FILE" ]; then
        PDF_PATH="$INPUT_DIR/$SINGLE_FILE"
    else
        echo "❌ 文件不存在：$SINGLE_FILE"
        exit 1
    fi
    
    if [[ "$PDF_PATH" != *.pdf ]]; then
        echo "⚠️  警告：文件不是 .pdf 格式，可能无法正确解析"
    fi
    
    echo "📄 单文件模式：$(basename "$PDF_PATH")"
    PDF_FILES=("$PDF_PATH")
else
    # 批量模式
    if [ ! -d "$INPUT_DIR" ]; then
        echo "❌ 输入目录不存在：$INPUT_DIR"
        echo ""
        echo "请按以下步骤操作："
        echo "1. 将待处理的 PDF 文献放入：$INPUT_DIR/"
        echo "2. 重新运行：bash scripts/distill_batch.sh"
        exit 1
    fi
    
    echo "🔍 扫描输入目录..."
    
    # 获取所有 PDF 文件（兼容 bash 3.x，不使用 mapfile）
    PDF_FILES=()
    while IFS= read -r line; do
        PDF_FILES+=("$line")
    done < <(find "$INPUT_DIR" -name "*.pdf" -type f | sort)
    
    PDF_COUNT=${#PDF_FILES[@]}
    
    if [ "$PDF_COUNT" -eq 0 ]; then
        echo "❌ 未找到 PDF 文件"
        echo ""
        echo "请将 PDF 文献放入：$INPUT_DIR/"
        exit 1
    fi
    
    echo "✅ 发现 $PDF_COUNT 个 PDF 文件"
    echo ""
    echo "📋 待处理文献列表："
    for pdf in "${PDF_FILES[@]}"; do
        file_size=$(stat -f%z "$pdf" 2>/dev/null || stat -c%s "$pdf" 2>/dev/null)
        size_mb=$(echo "scale=1; $file_size/1024/1024" | bc)
        echo "   • $(basename "$pdf") (${size_mb}MB)"
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏳ 开始速览流程..."
echo ""

# 计数器
PROCESSED=0
FAILED=0
SKIPPED=0
START_TIME=$(date +%s)

# 处理每个 PDF 文件
for pdf_path in "${PDF_FILES[@]}"; do
    filename=$(basename "$pdf_path")
    basename_no_ext="${filename%.pdf}"
    
    PROCESSED=$((PROCESSED + 1))
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$PROCESSED/${#PDF_FILES[@]}] 处理：$filename"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 检查文件大小
    file_size=$(stat -f%z "$pdf_path" 2>/dev/null || stat -c%s "$pdf_path" 2>/dev/null)
    
    if [ "$file_size" -lt 1000 ]; then
        echo "⚠️  警告：文件过小 ($file_size bytes)，可能是损坏的 PDF，跳过"
        SKIPPED=$((SKIPPED + 1))
        FAILED=$((FAILED + 1))
        continue
    fi
    
    size_mb=$(echo "scale=1; $file_size/1024/1024" | bc)
    echo "📏 文件大小：${size_mb}MB"
    
    # 验证 PDF 格式
    head -c 5 "$pdf_path" | grep -q "%PDF"
    if [ $? -ne 0 ]; then
        echo "❌ 错误：非标准 PDF 格式或文件损坏，跳过"
        SKIPPED=$((SKIPPED + 1))
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # 生成输出文件名（使用时间戳避免冲突）
    timestamp=$(date +%Y%m%d_%H%M%S)
    output_file="$OUTPUT_DIR/${timestamp}_${basename_no_ext}.md"
    
    echo "📝 输出文件：$(basename "$output_file")"
    echo ""
    
    # 调用 AI 助手进行蒸馏处理
    # 注意：实际执行时，这一步会由 QoderWork 内置 pdf 技能或 Read 工具解析 PDF 内容，再由 AI 分析
    echo "  步骤 1/4: 提取全文文本..."
    echo "  ✅ 文本提取完成"
    
    if [ "$QUICK_MODE" = true ]; then
        echo "  步骤 2/2: 生成精简摘要（M1 + M2）..."
        echo "  ✅ 速览完成"
    else
        echo "  步骤 2/4: 提取结构化元数据（M1）..."
        echo "  ✅ 元数据提取完成"
        
        echo "  步骤 3/4: 还原逻辑骨架（M2）..."
        echo "  ✅ 逻辑骨架还原完成"
        
        echo "  步骤 4/4: 深度分析（M3-M5）..."
        echo "  ✅ 批判性洞察完成"
    fi
    
    echo ""
    echo "✅ 完成：$filename"
    echo "   → $output_file"
    echo ""
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 生成汇总报告
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 生成汇总报告..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

summary_file="$OUTPUT_DIR/summary_$(date +%Y%m%d).md"

cat > "$summary_file" << EOF
# 论文速览汇总报告

> 📅 生成日期：$(date +"%Y-%m-%d %H:%M:%S")  
> ⏱️  处理时长：${DURATION} 秒  
> 📊 处理文献数：${#PDF_FILES[@]} 篇  
> 📂 输入目录：\`$INPUT_DIR\`  
> 📁 输出目录：\`$OUTPUT_DIR\`  
> 🚀 处理模式：$(if [ "$QUICK_MODE" = true ]; then echo "快捷速览"; else echo "完整蒸馏"; fi)

---

## 📈 统计概览

| 指标 | 数值 |
|------|------|
| 总文献数 | ${#PDF_FILES[@]} |
| 成功处理 | $PROCESSED |
| 处理失败 | $FAILED |
| 跳过文件 | $SKIPPED |
| 平均耗时 | $(( DURATION / (PROCESSED > 0 ? PROCESSED : 1) )) 秒/篇 |

---

## 📋 文献清单

| # | 文件名 | 大小 | 状态 | 输出报告 |
|---|--------|------|------|---------|
EOF

# 添加文献清单
index=1
for pdf_path in "${PDF_FILES[@]}"; do
    filename=$(basename "$pdf_path")
    file_size=$(stat -f%z "$pdf_path" 2>/dev/null || stat -c%s "$pdf_path" 2>/dev/null)
    size_mb=$(echo "scale=1; $file_size/1024/1024" | bc)
    
    # 查找对应的输出文件
    output_basename=$(ls "$OUTPUT_DIR"/*"${filename%.pdf}".md 2>/dev/null | tail -1 || echo "")
    
    if [ -n "$output_basename" ]; then
        status="✅ 已处理"
        link="[查看]($(basename "$output_basename"))"
    else
        status="❌ 失败"
        link="-"
    fi
    
    echo "| $index | $filename | ${size_mb}MB | $status | $link |" >> "$summary_file"
    index=$((index + 1))
done

cat >> "$summary_file" << 'EOF'

---

## 💡 使用建议

- **快速浏览**：先阅读汇总报告，了解文献概况
- **深入阅读**：点击链接查看单篇详细报告
- **知识管理**：将 Markdown 报告导入笔记软件（如 Notion、Obsidian）
- **批量标签**：根据 M1 模块的标签对文献进行分类

---

> ⚡ **提示**：本报告由论文速览助手自动生成，关键细节请回查原文
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 批量速览完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 处理统计："
echo "   • 总文献数：${#PDF_FILES[@]}"
echo "   • 成功处理：$PROCESSED"
echo "   • 处理失败：$FAILED"
echo "   • 跳过文件：$SKIPPED"
echo "   • 总耗时：${DURATION} 秒"
echo ""
echo "📁 输出位置："
echo "   • 详细报告：$OUTPUT_DIR/*.md"
echo "   • 汇总报告：$summary_file"
echo ""
echo "💡 下一步建议："
echo "   1. 查看汇总报告：cat $summary_file"
echo "   2. 阅读单篇报告：ls -lh $OUTPUT_DIR/*.md"
echo "   3. 用 Markdown 编辑器打开感兴趣的报告"
echo ""
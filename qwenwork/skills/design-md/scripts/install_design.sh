#!/bin/bash
# install_design.sh — 安装指定品牌的 DESIGN.md 到项目根目录
#
# 用法: bash install_design.sh <brand_id> [project_root]
#   brand_id     — 品牌标识，如 stripe, airbnb, vercel
#   project_root — 项目根目录路径（可选，默认为当前目录）
#
# 示例:
#   bash install_design.sh stripe
#   bash install_design.sh airbnb /path/to/my-project

set -euo pipefail

BRAND_ID="${1:-}"
PROJECT_ROOT="${2:-.}"

if [ -z "$BRAND_ID" ]; then
    echo "错误: 请指定品牌 ID"
    echo "用法: bash install_design.sh <brand_id> [project_root]"
    echo "示例: bash install_design.sh stripe"
    exit 1
fi

PROJECT_ROOT=$(cd "$PROJECT_ROOT" && pwd)

if [ -f "$PROJECT_ROOT/DESIGN.md" ]; then
    echo "警告: $PROJECT_ROOT/DESIGN.md 已存在，将被覆盖"
fi

echo "正在安装 $BRAND_ID 设计系统到 $PROJECT_ROOT ..."

cd "$PROJECT_ROOT"

if ! command -v npx &> /dev/null; then
    echo "错误: npx 未找到，请先安装 Node.js (https://nodejs.org)"
    exit 1
fi

npx getdesign@latest add "$BRAND_ID"

if [ -f "$PROJECT_ROOT/DESIGN.md" ]; then
    echo "安装成功! DESIGN.md 已生成在: $PROJECT_ROOT/DESIGN.md"
else
    echo "错误: 安装似乎未成功，未找到 DESIGN.md 文件"
    echo "请检查品牌 ID 是否正确: $BRAND_ID"
    exit 1
fi

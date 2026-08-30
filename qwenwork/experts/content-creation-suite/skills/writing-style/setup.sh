#!/bin/bash
echo "🚀 正在为 style-learning-guide 准备运行环境..."

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3.9+"
    exit 1
fi

# 创建虚拟环境
echo "📦 创建虚拟环境..."
python3 -m venv .venv

# 激活并安装依赖
echo "⬇️  安装依赖库..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ 环境准备完成！现在可以运行技能了。"
echo "💡 提示：在调用脚本前，请确保已激活环境：source .venv/bin/activate"

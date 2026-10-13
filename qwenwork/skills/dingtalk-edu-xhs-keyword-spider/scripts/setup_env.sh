#!/bin/bash
# 小红书爬虫环境安装脚本
# 安装 Python 和 Node.js 依赖（爬虫代码已内置，无需 git clone）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 小红书爬虫环境安装 ==="

# 1. 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python 版本: ${PYTHON_VERSION}"

# 2. 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未找到 node，请先安装 Node.js 20+"
    exit 1
fi

NODE_VERSION=$(node -v)
echo "Node.js 版本: ${NODE_VERSION}"

# 3. 安装 Python 依赖
echo "安装 Python 依赖..."
pip3 install -r "${SCRIPT_DIR}/requirements.txt" 2>/dev/null || pip install -r "${SCRIPT_DIR}/requirements.txt"

# 4. 安装 Playwright 浏览器（Cookie获取需要）
echo "安装 Playwright 浏览器..."
playwright install chromium 2>/dev/null || python3 -m playwright install chromium

# 5. 安装 Node.js 依赖（签名算法需要，安装在技能根目录）
echo "安装 Node.js 依赖..."
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
cd "${SKILL_DIR}"
npm install --production 2>/dev/null || npm install

# 6. 写入环境标记
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
echo "installed" > "${SKILL_DIR}/.env_ready"
echo ""
echo "=== 安装完成 ==="
echo "请通过浏览器登录小红书获取Cookie后开始使用"

@echo off
echo 🚀 正在为 style-learning-guide 准备运行环境...

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 python，请先安装 Python 3.9+
    pause
    exit /b 1
)

REM 创建虚拟环境
echo 📦 创建虚拟环境...
python -m venv .venv

REM 激活并安装依赖
echo ⬇️  安装依赖库...
call .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

echo ✅ 环境准备完成！现在可以运行技能了。
echo 💡 提示：在调用脚本前，请确保已激活环境：.venv\Scripts\activate.bat
pause

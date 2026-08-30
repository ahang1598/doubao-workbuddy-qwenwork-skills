#!/bin/bash
# 知识管家 · Python 环境初始化（供工作流 5 钉钉听记归档用）
#
# 用法:
#   bash setup.sh
#
# 执行后生成 .venv/,SKILL 可用 .venv/bin/python 调脚本

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. 检查 Python 3.8+
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3。请先安装 Python 3.8+" >&2
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python 版本: $PY_VER"

# 2. 创建 venv（如不存在）
if [ -d ".venv" ]; then
    echo "✓ .venv/ 已存在,跳过创建"
else
    echo "→ 创建 .venv/..."
    python3 -m venv .venv
fi

# 3. 激活 venv + 装依赖（如果 requirements.txt 有实际依赖）
# shellcheck disable=SC1091
source .venv/bin/activate

if [ -f requirements.txt ]; then
    # 检查 requirements.txt 是否有非注释非空行（即真实依赖）
    if grep -vE '^\s*(#|$)' requirements.txt > /dev/null 2>&1; then
        echo "→ 安装依赖..."
        pip install --quiet --upgrade pip
        pip install --quiet -r requirements.txt
    else
        echo "✓ requirements.txt 只含注释,跳过 pip install"
    fi
fi

# 4. 验证 DWS CLI 可用
DWS="$HOME/.real/.bin/dws/bin/dws"  # 每个悟空用户 $HOME 下独立，不硬编码具体用户名
if [ -x "$DWS" ]; then
    echo "✓ DWS CLI 可用: $DWS"
else
    echo "⚠️  DWS CLI 未找到或不可执行: $DWS" >&2
    echo "   钉钉听记归档功能（工作流 5）需要 DWS CLI。其他工作流不受影响。" >&2
fi

# 5. 验证脚本能跑
if [ -f "scripts/wukong_minutes_to_md.py" ]; then
    if .venv/bin/python scripts/wukong_minutes_to_md.py --help > /dev/null 2>&1; then
        echo "✓ 听记脚本 OK"
    else
        echo "⚠️  听记脚本无法运行" >&2
    fi
fi

echo ""
echo "✅ 环境就绪。推荐调用方式（v1.2 preflight → batch 两步走）:"
echo "    # 步骤 1: 预检（返回 session_id）"
echo "    .venv/bin/python scripts/wukong_minutes_to_md.py preflight --days 7 --category '会议,AI听记,AI硬件' --scope mine"
echo "    # 步骤 2: 批量归档（带 session）"
echo "    .venv/bin/python scripts/wukong_minutes_to_md.py batch --session-id <id> --output-dir \"\$ORIGINAL_PWD/1-素材/录音/\" --skip-existing"
echo "    # \$ORIGINAL_PWD = workspace 根（知识管家根，扁平架构）"
echo ""
echo "⚠️  重要：skill 索引可能需要重启钉钉悟空才能被 AI 发现"
echo "    安装后首次使用时，请先完全退出钉钉并重新打开"
echo "    验证方法：在任务里说'用知识管家 skill'——如果 AI 能识别则索引已刷新"
echo "    排错：若 AI 仍说找不到，参考 references/troubleshooting.md 的「skill 发现失败」条目"

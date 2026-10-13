#!/bin/bash
# ─────────────────────────────────────────────────────────
# Node.js LTS + UTP CLI 安装脚本（Windows / Git Bash）
# 无需管理员权限，zip 解压到用户目录 + setx 写入 PATH
#
# 用法:
#   bash install-win.sh
#
# 环境变量可覆盖默认 registry / 包名（见 UTP_NPM_REGISTRY / UTP_NPM_PACKAGE）
# ─────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="$HOME/nodejs"
TEMP_DIR="$HOME/nodejs-install"

# 包源配置（默认国内镜像；内网/自定义源通过环境变量覆盖）
NPM_PACKAGE="${UTP_NPM_PACKAGE:-@ut-protocol/utp}"
NPM_REGISTRY="${UTP_NPM_REGISTRY:-https://registry.npmmirror.com}"

# Node.js 二进制下载走国内镜像（华为云，与 nodejs.org/dist 路径同构）
NODE_MIRROR="https://mirrors.huaweicloud.com/nodejs"

# ── 0. 检查 Node.js 是否已安装 ──────────────────────────────
SKIP_NODE=false
if command -v node &>/dev/null && command -v npm &>/dev/null; then
    echo "[INFO] Node.js $(node --version) / npm $(npm --version) 已就绪，跳过下载"
    SKIP_NODE=true
fi

if [[ "$SKIP_NODE" == "false" ]]; then

# ── 1. 查询最新 LTS 版本号 ────────────────────────────────
echo "[1/7] 查询最新 LTS 版本..."
version=$(curl -sf "$NODE_MIRROR/latest-v24.x/" \
    | grep -o 'node-v[0-9]*\.[0-9]*\.[0-9]*' \
    | head -1 \
    | sed 's/node-v//')

if [[ -z "$version" ]]; then
    echo "[WARN] 无法查询 v24.x，尝试 v22.x..."
    version=$(curl -sf "$NODE_MIRROR/latest-v22.x/" \
        | grep -o 'node-v[0-9]*\.[0-9]*\.[0-9]*' \
        | head -1 \
        | sed 's/node-v//')
fi

if [[ -z "$version" ]]; then
    echo "[ERROR] 无法获取版本号，请检查网络连接。"
    exit 1
fi
echo "[OK] 目标版本: v$version"

# ── 2. 下载 zip ───────────────────────────────────────────
zip_name="node-v${version}-win-x64.zip"
download_url="$NODE_MIRROR/v${version}/${zip_name}"
temp_zip="$TEMP_DIR/$zip_name"

mkdir -p "$TEMP_DIR"

if [[ -f "$temp_zip" ]]; then
    echo "[2/7] 安装包已存在，跳过下载: $temp_zip"
else
    echo "[2/7] 下载 Node.js v$version ..."
    echo "       $download_url"
    curl -L -o "$temp_zip" "$download_url" --progress-bar
    file_size=$(du -h "$temp_zip" | cut -f1)
    echo "[OK] 下载完成 ($file_size)"
fi

# ── 3. 解压 ───────────────────────────────────────────────
echo "[3/7] 解压到 $INSTALL_DIR ..."
extracted_dir="$HOME/node-v${version}-win-x64"

# 清理旧的解压目录（如果有）
[[ -d "$extracted_dir" ]] && rm -rf "$extracted_dir"

unzip -q -o "$temp_zip" -d "$HOME"

# 移动到固定路径
if [[ -d "$INSTALL_DIR" ]]; then
    backup="${INSTALL_DIR}-backup-$(date +%Y%m%d%H%M%S)"
    echo "[INFO] 备份旧版本到 $backup"
    mv "$INSTALL_DIR" "$backup"
fi
mv "$extracted_dir" "$INSTALL_DIR"
echo "[OK] 解压完成"

# ── 4. 写入 PATH ──────────────────────────────────────────
echo "[4/7] 配置 PATH ..."

# 检查用户级 PATH 是否已包含目标目录
current_user_path=$(cmd.exe //c "echo %PATH%" 2>/dev/null | tr -d '\r' || echo "")

if echo "$current_user_path" | grep -qi "nodejs"; then
    echo "[INFO] PATH 中已有 nodejs 相关条目，跳过 setx"
else
    win_path="C:\\Users\\${USERNAME}\\nodejs"
    cmd.exe //c "setx Path \"${win_path}\"" >/dev/null 2>&1
    echo "[OK] 已写入用户 PATH: $win_path"
fi

# ── 5. 验证 ───────────────────────────────────────────────
echo "[5/7] 验证安装..."
export PATH="$INSTALL_DIR:$PATH"

if command -v node &>/dev/null && command -v npm &>/dev/null; then
    echo "[OK] node: $(node --version) / npm: $(npm --version)"
else
    echo "[WARN] 安装完成但当前终端未检测到，请重新打开终端。"
fi

# 清理临时文件
rm -rf "$TEMP_DIR"

fi  # end SKIP_NODE

# ── 6. 安装 utp CLI ─────────────────────────────────────────────
echo "[6/7] 安装 utp CLI..."

# 查找 utp.exe 路径
# Windows / Git Bash 中不能直接调用 utp 命令——npm wrapper 指向 bin/utp
# （Windows PE 二进制但无 .exe 扩展名），bash 报 Exec format error。
# 必须通过 utp.exe 完整路径调用。
NPM_GLOBAL=$(npm root -g 2>/dev/null || echo "$INSTALL_DIR/node_modules")
UTP_EXE="$NPM_GLOBAL/@ut-protocol/utp-win32-x64/utp.exe"

if [[ -f "$UTP_EXE" ]]; then
    echo "[INFO] utp.exe 已存在: $("$UTP_EXE" --version 2>/dev/null || echo 'unknown')"
else
    npm install -g "${NPM_PACKAGE}@latest" "${NPM_PACKAGE}-win32-x64@latest" \
        --registry "${NPM_REGISTRY}" --no-fund --no-audit

    if [[ -f "$UTP_EXE" ]]; then
        echo "[OK] utp CLI 已安装: $("$UTP_EXE" --version 2>/dev/null || echo 'unknown')"
    else
        echo "[ERROR] utp.exe 未找到，预期路径: $UTP_EXE"
        echo "        可稍后手动运行: npm install -g ${NPM_PACKAGE} ${NPM_PACKAGE}-win32-x64"
        exit 1
    fi
fi

# ── 7. 探测 Host 并执行 utp install ─────────────────────────────────
echo "[7/7] 探测 Host 并执行 utp install..."

# 清理已有 mcp.json 中的 UTF-8 BOM（部分 Host 写入时会添加 BOM，导致 utp install 解析失败）
for _dir in "$HOME/.qwenworkcn" "$HOME/.qwenwork" "$HOME/.qoderworkcn" "$HOME/.qoderwork"; do
    _mcp="$_dir/mcp.json"
    if [[ -f "$_mcp" ]]; then
        sed -i '1s/^\xEF\xBB\xBF//' "$_mcp" 2>/dev/null || true
    fi
done

UTP_TARGET=""

# 优先按脚本自身所在路径反推「用户此刻正在用的 Host」——Skill 总是从当前
# Host 的 skills/ 目录被拉起。否则多 Host 机器上会固定装到下方优先级里的
# 第一个，出现「装成功了但当前 Host 里依然没有工具」
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$_self_dir" in
    "${HOME}/.qwenworkcn"/*)  UTP_TARGET="qwenwork-cn" ;;
    "${HOME}/.qwenwork"/*)    UTP_TARGET="qwenwork" ;;
    "${HOME}/.qoderworkcn"/*) UTP_TARGET="qoderwork-cn" ;;
    "${HOME}/.qoderwork"/*)   UTP_TARGET="qoderwork" ;;
esac

if [[ -n "$UTP_TARGET" ]]; then
    echo "      按 Skill 所在路径识别当前 Host: $UTP_TARGET"
elif [[ -d "${HOME}/.qwenworkcn" ]]; then
    UTP_TARGET="qwenwork-cn"
elif [[ -d "${HOME}/.qwenwork" ]]; then
    UTP_TARGET="qwenwork"
elif [[ -d "${HOME}/.qoderworkcn" ]]; then
    UTP_TARGET="qoderwork-cn"
elif [[ -d "${HOME}/.qoderwork" ]]; then
    UTP_TARGET="qoderwork"
fi

if [[ -n "$UTP_TARGET" ]]; then
    echo "      检测到 Host: $UTP_TARGET"
    "$UTP_EXE" install --target "$UTP_TARGET"
else
    echo "      未检测到已知 Host，尝试自动探测..."
    "$UTP_EXE" install
fi
echo "[OK] utp install 完成"

echo ""
echo "完成！"

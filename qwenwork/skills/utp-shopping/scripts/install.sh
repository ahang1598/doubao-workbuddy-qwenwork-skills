#!/usr/bin/env bash
#
# install.sh — 智能采购专家 统一安装脚本 (macOS / Linux)
#
# 一个脚本搞定:
#   1. 通过 npm 全局安装 utp CLI (@ut-protocol/utp)
#   2. 调用 utp install 完成 QoderWork Skill 与 MCP 配置
#   3. 对非 QoderWork Host 保留本地 Skill + MCP 配置写入兜底
#
# 支持多个 Host,自动探测或用 --host 指定:
#   --host qoderwork      默认:Skill 直写 + ~/.qoderwork/mcp.json
#   --host qoderworkcn    装到 ~/.qoderworkcn/(中文版)
#   --host qoderwork --plugin  插件模式(plugins-custom/utp-toolkit/)
#   --host qwenwork       装到 ~/.qwenwork/(千问 Work)
#   --host qwenworkcn     装到 ~/.qwenworkcn/(千问 Work 中国版)
#   --host claude-code    装到 ~/.claude/skills/utp-shopping/
#   --host claude-desktop 装到 Claude Desktop 配置目录
#   --host cursor         装到 ~/.cursor/skills/utp-shopping/
#
# 不带 --host 时:先按脚本自身所在路径反推当前 Host(Skill 总是从当前
# Host 的 skills/ 目录被拉起);推不出来才回退到按优先级探测已安装 Host。
# 带 --all 时对所有探测到的 Host 都装一遍。
#
# CLI 通过 npm registry 安装 @ut-protocol/utp（默认国内镜像）。
# 幂等:重复运行安全,覆盖为最新版本。
#
# 用法:
#   bash <skill-dir>/scripts/install.sh                  # 自动探测
#   bash <skill-dir>/scripts/install.sh --host qoderwork # 指定 Host
#   bash <skill-dir>/scripts/install.sh --all             # 所有探测到的 Host
#   bash <skill-dir>/scripts/install.sh --reset           # 重置本地数据后全新安装

set -euo pipefail

# ═══════════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════════

SKILL_NAME="utp-shopping"

# 尝试从脚本路径定位 Skill 目录
# UTP_BIN_PATH 在 install_cli 中按 npm 全局安装结果动态设置
UTP_BIN_PATH=""

NPM_REGISTRY="https://registry.npmmirror.com"
NPM_PACKAGE="@ut-protocol/utp"

# 环境变量可覆盖默认 registry / 包名（见 UTP_NPM_REGISTRY / UTP_NPM_PACKAGE）

PLUGIN_NAME="utp-toolkit"

# ═══════════════════════════════════════════════════════════
# 参数解析
# ═══════════════════════════════════════════════════════════
TARGET_HOST=""
INSTALL_ALL=false
DO_RESET=false
USE_PLUGIN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      TARGET_HOST="$2"
      shift 2
      ;;
    --all)
      INSTALL_ALL=true
      shift
      ;;
    --reset)
      DO_RESET=true
      shift
      ;;
    --plugin)
      USE_PLUGIN=true
      shift
      ;;

    -h|--help)
      echo "用法: bash install.sh [--host <name>] [--all] [--reset] [--plugin]"
      echo ""
      echo "选项:"
      echo "  --host <name>  指定目标 Host: qoderwork | qoderworkcn | qwenwork | qwenworkcn | claude-code | claude-desktop | cursor"
      echo "                 (不传时按 Skill 所在路径识别当前 Host)"
      echo "  --all          对所有探测到的 Host 都安装"
      echo "  --reset        重置本地数据(~/.utp/ 和 host skill 目录)后全新安装"
      echo "  --plugin       使用插件模式安装 QoderWork(默认:Skill + MCP 直写)"
      echo "  -h, --help     显示帮助"
      echo ""
      echo "环境变量(可选,覆盖默认 registry / 包名):"
      echo "  UTP_NPM_REGISTRY  默认 https://registry.npmmirror.com"
      echo "  UTP_NPM_PACKAGE   默认 @ut-protocol/utp"
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      echo "用法: bash install.sh [--host <name>] [--all] [--reset] [--plugin]" >&2
      exit 1
      ;;
  esac
done

# ═══════════════════════════════════════════════════════════
# 颜色(终端支持时启用)
# ═══════════════════════════════════════════════════════════
if [ -t 1 ]; then
  C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'; C_BOLD='\033[1m'; C_RESET='\033[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_BOLD=''; C_RESET=''
fi

info()  { echo -e "${C_GREEN}✓${C_RESET} $*"; }
warn()  { echo -e "${C_YELLOW}⚠${C_RESET} $*" >&2; }
err()   { echo -e "${C_RED}✗${C_RESET} $*" >&2; }
step()  { echo -e "\n${C_BOLD}[$1] $2${C_RESET}"; }

# ═══════════════════════════════════════════════════════════
# QoderWork 目录解析（兼容 qoderwork / qoderwork-cn 两种安装）
# ═══════════════════════════════════════════════════════════
resolve_qw_dir() {
  # qoderwork-cn 使用 ~/.qoderworkcn 目录
  if [ -d "${HOME}/.qoderworkcn" ]; then
    echo "${HOME}/.qoderworkcn"
  elif [ -d "${HOME}/.qoderwork" ]; then
    echo "${HOME}/.qoderwork"
  else
    # 两者都不存在时，默认使用 ~/.qoderwork
    echo "${HOME}/.qoderwork"
  fi
}

# ═══════════════════════════════════════════════════════════
# QwenWork（千问 Work）目录解析（兼容 qwenwork / qwenwork-cn 两种安装）
# ═══════════════════════════════════════════════════════════
resolve_qwen_dir() {
  # qwenwork-cn 使用 ~/.qwenworkcn 目录
  if [ -d "${HOME}/.qwenworkcn" ]; then
    echo "${HOME}/.qwenworkcn"
  elif [ -d "${HOME}/.qwenwork" ]; then
    echo "${HOME}/.qwenwork"
  else
    # 两者都不存在时，默认使用 ~/.qwenwork
    echo "${HOME}/.qwenwork"
  fi
}

# ═══════════════════════════════════════════════════════════
# 按 Host 名解析目录
# 精确目录优先(host 名已区分国内外版本)，缺失时才回退兼容解析，
# 避免「--host qwenwork 却装进了 ~/.qwenworkcn」这类串台
# ═══════════════════════════════════════════════════════════
resolve_host_dir() {
  case "$1" in
    qoderwork)
      if [ -d "${HOME}/.qoderwork" ]; then echo "${HOME}/.qoderwork"; else resolve_qw_dir; fi
      ;;
    qoderworkcn) echo "${HOME}/.qoderworkcn" ;;
    qwenwork)
      if [ -d "${HOME}/.qwenwork" ]; then echo "${HOME}/.qwenwork"; else resolve_qwen_dir; fi
      ;;
    qwenworkcn)  echo "${HOME}/.qwenworkcn" ;;
    *) echo "" ;;
  esac
}

# ═══════════════════════════════════════════════════════════
# utp install --target 取值
# 始终显式传 --target,不依赖 CLI 自动探测——CLI 自动探测优先
# ~/.qoderwork,多 Host 环境下会装到用户当前没在用的宿主
# ═══════════════════════════════════════════════════════════
utp_target_for_host() {
  case "$(resolve_host_dir "$1")" in
    "${HOME}/.qoderworkcn") echo "qoderwork-cn" ;;
    "${HOME}/.qoderwork")   echo "qoderwork" ;;
    "${HOME}/.qwenworkcn")  echo "qwenwork-cn" ;;
    "${HOME}/.qwenwork")    echo "qwenwork" ;;
    *) echo "" ;;
  esac
}

# ═══════════════════════════════════════════════════════════
# 当前 Host 识别(按脚本自身所在路径反推)
# Skill 总是从当前 Host 的 skills/ 目录被拉起,所以脚本路径比
# 「按固定优先级探测已安装目录」更能代表用户此刻正在用的 Host
# ═══════════════════════════════════════════════════════════
detect_current_host() {
  case "$1" in
    "${HOME}/.qoderworkcn"/*) echo "qoderworkcn" ;;
    "${HOME}/.qoderwork"/*)   echo "qoderwork" ;;
    "${HOME}/.qwenworkcn"/*)  echo "qwenworkcn" ;;
    "${HOME}/.qwenwork"/*)    echo "qwenwork" ;;
    "${HOME}/.claude"/*)      echo "claude-code" ;;
    "${HOME}/Library/Application Support/Claude"/*) echo "claude-desktop" ;;
    "${HOME}/.config/Claude"/*) echo "claude-desktop" ;;
    "${HOME}/.cursor"/*)      echo "cursor" ;;
    *) echo "" ;;
  esac
}

# ═══════════════════════════════════════════════════════════
# Host 探测
# ═══════════════════════════════════════════════════════════
detect_hosts() {
  local hosts=()
  [ -d "${HOME}/.qoderwork" ] && hosts+=("qoderwork")
  [ -d "${HOME}/.qoderworkcn" ] && hosts+=("qoderworkcn")
  [ -d "${HOME}/.qwenwork" ] && hosts+=("qwenwork")
  [ -d "${HOME}/.qwenworkcn" ] && hosts+=("qwenworkcn")
  [ -d "${HOME}/.claude" ] && hosts+=("claude-code")
  # macOS Claude Desktop
  if [ "$(uname -s)" = "Darwin" ] && [ -d "${HOME}/Library/Application Support/Claude" ]; then
    hosts+=("claude-desktop")
  fi
  # Linux Claude Desktop
  if [ "$(uname -s)" = "Linux" ] && [ -d "${HOME}/.config/Claude" ]; then
    hosts+=("claude-desktop")
  fi
  [ -d "${HOME}/.cursor" ] && hosts+=("cursor")
  echo "${hosts[@]}"
}

# ═══════════════════════════════════════════════════════════
# STEP 0: 重置本地数据(仅 --reset 时)
# ═══════════════════════════════════════════════════════════
reset_local_data() {
  local hosts=("$@")

  step "0/3" "重置本地数据"

  # 1. 清除 ~/.utp/ 全部数据(config / preferences / 旧 bin 等)
  if [ -d "${HOME}/.utp" ]; then
    rm -rf "${HOME}/.utp"
    info "已清除 ~/.utp/"
  else
    info "~/.utp/ 不存在,跳过"
  fi

  # 2. 清除各 Host 下的 skill 目录和 MCP 配置中的 utp 条目
  for host in "${hosts[@]}"; do
    case "$host" in
      qoderwork)
        local qw_dir
        qw_dir="$(resolve_host_dir "$host")"
        if $USE_PLUGIN; then
          local plugin_dir="${qw_dir}/plugins-custom/${PLUGIN_NAME}"
          if [ -d "$plugin_dir" ]; then
            rm -rf "$plugin_dir"
            info "已清除 QoderWork 插件目录"
          fi
        else
          local skill_dir="${qw_dir}/skills/${SKILL_NAME}"
          [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 QoderWork skill 目录"
          remove_mcp_entry "${qw_dir}/mcp.json"
        fi
        ;;
      qoderworkcn)
        local skill_dir="${HOME}/.qoderworkcn/skills/${SKILL_NAME}"
        [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 QoderWork CN skill 目录"
        remove_mcp_entry "${HOME}/.qoderworkcn/mcp.json"
        ;;
      qwenwork)
        local qwen_dir
        qwen_dir="$(resolve_host_dir "$host")"
        local skill_dir="${qwen_dir}/skills/${SKILL_NAME}"
        [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 QwenWork skill 目录"
        remove_mcp_entry "${qwen_dir}/mcp.json"
        ;;
      qwenworkcn)
        local skill_dir="${HOME}/.qwenworkcn/skills/${SKILL_NAME}"
        [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 QwenWork CN skill 目录"
        remove_mcp_entry "${HOME}/.qwenworkcn/mcp.json"
        ;;
      claude-code)
        local skill_dir="${HOME}/.claude/skills/${SKILL_NAME}"
        [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 Claude Code skill 目录"
        remove_mcp_entry "${HOME}/.claude/.mcp.json"
        ;;
      claude-desktop)
        if [ "$(uname -s)" = "Darwin" ]; then
          local skill_dir="${HOME}/Library/Application Support/Claude/skills/${SKILL_NAME}"
          local mcp_json="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
        else
          local skill_dir="${HOME}/.config/Claude/skills/${SKILL_NAME}"
          local mcp_json="${HOME}/.config/Claude/claude_desktop_config.json"
        fi
        [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 Claude Desktop skill 目录"
        remove_mcp_entry "$mcp_json"
        ;;
      cursor)
        local skill_dir="${HOME}/.cursor/skills/${SKILL_NAME}"
        [ -d "$skill_dir" ] && rm -rf "$skill_dir" && info "已清除 Cursor skill 目录"
        remove_mcp_entry "${HOME}/.cursor/mcp.json"
        ;;
    esac
  done

  echo ""
}

# 从 MCP 配置文件中移除 utp-connector 条目
remove_mcp_entry() {
  local mcp_path="$1"
  if [ ! -f "$mcp_path" ]; then
    return 0
  fi

  if command -v node >/dev/null 2>&1; then
    node -e "
      const fs = require('fs');
      const path = '${mcp_path}';
      try {
        let cfg = JSON.parse(fs.readFileSync(path, 'utf8'));
        if (cfg.mcpServers && cfg.mcpServers['utp-connector']) {
          delete cfg.mcpServers['utp-connector'];
          fs.writeFileSync(path, JSON.stringify(cfg, null, 2) + '\n');
        }
      } catch(e) { /* ignore parse errors */ }
    " 2>/dev/null && return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
path = '${mcp_path}'
try:
    with open(path) as f: cfg = json.load(f)
    if 'mcpServers' in cfg and 'utp-connector' in cfg['mcpServers']:
        del cfg['mcpServers']['utp-connector']
        with open(path, 'w') as f: json.dump(cfg, f, indent=2)
except: pass
" 2>/dev/null && return 0
  fi

  warn "无法从 ${mcp_path} 中移除 utp-connector 条目,请手动清理"
}

# ═══════════════════════════════════════════════════════════
# STEP 1: 安装 utp CLI(npm 全局安装)
# ═══════════════════════════════════════════════════════════
install_cli() {
  step "1/3" "安装 utp CLI (npm 全局安装)"

  # 环境变量覆盖默认值（默认国内镜像；内网/自定义源通过 UTP_NPM_REGISTRY / UTP_NPM_PACKAGE 覆盖）
  NPM_REGISTRY="${UTP_NPM_REGISTRY:-$NPM_REGISTRY}"
  NPM_PACKAGE="${UTP_NPM_PACKAGE:-$NPM_PACKAGE}"

  if ! command -v npm >/dev/null 2>&1; then
    err "未找到 npm,无法安装 utp CLI。请先安装 Node.js 后重试。"
    exit 1
  fi

  echo "  执行: npm i -g ${NPM_PACKAGE} --registry ${NPM_REGISTRY}"

  local npm_out=""
  local npm_ok=false
  if npm_out="$(npm i -g "${NPM_PACKAGE}" --registry "${NPM_REGISTRY}" 2>&1)"; then
    npm_ok=true
  fi
  echo "$npm_out"

  # bin 冲突(EEXIST):全局 utp 命令被其它包(如旧版/内网包)占用,
  # npm 拒绝覆盖。这不是网络/registry 问题,带 --force 覆盖重试即可
  if ! $npm_ok && echo "$npm_out" | grep -q "EEXIST"; then
    warn "全局 utp 命令已被其它 npm 包占用(EEXIST),正在覆盖安装。"
    echo "  执行: npm i -g ${NPM_PACKAGE} --registry ${NPM_REGISTRY} --force"
    if npm i -g "${NPM_PACKAGE}" --registry "${NPM_REGISTRY}" --force 2>&1; then
      npm_ok=true
    fi
  fi

  if ! $npm_ok; then
    err "npm install -g 失败。请检查网络和 npm registry 配置后重试。"
    echo "  手动执行: npm i -g ${NPM_PACKAGE} --registry ${NPM_REGISTRY} --force"
    exit 1
  fi

  # 解析 utp 实际路径
  UTP_BIN_PATH="$(command -v utp 2>/dev/null || echo '')"
  if [ -z "$UTP_BIN_PATH" ]; then
    local npm_prefix
    npm_prefix="$(npm config get prefix 2>/dev/null || echo '')"
    if [ -n "$npm_prefix" ] && [ -f "${npm_prefix}/bin/utp" ]; then
      UTP_BIN_PATH="${npm_prefix}/bin/utp"
    fi
  fi
  # 三级 fallback：部分版本的 @ut-protocol/utp 的 bin/utp 包装脚本缺失，
  # npm 无法创建全局 symlink，但平台二进制已安装到 optionalDependencies 目录下
  if [ -z "$UTP_BIN_PATH" ]; then
    local npm_root
    npm_root="$(npm root -g 2>/dev/null || echo '')"
    if [ -n "$npm_root" ]; then
      UTP_BIN_PATH="$(find "$npm_root/${NPM_PACKAGE}" -name utp -type f 2>/dev/null | head -1 || echo '')"
    fi
  fi
  if [ -z "$UTP_BIN_PATH" ]; then
    err "utp 安装后未找到可执行文件,请检查 npm 全局安装配置。"
    exit 1
  fi
  info "CLI 已安装到 ${UTP_BIN_PATH}"

  # macOS: 清除 quarantine 属性
  if command -v xattr >/dev/null 2>&1; then
    xattr -c "$UTP_BIN_PATH" 2>/dev/null || true
  fi

  if "$UTP_BIN_PATH" --version >/dev/null 2>&1; then
    info "CLI 版本校验通过"
  else
    warn "CLI 已安装,但版本校验未通过。"
    echo "  若是 macOS 首次运行被系统拦截,手动执行一次:xattr -cr ${UTP_BIN_PATH}"
  fi
}

# ═══════════════════════════════════════════════════════════
# STEP 2: 调用 utp install（QoderWork 主路径）
# ═══════════════════════════════════════════════════════════
run_utp_install_for_host() {
  local host="$1"

  case "$host" in
    qoderwork|qoderworkcn|qwenwork|qwenworkcn)
      step "2/3" "执行 utp install"
      local target
      target="$(utp_target_for_host "$host")"
      if [ -z "$target" ]; then
        err "无法确定 utp install 目标(host=${host})。"
        exit 1
      fi
      echo "  执行: ${UTP_BIN_PATH} install --target ${target}"
      "${UTP_BIN_PATH}" install --target "${target}"
      info "utp install 已完成(目标:${target})"
      ;;
    *)
      install_skill_for_host "$host"
      ;;
  esac
}

# ═══════════════════════════════════════════════════════════
# STEP 2 fallback: 安装采购 Skill 文件到非 QoderWork Host
# ═══════════════════════════════════════════════════════════
install_skill_for_host() {
  local host="$1"
  local skill_dir=""
  local mcp_json_path=""

  step "2/3" "安装采购 Skill 到 ${host}"

  case "$host" in
    qoderwork)
      local qw_dir
      qw_dir="$(resolve_host_dir "$host")"
      if $USE_PLUGIN; then
        skill_dir="${qw_dir}/plugins-custom/${PLUGIN_NAME}/skills/智能采购专家"
        mcp_json_path="${qw_dir}/plugins-custom/${PLUGIN_NAME}/.mcp.json"
        mkdir -p "${qw_dir}/plugins-custom/${PLUGIN_NAME}/.qoder-plugin"
        # 写入 plugin.json
        cat > "${qw_dir}/plugins-custom/${PLUGIN_NAME}/.qoder-plugin/plugin.json" << 'PJEOF'
{
  "name": "utp-toolkit",
  "displayName": "智能采购专家",
  "version": "1.0.8",
  "description": "Intelligent Procurement Expert — 1688 source supply, low price, high cost performance",
  "descriptionZh": "智能采购专家，打通1688优质供给，源头好货、低价高性价比、供给保障",
  "category": "procurement",
  "tags": ["utp", "b2b", "shopping", "procurement", "payment", "1688"],
  "skills": ["skills/智能采购专家"]
}
PJEOF
        info "QoderWork plugin.json 已写入"
      else
        skill_dir="${qw_dir}/skills/${SKILL_NAME}"
        mcp_json_path="${qw_dir}/mcp.json"
      fi
      ;;
    qoderworkcn)
      skill_dir="${HOME}/.qoderworkcn/skills/${SKILL_NAME}"
      mcp_json_path="${HOME}/.qoderworkcn/mcp.json"
      ;;
    qwenwork)
      local qwen_dir
      qwen_dir="$(resolve_host_dir "$host")"
      skill_dir="${qwen_dir}/skills/${SKILL_NAME}"
      mcp_json_path="${qwen_dir}/mcp.json"
      ;;
    qwenworkcn)
      skill_dir="${HOME}/.qwenworkcn/skills/${SKILL_NAME}"
      mcp_json_path="${HOME}/.qwenworkcn/mcp.json"
      ;;
    claude-code)
      skill_dir="${HOME}/.claude/skills/${SKILL_NAME}"
      mcp_json_path="${HOME}/.claude/.mcp.json"
      ;;
    claude-desktop)
      if [ "$(uname -s)" = "Darwin" ]; then
        skill_dir="${HOME}/Library/Application Support/Claude/skills/${SKILL_NAME}"
        mcp_json_path="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
      else
        skill_dir="${HOME}/.config/Claude/skills/${SKILL_NAME}"
        mcp_json_path="${HOME}/.config/Claude/claude_desktop_config.json"
      fi
      ;;
    cursor)
      skill_dir="${HOME}/.cursor/skills/${SKILL_NAME}"
      mcp_json_path="${HOME}/.cursor/mcp.json"
      ;;
    *)
      err "未知 Host: ${host}"
      echo "  支持的 Host:qoderwork | qoderworkcn | qwenwork | qwenworkcn | claude-code | claude-desktop | cursor"
      return 1
      ;;
  esac

  echo "  目标:${host} → ${skill_dir}"

  # ---- 复制 Skill 文件 ----
  # 如果源和目标相同(已安装到该目录)且文件存在,跳过复制
  if [ "${SKILL_DIR}" = "${skill_dir}" ] && [ -f "${skill_dir}/SKILL.md" ]; then
    info "Skill 目录与目标一致,跳过文件复制"
  else
    mkdir -p "$skill_dir"

    if [ -f "${SKILL_DIR}/SKILL.md" ]; then
      cp "${SKILL_DIR}/SKILL.md" "${skill_dir}/SKILL.md"
      info "SKILL.md 已复制"
    else
      warn "未找到 SKILL.md,跳过"
    fi

    if [ -d "${SKILL_DIR}/references" ]; then
      rm -rf "${skill_dir}/references"
      cp -R "${SKILL_DIR}/references" "${skill_dir}/references"
      info "references/ 已复制"
    fi

    if [ -d "${SKILL_DIR}/scripts" ]; then
      rm -rf "${skill_dir}/scripts"
      cp -R "${SKILL_DIR}/scripts" "${skill_dir}/scripts"
      info "scripts/ 已复制"
    fi

    if [ -f "${SKILL_DIR}/package.json" ]; then
      cp "${SKILL_DIR}/package.json" "${skill_dir}/package.json"
      info "package.json 已复制"
    fi
  fi

  # ---- 写入 MCP 配置 ----
  # 不同 Host 的 MCP 配置格式略有不同,这里统一用 JSON 写入
  # 如果目标文件已存在,尝试合并;否则新建
  write_mcp_config "$mcp_json_path" "$host"
  info "MCP 配置已写入 ${mcp_json_path}"
}

# ═══════════════════════════════════════════════════════════
# 写入 MCP 配置(合并或新建)
# ═══════════════════════════════════════════════════════════
write_mcp_config() {
  local mcp_path="$1"
  local host="$2"

  # 构建 MCP server 条目（JSON 格式）
  local new_entry
  new_entry=$(cat << MCPEOF
{
  "command": "${UTP_BIN_PATH}",
  "args": ["mcp", "serve"],
  "type": "stdio",
  "disabled": true,
  "_displayName": "UTP Connector",
  "_displayName_zh": "智能采购专家",
  "_displayDescription": "Connect to 1688 and millions of source factories, providing preferred full-category goods",
  "_displayDescription_zh": "连接1688等百万源头工厂，提供优选全品类好货"
}
MCPEOF
)

  # 优先用 node 合并（node 最可靠，且能正确格式化 JSON）
  if command -v node >/dev/null 2>&1; then
    node -e "
      const fs = require('fs');
      const path = '${mcp_path}';
      let cfg = {};
      try { cfg = JSON.parse(fs.readFileSync(path, 'utf8')); } catch {}
      if (!cfg.mcpServers) cfg.mcpServers = {};
      cfg.mcpServers['utp-connector'] = ${new_entry};
      fs.writeFileSync(path, JSON.stringify(cfg, null, 2) + '\n');
    " 2>/dev/null && return 0
  fi

  # 备选 python3
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json
path = '${mcp_path}'
try:
    with open(path) as f: cfg = json.load(f)
except: cfg = {}
if 'mcpServers' not in cfg: cfg['mcpServers'] = {}
cfg['mcpServers']['utp-connector'] = ${new_entry}
with open(path, 'w') as f: json.dump(cfg, f, indent=2)
" 2>/dev/null && return 0
  fi

  # 都不可用时，直接写入正确格式的 JSON
  warn "node/python3 均不可用,直接写入 MCP 配置(无法合并已有配置)"
  mkdir -p "$(dirname "$mcp_path")"
  cat > "$mcp_path" << FULLEOF
{
  "mcpServers": {
    "utp-connector": {
      "command": "${UTP_BIN_PATH}",
      "args": ["mcp", "serve"],
      "type": "stdio",
      "_displayName": "UTP Procurement Expert",
      "_displayName_zh": "智能采购专家",
      "_displayDescription": "1688 source supply, low price, high cost performance",
      "_displayDescription_zh": "打通1688优质供给，源头好货、低价高性价比、供给保障"
    }
  }
}
FULLEOF
}

# ═══════════════════════════════════════════════════════════
# STEP 3: 输出下一步指引
# ═══════════════════════════════════════════════════════════
print_next_steps() {
  local hosts=("$@")

  step "3/3" "安装完成 — 接下来你需要"

  echo ""
  echo "  CLI 路径: ${UTP_BIN_PATH}"
  echo ""
  for h in "${hosts[@]}"; do
    case "$h" in
      qoderwork)
        local qw_label="QoderWork"
        if [ "$(resolve_qw_dir)" = "${HOME}/.qoderworkcn" ]; then
          qw_label="QoderWork CN"
        fi
        echo "  ${qw_label}:"
        if $USE_PLUGIN; then
          echo "    1. 设置 → 插件 → 找到「智能采购专家」→ 开启"
          echo "    2. 启用 MCP 连接器（默认已关闭，需手动开启）："
          echo "       方式一：对话中输入 qoderwork.settings.connector.custom.utp-connector · enable"
          echo "       方式二：浏览器打开 qoder-work://connectors"
          echo "               → 已安装 → 本地安装 → 自定义 → 智能采购专家 → 启动"
        else
          echo "    1. 启用 MCP 连接器（默认已关闭，需手动开启）："
          echo "       方式一：对话中输入 qoderwork.settings.connector.custom.utp-connector · enable"
          echo "       方式二：浏览器打开 qoder-work://connectors"
          echo "               → 已安装 → 本地安装 → 自定义 → 智能采购专家 → 启动"
        fi
        ;;
      qoderworkcn)
        echo "  QoderWork CN:"
        echo "    1. 启用 MCP 连接器（默认已关闭，需手动开启）："
        echo "       方式一：对话中输入 qoderwork.settings.connector.custom.utp-connector · enable"
        echo "       方式二：浏览器打开 qoder-work://connectors"
        echo "               → 已安装 → 本地安装 → 自定义 → 智能采购专家 → 启动"
        ;;
      qwenwork|qwenworkcn)
        local qwen_label="QwenWork"
        if [ "$h" = "qwenworkcn" ] || [ "$(resolve_qwen_dir)" = "${HOME}/.qwenworkcn" ]; then
          qwen_label="QwenWork CN（千问 Work）"
        fi
        echo "  ${qwen_label}:"
        echo "    1. utp install 已写入 skills/ 与 mcp.json（连接器默认启用）"
        echo "    2. 若对话中检测不到工具,在设置中确认 utp-connector 已启用,或重启 QwenWork"
        ;;
      claude-code)
        echo "  Claude Code:"
        echo "    1. 运行 /mcp 重连,或重启会话"
        ;;
      claude-desktop)
        echo "  Claude Desktop:"
        echo "    1. 重启 Claude Desktop 应用"
        ;;
      cursor)
        echo "  Cursor:"
        echo "    1. Settings → MCP → 找到 utp → Reload"
        ;;
    esac
    echo ""
  done
  echo "  完成后,在对话中说「帮我买双袜子」即可开始使用。"
  echo ""
}

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════╗"
echo "║   智能采购专家 — 一键安装                 ║"
echo "╚══════════════════════════════════════════════╝"

# ---- 定位 Skill 目录 ----
# 尝试从脚本路径定位 Skill 目录
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]:-}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-}")" && pwd)"
  SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd 2>/dev/null || echo '')"
else
  SCRIPT_DIR=""
  SKILL_DIR=""
fi

# 无法定位 Skill 目录(管道执行) 或 缺少 SKILL.md → 报错引导
if [ -z "$SKILL_DIR" ] || [ ! -f "${SKILL_DIR}/SKILL.md" ]; then
  echo "" >&2
  echo "======================================================" >&2
  echo "  未找到 Skill 文件 (SKILL.md, scripts/, references/)" >&2
  echo "  请先克隆仓库: git clone <repo-url> utp-shopping" >&2
  echo "  然后运行: cd utp-shopping && bash scripts/install.sh" >&2
  echo "======================================================" >&2
  echo "" >&2
  exit 1
fi

# ---- 确定目标 Host 列表 ----
target_hosts=()

if [ -n "$TARGET_HOST" ]; then
  target_hosts=("$TARGET_HOST")
else
  detected_str="$(detect_hosts)"
  detected=()
  for h in $detected_str; do
    detected+=("$h")
  done
  if [ ${#detected[@]} -eq 0 ]; then
    err "未探测到任何已安装的 Agent Host。"
    echo "  请用 --host 参数指定:qoderwork | qwenwork | claude-code | claude-desktop | cursor"
    exit 1
  fi
  if $INSTALL_ALL; then
    target_hosts=("${detected[@]}")
  else
    # 未显式指定 --host 时,优先按脚本自身路径反推「用户此刻正在用的 Host」,
    # 否则多 Host 机器上会固定装到探测顺序里的第一个(qoderwork),
    # 出现「装成功了但当前 Host 里依然没有工具」
    current_host="$(detect_current_host "$SKILL_DIR")"
    if [ -n "$current_host" ]; then
      target_hosts=("$current_host")
      info "按 Skill 所在路径识别当前 Host:${current_host}"
    else
      target_hosts=("${detected[0]}")
      if [ ${#detected[@]} -gt 1 ]; then
        warn "探测到多个 Host:${detected[*]}"
        echo "  无法识别当前 Host,仅安装到第一个(${detected[0]})。"
        echo "  如需装到指定 Host,加 --host <name>;全部安装,加 --all。"
      fi
    fi
  fi
fi

echo "  目标 Host:${target_hosts[*]}"

# ---- 重置(仅 --reset) ----
if $DO_RESET; then
  reset_local_data "${target_hosts[@]}"
fi

# ---- 执行安装 ----
install_cli

for host in "${target_hosts[@]}"; do
  run_utp_install_for_host "$host"
done

print_next_steps "${target_hosts[@]}"

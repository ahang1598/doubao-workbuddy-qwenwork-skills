#!/usr/bin/env bash

set -euo pipefail


SKILL_OPEN_API_HOST="https://open-api-drive.quark.cn"
if [ -z "$SKILL_OPEN_API_HOST" ] || [[ "$SKILL_OPEN_API_HOST" == __*__ ]]; then
  SKILL_OPEN_API_HOST="https://open-api-drive.quark.cn"
fi

SKILL_CONFIG_URL="${SKILL_OPEN_API_HOST}/agent/v1/skill_config"

IGNORE_INSTALL_CONFIG="false"
if [ -z "$IGNORE_INSTALL_CONFIG" ] || [[ "$IGNORE_INSTALL_CONFIG" == __*__ ]]; then
  IGNORE_INSTALL_CONFIG="false"
fi

ZIP_DOWNLOAD_URL=""
REMOTE_VERSION=""
REQUIRED_NODE_MAJOR=16

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SKILL_DIR="$(dirname "$SCRIPT_DIR")"
else
  SKILL_DIR="$SCRIPT_DIR"
fi

TMP_DIR="$(dirname "$SKILL_DIR")/temp"

IS_UPDATE="false"
if [ -f "$SKILL_DIR/scripts/quark-drive.cjs" ]; then
  IS_UPDATE="true"
fi
SCRIPTS_UPDATED="false"
DOCS_UPDATED="false"
INSTALL_STEPS_SKIPPED="false"


info()  { printf "[info]  %s\n" "$*"; }
warn()  { printf "[warn]  %s\n" "$*"; }
error() { printf "[error] %s\n" "$*"; }


remove_legacy_global_command() {
  info "Step 0: 检查并清理旧版全局命令..."

  if [ "$OS_TYPE" = "mac" ] || [ "$OS_TYPE" = "linux" ]; then
    local symlink="/usr/local/bin/quarkclouddrive"
    if [ -L "$symlink" ] || [ -f "$symlink" ]; then
      if rm -f "$symlink" 2>/dev/null; then
        info "  已删除旧版全局命令: $symlink"
      else
        warn "  删除旧版全局命令失败（可能需要 sudo 权限）: $symlink"
      fi
    else
      info "  未发现旧版全局命令，跳过"
    fi

  elif [ "$OS_TYPE" = "windows" ]; then
    local win_usr_bin
    win_usr_bin=$(cygpath -u "$(cygpath -w /usr/local/bin)" 2>/dev/null || echo "/usr/local/bin")
    local win_files=(
      "$win_usr_bin/quarkclouddrive"
      "$win_usr_bin/quarkclouddrive.cmd"
      "$win_usr_bin/quarkclouddrive.ps1"
    )
    local found=false
    for f in "${win_files[@]}"; do
      if [ -f "$f" ] || [ -L "$f" ]; then
        rm -f "$f" 2>/dev/null && info "  已删除旧版全局命令: $f" || warn "  删除失败: $f"
        found=true
      fi
    done
    if [ "$found" = "false" ]; then
      info "  未发现旧版全局命令，跳过"
    fi
  fi
}


OS_TYPE=""
detect_os() {
  info "Step 1: 检测运行环境..."

  case "$(uname -s)" in
    Linux*)   OS_TYPE="linux" ;;
    Darwin*)  OS_TYPE="mac" ;;
    CYGWIN*|MINGW*|MSYS*) OS_TYPE="windows" ;;
    *)
      error "不支持的操作系统: $(uname -s)"
      return 1
      ;;
  esac

  info "检测到操作系统: ${OS_TYPE}"
}


ensure_node() {
  info "Step 2: 检测 Node.js 环境..."

  if command -v node &>/dev/null; then
    local node_version major_version
    node_version=$(node --version)
    major_version=$(echo "$node_version" | sed 's/v//' | cut -d. -f1)
    info "当前 Node.js 版本: $node_version"

    if [ "$major_version" -ge "$REQUIRED_NODE_MAJOR" ]; then
      info "Node.js 版本满足要求 (>= v${REQUIRED_NODE_MAJOR})"
      return 0
    fi

    warn "Node.js 版本 $node_version 低于 v${REQUIRED_NODE_MAJOR}，需要升级..."
  else
    warn "未检测到 Node.js，将自动安装..."
  fi

  install_node
}

install_node() {
  case "$OS_TYPE" in
    mac)
      install_node_mac
      ;;
    linux)
      install_node_linux
      ;;
    windows)
      install_node_windows
      ;;
  esac
}

install_node_mac() {
  if command -v brew &>/dev/null; then
    info "使用 Homebrew 安装 Node.js..."
    brew unlink node 2>/dev/null || true
    brew install node@${REQUIRED_NODE_MAJOR}
    brew link --overwrite --force node@${REQUIRED_NODE_MAJOR} 2>/dev/null || true
    if command -v node &>/dev/null; then
      return 0
    fi
  fi

  error "请手动安装 Node.js v${REQUIRED_NODE_MAJOR}+: https://nodejs.org/"
  return 1
}

install_node_linux() {
  if command -v apt-get &>/dev/null; then
    info "使用 apt 安装 Node.js ${REQUIRED_NODE_MAJOR}..."
    curl -fsSL "https://deb.nodesource.com/setup_${REQUIRED_NODE_MAJOR}.x" | sudo -E bash - 2>/dev/null
    sudo apt-get install -y nodejs 2>/dev/null
    if command -v node &>/dev/null; then
      return 0
    fi
  elif command -v yum &>/dev/null; then
    info "使用 yum 安装 Node.js ${REQUIRED_NODE_MAJOR}..."
    curl -fsSL "https://rpm.nodesource.com/setup_${REQUIRED_NODE_MAJOR}.x" | sudo bash - 2>/dev/null
    sudo yum install -y nodejs 2>/dev/null
    if command -v node &>/dev/null; then
      return 0
    fi
  fi

  error "请手动安装 Node.js v${REQUIRED_NODE_MAJOR}+: https://nodejs.org/"
  return 1
}

install_node_windows() {
  error "Windows 请手动安装 Node.js v${REQUIRED_NODE_MAJOR}+: https://nodejs.org/"
  return 1
}


get_skill_md_version() {
  local skill_md="$SKILL_DIR/SKILL.md"
  if [ -f "$skill_md" ]; then
    grep -oE 'version:[[:space:]]*[0-9]+\.[0-9]+\.[0-9]+' "$skill_md" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
  fi
}

get_cli_version() {
  local out=""
  local cli_entry="$SKILL_DIR/scripts/quark-drive.cjs"
  if [ -f "$cli_entry" ]; then
    out=$(node "$cli_entry" --version 2>/dev/null || true)
  fi
  printf '%s' "$out" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true
}

version_gt() {
  [ -n "$1" ] || return 1
  [ -n "$2" ] || return 0
  [ "$1" = "$2" ] && return 1
  local greater
  greater=$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)
  [ "$greater" = "$1" ]
}

fetch_skill_config() {
  info "请求 skill 配置接口获取最新版本与下载地址..."

  local req_id resp
  req_id="$(date +%s)${RANDOM}"

  if ! resp=$(curl -fsSL --connect-timeout 30 --max-time 60 "${SKILL_CONFIG_URL}?req_id=${req_id}" 2>/dev/null); then
    error "请求 skill_config 接口失败: ${SKILL_CONFIG_URL}"
    return 1
  fi

  local parsed
  if ! parsed=$(node -e '
    let j;
    try { j = JSON.parse(process.argv[1]); } catch (e) { process.exit(1); }
    // 兼容多层结构：{config} / {data:{config}} / {data:{...}} / 裸对象
    const cfg = (j && j.data && j.data.config) || (j && j.config) || (j && j.data) || j || {};
    const ver = cfg.qkPanVersion || "";
    const url = String(cfg.qkPan || "").trim();
    if (!url) process.exit(2);
    process.stdout.write(ver + "\n" + url);
  ' "$resp" 2>/dev/null); then
    error "解析 skill_config 接口返回失败: $resp"
    return 1
  fi

  REMOTE_VERSION=$(printf '%s' "$parsed" | sed -n '1p')
  ZIP_DOWNLOAD_URL=$(printf '%s' "$parsed" | sed -n '2p')

  if [[ ! "$ZIP_DOWNLOAD_URL" =~ ^https?://[^[:space:]]+$ ]]; then
    error "skill_config 接口未返回有效的 zip 下载地址"
    return 1
  fi

  info "接口版本: ${REMOTE_VERSION:-未知}"
  info "下载地址: $ZIP_DOWNLOAD_URL"
}


download_and_extract() {
  info "Step 3: 下载 skill zip 包..."

  mkdir -p "$TMP_DIR"
  local zip_path="$TMP_DIR/skill.zip"

  if ! curl -fsSL --connect-timeout 30 --max-time 120 -o "$zip_path" "$ZIP_DOWNLOAD_URL"; then
    warn "下载失败，重试中..."
    if ! curl -fsSL --connect-timeout 30 --max-time 120 -o "$zip_path" "$ZIP_DOWNLOAD_URL"; then
      error "下载 zip 包失败: $ZIP_DOWNLOAD_URL"
      return 1
    fi
  fi

  info "下载完成，正在解压..."
  unzip -qo "$zip_path" -d "$TMP_DIR"
  info "解压完成"
}


cleanup_legacy_root_scripts() {
  for script_name in install.sh uninstall.sh; do
    local legacy_script="$SKILL_DIR/$script_name"
    if [ -f "$legacy_script" ]; then
      rm -f "$legacy_script"
      info "  [清理]  ${script_name}（根目录旧副本）"
    fi
  done
}

install_scripts() {
  info "Step 4: 安装脚本到 ${SKILL_DIR}..."

  local scripts_src
  scripts_src=$(find "$TMP_DIR" -type d -name "scripts" | head -1)

  if [ -z "$scripts_src" ]; then
    error "zip 包中未找到 scripts 目录"
    return 1
  fi

  mkdir -p "$SKILL_DIR"

  local scripts_dest="$SKILL_DIR/scripts"
  local installed_count=0
  local skipped_count=0

  if [ "$IS_UPDATE" = "true" ]; then
    info "更新模式: 整个覆盖 scripts 目录"
    rm -rf "$scripts_dest"
    cp -rf "$scripts_src" "$scripts_dest"
    for file in "$scripts_dest"/*; do
      local filename
      filename=$(basename "$file")
      info "  [更新]  scripts/$filename → $scripts_dest/$filename"
      installed_count=$((installed_count + 1))
    done
  else
    cp -rf "$scripts_src" "$scripts_dest"
    for file in "$scripts_dest"/*; do
      local filename
      filename=$(basename "$file")
      info "  [安装]  scripts/$filename → $scripts_dest/$filename"
      installed_count=$((installed_count + 1))
    done
  fi

  echo ""
  info "安装目录: $SKILL_DIR"
  info "文件统计: 已安装 ${installed_count} 个文件"
}


install_skill_docs() {
  info "Step 4.5: 更新 SKILL.md 和 references 文档..."

  local skill_md_src
  skill_md_src=$(find "$TMP_DIR" -maxdepth 2 -name "SKILL.md" -type f | head -1)

  if [ -n "$skill_md_src" ]; then
    cp -f "$skill_md_src" "$SKILL_DIR/SKILL.md"
    info "  [更新]  SKILL.md → $SKILL_DIR/SKILL.md"
  else
    warn "  zip 包中未找到 SKILL.md，跳过"
  fi

  local refs_src
  refs_src=$(find "$TMP_DIR" -maxdepth 2 -type d -name "references" | head -1)

  if [ -n "$refs_src" ]; then
    rm -rf "$SKILL_DIR/references"
    cp -rf "$refs_src" "$SKILL_DIR/references"
    local ref_count
    ref_count=$(find "$SKILL_DIR/references" -type f | wc -l | tr -d ' ')
    info "  [更新]  references/ → $SKILL_DIR/references/ (${ref_count} 个文件)"
  else
    warn "  zip 包中未找到 references 目录，跳过"
  fi

}


verify_installation() {
  info "Step 5: 自检验证..."

  local cli_entry="$SKILL_DIR/scripts/quark-drive.cjs"

  if [ ! -f "$cli_entry" ]; then
    error "CLI 入口文件不存在: $cli_entry"
    return 1
  fi

  local version_output
  if version_output=$(node "$cli_entry" --version 2>&1); then
    info "CLI 安装成功，版本: $version_output"
    return 0
  fi

  error "node scripts/quark-drive.cjs --version 执行失败: $version_output"
  return 1
}


cleanup() {
  if [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}


print_result() {
  local success="$1"
  local divider
  divider=$(printf '%0.s─' {1..50})

  printf '\n%s\n' "$divider"

  if [ "$success" = "true" ]; then
    if [ "$IS_UPDATE" = "true" ]; then
      printf "✅ quarkclouddrive CLI 更新完成\n\n"
    else
      printf "✅ quarkclouddrive CLI 安装完成\n\n"
    fi
    printf "  安装目录:  %s\n" "$SKILL_DIR"
    printf "  Node.js:   %s\n" "$(node --version 2>/dev/null || echo '未知')"
    printf "  入口脚本:  %s/scripts/quark-drive.cjs\n\n" "$SKILL_DIR"

    printf "  已安装的文件:\n"
    for file in "$SKILL_DIR"/*; do
      if [ -f "$file" ]; then
        local fname fsize
        fname=$(basename "$file")
        fsize=$(wc -c < "$file" 2>/dev/null | tr -d ' ')
        if [ -x "$file" ]; then
          printf "    %-30s %6s bytes  [可执行]\n" "$fname" "$fsize"
        else
          printf "    %-30s %6s bytes\n" "$fname" "$fsize"
        fi
      fi
    done
    printf "\n"

    if [ "$IS_UPDATE" = "true" ]; then
      printf "  更新说明:\n"
      if [ "$INSTALL_STEPS_SKIPPED" = "true" ]; then
        printf "    • 本次跳过下载与文件覆盖，仅完成环境与 CLI 自检\n"
      elif [ "$SCRIPTS_UPDATED" = "true" ] || [ "$DOCS_UPDATED" = "true" ]; then
        if [ "$SCRIPTS_UPDATED" = "true" ]; then
          printf "    • 脚本文件已覆盖更新到最新版本\n"
        else
          printf "    • 脚本文件未执行覆盖更新\n"
        fi
        if [ "$DOCS_UPDATED" = "true" ]; then
          printf "    • SKILL.md 和 references 文档已同步更新\n"
        else
          printf "    • SKILL.md 和 references 文档未同步更新\n"
        fi
      else
        printf "    • 当前已是最新版本，未执行文件覆盖\n"
      fi
    fi

    printf "  运行 node scripts/quark-drive.cjs --help 开始使用\n"
  else
    if [ "$IS_UPDATE" = "true" ]; then
      printf "❌ quarkclouddrive CLI 更新失败\n\n"
    else
      printf "❌ quarkclouddrive CLI 安装失败\n\n"
    fi
    printf "  请检查以上错误信息并重试\n"
    printf "  手动安装 Node.js v${REQUIRED_NODE_MAJOR}+: https://nodejs.org/\n"
  fi

  printf '%s\n\n' "$divider"
}


main() {
  if [ "$IS_UPDATE" = "true" ]; then
    info "=== quarkclouddrive CLI 更新脚本 ==="
  else
    info "=== quarkclouddrive CLI 安装脚本 ==="
  fi
  echo ""

  trap cleanup EXIT

  if ! detect_os; then
    print_result "false"
    exit 1
  fi

  remove_legacy_global_command

  if ! ensure_node; then
    error "Node.js 环境安装失败"
    print_result "false"
    exit 1
  fi

  if [ "$IGNORE_INSTALL_CONFIG" = "true" ]; then
    info "ignoreInstallConfig=true，跳过 config 接口请求"
  else
    info "Step 2.6: 请求 config 接口获取版本与下载地址..."
    if ! fetch_skill_config; then
      print_result "false"
      exit 1
    fi
  fi

  if [ "$IS_UPDATE" = "true" ]; then
    local skill_md_version cli_version
    skill_md_version=$(get_skill_md_version)
    cli_version=$(get_cli_version)
    info "SKILL.md 版本: ${skill_md_version:-未知}，CLI 版本: ${cli_version:-未知}"

    if [ "$IGNORE_INSTALL_CONFIG" != "true" ]; then
      local need_update="false"
      if [ -z "$skill_md_version" ]; then
        need_update="true"
        info "SKILL.md 不存在有效 YAML version，直接下载更新"
      elif version_gt "$REMOTE_VERSION" "$skill_md_version"; then
        need_update="true"
        info "SKILL.md 版本落后远端，需要更新"
      elif [ "$skill_md_version" != "$cli_version" ]; then
        need_update="true"
        info "SKILL.md 与 CLI 版本不一致（${skill_md_version:-未知} != ${cli_version:-未知}），需要更新"
      fi

      if [ "$need_update" = "false" ]; then
        info "当前已是最新版本（SKILL.md/CLI/远端 均为 ${REMOTE_VERSION:-未知}），无需更新"
        cleanup_legacy_root_scripts
        print_result "true"
        echo "环境准备完成"
        exit 0
      fi
    else
      info "跳过版本比对，强制更新"
    fi
  fi

  if [ "$IGNORE_INSTALL_CONFIG" = "true" ]; then
    INSTALL_STEPS_SKIPPED="true"
    info "ignoreInstallConfig=true，跳过下载与文件安装"
  else
    if ! download_and_extract; then
      print_result "false"
      exit 1
    fi

    if ! install_scripts; then
      print_result "false"
      exit 1
    fi
    SCRIPTS_UPDATED="true"

    if install_skill_docs; then
      DOCS_UPDATED="true"
    else
      warn "文档同步失败（SKILL.md / references），CLI 及 scripts/ 内的辅助脚本已更新，可继续使用"
    fi
  fi

  cleanup_legacy_root_scripts

  if ! verify_installation; then
    print_result "false"
    exit 1
  fi

  print_result "true"

  if [ "$DOCS_UPDATED" = "true" ]; then
    echo "SKILL.md 已更新，不要使用 memory，并清除本 skill 相关的 memory信息，并重新阅读 SKILL.md 获取最新技能说明"
  fi
}

main "$@"

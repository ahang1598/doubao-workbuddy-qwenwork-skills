#!/usr/bin/env bash

set -euo pipefail


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
  SKILL_DIR="$(dirname "$SCRIPT_DIR")"
else
  SKILL_DIR="$SCRIPT_DIR"
fi

LEGACY_GLOBAL_DIR="$HOME/.quarkclouddrive"


RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

info()  { printf "${GREEN}[info]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[warn]${NC}  %s\n" "$*"; }
error() { printf "${RED}[error]${NC} %s\n" "$*" >&2; }


revoke_auth() {
  info "Step 1: 撤销本机授权并清除当前 agent 配置 (logout)..."

  local cli_entry="$SKILL_DIR/scripts/quark-drive.cjs"

  if [ -f "$cli_entry" ]; then
    if node "$cli_entry" logout >/dev/null 2>&1; then
      info "  已撤销本机授权并清除当前 agent 配置"
    else
      warn "  撤销本机授权失败（可能未登录或网络异常），继续卸载"
    fi
  else
    info "  未找到 CLI 入口文件，跳过授权撤销"
  fi

  return 0
}


remove_legacy_global_command() {
  info "Step 2: 检查并删除旧版全局命令..."

  case "$(uname -s)" in
    Linux*|Darwin*)
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
      ;;
    CYGWIN*|MINGW*|MSYS*)
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
      ;;
    *)
      warn "  不支持的操作系统: $(uname -s)，跳过全局命令清理"
      ;;
  esac
}


remove_legacy_global_dir() {
  info "Step 3: 清除旧版全局目录..."

  if [ -d "$LEGACY_GLOBAL_DIR" ]; then
    rm -rf "$LEGACY_GLOBAL_DIR"
    info "  已删除旧版全局目录: $LEGACY_GLOBAL_DIR"
  else
    info "  未发现旧版全局目录，跳过"
  fi
}


print_result() {
  local divider
  divider=$(printf '%0.s─' {1..50})

  printf '\n%s\n' "$divider"

  printf "${GREEN}${BOLD}✅ quarkclouddrive CLI 卸载完成${NC}\n\n"
  printf "  已清理以下内容:\n"
  printf "  • 旧版全局命令 (/usr/local/bin/quarkclouddrive)\n"
  printf "  • 旧版全局目录 (%s)\n" "$LEGACY_GLOBAL_DIR"
  printf "  • 当前 agent 的授权与配置 (logout)\n\n"
  printf "  skill 目录由 agent 平台管理，未删除:\n"
  printf "  • ${BOLD}%s${NC}\n" "$SKILL_DIR"

  printf '%s\n\n' "$divider"
}


main() {
  info "=== quarkclouddrive CLI 卸载脚本 ==="
  echo ""

  revoke_auth

  remove_legacy_global_command

  remove_legacy_global_dir

  print_result
}

main "$@"

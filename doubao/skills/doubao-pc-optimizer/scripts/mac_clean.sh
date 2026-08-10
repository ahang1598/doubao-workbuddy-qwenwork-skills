#!/bin/bash
# mac_clean.sh — macOS 安全清理(L1,只清用户级缓存/日志/废纸篓,不碰系统目录和个人文件)
# 用法: bash mac_clean.sh                    # 默认【预演】,只统计不删除
#       bash mac_clean.sh --execute          # 实际清理(废纸篓仍需额外 --trash)
#       bash mac_clean.sh --execute --trash  # 实际清理 + 清空废纸篓
# 未知参数会直接报错退出(防止 --dryrn 这类笔误意外触发真删)
# 刻意不用 sudo:所有系统级路径(/System /Library /private)都不在清理范围内
DRY=1; TRASH=0
for arg in "$@"; do
  case "$arg" in
    --execute) DRY=0 ;;
    --trash)   TRASH=1 ;;
    --dry-run) DRY=1 ;;   # 兼容显式写法
    *) echo "错误: 未知参数 '$arg'(可用: --execute --trash --dry-run)"; exit 2 ;;
  esac
done

total_kb=0
# 系统关键缓存排除清单:CloudKit/家人共享/账号相关,清了会引发 iCloud 重新同步或登录异常
EXCLUDES="com.apple.cloudkit CloudKit com.apple.FamilyCircle com.apple.ap.adprivacyd com.apple.homed com.apple.Safari.SafeBrowsing com.apple.akd"
is_excluded() {  # $1=目录名
  for ex in $EXCLUDES; do [ "$1" = "$ex" ] && return 0; done
  return 1
}
clean_dir() {  # $1=标签 $2=路径 —— 只删目录【内容】,保留目录本身;被占用的文件自动跳过
  [ -d "$2" ] || return
  size_kb=$(du -sk "$2" 2>/dev/null | awk '{print $1}')
  [ -z "$size_kb" ] && size_kb=0
  if [ "$DRY" = "1" ]; then
    echo "[预演] $1: 可清理 $((size_kb/1024)) MB ($2)"
  else
    find "$2" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
    echo "[完成] $1: 清理约 $((size_kb/1024)) MB"
  fi
  total_kb=$((total_kb+size_kb))
}
clean_caches_dir() {  # 逐个子目录处理 ~/Library/Caches:跳过排除清单;只清各子目录内容,保留子目录本身
  base="$HOME/Library/Caches"
  [ -d "$base" ] || return
  size_kb=0
  for d in "$base"/*; do
    [ -e "$d" ] || continue
    name=$(basename "$d")
    if is_excluded "$name"; then
      echo "[跳过] 系统关键缓存: $name"
      continue
    fi
    s=$(du -sk "$d" 2>/dev/null | awk '{print $1}'); [ -z "$s" ] && s=0
    size_kb=$((size_kb+s))
    if [ "$DRY" != "1" ]; then
      if [ -d "$d" ]; then
        find "$d" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
      else
        rm -f "$d" 2>/dev/null
      fi
    fi
  done
  if [ "$DRY" = "1" ]; then
    echo "[预演] 用户应用缓存: 可清理 $((size_kb/1024)) MB (已排除系统关键项;含 Chrome 等浏览器缓存)"
  else
    echo "[完成] 用户应用缓存: 清理约 $((size_kb/1024)) MB (已排除系统关键项)"
  fi
  total_kb=$((total_kb+size_kb))
}

echo "=== macOS 安全清理 $([ $DRY = 1 ] && echo '(预演模式,未删除任何文件)') $(date '+%F %T') ==="

# 注: Chrome 缓存位于 ~/Library/Caches/Google 内,已包含在下面的整体清理中,不单独统计(避免重复计数)
clean_caches_dir
clean_dir "用户日志" "$HOME/Library/Logs"
clean_dir "Xcode编译缓存" "$HOME/Library/Developer/Xcode/DerivedData"

if [ "$TRASH" = "1" ] && [ "$DRY" != "1" ]; then
  clean_dir "废纸篓" "$HOME/.Trash"
else
  size_kb=$(du -sk "$HOME/.Trash" 2>/dev/null | awk '{print $1}'); [ -z "$size_kb" ] && size_kb=0
  echo "[跳过] 废纸篓($((size_kb/1024)) MB)— 清空不可恢复,需 --execute --trash 同时传入才执行"
fi

echo "=== $([ $DRY = 1 ] && echo "预演结束,合计约 $((total_kb/1024)) MB 可清理。确认后加 --execute 执行" || echo "清理完成,合计约 $((total_kb/1024)) MB") ==="
echo "未触碰: 系统目录、钥匙串、个人文件(桌面/文稿/下载等)、时间机器快照"
echo "提示: 本地时间机器快照可用 'tmutil listlocalsnapshots /' 查看,占空间大时另行处理(L2)"

#!/usr/bin/env bash
set -euo pipefail

# Enterprise Skill Installation Script
# Downloads, validates, and installs an enterprise skill from a ZIP URL.
# Usage: install-skill.sh --name <skillName> --url <downloadUrl> [--target-dir <dir>]

# ─── Defaults ───────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NAME=""
URL=""

# ─── Argument Parsing ───────────────────────────────────────────────────────────
print_usage() {
  cat >&2 <<'EOF'
Usage:
  install-skill.sh --name <skillName> --url <downloadUrl> [--target-dir <dir>]

Options:
  --name        (required) Skill name. Only [a-zA-Z0-9_-] allowed.
  --url         (required) Full URL to download the skill ZIP package.
  --target-dir  (optional) Installation target directory. Default: current product skills directory
  --help        Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      NAME="$2"; shift 2 ;;
    --url)
      URL="$2"; shift 2 ;;
    --target-dir)
      TARGET_DIR="$2"; shift 2 ;;
    --help|-h)
      print_usage; exit 0 ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      print_usage
      exit 1 ;;
  esac
done

# ─── Validation ─────────────────────────────────────────────────────────────────
if [[ -z "$NAME" ]]; then
  echo "Error: --name is required." >&2
  print_usage
  exit 1
fi

if [[ -z "$URL" ]]; then
  echo "Error: --url is required." >&2
  print_usage
  exit 1
fi

if ! echo "$NAME" | grep -qE '^[a-zA-Z0-9_-]+$'; then
  echo "Error: Invalid skill name '$NAME'. Only [a-zA-Z0-9_-] characters are allowed." >&2
  exit 1
fi

# ─── Variables ──────────────────────────────────────────────────────────────────
# 使用 mktemp 生成系统唯一临时目录，避免路径冲突
TEMP_DIR="$(mktemp -d)"
TEMP_ZIP="${TEMP_DIR}/skill.zip"

# ─── Cleanup helper ─────────────────────────────────────────────────────────────
cleanup() {
  # 临时目录由系统管理，不做 rm -rf
  :
}

# ─── Frontmatter helper ────────────────────────────────────────────────────────
# 将 SKILL.md 的 YAML frontmatter 注入或更新 install_source 字段，
# 用于在「已安装技能」列表中标记此技能来源为 skill-market。
inject_install_source_field() {
  local file="$1"
  local source_value="skill-market"
  local tmp="${file}.tmp"

  # 首行不是 --- 时，视为缺失 frontmatter，前置一个最小 frontmatter 块
  if [[ "$(head -n 1 "$file" 2>/dev/null || true)" != "---" ]]; then
    {
      echo "---"
      echo "install_source: ${source_value}"
      echo "---"
      cat "$file"
    } > "$tmp" && mv "$tmp" "$file"
    return 0
  fi

  # 已存在 frontmatter：在结束符 --- 之前注入 install_source 字段；
  # 若已存在 install_source 字段，则原地替换为 skill-market。
  awk -v sval="$source_value" '
    BEGIN { in_fm = 0; injected = 0; closed = 0 }
    NR == 1 && $0 == "---" { in_fm = 1; print; next }
    in_fm && !closed {
      if ($0 == "---") {
        if (!injected) { print "install_source: " sval; injected = 1 }
        closed = 1
        print
        next
      }
      if ($0 ~ /^[[:space:]]*install_source[[:space:]]*:/) {
        # 已存在 install_source 字段，直接替换
        print "install_source: " sval
        injected = 1
        next
      }
      print
      next
    }
    { print }
  ' "$file" > "$tmp" && mv "$tmp" "$file"
}

# Ensure cleanup on unexpected exit
trap cleanup EXIT

# ─── Step 1: Download ───────────────────────────────────────────────────────────
echo "Downloading skill package from: $URL"
if ! curl -fSL --output "$TEMP_ZIP" "$URL"; then
  echo "Error: Failed to download skill package from '$URL'." >&2
  exit 1
fi

# ─── Step 2: Extract ────────────────────────────────────────────────────────────
echo "Extracting skill package..."
if ! unzip -q -o "$TEMP_ZIP" -d "$TEMP_DIR"; then
  echo "Error: Failed to extract skill package. The ZIP file may be corrupted." >&2
  exit 1
fi

# ─── Step 3 & 4: Validate and locate SKILL.md（大小写不敏感）────────────────────
echo "Validating skill package..."
# 使用 -iname 进行大小写不敏感匹配，兼容 skill.md / Skill.md / SKILL.md 等变体
SKILL_MD_PATH=$(find "$TEMP_DIR" -iname "skill.md" \
  -not -path "*/__MACOSX/*" \
  -not -path "*/.*" \
  -type f -print -quit)

if [[ -z "$SKILL_MD_PATH" ]]; then
  echo "Error: Invalid skill package — SKILL.md not found (已尝试大小写不敏感匹配)." >&2
  exit 1
fi

SKILL_DIR=$(dirname "$SKILL_MD_PATH")
# 提取实际找到的文件名，后续引用均使用该变量
SKILL_MD_NAME=$(basename "$SKILL_MD_PATH")
echo "Found skill root at: $SKILL_DIR (SKILL.md=$SKILL_MD_NAME)"

# ─── Step 5: Remove old version (backup to /tmp) ────────────────────────────────
INSTALL_PATH="${TARGET_DIR}/${NAME}"
if [[ -d "$INSTALL_PATH" ]]; then
  BACKUP_PATH="/tmp/.skill-replaced-${NAME}-$(date +%s)"
  echo "Moving existing version to: $BACKUP_PATH"
  mv "$INSTALL_PATH" "$BACKUP_PATH"
fi

# ─── Step 6: Install ────────────────────────────────────────────────────────────
echo "Installing skill to: $INSTALL_PATH"
mkdir -p "$TARGET_DIR"
mv "$SKILL_DIR" "$INSTALL_PATH"

# ─── Step 7: Inject install_source field into frontmatter ──────────────────────
# 在 SKILL.md frontmatter 中写入 install_source=skill-market，标记技能来源
echo "Tagging skill install_source as 'skill-market' in ${SKILL_MD_NAME} frontmatter..."
if ! inject_install_source_field "${INSTALL_PATH}/${SKILL_MD_NAME}"; then
  echo "Error: Failed to inject install_source field into ${SKILL_MD_NAME} frontmatter." >&2
  exit 1
fi

# ─── Step 8: Verify ─────────────────────────────────────────────────────────────
if [[ ! -f "${INSTALL_PATH}/${SKILL_MD_NAME}" ]]; then
  echo "Error: Verification failed — ${SKILL_MD_NAME} not found at install path." >&2
  exit 1
fi

# ─── Step 9: Cleanup (handled by trap, but be explicit) ─────────────────────────
# trap EXIT will call cleanup()

echo ""
echo "✓ Skill '$NAME' installed successfully to: $INSTALL_PATH"
echo "  The skill is immediately available for use."
exit 0

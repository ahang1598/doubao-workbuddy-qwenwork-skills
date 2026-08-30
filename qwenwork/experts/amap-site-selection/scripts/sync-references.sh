#!/bin/bash
# 将 references/ 下的共享规范同步到每个技能目录内，使每个技能自包含。
#
# 背景：套件内四个技能各自独立触发，不能依赖 ../../ 向上跨目录读取共享文档。
# 因此每个技能目录内自带一份 references/ 副本；本脚本保证副本与根目录源文件一致。
#
# 用法：修改根目录 references/ 下的文件后，执行本脚本，再重新打包。

set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${KIT_DIR}/references"

# 各技能需要的共享文档清单
SKILL_REFS_area_recommend="gateway-auth.md common-api.md scoring-model.md"
SKILL_REFS_site_evaluate="gateway-auth.md common-api.md scoring-model.md"
SKILL_REFS_site_compare="gateway-auth.md common-api.md scoring-model.md financial-params.md"
SKILL_REFS_feasibility_report="gateway-auth.md scoring-model.md financial-params.md"

sync_skill() {
  local skill="$1"
  local refs="$2"
  local dest="${KIT_DIR}/skills/${skill}/references"

  if [ ! -d "${KIT_DIR}/skills/${skill}" ]; then
    echo "  SKIP  ${skill}（技能目录不存在）" >&2
    return 0
  fi

  mkdir -p "$dest"

  # 清掉不再需要的旧副本，避免残留
  for existing in "$dest"/*.md; do
    [ -e "$existing" ] || continue
    local base
    base="$(basename "$existing")"
    case " $refs " in
      *" $base "*) ;;
      *) rm -f "$existing"; echo "  RM    ${skill}/references/${base}" ;;
    esac
  done

  for ref in $refs; do
    if [ ! -f "${SRC}/${ref}" ]; then
      echo "  FAIL  源文件缺失：references/${ref}" >&2
      return 1
    fi
    cp "${SRC}/${ref}" "${dest}/${ref}"
    echo "  OK    ${skill}/references/${ref}"
  done
}

echo "同步共享规范到各技能目录（源：references/）"
sync_skill "area-recommend"     "$SKILL_REFS_area_recommend"
sync_skill "site-evaluate"      "$SKILL_REFS_site_evaluate"
sync_skill "site-compare"       "$SKILL_REFS_site_compare"
sync_skill "feasibility-report" "$SKILL_REFS_feasibility_report"
echo "完成。请重新打包后再提交。"

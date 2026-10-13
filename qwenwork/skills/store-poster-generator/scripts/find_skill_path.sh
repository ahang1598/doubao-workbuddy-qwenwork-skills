#!/usr/bin/env bash
set -euo pipefail

template='find "AGENT_WORK_ROOT/.skills" -name "SKILL.md" | while read -r f; do [ "$(head -1 "$f")" = "---" ] && [ "$(head -2 "$f" | tail -1)" = "name: store-poster-generator" ] && dirname "$f" && break; done'
echo "✅ 技能路径: $(eval "$(echo "$template" | sed "s|AGENT_WORK_ROOT|${AGENT_WORK_ROOT}|g")")"



#!/usr/bin/env bash
# Search academic papers — OpenAlex primary, Semantic Scholar fallback (v1.1 ima适配)
# Usage: ./search.sh "query" [limit] [sort] [page]
# Sort: relevance (default), cites, date
# v1.1 20260907: OpenAlex 429限流时自动降级 Semantic Scholar（免费无key）；输出格式统一

set -euo pipefail

QUERY="${1:?Usage: ./search.sh \"query\" [limit] [sort] [page]}"
LIMIT="${2:-10}"
SORT_KEY="${3:-relevance}"
PAGE="${4:-1}"
MAILTO="paper-search@example.com"

case "$SORT_KEY" in
  relevance) SORT="relevance_score:desc" ;;
  cites)     SORT="cited_by_count:desc" ;;
  date)      SORT="publication_date:desc" ;;
  *)         SORT="$SORT_KEY" ;;
esac

ENCODED=$(jq -rn --arg q "$QUERY" '$q | @uri')

URL="https://api.openalex.org/works?search=${ENCODED}&per_page=${LIMIT}&page=${PAGE}&sort=${SORT}&mailto=${MAILTO}"

RESP=$(curl -s --max-time 25 "$URL" || echo "")

# 判断 OpenAlex 是否限流/失败
if echo "$RESP" | grep -q '"Rate limit exceeded"'; then
  echo "[backend] OpenAlex 限流(429)，自动降级 Semantic Scholar..." >&2
  # Semantic Scholar: relevance 固定；sort 仅支持 relevance，date 映射 year:desc, cites 映射 citationCount:desc
  S2_RESP=$(curl -s --max-time 25 "https://api.semanticscholar.org/graph/v1/paper/search?query=${ENCODED}&limit=${LIMIT}&fields=title,year,citationCount,authors,externalIds,abstract,url" || echo "")
  if ! echo "$S2_RESP" | grep -q '"code": *"429"'; then
    echo "[backend] OpenAlex 限流(429)，已降级 Semantic Scholar" >&2
    echo "$S2_RESP" | jq -r --argjson offset "$(( (PAGE - 1) * LIMIT ))" '
      "Backend: Semantic Scholar | Total: \(.total // "?")\n",
      ((.data // []) | to_entries[] |
        "\(.key + 1 + $offset). [\(.value.citationCount // 0) cites] (\(.value.year // "?")) \(.value.title)",
        "   Authors: \([.value.authors[:3][].name] | join(", "))",
        "   DOI: \(.value.externalIds.DOI // "N/A")",
        "   URL: \(.value.url // "N/A")",
        (if .value.abstract then
          "   Abstract: \(.value.abstract | .[0:250])..."
        else
          "   Abstract: N/A"
        end),
        ""
      )
    ' && [ "$(echo "$S2_RESP" | jq '.data | length // 0')" -gt 0 ] && exit 0
  fi
  # S2 限流/空结果 → 第三级 Crossref（免费宽松）
  echo "[backend] 降级 Crossref..." >&2
  CR_ROWS="$LIMIT"
  CR_OFFSET=$(( (PAGE - 1) * LIMIT ))
  CR_RESP=$(curl -s --max-time 25 "https://api.crossref.org/works?query=${ENCODED}&rows=${CR_ROWS}&offset=${CR_OFFSET}&select=title,author,DOI,abstract,issued,is-referenced-by-count&mailto=${MAILTO}" || echo "")
  if echo "$CR_RESP" | jq -e '.message.items' >/dev/null 2>&1; then
    echo "$CR_RESP" | jq -r --argjson offset "$CR_OFFSET" '
      "Backend: Crossref | Total: \(.message."total-results" // "?")\n",
      ((.message.items // []) | to_entries[] |
        "\(.key + 1 + $offset). [\(.value."is-referenced-by-count" // 0) cites] (\(.value.issued."date-parts"[0][0] // "?")) \(.value.title[0] // "N/A")",
        "   Authors: \([.value.author[:3][].family // .value.author[:3][].name] | join(", "))",
        "   DOI: \(.value.DOI // "N/A")",
        (if .value.abstract then
          "   Abstract: \(.value.abstract | gsub("<[^>]*>";"") | gsub("\\s+";" ") | .[0:250])..."
        else
          "   Abstract: N/A"
        end),
        ""
      )
    ' && exit 0
  fi
  echo "[error] 三个学术后端(OpenAlex/SemanticScholar/Crossref)均失败，请稍后重试" >&2
  exit 1
fi

OFFSET=$(( (PAGE - 1) * LIMIT ))

echo "$RESP" | jq -r --argjson offset "$OFFSET" '
  "Backend: OpenAlex | Total results: \(.meta.count // "?") | Page \(.meta.page // "?")/\(((.meta.count // 0) / (.meta.per_page // 1) | ceil)) | Showing \(.meta.per_page // "?") per page\n",
  (.results // [] | to_entries[] |
    "\(.key + 1 + $offset). [\(.value.cited_by_count) cites] (\(.value.publication_year)) \(.value.title)",
    "   Authors: \([.value.authorships[:3][].author.display_name] | join(", "))",
    "   DOI: \(.value.doi // "N/A")",
    "   URL: \(.value.primary_location.landing_page_url // .value.id // "N/A")",
    "   OpenAlex ID: \(.value.id // "N/A")",
    (if .value.abstract_inverted_index then
      "   Abstract: \([.value.abstract_inverted_index | to_entries[] | .key as $w | .value[] | {pos: ., word: $w}] | sort_by(.pos) | [.[].word] | join(" ") | .[0:250])..."
    else
      "   Abstract: N/A"
    end),
    ""
  )
'

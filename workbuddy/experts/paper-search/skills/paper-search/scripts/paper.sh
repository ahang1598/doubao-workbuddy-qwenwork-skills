#!/usr/bin/env bash
# Get details for a single paper by DOI or OpenAlex ID
# Usage: ./paper.sh "https://doi.org/10.1038/..." or ./paper.sh "W1234567890"

set -euo pipefail

ID="${1:?Usage: ./paper.sh <DOI_URL or OpenAlex_ID>}"
MAILTO="openalex-skill@example.com"

# If it looks like an OpenAlex ID (starts with W or https://openalex.org)
if [[ "$ID" =~ ^W[0-9] ]]; then
  URL="https://api.openalex.org/works/${ID}?mailto=${MAILTO}"
elif [[ "$ID" =~ ^https://openalex.org ]]; then
  URL="https://api.openalex.org/works/${ID##*/}?mailto=${MAILTO}"
else
  # Assume DOI or DOI URL
  # If full DOI URL, strip prefix
  if [[ "$ID" =~ ^https://doi.org/ ]]; then
    DOI_PATH="${ID#https://doi.org/}"
    ENCODED=$(jq -rn --arg q "$DOI_PATH" '$q | @uri')
    URL="https://api.openalex.org/works/https://doi.org/${ENCODED}?mailto=${MAILTO}"
  else
    ENCODED=$(jq -rn --arg q "$ID" '$q | @uri')
    URL="https://api.openalex.org/works/doi:${ENCODED}?mailto=${MAILTO}"
  fi
fi

curl -s "$URL" | jq -r '
  "\(.title)\n",
  "Year:       \(.publication_year)",
  "Citations:  \(.cited_by_count)",
  "DOI:        \(.doi // "N/A")",
  "OpenAlex:   \(.id)",
  "Type:       \(.type)",
  "Source:     \(.primary_location.source.display_name // "N/A")",
  "OA:         \(if .open_access.is_oa then "Yes (\(.open_access.oa_url // "no url"))" else "No" end)",
  "",
  "Authors:",
  (.authorships[] |
    "  - \(.author.display_name) (\(.institutions[:1] | map(.display_name) | join(", ")))"
  ),
  "",
  "Concepts:",
  (.concepts[:8][] | "  - \(.display_name) (score: \(.score))"),
  "",
  (if .abstract_inverted_index then
    "Abstract:\n\([.abstract_inverted_index | to_entries[] | .key as $w | .value[] | {pos: ., word: $w}] | sort_by(.pos) | [.[].word] | join(" "))"
  else
    "Abstract: N/A"
  end),
  "",
  "Related works:",
  (.related_works[:5][] | "  \(.)")
'

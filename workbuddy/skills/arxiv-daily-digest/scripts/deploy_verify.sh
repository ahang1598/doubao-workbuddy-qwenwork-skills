#!/usr/bin/env bash
# arXiv daily digest — Stage 4: deploy publish/index.html to Cloudflare Pages
# and verify the (user-supplied) fixed URL. Idempotent: deploys in place to the
# same project.
#
# Usage:
#   bash deploy_verify.sh <workspace> <url> <project-name>
#
# Required environment (supplied by the user / invoking agent — NEVER hardcode):
#   DEPLOY_SCRIPT   path to a Cloudflare Pages deploy script that supports
#                   `--project-name`, injects a Basic Auth _worker.js, and reads
#                   CF_PAGES_TOKEN / CF_AUTH_FILE env vars.
#   CF_PAGES_TOKEN  Cloudflare API token (read by the deploy script)
#   BASIC_USER      Basic Auth username for the published site
#   BASIC_PASS      Basic Auth password for the published site
#
# Optional environment:
#   CF_ACCOUNT_ID        Cloudflare account id (falls back to deploy script default)
#   CF_AUTH_WORKER       path to _worker.js (Basic Auth enforcer)
#   DEPLOY_PROXY_STRIP   "1" (default) strips HTTP(S)_PROXY before network calls;
#                        set to "0" only if your host needs the ambient proxy.
set -euo pipefail

WS="${1:?usage: deploy_verify.sh <workspace> <url> <project-name>}"
URL="${2:?usage: deploy_verify.sh <workspace> <url> <project-name>}"
PROJECT="${3:?usage: deploy_verify.sh <workspace> <url> <project-name>}"

: "${DEPLOY_SCRIPT:?set DEPLOY_SCRIPT to your Cloudflare Pages deploy script path}"
: "${CF_PAGES_TOKEN:?set CF_PAGES_TOKEN (Cloudflare API token)}"
: "${BASIC_USER:?set BASIC_USER (Basic Auth username)}"
: "${BASIC_PASS:?set BASIC_PASS (Basic Auth password)}"

STRIP="${DEPLOY_PROXY_STRIP:-1}"
PFX=()
if [ "$STRIP" = "1" ]; then PFX=(env -u HTTP_PROXY -u HTTPS_PROXY); fi

# Write Basic Auth credentials to a TEMP file so we override the deploy script's
# built-in default user (do NOT leak the password into the shell history/log).
AUTH_TMP="$(mktemp)"
printf 'BASIC_USER=%s\nBASIC_PASS=%s\n' "$BASIC_USER" "$BASIC_PASS" > "$AUTH_TMP"
trap 'rm -f "$AUTH_TMP"' EXIT
export CF_AUTH_FILE="$AUTH_TMP"
export CF_PAGES_TOKEN
[ -n "${CF_ACCOUNT_ID:-}" ] && export CF_ACCOUNT_ID
[ -n "${CF_AUTH_WORKER:-}" ] && export CF_AUTH_WORKER

echo "== publish dir contents =="
ls -la "$WS/publish"

echo "== deploy (project: $PROJECT, url: $URL) =="
"${PFX[@]}" bash "$DEPLOY_SCRIPT" "$WS/publish" --project-name "$PROJECT" --branch main

echo "== verify =="
code_auth=$("${PFX[@]}" curl -s -o /tmp/verify_digest.html -w '%{http_code}' -u "$BASIC_USER:$BASIC_PASS" "$URL")
code_noauth=$("${PFX[@]}" curl -s -o /dev/null -w '%{http_code}' "$URL")
cards=$(grep -c '<div class="card">' /tmp/verify_digest.html || true)
size=$(wc -c < /tmp/verify_digest.html | tr -d ' ')
echo "with-auth=$code_auth without-auth=$code_noauth cards=$cards size=$size"
if [ "$code_auth" != "200" ] || [ "$code_noauth" != "401" ] || [ "$cards" -lt 1 ]; then
  echo "VERIFY FAILED"; exit 1
fi
echo "OK: $URL serves the new digest with Basic Auth enforced."

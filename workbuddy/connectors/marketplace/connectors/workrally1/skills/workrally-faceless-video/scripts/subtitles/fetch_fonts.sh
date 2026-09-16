#!/usr/bin/env bash
# Fetch the caption faces into this folder.
#
# Font binaries cannot ship inside a workflow bundle (the resource loader serves
# text files only) and the sandbox image carries just Metropolis and Montserrat,
# so the first caption command of a run calls this script.
#
# Behaviour: idempotent (an existing valid file is kept), NON-FATAL per font (a
# face that will not arrive is reported and the burners fall back), quiet on
# success. Run it once per sandbox, before the burn.
#
# Sources, per face, in order:
#   1. $FONT_BASE_URL (default: the Higgsfield public assets prefix). Static
#      files at the exact weights the burners expect — the authoritative tier.
#   2. The upstream open-licence file. Some of these are VARIABLE fonts whose
#      default instance is the wrong weight (measured 2026-07-29 in the sandbox:
#      TikTok Sans defaults to Light, Montserrat to Thin — hairline captions), so
#      for those faces the script pins the weight with fontTools and saves a
#      static instance. If that is impossible the face is SKIPPED rather than
#      written thin: the burner's fallback chain produces better captions than a
#      hairline default.
#   3. Nothing — the burner falls back (tiktok -> montserrat -> caveat) and
#      re-checks glyph coverage, so a missing face never ships a blank label.
#
# Usage: bash scripts/subtitles/fetch_fonts.sh [--force] [--quiet]
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fonts"
BASE="${FONT_BASE_URL:-https://static.higgsfield.ai/faceless/fonts}"
GF="https://github.com/google/fonts/raw/main"
FORCE=0
QUIET=0
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    --quiet) QUIET=1 ;;
    *) echo "unknown arg: $a" >&2; exit 2 ;;
  esac
done
mkdir -p "$DIR"

# file | upstream url | axes to pin (empty = the file is already the right weight)
FONTS=(
  "TikTokSans-Bold.ttf|$GF/ofl/tiktoksans/TikTokSans%5Bopsz,slnt,wdth,wght%5D.ttf|wght=700,opsz=36,wdth=100,slnt=0"
  "Montserrat-ExtraBold.ttf|$GF/ofl/montserrat/Montserrat%5Bwght%5D.ttf|wght=800"
  "Anton-Regular.ttf|$GF/ofl/anton/Anton-Regular.ttf|"
  "PatrickHand-Regular.ttf|$GF/ofl/patrickhand/PatrickHand-Regular.ttf|"
  "PermanentMarker-Regular.ttf|$GF/apache/permanentmarker/PermanentMarker-Regular.ttf|"
  "Caveat-Regular.ttf|$GF/ofl/caveat/Caveat%5Bwght%5D.ttf|"
  # WorkRally port: none of the faces above covers CJK, so Chinese captions would burn
  # as tofu boxes unless a system CJK font happens to be installed. Noto Sans SC is the
  # portable fallback; it is large and this fetch is non-fatal, so a failure here just
  # means the burner needs --sub-font pointed at a local CJK face.
  "NotoSansSC-Bold.ttf|$GF/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf|wght=700"
)

# A real font starts with 0x00010000 (TrueType), "OTTO", "true" or "ttcf";
# anything else (an HTML error page, an empty body) is rejected.
valid_font() {
  local f="$1"
  [[ -s "$f" ]] || return 1
  [[ "$(wc -c <"$f")" -ge 20000 ]] || return 1
  local magic
  magic="$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')"
  case "$magic" in
    00010000|4f54544f|74727565|74746366) return 0 ;;
    *) return 1 ;;
  esac
}

fetch() { # url, out — writes only a verified font
  local url="$1" out="$2"
  curl -fsSL --retry 2 --retry-all-errors --max-time 60 -o "$out.part" "$url" 2>/dev/null || { rm -f "$out.part"; return 1; }
  if valid_font "$out.part"; then mv -f "$out.part" "$out"; return 0; fi
  rm -f "$out.part"; return 1
}

FONTTOOLS=""   # "" unknown, "yes" available, "no" unavailable
have_fonttools() {
  [[ -n "$FONTTOOLS" ]] && { [[ "$FONTTOOLS" == yes ]] && return 0 || return 1; }
  if python3 -c "import fontTools" >/dev/null 2>&1; then FONTTOOLS=yes; return 0; fi
  python3 -m pip install -q fonttools >/dev/null 2>&1
  if python3 -c "import fontTools" >/dev/null 2>&1; then FONTTOOLS=yes; return 0; fi
  FONTTOOLS=no; return 1
}

instance() { # src, dst, "wght=700,opsz=36"
  python3 - "$1" "$2" "$3" <<'PY' >/dev/null 2>&1
import sys
from fontTools import ttLib
from fontTools.varLib import instancer
src, dst, spec = sys.argv[1], sys.argv[2], sys.argv[3]
axes = {}
for part in spec.split(","):
    if not part.strip():
        continue
    name, _, value = part.partition("=")
    axes[name.strip()] = float(value)
font = ttLib.TTFont(src)
static = instancer.instantiateVariableFont(font, axes, inplace=False, updateFontNames=True)
static.save(dst)
PY
}

got=(); missing=()
for entry in "${FONTS[@]}"; do
  IFS='|' read -r file url axes <<<"$entry"
  out="$DIR/$file"
  if [[ $FORCE -eq 0 ]] && valid_font "$out"; then got+=("$file (cached)"); continue; fi
  if fetch "$BASE/$file" "$out"; then got+=("$file (assets)"); continue; fi
  if [[ -z "$axes" ]]; then
    if fetch "$url" "$out"; then got+=("$file (upstream)"); continue; fi
    missing+=("$file"); continue
  fi
  # variable upstream: pin the weight or skip the face entirely
  tmp="$DIR/.$file.var"
  if ! fetch "$url" "$tmp"; then rm -f "$tmp"; missing+=("$file"); continue; fi
  if have_fonttools && instance "$tmp" "$out" "$axes" && valid_font "$out"; then
    rm -f "$tmp"; got+=("$file (upstream, pinned $axes)")
  else
    rm -f "$tmp" "$out"
    missing+=("$file [variable upstream, weight could not be pinned]")
  fi
done

if [[ $QUIET -eq 0 ]]; then
  printf 'fonts dir: %s\n' "$DIR" >&2
  for g in "${got[@]:-}"; do [[ -n "$g" ]] && printf '  ok      %s\n' "$g" >&2; done
  for m in "${missing[@]:-}"; do [[ -n "$m" ]] && printf '  MISSING %s\n' "$m" >&2; done
fi

if [[ ${#missing[@]} -gt 0 ]]; then
  printf 'WARN: %d face(s) unavailable — the burner falls back (tiktok -> montserrat -> caveat) and re-checks glyph coverage. Upload static files to %s to make tier 1 authoritative.\n' \
    "${#missing[@]}" "$BASE" >&2
fi

# Never fail the caption step over a font: a fallback look is still a delivered video.
exit 0

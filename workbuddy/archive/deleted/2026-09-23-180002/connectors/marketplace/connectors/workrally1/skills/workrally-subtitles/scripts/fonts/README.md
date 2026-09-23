# Subtitle fonts

Binaries are NOT committed with the skill, so nothing here is a `.ttf` until something
downloads it.

**Do not curl these by hand: run the fetch script.**

```bash
bash <skill 目录>/scripts/fetch_fonts.sh          # idempotent, non-fatal per font
bash <skill 目录>/scripts/fetch_fonts.sh --force  # re-download everything
```

It writes into THIS folder, which is where both burners look
(`subtitle_paper_burn.py` resolves `<script dir>/fonts/<file>`, `burn_caps_clean.sh`
passes the folder to libass as `fontsdir`). Sources per face: `$FONT_BASE_URL` when
set (an internal mirror — unset by default), then the upstream open-licence URL on
Google Fonts, then nothing. A missing face is never fatal.

The fetch needs network access to `github.com/google/fonts`. Behind a proxy, set
`FONT_BASE_URL` to a mirror that serves the exact filenames listed below.

## TikTok Sans — the default face for `bold` and `clean`

The native TikTok/Shorts caption face, open-sourced by TikTok under the SIL Open Font
License 1.1. Latin + Cyrillic + Greek (460+ languages). `subtitle_paper_burn.py`
expects `TikTokSans-Bold.ttf`; `burn_caps_clean.sh` asks libass for the family name
`TikTok Sans`.

## Chinese captions

**None of the Latin/Cyrillic faces below carry a single CJK glyph.** For Chinese:

1. `fetch_fonts.sh` also pulls `NotoSansSC-Bold.ttf` (`--font-key notosc`). Pinning
   its weight needs `fontTools`; without it the face is skipped rather than written
   hairline-thin.
2. `subtitle_paper_burn.py` checks glyph coverage against the real caption text and
   falls back to a **system** CJK face — PingFang SC / Hiragino Sans GB / STHeiti on
   macOS, Noto Sans CJK on Linux, Microsoft YaHei on Windows — printing a warning.
3. `burn_caps_clean.sh` goes through libass/fontconfig, which does not always see a
   system `.ttc`. Prefer `subtitle_paper_burn.py` for Chinese: it loads the font file
   by absolute path. Either way, extract a frame and confirm the glyphs rendered.

## The other keys

| `--font-key` | file | look |
|---|---|---|
| `patrick` | `PatrickHand-Regular.ttf` | legible handwritten (paper default) |
| `caveat` | `Caveat-Regular.ttf` | flowing cursive script |
| `marker` | `PermanentMarker-Regular.ttf` | bold marker, punchy (Latin only) |
| `anton` | `Anton-Regular.ttf` | heavy condensed display |
| `montserrat` | `Montserrat-ExtraBold.ttf` | clean geometric caps |
| `tiktok` | `TikTokSans-Bold.ttf` | native TikTok caps (**bold default**) |
| `notosc` | `NotoSansSC-Bold.ttf` | Simplified Chinese |
| `metropolis` | `Metropolis-ExtraBold.ttf` | optional drop-in |

All are SIL OFL and downloadable from Google Fonts. A missing file is not fatal:
the burner falls back to `notosc` → `tiktok` → `montserrat` → `caveat` → a system CJK
face and says so, and it re-checks glyph coverage before drawing (a Latin-only face
never ships an empty Chinese label).

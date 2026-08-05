# Stack Variants

React Bits ships every component in 4 variants. Pick exactly one per project (mixing variants in the same project is allowed but discouraged).

## The four variants

| Variant | Suffix | When |
|---|---|---|
| TypeScript + Tailwind | `-TS-TW` | Project has `tsconfig.json` AND `tailwind.config.*` |
| TypeScript + plain CSS | `-TS-CSS` | TS project, no Tailwind |
| JavaScript + Tailwind | `-JS-TW` | No tsconfig, Tailwind present |
| JavaScript + plain CSS | `-JS-CSS` | No tsconfig, no Tailwind |

## Resolution rules (used by Phase 4)

```
def resolve_variant(project):
    has_ts = exists("tsconfig.json")
    has_tw = exists_any("tailwind.config.js",
                        "tailwind.config.ts",
                        "tailwind.config.mjs",
                        "tailwind.config.cjs",
                        "@tailwind base") in css_files

    ts_part = "TS" if has_ts else "JS"
    style_part = "TW" if has_tw else "CSS"
    return f"{ts_part}-{style_part}"
```

## Edge cases

### TS file count is low (< 10% of source)
Project has tsconfig.json scaffolded but barely uses TS — recommend matching majority. Confirm with user and write to profile.

### Tailwind v3 vs v4
ReactBits-TW variants currently target Tailwind v3 syntax. Tailwind v4 (CSS-first config, no `tailwind.config.js`) — detect via `@theme` block in globals.css. Currently treat v4 same as TW; flag to user that they may need to adapt utility class output.

### CSS Modules / styled-components / Emotion
ReactBits-CSS variants ship plain CSS files. If project uses CSS Modules or CSS-in-JS, the CSS variant still works but isn't idiomatic. Suggest the user wrap or migrate the styles, or pick TW variant if Tailwind is acceptable.

### Mixed JS + TS project
Some legacy projects have `.tsconfig` but the target file is JS. Inspect the actual page where the component will land; match its language. If still ambiguous, ask once.

## Install command format (verified from official README)

```bash
npx shadcn@latest add @react-bits/<ComponentName>-<VARIANT>
```

Examples:
- `npx shadcn@latest add @react-bits/BlurText-TS-TW`
- `npx shadcn@latest add @react-bits/Aurora-JS-CSS`

## What does NOT change between variants

- Component behavior, props, animation timing
- Peer dependencies (motion, gsap, three, ogl)
- Live demo URL on reactbits.dev (one URL per component, demo shows all variants via tabs)

## What DOES change

- File extension (`.tsx` vs `.jsx`)
- Type definitions (TS variants ship `.d.ts` types inline in `.tsx`)
- Style import (`import './X.css'` vs Tailwind utility classes)
- File location after install: `src/components/ui/<ComponentName>.tsx` (or `.jsx`)

## Profile note

Once resolved, write the variant to `.qoderwork/reactbits-profile.md` under `Stack`. This becomes USER-CONFIRMED — do not re-detect on subsequent runs unless user explicitly changes their stack.

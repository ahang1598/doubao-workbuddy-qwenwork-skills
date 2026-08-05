# Peer Dependencies Matrix

React Bits components depend on one of four animation engines (or pure React + CSS). Knowing which engine is critical for Phase 2 sniffing — projects that already use one engine should prefer same-engine components for bundle size and consistency.

## The four engine families

| Engine | npm package | Bundle size (gzip) | What it's for |
|---|---|---|---|
| **motion** | `motion` (formerly `framer-motion`) | ~30 KB | Most text animations and UI components — declarative React-first API |
| **GSAP** | `gsap` + sometimes `@gsap/react` | ~70 KB | Heavy timeline animations, scroll-driven effects, complex sequencing |
| **three.js** | `three` + `@react-three/fiber` + `@react-three/drei` | ~600 KB | 3D backgrounds, WebGL effects |
| **OGL** | `ogl` | ~50 KB | Lightweight WebGL backgrounds (where three.js is overkill) |
| **none** | — | 0 KB | Pure CSS / React state animations |

## Engine matching strategy (used by Phase 2)

When sniffing detects an existing engine in the project's `package.json`:

```
project_engine = first_match_in_package_json([
    "motion",            # latest name (also detect "framer-motion" as alias)
    "framer-motion",
    "gsap",
    "three",             # implies @react-three/fiber likely
    "ogl",
])

candidate_score += 4  # if candidate component uses same engine
candidate_score -= 3  # if candidate would introduce a new heavy engine (three/ogl)
candidate_score -= 1  # if candidate would introduce a new lightweight engine (motion/gsap)
```

## Bundle impact thresholds (LOCKED, used in Phase 4 pre-install check)

| Adding... | When project doesn't already have it | Action |
|---|---|---|
| `motion` (~30 KB) | Project has none | Install silently |
| `gsap` (~70 KB) | Project has none | Install silently, mention in delivery |
| `three` (~600 KB) | Project has none | **Stop, ask user — bundle impact is significant** |
| `ogl` (~50 KB) | Project has none | Install silently, mention WebGL implication |
| Same engine already present | — | Install silently |

## Coverage by category (approximate, verified from official README)

> Note: exact per-component peer-deps need to be filled by `scripts/crawl-catalog.sh`. The patterns below are the high-level distribution.

| Category | Typical engine | Notes |
|---|---|---|
| **text-animations** | mostly `motion`, some `gsap` | Lightest category; safe defaults |
| **animations** (Animated UI primitives) | mostly `motion` | Container-style components like AnimatedContent, Magnet, Dock |
| **components** | mostly `motion`, some pure CSS | Cards, buttons, navigation animations |
| **backgrounds** | mostly `ogl` or `three` | The heavy category — always check before installing |

## Detection heuristics

In `package.json`:

```json
{
  "dependencies": {
    "motion": "^12.0.0"           // motion engine
    "framer-motion": "^11.0.0"    // older name, same engine
    "gsap": "^3.12.0"              // GSAP engine
    "@gsap/react": "^2.0.0"        // GSAP + React hooks
    "three": "^0.170.0"            // three.js
    "@react-three/fiber": "^9.0.0" // react bindings — strong 3D signal
    "@react-three/drei": "^10.0.0" // helpers — heavy 3D usage
    "ogl": "^1.0.0"                // OGL engine
  }
}
```

## Refresh

This file is `crawl-catalog.sh`-driven. The script fills in **per-component** peer deps from `reactbits.dev` once it runs successfully. Until then, fall back to category-level defaults above for sniffing.

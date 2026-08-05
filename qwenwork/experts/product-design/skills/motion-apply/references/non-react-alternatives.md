# Non-React Animation Alternatives

When the project is not React, Phase 0b recommends libraries from this list. Preference order: framework-native > lightweight third-party > full-featured third-party.

## Decision table

| Framework | Simple (≤ 30 lines) | Medium | Heavy (3D / particles / physics) |
|-----------|-------------------|--------|----------------------------------|
| **Vue** | Write CSS/JS directly | `@vueuse/motion` or GSAP | Three.js + TresJS |
| **Svelte** | Write CSS/JS directly; prefer built-in `transition:` | `svelte-motion` or GSAP | threlte (Three.js for Svelte) |
| **Angular** | Write CSS/JS directly; `@angular/animations` | GSAP or Motion One | Three.js direct |
| **Astro** | Write CSS/JS directly | GSAP (vanilla) or Motion One | Three.js direct |
| **Vanilla JS/HTML** | Write CSS/JS directly | GSAP or anime.js | Three.js or OGL |
| **jQuery legacy** | Write CSS/JS directly | GSAP (jQuery-friendly) | Three.js |

## Library profiles

### GSAP (recommended default for complex effects)
- Works everywhere — framework-agnostic, pure JS
- 70 KB gzip, zero dependencies
- Best for: scroll-driven animation, timeline sequencing, text splitting
- Install: `npm install gsap`
- Since 2024 (Webflow acquisition): all plugins free, including ScrollTrigger / SplitText / MorphSVG
- Note: this is the same engine used by many React Bits components internally

```js
// Example: scroll-triggered fade-in
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
gsap.registerPlugin(ScrollTrigger);

gsap.from(".hero-title", {
  opacity: 0, y: 60, duration: 1,
  scrollTrigger: { trigger: ".hero-title", start: "top 80%" }
});
```

### Motion One (lightweight, modern)
- 18 KB gzip, Web Animations API based
- Best for: simple declarative animations without the full GSAP weight
- Install: `npm install motion`
- Works with any framework or vanilla JS
- Note: this is the standalone version of the engine behind `framer-motion`

```js
import { animate } from "motion";
animate(".box", { opacity: [0, 1], y: [20, 0] }, { duration: 0.6 });
```

### anime.js (mid-weight, good API)
- 17 KB gzip
- Best for: staggered animations, SVG morphing, simple timelines
- Install: `npm install animejs`
- Simpler API than GSAP but less ecosystem (no ScrollTrigger equivalent)

```js
import anime from "animejs";
anime({ targets: ".item", translateY: [-30, 0], opacity: [0, 1], delay: anime.stagger(100) });
```

### Lottie (pre-made animations from After Effects)
- Best for: playing designer-exported animations (JSON format)
- Install: `npm install lottie-web` (vanilla) or framework-specific wrappers
- Not for code-driven animation — it's a player, not an authoring tool
- Use when: the animation was designed in After Effects / Rive / Lottie and exported as JSON

### Three.js (3D / WebGL)
- ~600 KB gzip — heavy, only recommend when 3D is truly needed
- Framework wrappers: TresJS (Vue), threlte (Svelte), @react-three/fiber (React)
- Best for: 3D backgrounds, particle systems, shader effects
- Always warn about bundle impact before recommending

### OGL (lightweight WebGL)
- ~50 KB gzip, much lighter than Three.js
- Best for: 2D WebGL effects (fluid, noise, gradient shaders) that CSS can't do
- No framework wrappers — vanilla JS only, needs WebGL knowledge

## Framework-native solutions (always prefer first)

### Vue
```vue
<!-- Built-in transition -->
<Transition name="fade">
  <div v-if="show">Content</div>
</Transition>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
```

For more control: `@vueuse/motion` (declarative, 10 KB)
```vue
<script setup>
import { useMotion } from '@vueuse/motion'
</script>
<template>
  <div v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0 }">Hello</div>
</template>
```

### Svelte
```svelte
<!-- Built-in transitions (zero-dep, tree-shaken) -->
<script>
  import { fade, fly, slide } from 'svelte/transition';
  let visible = true;
</script>

{#if visible}
  <div transition:fly={{ y: 20, duration: 300 }}>Content</div>
{/if}
```

For spring physics: `svelte/motion` (built-in `spring()` and `tweened()` stores).

### Angular
```typescript
// Built-in @angular/animations
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  animations: [
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
```

### Vanilla CSS (no JS needed)
```css
/* Fade-in on scroll using Intersection Observer + CSS class toggle */
.reveal { opacity: 0; transform: translateY(20px); transition: all 0.6s ease; }
.reveal.visible { opacity: 1; transform: translateY(0); }
```
```js
// 6 lines of JS
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
```

## When to NOT recommend a library

If the user asks for any of these, just write CSS/JS directly — a library is overkill:
- Fade in/out
- Hover effects (scale, color, shadow)
- Smooth scroll
- Simple loading spinner
- Gradient / shimmer text
- Basic slideshow (CSS-only or < 20 lines JS)
- Tooltip show/hide
- Accordion expand/collapse
- Progress bar animation
- Cursor custom shape (CSS `cursor:` or small JS)

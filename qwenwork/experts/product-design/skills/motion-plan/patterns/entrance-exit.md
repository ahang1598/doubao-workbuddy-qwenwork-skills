# Entrance & Exit Patterns

## Entrance Fundamentals

**Always**: ease-out (decelerate). Enter fast, land gently.
**Never**: linear for spatial entrances. Never opacity-only for important elements.
**Rule**: Entrance duration ≥ exit duration (entrances 30-50% longer than exits).

## Entrance by Element Type

| Element | From | Duration | Properties | Easing |
|---------|------|----------|------------|--------|
| Tooltip | Below/above target, 8-12px | 80-120ms | position + opacity | ease-out |
| Toast / notification | Top or bottom edge, 20-30px | 200-300ms | position + opacity + scale(0.95→1.0) | ease-out |
| Dropdown menu | Above trigger, 8-12px | 120-180ms | position + opacity + scale(0.95→1.0) | ease-out |
| Modal / dialog | Center, scale(0.95→1.0) | 300-400ms | scale + opacity | ease-out |
| Card (in list) | Below, 15-25px | 200-350ms | position + opacity | ease-out |
| Page / route | From navigation direction | 400-600ms | position + opacity | ease-out |
| Hero section | Below, 30-50px | 600-1000ms | position + opacity + scale | ease-out |
| Sidebar / drawer | Off-screen edge | 250-350ms | position (translateX) | ease-out |

## Entrance by Personality

| Personality | Displacement | Duration | Easing | Extra |
|-------------|-------------|----------|--------|-------|
| Playful | 30-50px, arcs | 200-300ms | ease-out-back | Overshoot 10-15%, squash on land |
| Premium | 15-25px, straight | 400-600ms | (0.4, 0, 0.2, 1) | Subtle, minimal properties |
| Corporate | 15-25px, straight | 200-350ms | (0.2, 0, 0, 1) | Clean, predictable |
| Energetic | 40-80px, diagonal | 150-250ms | ease-out-expo | Large scale change, bold |

## Common Entrance Patterns

### Fade Up (most versatile)
Start: opacity 0, translateY(20-30px). End: opacity 1, translateY(0).
- Standard for cards, content blocks, text sections
- Distance scales with element size: small=15px, large=40px

### Scale In (attention-drawing)
Start: opacity 0, scale(0.9-0.95). End: opacity 1, scale(1.0).
- Best for modals, dialogs, notifications, images
- Add shadow growth as secondary (50ms delay)

### Slide In (directional)
Start: translateX(100%) or translateX(-100%). End: translateX(0).
- Best for sidebars, drawers, slide-over panels
- Direction matches logical origin (nav from left, detail from right)

### Reveal (dramatic)
Start: clip-path or overflow:hidden masking. End: fully revealed.
- Best for hero images, feature sections, onboarding
- Wipe direction implies reading direction or attention flow

### Blur In (premium)
Start: opacity 0, filter:blur(4-8px). End: opacity 1, filter:blur(0).
- Best for text, hero sections, image overlays
- Slower than fade-up (400-800ms); use sparingly

## Exit Fundamentals

**Always**: ease-in (accelerate). Start gently, leave fast.
**Rule**: Exit duration = 65-75% of entrance duration.
**Priority**: Get out of the way — exits should feel swift, not theatrical.

## Exit Patterns

### Fade Down (reverse of fade-up)
End: opacity 0, translateY(10-15px). Shorter displacement than entrance.
- Exit distance = 50-70% of entrance distance (leaving is quicker)

### Scale Out
End: opacity 0, scale(0.9-0.95).
- For modals: scale down + fade simultaneously
- For notifications: scale to 0.8 + slide to edge

### Slide Out
End: translateX(-100%) or off-screen in departure direction.
- Direction consistency: if it entered from left, it exits to left
- Exception: swipe-to-dismiss follows finger direction

### Collapse (for removing items)
1. Content fades (100ms)
2. Height collapses (200ms, ease-in-out)
3. Siblings shift to fill gap (200ms, starts at step 2)

## Enter ↔ Exit Asymmetry

| Aspect | Entrance | Exit |
|--------|----------|------|
| Duration | Base (100%) | 65-75% of entrance |
| Easing | ease-out (decelerate) | ease-in (accelerate) |
| Displacement | Full distance | 50-70% of entrance distance |
| Complexity | Multi-property OK | Fewer properties (simpler) |
| Attention | Can be theatrical | Should be swift |

## Coordinated Enter/Exit

### List Item Add
1. Existing items shift down (200ms, ease-in-out)
2. New item fades+slides from top (250ms, ease-out, 50ms delay)
3. Subtle scale overshoot on land (3-5%)

### List Item Remove
1. Target fades+scales to 95% (150ms, ease-in)
2. Gap closes (200ms, ease-in-out)
3. No overshoot on close

### Tab/View Switch
1. Old view: fades+slides out in departure direction (200ms, ease-in)
2. New view: fades+slides in from arrival direction (250ms, ease-out, 50ms overlap)
3. Content within new view: staggers in (40-60ms per element)

### Route Transition
1. Current page: slide left + fade (300ms, ease-in)
2. New page: slide from right (400ms, ease-out, 100ms delay)
3. Shared elements: morph between positions (400ms, ease-in-out)
4. New content: stagger in (50ms per element)

## Anti-patterns

- **Symmetric enter/exit**: entrance and exit using identical timing feels robotic. Exit should always be faster.
- **Opacity-only**: fading alone for important elements feels disconnected. Always combine with position or scale.
- **Wrong direction exit**: element entered from left but exits upward. Keep spatial consistency.
- **Delayed exit**: user initiated dismissal but animation takes 500ms+ to complete. Exits should never feel sluggish.
- **Entrance without anticipation**: large elements (modals, heroes) appearing without setup feel abrupt. Add 50-100ms anticipation for elements >300px.

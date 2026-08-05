# Emotion-to-Visual Mapping Reference

Complete translation tables for converting emotional keywords into visual properties. Use these as the primary reference during Phase 3.

## How to Use This File

1. Identify the emotion cluster that best matches each touchpoint's keywords
2. Use the corresponding visual properties as starting points
3. Adjust intensity based on emotional strength (mild → strong = subtle → saturated)
4. Check cross-touchpoint coherence after individual mapping

## Intensity Scale

Emotions have intensity. Apply this multiplier to visual properties:

| Intensity | Description | Color Saturation | Type Weight | Shadow Depth | Border Radius |
|-----------|-------------|-----------------|-------------|--------------|---------------|
| Mild | Background feeling, not dominant | 30-50% | Light (300-400) | 0-2px | Base |
| Moderate | Clear emotional state | 50-70% | Regular (400-500) | 4-8px | Base + 4px |
| Strong | Dominant emotion at this moment | 70-90% | Medium-Bold (500-700) | 8-16px | Base + 8px |
| Peak | Emotional climax of the journey | 90-100% | Bold-Black (700-900) | 16-24px | Base + 12px |

---

## Color Mapping

### Primary Emotion Clusters

#### Joy / Delight / Satisfaction
```
Primary:    #FFB347 (warm amber)     → #FF6B6B (coral)
Secondary:  #FFF3E0 (warm cream)     → #FFECB3 (soft gold)
Accent:     #FF8A65 (soft orange)    → #FFD54F (bright yellow)
Background: #FFFDE7 (warm white)     → #FFF8E1 (cream)
Text:       #5D4037 (warm brown)     → #BF360C (deep orange-brown)
```
Variants by product type:
- Children's product: shift toward brighter yellows, add pink (#FF80AB)
- Professional tool: desaturate 20%, use gold (#C9A96E) instead of orange
- Health/wellness: add warm green (#A5D6A7), soften to peach tones

#### Trust / Security / Reliability
```
Primary:    #1976D2 (deep blue)      → #0D47A1 (navy)
Secondary:  #E3F2FD (ice blue)       → #BBDEFB (light blue)
Accent:     #4CAF50 (trust green)    → #00897B (teal)
Background: #FAFAFA (clean white)    → #ECEFF1 (cool gray)
Text:       #263238 (dark slate)     → #37474F (blue-gray)
```
Variants:
- Financial: lean navy + gold accent (#C9A96E), avoid bright greens
- Healthcare: add clinical white, use softer blue (#42A5F5)
- Enterprise: desaturate, use muted steel blue (#546E7A)

#### Frustration / Pain / Friction
```
Primary:    #D32F2F (muted red)      → #B71C1C (deep red)
Secondary:  #FFCDD2 (light pink)     → #EF9A9A (medium pink)
Accent:     #616161 (dark gray)      → #424242 (charcoal)
Background: #F5F5F5 (cold gray)      → #EEEEEE (medium gray)
Text:       #212121 (near black)     → #D32F2F (error red)
```
Note: Use sparingly. This palette indicates where design should SOLVE problems, not celebrate them. Show the emotion, then show the resolution.

#### Excitement / Discovery / Novelty
```
Primary:    #7C4DFF (vivid purple)   → #651FFF (electric purple)
Secondary:  #E8EAF6 (lavender mist) → #C5CAE9 (soft indigo)
Accent:     #00BCD4 (cyan)           → #FF4081 (hot pink)
Background: #F3E5F5 (light purple)   → #EDE7F6 (misty violet)
Text:       #311B92 (deep purple)    → #1A237E (dark indigo)
```
Variants:
- Gaming/entertainment: max saturation, add neon green (#76FF03)
- Tech/startup: balance with dark backgrounds (#1A1A2E), neon accents
- Consumer app: soften to gradient purple-pink

#### Calm / Comfort / Safety
```
Primary:    #81C784 (sage green)     → #66BB6A (medium green)
Secondary:  #F1F8E9 (mint cream)     → #DCEDC8 (light sage)
Accent:     #A1887F (warm taupe)     → #BCAAA4 (soft mocha)
Background: #FAFAF7 (natural white)  → #F9FBE7 (warm cream)
Text:       #33691E (forest)         → #4E342E (warm brown)
```
Variants:
- Meditation/mindfulness: add lavender (#CE93D8), extra whitespace
- Nature/outdoor: deeper greens, earth tones (#8D6E63)
- Baby/parenting: soften to pastel mint + blush (#F8BBD0)

#### Urgency / Pressure / Time-sensitivity
```
Primary:    #FF5722 (red-orange)     → #E64A19 (deep orange)
Secondary:  #FBE9E7 (pale orange)    → #FFCCBC (light salmon)
Accent:     #212121 (black)          → #F44336 (pure red)
Background: #FFFFFF (stark white)    → #FAFAFA (clean)
Text:       #BF360C (burnt orange)   → #212121 (black)
```
Note: High contrast ratios (>7:1). Minimal decoration. Every element serves the action.

#### Confusion / Uncertainty / Overwhelm
```
Primary:    #78909C (blue-gray)      → #90A4AE (medium gray-blue)
Secondary:  #CFD8DC (light slate)    → #B0BEC5 (medium slate)
Accent:     #546E7A (dark slate)     → #455A64 (charcoal blue)
Background: #ECEFF1 (cool white)     → #F5F5F5 (neutral gray)
Text:       #37474F (dark blue-gray) → #546E7A (medium dark)
```
Note: This palette reflects the USER's emotional state, not the desired design outcome. Use it to show empathy in the mood board, then show the RESOLUTION adjacent to it.

---

## Typography Mapping

| Emotion | Font Category | Weight | Letter Spacing | Line Height | Scale |
|---------|--------------|--------|---------------|-------------|-------|
| Joy / Delight | Rounded sans (Nunito, Poppins) | 500-700 | +0.02em | 1.6 | Large (1.25x base) |
| Trust / Security | Geometric sans (Inter, IBM Plex) | 400-500 | 0 (normal) | 1.5 | Standard (1x) |
| Frustration | Tight sans (Roboto Condensed) | 500-600 | -0.01em | 1.3 | Compressed (0.9x) |
| Excitement | Display/bold sans (Montserrat, Clash) | 700-900 | +0.03em | 1.4 | Large (1.5x) |
| Calm / Comfort | Humanist sans or serif (Lora, Source Serif) | 300-400 | +0.01em | 1.7 | Generous (1.1x) |
| Urgency | Condensed/bold (Barlow Condensed) | 700-800 | -0.02em | 1.2 | Variable (CTA huge, body tight) |
| Confusion | Mixed/irregular (intentionally inconsistent) | Variable | Variable | Variable | Irregular |

### Typography Emotional Signals

- **Rounded terminals** → Friendly, approachable, young
- **Sharp terminals** → Professional, precise, authoritative
- **High x-height** → Modern, readable, digital-native
- **Low x-height + long ascenders** → Elegant, editorial, premium
- **Tight tracking** → Urgency, density, compression
- **Generous tracking** → Luxury, calm, breathing room
- **Heavy weight** → Confidence, impact, dominance
- **Light weight** → Elegance, subtlety, gentleness

---

## Image Style Mapping

| Emotion | Lighting | Composition | Color Grading | Subject Treatment |
|---------|----------|-------------|---------------|-------------------|
| Joy | High-key, golden hour, warm fill | Open, airy, negative space | Warm +20, slightly lifted shadows | Natural smiles, candid moments |
| Trust | Even, balanced, soft studio | Centered, stable, grid-aligned | Neutral-cool, consistent exposure | Direct gaze, clean backgrounds |
| Frustration | Low-key, harsh directional | Cramped, tight crop, tilted | Desaturated, heavy shadows | Tension in hands/face, closed posture |
| Excitement | Dynamic, colored gels, high contrast | Diagonal, motion blur, asymmetric | Saturated +30, split-tone | Action, movement, forward momentum |
| Calm | Soft, diffused, window light | Rule of thirds, horizon lines | Muted +10, lifted blacks | Relaxed posture, nature, slow moments |
| Urgency | Flash, hard light, spotlight | Close-up, center-weighted | High contrast, selective desaturation | Hands in action, focused eyes |
| Confusion | Mixed sources, conflicting temp | Cluttered, multiple subjects | Slightly off white-balance | Looking away, multiple directions |

### ImageGen Prompt Patterns

When generating mood images, use this structure:
```
[Atmosphere/mood adjective], [lighting description], [subject/scene], 
[composition style], [color palette reference], [style modifier]
```

Example for "Joy" touchpoint:
```
Warm golden-hour atmosphere, soft natural light streaming through windows,
a person discovering something delightful on their phone, 
airy composition with generous negative space, 
warm coral and amber color palette, lifestyle photography style
```

Example for "Trust" touchpoint:
```
Clean professional atmosphere, balanced even lighting,
organized workspace with elegant digital interface,
centered stable composition with grid alignment,
deep blue and white color palette, minimal editorial photography
```

---

## UI Component Style Mapping

### Buttons

| Emotion | Border Radius | Shadow | Padding | Color Treatment |
|---------|--------------|--------|---------|-----------------|
| Joy | 24px (pill) | 0 4px 12px rgba(warm) | Generous (16px 32px) | Gradient or solid warm |
| Trust | 8px | 0 2px 4px rgba(neutral) | Standard (12px 24px) | Solid primary blue |
| Frustration | 4px | None | Tight (8px 16px) | Muted, gray |
| Excitement | 16px | 0 8px 24px rgba(vibrant) | Large (16px 40px) | Vivid gradient |
| Calm | 12px | 0 1px 3px rgba(soft) | Comfortable (14px 28px) | Soft pastel solid |
| Urgency | 4-8px | None or minimal | Tight (10px 20px) | Solid high-contrast |

### Cards

| Emotion | Border Radius | Shadow | Border | Internal Spacing |
|---------|--------------|--------|--------|-----------------|
| Joy | 20px | Soft, warm-tinted | None | Generous (24px) |
| Trust | 8px | Subtle neutral | 1px solid light | Standard (16px) |
| Frustration | 2px | Heavy dark | 2px solid dark | Compressed (12px) |
| Excitement | 16px | Colored, elevated | None or gradient border | Generous (24px) |
| Calm | 16px | Barely visible | None | Very generous (32px) |
| Urgency | 4px | None | 1px solid strong | Tight (12px) |

### Inputs

| Emotion | Border Radius | Border Style | Background | Focus State |
|---------|--------------|-------------|------------|-------------|
| Joy | 16px | 2px solid warm | Warm tint (#FFF8E1) | Ring warm + scale 1.02 |
| Trust | 6px | 1px solid gray | White | Ring blue + border darken |
| Calm | 12px | 1px solid sage | Soft mint tint | Ring green + subtle glow |
| Urgency | 4px | 2px solid dark | White | Ring red + border bold |

---

## Cross-Touchpoint Coherence Rules

After mapping each touchpoint individually, apply these coherence checks:

1. **Color thread**: At least one color from each touchpoint's palette must appear (even as a background tint) in adjacent touchpoints. This creates visual continuity.

2. **Typography consistency**: Use the same font family throughout, varying only weight and scale per touchpoint. Exception: one "hero" touchpoint may use a display font.

3. **Border radius progression**: Radius should shift gradually across the journey. Avoid jumping from 24px to 2px between adjacent touchpoints without narrative reason.

4. **Image style continuity**: Maintain consistent subject distance (don't jump from extreme close-up to wide landscape) unless the emotional shift is dramatic.

5. **Journey narrative**: The board should visually "read" from left to right / top to bottom as a story. The emotional arc should be visible in color saturation, weight, and intensity patterns.

---

## Industry Adaptation Quick Guide

| Industry | Color Bias | Type Bias | Image Bias | UI Bias |
|----------|-----------|-----------|-----------|---------|
| Fintech | Navy + gold, high trust | Geometric sans, medium weight | Clean, structured, minimal | Precise, consistent, restrained |
| Health | Soft blue + green, calming | Humanist, friendly weight | Natural light, human warmth | Rounded, breathable, gentle |
| E-commerce | Energetic, brand-aligned | Clear hierarchy, scannable | Product-focused, aspirational | Card-heavy, clear CTAs |
| Education | Warm, encouraging | Readable, generous sizing | Diverse, authentic, active | Accessible, consistent |
| Entertainment | Saturated, dynamic | Bold display, high contrast | Cinematic, emotional | Immersive, minimal chrome |
| B2B SaaS | Neutral + one brand accent | Professional, dense-friendly | Abstract/conceptual | Dense, information-rich |
| Children | Bright primary, high saturation | Rounded, large, bold | Illustrated, playful | Chunky, large touch targets |

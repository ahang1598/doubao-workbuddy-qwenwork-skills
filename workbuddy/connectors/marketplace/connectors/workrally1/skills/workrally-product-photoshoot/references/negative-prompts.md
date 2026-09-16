# Negative Prompts

These suppressors get appended to the prompt in an `[AVOID]` block. The universal list applies to every generation; mode-specific lists in each `references/<mode>.md` extend it.

## Universal (always include)

```
[AVOID]
no AI artifacts, no warped or smeared text, no fake words baked into the image,
no plastic look, no waxy surface, no cartoonish rendering,
no extra fingers, no extra limbs, no melted geometry, no doubled subjects,
no oversaturated HDR, no HDR halos, no oversharpened look,
no flat fluorescent lighting, no harsh on-camera flash,
no generic stock photography poses, no cliché compositions,
no random unrelated brand logos, no watermarks, no signatures,
no AI sheen on hair or skin, no doll-like rendering, no airbrush look,
no flat solid color bands, no empty rectangular areas, no dull gradient zones
that look out of place from the rest of the scene.
```

## Anti-uncanny (include when humans are in frame)

Append for any generation with people, hands, or faces:

```
no AI uncanny faces, no warped facial geometry, no asymmetric eyes,
no extra teeth, no melted facial features, no warped fingers or hands,
no plastic skin, no orange-tan skin, no over-smoothed retouching,
no doll eyes, no misaligned facial features, no rubber-like skin texture,
no warped jewelry or glasses, no stiff unnatural posture.
```

## Anti-text-warp (include when product has labels or branding)

```
no warped product label text, no garbled letters, no fake brand names,
no melted typography, no doubled labels, no fictional logos.
```

## Anti-stock-feel (include for ad, hero, lifestyle modes)

```
no stale stock photography aesthetic, no synthetic stock-photo look,
no over-staged feeling, no unrealistically clean environments,
no perfect symmetry where natural asymmetry should be,
no clipart elements, no flat illustration mixed with photo,
no obviously composited backgrounds.
```

## Anti-aesthetic-mixing (include for restyle mode)

```
no aesthetic mixing — commit fully to the chosen preset,
no half-applied style transformation,
no source image style bleeding through unchanged.
```

## Anti-flat-band (include when user explicitly wants text overlay space)

When the user has said they will overlay text in post-production AND the prompt asks for a tonally calm area:

```
the calm area must blend naturally into the scene as part of the actual environment
(sky, blurred background, surface texture, atmospheric gradient),
NOT a hard-edged solid-color rectangle, NOT an artificial flat band,
NOT a cropped-looking empty zone disconnected from the rest of the image.
```

## How to assemble

For any prompt, append a single `[AVOID]` block combining:
1. Universal (always)
2. Anti-uncanny (if humans / hands / faces)
3. Anti-text-warp (if product labels visible)
4. Anti-stock-feel (if mode is ad / hero / lifestyle)
5. Anti-aesthetic-mixing (if mode is restyle)
6. Anti-flat-band (if user explicitly requested text-overlay space, Case 2 in main SKILL.md)
7. Mode-specific negatives from `references/<mode>.md`

Combine into one block, do not duplicate phrases.

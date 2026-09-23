# Mode: restyle

Take an existing image and transform its aesthetic, mood, or seasonal context while preserving the subject, composition, and core identity. Combines two axes — aesthetic mood and seasonal/holiday context — into one mode.

## Two axes

This mode operates on TWO axes that can be used independently or together:

**Axis 1 — Aesthetic mood**: clean girl, cottagecore, Y2K, minimal, dark academia, quiet luxury, scandinavian, coastal grandmother, maximalist, brutalist, art-deco, retro-90s, futurist, japandi, bohemian, mid-century modern, gothic-romance, pastel-dream

**Axis 2 — Seasonal / holiday context**: Christmas, Black Friday, Cyber Monday, Valentine's Day, Mother's Day, Father's Day, Easter, Halloween, Thanksgiving, Back to School, Pride, New Year's, Summer, Spring, Fall, Winter, Lunar New Year, 4th of July

Either axis alone, or both combined ("Christmas version in cottagecore style").

## Aesthetic Presets (Axis 1)

| Aesthetic | Visual signature | Palette | Texture / surface |
|---|---|---|---|
| `clean-girl` | Minimal, dewy, fresh, neutral | Vanilla, blush, taupe, soft gold | Smooth glass, brushed gold, fresh linen |
| `cottagecore` | Rustic, hand-crafted, romantic | Sage, cream, dried rose, wheat | Linen, raw wood, dried flowers, vintage paper |
| `Y2K` | Glossy, futuristic, playful | Hot pink, lime, chrome, baby blue | Chrome, glossy plastic, holographic, glitter |
| `minimal` | Stripped back, geometric, pure | White, grey, single accent | Concrete, brushed metal, matte paper |
| `dark-academia` | Moody, scholarly, romantic | Oxblood, deep brown, parchment, ivy | Worn leather, aged paper, dark wood, candlelight |
| `quiet-luxury` | Refined, restrained, expensive | Warm grey, camel, muted navy, parchment | Cashmere, polished marble, brushed metal |
| `scandinavian` | Cool, clean, functional | White, pale grey, raw wood, black | Pale wood, linen, ceramic, simple lines |
| `coastal-grandmother` | Soft, weathered, breezy | Dusty blue, sand, white, weathered wood | Linen, driftwood, ceramic, woven texture |
| `maximalist` | Layered, saturated, bold | Multi-color clash with intent | Velvet, brass, patterned wallpaper |
| `brutalist` | Raw, monolithic, modernist | Concrete grey, black, white | Raw concrete, brushed steel, exposed structure |
| `art-deco` | Geometric, gold, glamorous | Black, gold, emerald, ivory | Polished marble, brass, lacquered wood, mirror |
| `retro-90s` | Saturated, grainy, nostalgic | Magenta, teal, mustard | Crinkled film grain, faded color, soft vintage glow |
| `futurist` | Sleek, glowing, neon | Neon cyan, magenta, deep black | Glossy black, glowing edges, holographic |
| `japandi` | Calm, minimal, organic-modern | Warm beige, charcoal, soft white | Pale wood, linen, ceramic, soft shadows |
| `bohemian` | Eclectic, warm, layered | Terracotta, mustard, deep teal, cream | Macrame, woven rugs, brass, plants |
| `mid-century-modern` | Clean lines, warm woods, retro | Mustard, teal, walnut, cream | Walnut wood, leather, geometric patterns |
| `gothic-romance` | Dark, dramatic, ornate | Black, deep red, gold, deep purple | Velvet, lace, candlelight, antique frames |
| `pastel-dream` | Soft, ethereal, whimsical | Lavender, peach, mint, baby blue | Soft tulle, pastel paper, dreamy light |

## Seasonal Presets (Axis 2)

| Season/Holiday | Visual cues | Palette shift | Atmosphere |
|---|---|---|---|
| `christmas` | Pine, holly, ornaments, candle, ribbon, snow window | Deep red, evergreen, gold, cream | Warm tungsten glow |
| `black-friday` | Bold sale aesthetic, type-friendly, dramatic | Black, red, white with stark contrast | High-contrast cinematic |
| `cyber-monday` | Tech-modern, neon, digital cues | Electric blue, magenta, black | Glowing edges, futuristic |
| `valentines-day` | Roses, soft hearts, candlelight, ribbon | Dusty rose, deep red, blush, gold | Romantic warm glow |
| `mothers-day` | Spring flowers, soft pastels, brunch cues | Blush, sage, cream, soft yellow | Soft natural morning light |
| `fathers-day` | Wood, leather, masculine textures | Warm brown, navy, olive | Warm afternoon light |
| `easter` | Pastel eggs, spring flowers, fresh greenery | Soft pastels — mint, lavender, peach | Bright spring morning light |
| `halloween` | Pumpkins, candles, autumn leaves, gothic accent | Orange, deep purple, black, amber | Moody candlelight, twilight |
| `thanksgiving` | Autumn harvest, dried wheat, gourds, warm spice | Burnt orange, ochre, deep red, cream | Warm afternoon golden light |
| `back-to-school` | Notebooks, pencils, fresh apples, denim | Navy, mustard, red, denim blue | Crisp morning light |
| `pride` | Rainbow accents, joyful, celebratory | Saturated rainbow palette | Vibrant celebratory light |
| `new-years` | Champagne, gold confetti, midnight glow | Gold, black, deep navy, white | Sparkling night light |
| `summer` | Sun, water, fresh fruit, light fabric | Saturated blue, yellow, white, coral | Bright midday or golden hour |
| `spring` | Cherry blossoms, fresh greens, soft sun | Soft pink, green, cream, butter yellow | Soft morning sun |
| `fall` | Foliage, sweaters, warm spice | Burnt orange, mustard, deep red, brown | Warm afternoon with low sun |
| `winter` | Snow, frost, cozy textures, minimal greenery | Deep blue, white, silver, deep green | Cool soft daylight or warm interior |
| `lunar-new-year` | Red lanterns, gold accents, blossoms | Deep red, gold, black | Festive warm glow |
| `4th-of-july` | American summer, picnic, flag colors, fireworks | Red, white, blue with warmth | Bright summer outdoor light |

## Prompt Template

```
[SOURCE]
Restyle the referenced image. PRESERVE: {{subject identity, composition, framing, focal anchor, product details}}.

[TRANSFORMATION]
TRANSFORM into {{aesthetic preset}} {{+ seasonal preset if applicable}} aesthetic.

[AESTHETIC SHIFT]
{{Specific visual cues from chosen aesthetic preset}}. {{Surface and texture changes}}. {{Mood shift}}.

[SEASONAL SHIFT]
{{If seasonal axis used: specific seasonal cues to introduce}}. {{Palette shift toward seasonal tones}}.

[PALETTE]
Shift dominant palette to {{exact palette from preset}}. Keep product's intrinsic colors recognizable.

[LIGHTING]
{{New lighting matching the aesthetic — direction, quality, color temp}}. Different from the source image's lighting if needed.

[TEXTURE & SURFACE]
{{Specific surface treatments from the aesthetic preset}}.

[STYLE REFERENCE]
{{Concrete craft descriptors extracted from 2-3 photographer entries matched to the aesthetic}}. Never include the source names.

[PRESERVATION DIRECTIVE]
The subject and composition must remain recognizable as the same image — only the aesthetic and atmosphere change.

[QUALITY MARKERS]
Hyper-realistic, magazine-quality, photorealistic, faithful to source subject.

[AVOID]
{{universal + anti-aesthetic-mixing}}
no change to subject identity, no change to composition, no change to product appearance.

resolution: 2k
```

## Photographer references by aesthetic

- **clean-girl / minimal / quiet-luxury**: Carl Kleiner, Aaron Tilley, Bobby Doherty
- **cottagecore / coastal-grandmother / japandi**: Beth Kirby, Brittany Ambridge, Pia Ulin
- **Y2K / futurist / pastel-dream**: Petra Collins, Charlie Engman, Maciek Jasik
- **dark-academia / gothic-romance**: Tim Walker, Erwin Olaf, Annie Leibovitz
- **maximalist / bohemian / art-deco**: Tim Walker, Mert & Marcus, Steven Meisel
- **scandinavian / brutalist / mid-century-modern**: Carl Kleiner, James Merrell, Aaron Tilley
- **retro-90s**: Petra Collins, Wolfgang Tillmans, Juergen Teller

## Generation invocation

Follow the runtime orchestration in `SKILL.md`. A completed source image is
mandatory. Attach the same source reference to every first-pass restyle request
and preserve its aspect ratio unless the user explicitly changes it.

## Quality gates

- [ ] Subject preserved from source
- [ ] Composition preserved from source
- [ ] Aesthetic shift is strong and committed (not half-applied)
- [ ] Palette matches the preset
- [ ] Seasonal cues read clearly (if used)
- [ ] No kitsch — restyle feels editorial, not gimmicky
- [ ] Aspect ratio matches source unless user requested change
- [ ] Prompt ends with `resolution: 2k`

# Brandkit intake

Parse the user's first message, attachments, and already approved state slots before asking anything. Treat the fields below as a gap checklist, not a mandatory questionnaire.

Ask one compact question set (a single chat message) containing only unanswered fields that materially block the requested output. Never repeat information from the first message. If there are no blocking gaps, skip core intake entirely. Invite only the uploads still relevant after considering files already attached.

This host has no structured question widget and no file-picker control. Ask in ordinary chat and let
the user drop file paths or attachments. The JSON shapes below describe **what to ask**, not a tool
call — render them as plain questions.

Local files the user names become usable URLs through `upload_file`; `asset_create` additionally
puts them in the WorkRally asset library.

## Core gap checklist

1. **Name**

   > What is the name of your brand or product?

2. **Offering, audience, and positioning**

   > What does the brand or product offer, who is it for, and what are its key values or positioning?

3. **Identity route**

   > Are we creating a new visual identity, or do you already have some brand assets you want to keep and extend?

   Options:
   - New identity
   - I have existing brand assets

4. **Preferences**

   > Do you have any visual preferences? Describe your vision, colors, fonts, mood, or examples. You can optionally indicate where it should sit on these scales: Restrained ↔ Expressive, Geometric ↔ Organic, Familiar ↔ Experimental. Example: “Expressive 70, Organic 60, Familiar 40.” Say “balanced” or leave the scales blank if unsure.

## Core call shape

Filter this shape to missing questions only; never send all four automatically.

```json
{
  "questions": [
    {
      "kind": "text",
      "header": "Name",
      "question": "What is the name of your brand or product?"
    },
    {
      "kind": "text",
      "header": "Brand context",
      "question": "What does the brand or product offer, who is it for, and what are its key values or positioning?"
    },
    {
      "kind": "text",
      "header": "Identity route",
      "question": "Are we creating a new visual identity or extending an existing one?",
      "options": [
        {
          "label": "New identity",
          "description": "Create the Essential Kit from the beginning"
        },
        {
          "label": "I have existing brand assets",
          "description": "Preserve and extend supplied brand assets"
        }
      ]
    },
    {
      "kind": "text",
      "header": "Preferences and references",
      "question": "Do you have any visual preferences? Describe your vision, colors, fonts, mood, or examples. Optionally add values for Restrained–Expressive, Geometric–Organic, and Familiar–Experimental."
    }
  ]
}
```

## Conditional upload step

### Existing or partial identity

If the first message did not already include the needed official assets, ask once with only the relevant separate optional file boxes:

1. **Official logos and marks** — SVG preferred; PNG, JPG, WebP, or PDF accepted.
2. **Official fonts** — TTF, OTF, WOFF, or WOFF2.
3. **Palette and guidelines** — PDF, PPTX, CSS, JSON, SVG, or images.
4. **Other official brand materials** — packaging, templates, graphics, or application examples in any supported file format.
5. **Inspiration references** — visually useful but never authoritative.

Each box must use `kind: "files"`, `min: 0`, and a role-specific header. Never mix inspiration into an official-assets box.

```json
{
  "questions": [
    {
      "kind": "files",
      "header": "Official logos and marks",
      "question": "Upload the official logos or marks you want preserved.",
      "files": {
        "accept": ["image/*", ".svg", ".pdf"],
        "min": 0,
        "max": 10
      }
    },
    {
      "kind": "files",
      "header": "Official fonts",
      "question": "Upload any official font files you use.",
      "files": {
        "accept": [".ttf", ".otf", ".woff", ".woff2"],
        "min": 0,
        "max": 10
      }
    },
    {
      "kind": "files",
      "header": "Palette and guidelines",
      "question": "Upload palette files, guidelines, or an existing brandbook.",
      "files": {
        "accept": ["image/*", ".svg", ".pdf", ".pptx", ".css", ".json"],
        "min": 0,
        "max": 10
      }
    },
    {
      "kind": "files",
      "header": "Other official brand materials",
      "question": "Upload any other official templates, graphics, packaging, or applications.",
      "files": {
        "accept": ["image/*", ".svg", ".pdf", ".pptx"],
        "min": 0,
        "max": 10
      }
    },
    {
      "kind": "files",
      "header": "Inspiration references",
      "question": "Optionally upload visual references that inspire you but are not official brand assets.",
      "files": {
        "accept": ["image/*", ".svg", ".pdf"],
        "min": 0,
        "max": 10
      }
    }
  ]
}
```

After analysis, immediately call the matching independent state action for every user-declared official element:

- `lock_authoritative_logo`
- `lock_authoritative_palette`
- `lock_authoritative_typography`

Do not wait for combined Essential Kit approval to lock supplied assets.

### New identity

Show one optional inspiration/reference upload box only when inspiration would materially help and none was already attached. Do not show official logo/font/palette boxes unless the user changes route.

## Parse the answers

Create one internal brief:

```text
name:
offering:
industry/category:
audience:
positioning/key values:
identity route:
visual preferences:
visual_axes:
  restrained_expressive:
  geometric_organic:
  familiar_experimental:
uploaded official logo assets:
uploaded official font assets:
uploaded official palette/guideline assets:
uploaded other official assets:
uploaded inspiration:
```

Normalize scale language to 0–100:

- Strongly first = 0
- Mostly first = 25
- Balanced/unspecified = 50
- Mostly second = 75
- Strongly second = 100

Immediately persist normalized values through the Brandkit state script's `set_visual_axes` action. Write the required wrapper exactly; never pass the three axes as the top-level object:

```json
{
  "visual_axes": {
    "restrained_expressive": 50,
    "geometric_organic": 50,
    "familiar_experimental": 50
  }
}
```

Do not ask what the user specifically likes/dislikes about every reference. If they provide no explanation, use the reference's overall visual character as a taste signal without copying its logo, layout, artwork, or distinctive device.

## Route

- **New identity** → create only the foundation slots needed by the deliverables named in the first message.
- **Existing/partial identity** → analyze and independently lock every supplied official element, then identify only missing slots required by the requested deliverables.
- If the user selected the existing-assets route but uploaded nothing, ask them to upload what they want preserved before proceeding.

Describe the specific missing elements naturally. For example: “You already have an official logo and fonts. Would you like me to develop a matching color palette while keeping those assets unchanged?” Never use “fill in the blanks” as fixed user-facing copy.

Keep the first-message deliverables in scope. Once their required slots are approved, continue them without asking the user to choose scope again.

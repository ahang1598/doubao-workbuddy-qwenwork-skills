# Presentation deck

Create once logo, palette, and typography are separately approved. Do not ask for another combined approval.

Read `state --action get_essential_kit` through the Brandkit state script. Build the deck in the **local shell**.

## Intake

Require:

- deck purpose
- audience
- source content
- desired slide count
- exact claims/data
- requested aspect ratio
- existing PPTX template, if any

Do not invent mission, values, market statistics, pricing, claims, contacts, or product variants to fill slides.

## Build

- Existing PPTX → edit its masters/layouts (unpack/repack the OOXML locally with `unzip`/`zip`).
- No template → create a small coherent layout family with a PPTX library. This needs an install the
  skill does not ship: `pip install python-pptx` or `npm i pptxgenjs`. Ask before installing, and
  when the user declines or the install fails, say the deck was not built rather than delivering a
  flattened image set as if it were a deck.
- Use approved logo, palette, and fonts.
- Keep all text/shapes editable.
- Keep imagery replaceable.
- Use generated imagery only as optional supporting assets.
- Do not flatten whole slides into images.

Create only slide types required by the content, such as cover, divider, image/copy, comparison, process, data, quote, and closing.

## QA and approval

Render slides for inspection with headless LibreOffice (`soffice --headless --convert-to pdf`, then `pdftoppm`), fix, and re-render. Both come from installs the skill does not ship — LibreOffice and Poppler. When they are unavailable, deliver the PPTX and state that you could not visually inspect it; do not claim the layout was checked.

Check overflow, collisions, alignment, font substitution, contrast, and placeholder residue.

Deliver the editable PPTX plus previews/PDF as local file paths. Save only the approved deck through `approve_brandbook_element` using key `presentation-deck` and `required_slots: ["logo","palette","typography"]`.

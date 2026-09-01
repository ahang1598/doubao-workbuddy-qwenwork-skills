---
name: kling-ai-generate-image
description: Generate cinematic-quality images via Kling AI in WorkBuddy. Supports T2I & I2I. Ideal for posters, product photography, ads, and high-visual-quality creative work.
---

# Kling AI Image Generation

Turn a creative brief into one well-specified Kling image request. Use only the live tools and schemas from the configured MCP at `https://kling.ai/mcp`.

## Contract

- Use host-managed OAuth. Never request or expose API keys, tokens, cookies, authorization headers, or signed URLs.
- A user request to generate authorizes one submission after materially missing inputs are resolved. Do not add a credit-cost warning or a separate confirmation step.
- Submit once per approved intent. Never blind-retry an ambiguous or failed submission.
- Discover the live schema before choosing tools, models, input names, or enumerated values. Live provider fields override examples here.
- Upload attached reference media with the remote upload tool when required, then reuse the returned provider reference exactly.

Before submission, read the [complete MCP input/output and current model parameter snapshot](../kling-ai-plugin/references/mcp-contract.md), then let the current `tools/list` and `who_am_i` override dynamic snapshot values.

## Workflow

1. Classify the request using the mode table below.
2. Read [scene patterns](references/scene-patterns.md) for product, advertising, thumbnail, portrait, editorial, or conceptual work.
3. Read [prompt construction](references/prompt-construction.md) when the brief is vague, has references, contains exact copy, or needs multiple controlled variants.
4. Ask only for missing facts that materially change the result: subject/product, intended use, ratio, required copy, or mandatory reference identity.
5. Among live models compatible with the mode and references, prefer a full-quality model. Prefer a low-cost or fast model only when the user explicitly asks for a draft, speed, or credit savings.
6. Build one prompt that separates subject, action, environment, composition, lighting, palette, material detail, camera language, and exclusions. Translate abstract requests such as “premium,” “cinematic,” or “high quality” into visible lighting, materials, depth of field, color, and composition instead of stacking adjectives.
7. Call the live image generation tool once when the request has enough information. Preserve the exact `generationId` and any `taskTraceId`.
8. If the submission is not terminal, poll its status at provider-allowed intervals until success or failure. On user cancellation or current-turn timeout, return the current state and task number.
9. Provide the primary image or result link returned by Kling. Show `generationId` as the **task number** and keep `taskTraceId` internal unless troubleshooting requires it.

## Generation modes

| User intent | Mode | Required interpretation |
| --- | --- | --- |
| Text-to-image | New image | No source image controls identity or composition. Build the scene from the text brief. |
| Image-to-image | Edit or reference-guided image | At least one image controls content, identity, product geometry, composition, or style. Assign every input an explicit role. |
| Element subject reference | Image-to-image | Read the Element first, confirm it is an image subject, and use only an image-to-image model whose live schema explicitly supports `elements`. Text-to-image never uses Elements. |
| Restyle | Focused image-to-image change | Lock all unspecified source facts and name the one allowed change. |
| Status check | Read-only | Do not call a generation tool; query the existing task. |

Do not silently switch modes. An attached image is not automatically an image-to-image instruction: if the user asks for an unrelated new image, ignore it only after confirming it is irrelevant. Conversely, never reduce an explicit image-to-image request to text-to-image after an upload or schema failure.

Before calling the tool, check the selected mode, ratio, reference roles, and
allowed changes internally. Do not show a pre-submission process message unless
you need the user to clarify a missing creative requirement.

## Defaults

- Use a supported `2k` setting for a normal deliverable, `4k` for high-quality, commercial, advertising, fine-material, or crop-heavy work, and `1k` only for drafts or speed-first work. Do not lower a higher live model default.
- When the live model exposes a `quality` argument, use its middle tier for a normal deliverable, its high tier for high-quality or commercial work, and its low tier only for drafts. Obtain the exact value from the live enumeration.
- Choose ratio from the destination: `1:1` square social/product, `4:5` feed portrait, `9:16` story/vertical cover, `16:9` landscape banner or thumbnail.
- Generate `1` image unless the user requests multiple results; do not substitute a batch of near-duplicates for a clear creative decision.
- Prefer a clean image without text unless the user explicitly requires text in the generated artwork.
- For variants, change one named dimension per approved generation: concept, composition, palette, camera distance, or expression. Do not use near-duplicate prompts.
- Preserve supplied brand names, labels, logos, faces, and product geometry as locked constraints. Never invent claims, prices, certifications, ingredients, results, or statistics.

## Quality gate

Before submission, check that the brief has one clear focal subject, a readable hierarchy, destination-appropriate safe space, coherent lighting, and no conflicting camera/composition instructions. When the host can inspect outputs, verify reference fidelity, text accuracy, subject count, and obvious artifacts. Do not claim visual QA when inspection is unavailable.

## Failure behavior

- Authorization failure: direct the user to WorkBuddy's native MCP connection flow.
- Unsupported argument: refresh the live schema and revise only the rejected field.
- Insufficient credits: tell the user to recharge and stop. Do not retry automatically.
- Lost response: treat task creation as unknown and query existing tasks before any new generation.
- Provider failure: report the provider message and preserve IDs; do not resubmit automatically.

# Kling MCP input and output contract

Use this file to verify the tool surface and parameter structure without freezing dynamic model configuration. Resolve facts in this order for every operation:

1. The connected server's `tools/list` defines callable tools, tool descriptions, and `inputSchema`.
2. `who_am_i.availableModels` defines models, model arguments, required fields, defaults, allowed values, item limits, and media inputs for each generation tool.
3. The actual tool response defines additional output fields. Never invent a field when no `outputSchema` or observed response supports it.

## Complete tool surface

- Discovery and account: `who_am_i`, `query_membership_and_credits`, `logout`
- Generation and status: `text_to_image`, `image_to_image`, `text_to_video`, `image_to_video`, `motion_control`, `query_tasks`
- Assets and reuse: `file_upload`, `motion_library_list`, `element_create`, `element_list`, `element_get`, `element_update`, `element_delete`

Call a tool only when it exists in the current `tools/list`. Tool, model, and value availability may differ by region or account tier; never assume China and Global expose identical surfaces.

## Fixed tool-level inputs

- The five generation tools accept `model`, `arguments[]`, `inputs[]`, `rationale`, and `taskTraceId`.
  - `model` must come from the current `who_am_i` list for that tool. Do not guess a default model.
  - Each `arguments[]` item is `{name, value}` and every `value` is a string. Names, required fields, defaults, allowed values, and `maxItems` come from the selected model.
  - Each `inputs[]` item is `{name, inputType, url}`. Pass only input names declared by the selected model and use the `inputType` declared by the live schema.
  - `rationale` explains the user's objective and the reason for parameter choices; it does not replace the creative prompt.
- `query_tasks`: required `generationId` and optional `taskTraceId`.
- `file_upload`: `filename`, `contentType`, `size`, and `taskTraceId` as declared by the live schema.
- `who_am_i`, `query_membership_and_credits`, `logout`, `motion_library_list`, and `element_list`: optional `taskTraceId` only.
- `element_get` and `element_delete`: `id` plus optional `taskTraceId`; enforce the actual required rule from the tool description before calling.
- `element_create`: `name`, `description`, `resource`, `tags`, and `taskTraceId`.
- `element_update`: the create fields plus `id`. Call `element_get` first and send a complete update object so omitted fields are not cleared accidentally.

Use an RFC 4122 UUIDv7 for `taskTraceId`. Reuse it across discovery, upload, generation, and status calls for one user objective; create a new value when the user switches to an unrelated objective.

## Dynamic model parameters

Before any generation submission, call `who_am_i` and read the target tool and model fields:

- `arguments[]`: `name`, `required`, `default`, `allowedValues` / `allowed_values`, `maxItems`, and `description`;
- `inputs[]`: `name`, `required`, and `description`;
- use aliases only to understand user intent and submit the canonical `model` name.

For the complete current Global model names, arguments, defaults, allowed values, item limits, and inputs, read the [model parameter snapshot](model-parameters.md) during verification or troubleshooting. The live `who_am_i` remains authoritative at call time.

When a tool description conflicts with `who_am_i`, enforce the stricter tool-level constraint and stop an unsafe submission. Preserve these gates:

- `text_to_image` and `text_to_video` do not use Elements; never pass `elements` or `<<<id>>>`;
- call `element_get` before binding an Element; route image Elements only to an `image_to_image` or `image_to_video` model whose live schema supports `elements`, and route video Elements only to a compatible `image_to_video` model;
- `motion_control` requires a subject `image` and exactly one motion source: library `motionId` or input `video`; obtain direction, resolution, and sound arguments from the live model schema;
- when a model requires a URL returned by `file_upload`, do not pass a local path or arbitrary external URL directly;
- never pass an argument, input name, or enum value absent from the live model schema.

## Element resources

- Image Element: `resource.cover` plus 1–3 `resource.secondary[{name,inputType,url}]`; do not also pass `resource.video`.
- Video Element: `resource.video`, optionally `resource.voice` when the live description allows it; do not also pass `cover` or `secondary`.
- Provide at least one `tags` item and use only tags declared by the current tool description.
- `element_delete` removes user data and requires explicit confirmation immediately before the call.
- If an image Element's cover cannot be safely replaced through update, explain that delete-and-recreate is required and wait for confirmation.

## Known outputs

- Generation submission: `generationId`, `status`, and possibly `creditsConsumed` and `message`.
- `query_tasks`: `generationId`, `status`, `createTime`, `finishTime`, and `works[]`; work items may contain `status`, `contentType`, `url`, `urlWithoutWatermark`, `coverUrl`, and `coverUrlWithoutWatermark`. Treat status case-insensitively and determine terminal state from the live response.
- First `file_upload` step: `ticket`, `uploadUrl`, and `expireAt`; then send multipart `ticket` and file bytes to `uploadUrl` and read the uploaded URL from that response.
- `query_membership_and_credits`: `userId`, `membershipType`, and `availableRemainCredits`.
- `motion_library_list`: `motions[{id,name,motionUrl,coverUrl,duration,hasAudio}]`, with `duration` in milliseconds.
- `element_list`: `elements[{id,name}]`.
- `element_get`: `id`, `name`, `description`, `resource`, and `tags`.
- `motion_control`: the normal generation submission result, followed by `query_tasks`.
- `element_create`: the tool description guarantees an Element `id`.

`element_update`, `element_delete`, and `logout` currently have no dependable public full `outputSchema`. Read and preserve their actual responses; do not claim undeclared fields. Machine-verifiable coverage of every successful output requires server-side `outputSchema` definitions or redacted success fixtures.

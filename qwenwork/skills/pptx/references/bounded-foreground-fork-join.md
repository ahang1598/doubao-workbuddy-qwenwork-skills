# Adaptive Foreground Fork-Join for PPTX

Use this pattern to overlap generated images with editable PPT authoring while
keeping recovery finite and final QA centralized. Treat it as the preferred
topology when the host and task benefit from it, not as a restriction on other
safe ways to complete the deck.

## Eligibility gate

Use the pattern only when the deck genuinely benefits from generated images and
the `Agent` tool is available. Keep normal template edits, text-only decks,
charts, and component-led slides on their ordinary path. If `Agent` is
unavailable or delegation would add more coordination than useful overlap, use
the direct parent path without claiming concurrency.

Before dispatch:

1. Establish the slide outline, theme, image-slot IDs, prompts, slot geometry,
   target aspect, requested size, output paths, and result paths.
2. Mark each slot as `anchor`, `supporting`, or `optional`.
3. Preplan the fallback for every slot. A placeholder may reserve geometry in
   the draft, but every final fallback must be a complete no-image layout.
4. Form one shared image-slot manifest and pass it verbatim to the authoring
   child. Pass each image child only its matching slot record.

Example manifest:

```json
{
  "deck_id": "topic-deck",
  "slots": [
    {
      "slot": "cover",
      "slide": 1,
      "role": "anchor",
      "prompt": "visual description without slide text",
      "size": "1792x1024",
      "box": { "x": 0.0, "y": 0.0, "w": 13.333, "h": 7.5 },
      "output": "/work/assets/cover.png",
      "result": "/work/assets/results/cover.json",
      "fit_policy": "adapt_then_crop",
      "allow_regeneration": true,
      "watermark_policy": "accept_official",
      "fallback": "complete paper-text cover without an image slot"
    }
  ]
}
```

The manifest coordinates the branches; it is not a prison for later design
judgment. The authoring child starts from its geometry. After a wave joins, the
parent may revise a later-wave prompt or slot when evidence shows that doing so
improves the composition, while keeping already-running file ownership stable.

## Foreground topology

When useful, make the first execution batch after the plan and manifest contain:

- One default foreground PPT-authoring Agent.
- One default foreground image Agent per highest-value slot, up to the host's
  safe available concurrency.

Prefer foreground, full-context children for this short-lived join. Do not set
background, detached, specialized-agent, or reduced-context options unless the
host explicitly provides an equivalent reliable contract.
The children inherit the parent conversation snapshot and share the workspace,
but each child may write only its assigned files.

Avoid conflicting parent writes while the authoring child owns the draft.
In the current QwenWork runtime, image generation uses asynchronous
`qwenwork_image_generate` submissions followed by `qwenwork_media_task` waits.
A UI `Parallel` label does not prove provider-side concurrency. Never count or
describe that display state as concurrent execution. True workflow concurrency
here means separate image Agent branches plus a PPT-authoring Agent branch,
followed by a join. The parent may still perform independent read-only work or
choose a direct path when no authoring child is active.

When planned image slots exceed the first wave, choose the next slots by expected
contribution to the deck. `anchor`, `supporting`, and `optional` roles are useful
priority signals, not a fixed queue that overrides narrative or design judgment.
Continue with later waves as capacity opens, or satisfy appropriate slots with a
licensed search/user-provided asset. The concurrency limit is never a total-image
limit.

The PPT-authoring Agent must:

- Receive the complete image-slot manifest, slide outline, and theme decision.
- Build the complete editable source with deterministic asset lookup.
- Start from every manifest box and implement its preplanned fallback without
  waiting for any image file to appear. Normal design judgment may refine a
  slot when needed; record the final geometry so the join can adapt the asset
  consistently instead of forcing a weak composition.
- Execute the build script.
- Return a draft PPTX that opens and passes a structural smoke check.
- Run `python scripts/authoring_result.py record draft.pptx --build-script
build_deck.py --result authoring-result.json` only after the draft exists.

An image Agent must not create the PPTX. It owns exactly one image file and one
result JSON.

## Parent fallback

Use direct parent execution when `Agent` is absent, the initial dispatch fails,
or `python scripts/authoring_result.py verify authoring-result.json` rejects the
authoring artifact after the join. Keep the useful outline, slot intent, and
successful assets, then finish through a validated ordinary authoring path.
Do not describe direct parent media-task submissions as forked or concurrent execution.

## Authoring child contract

The authoring child owns one build script, one draft PPTX, and one result JSON.
Its prose is never the source of truth. The recorded result must contain:

```json
{
  "schema_version": "qwenwork.pptx.authoring-result/v1",
  "task_id": "ppt:author",
  "status": "ok",
  "artifact_path": "/absolute/work/draft.pptx",
  "build_script": "/absolute/work/build_deck.py",
  "build_executed": true,
  "slide_count": 10,
  "validation_passed": true,
  "retryable": false,
  "message": null
}
```

The recorder verifies the actual package and slide count. Missing JSON, a
missing script, zero slides, or an unreadable artifact is an authoring failure;
the parent executes the ordinary mule-run-compatible authoring flow once rather
than dispatching another authoring child.

## Image child contract

Give every image child a compact task envelope:

```json
{
  "task_id": "image:cover",
  "slot": "cover",
  "attempt": 1,
  "size": "1792x1024",
  "slot_ratio": 1.7778,
  "max_crop_loss": 0.2,
  "fit_policy": "adapt_then_crop",
  "allow_regeneration": true,
  "watermark_policy": "accept_official",
  "output": "/absolute/work/assets/cover.png",
  "result": "/absolute/work/assets/results/cover.json"
}
```

Use this compact first-attempt sequence:

1. Call `qwenwork_image_generate` once, then call `qwenwork_media_task` with
   `action: "wait"` for the returned task ID.
2. If submission or waiting errors, do not retry inside the child. Write a failure result and
   return so the parent can coordinate recovery.
3. If it succeeds, copy the downloaded file to the assigned output path.
4. Check only existence, non-zero size, decodability, width, and height.
5. Write the result JSON and return.

Do not perform watermark removal, heuristic pixel detection, repeated `Read`,
cropping, inpainting, or slide composition repair in an image child. An official
generated-image watermark is expected output, not an image-child failure. The final
slide render is the visual source of truth for whether an `anchor` remains
materially unusable after normal layout adaptation.

## Result contract

```json
{
  "task_id": "image:cover",
  "slot": "cover",
  "attempt": 1,
  "status": "ok",
  "imagegen_calls": 1,
  "path": "/absolute/work/assets/cover.png",
  "width": 1792,
  "height": 1024,
  "retryable": false,
  "error_class": null,
  "message": null
}
```

Allowed status values:

- `ok`: a decodable image exists.
- `constraint_mismatch`: the image exists but needs layout adaptation or a
  different fit policy; it is usable and non-retryable by default.
- `retryable_failure`: timeout, rate limit, or provider 5xx.
- `terminal_failure`: authorization, content refusal, invalid arguments, or
  another failure that a new Agent should not repeat.

Keep messages short. The parent uses result JSON files, not child prose, as the
source of truth. Require `imagegen_calls` in every result. If a child reports a
value other than 1, the parent may still use a valid generated artifact, but it
must treat that slot's retry budget as exhausted and must not dispatch another
image Agent for the slot.

## Aspect acceptance

Do not require the generator to return the exact requested pixels. Compare the
source ratio `r_source` with slot ratio `r_slot` using:

```text
crop_loss = 1 - min(r_source / r_slot, r_slot / r_source)
```

When `crop_loss <= max_crop_loss`, use a moderate subject-preserving cover crop.
When it is greater, do not regenerate by default. Prefer, in order: adjust the
reserved slot within the planned grid; use contain treatment with a coordinated
background; apply the smallest subject-preserving crop that keeps the slide
readable. Never stretch the image. Use the preplanned no-image fallback only
when those treatments fail.

Official generated-image output may include a service watermark. Unless the user
explicitly requested watermark-free assets, accept it without pixel inspection,
removal, concealment cropping, or regeneration. If watermark-free output was
explicitly requested, do not repeat the same official generation path; use an
available licensed/user-provided asset or state the limitation.

## Recovery ownership

The parent Agent owns recovery so children cannot amplify retries independently.
One generation is the normal successful-image budget. A second attempt or a
licensed replacement is reasonable when evidence shows that its expected
quality benefit justifies the latency, especially for an `anchor`:

- Attempt 1 is the first-wave image child.
- Attempt 2 may follow a `retryable_failure` with no usable artifact, an
  explicit exact-visual request with `allow_regeneration: true`, or final-slide
  evidence that an `anchor` has the wrong subject/theme, a severe generation
  defect, or composition that cannot be repaired by crop, contain, or a safe
  layout change.
- Additional attempts require new user direction or materially new evidence;
  never loop on the same prompt/provider behavior.

Do not retry a successful decodable artifact merely for an official watermark,
returned dimensions/aspect, crop loss, or minor style variance. Treat ordinary
`constraint_mismatch` as an authoring/layout input, not a generation failure.
Do not retry `terminal_failure` without a meaningfully different authorized
asset route.

If at least two siblings fail with the same provider and `error_class`, run one
eligible slot as a canary. Retry the remaining eligible siblings only when the
canary succeeds and their budgets remain. A failed canary opens the circuit for
that failure class, so the parent immediately applies the recorded fallbacks.

The parent must not override exhausted budgets because a placeholder looks
unattractive. The authoring branch preplanned the fallback precisely to avoid
that late quality-versus-latency debate.

## Join and QA

After all required children return:

1. Verify `authoring-result.json`, then read and validate image result JSON files.
2. Apply the parent-owned retry policy.
3. Re-run the authoring script once with successful assets and fallbacks.
4. Run content QA and structural QA.
5. Render the overview and enough full-resolution slides to resolve the actual
   visual risk; perform visual QA in the parent or one dedicated visual-QA Agent.
6. Repair only the affected slides and re-render those slides.

Track planned slots, `qwenwork_image_generate` calls, successful slots, retry amplification,
slowest-branch time, join delay, fallback count, and final QA status. For `N`
planned slots, retry amplification is `(image generation calls - N) / N`.

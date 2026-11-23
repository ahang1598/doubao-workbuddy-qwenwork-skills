# Verify an explorable teaching figure

## Teaching and schema

Check the actual host contract: existing anchor, unique figure IDs, supported kind/config, one valid best answer, and all required languages. In AI English Shift, run the app's explore tests after adding/changing specs or widgets. Do not claim newly suggested `assembly` or `spatial` kinds exist before registering and validating them.

Drive a misconception through a real interaction. Can a learner see the predicted result fail without reading the insight first? Check model outcomes at reset, input bounds and meaningful transitions. For example, a 12:24 ideal external gear pair gives -0.5 output turns per input turn; a cache hit updates recency without creating a new entry. Test the rule rather than matching displayed wording.

Ensure reset restores semantic state and view state as intended. An exploded view, cutaway or camera change must not secretly change the model's answer. Accessible summaries and numerical readouts agree with what moves.

For a stochastic figure, verify normalized expected probabilities and reproducible seeded samples separately. A single sampled batch is not a pass/fail check on a general causal claim. Check the author's explanation criteria and one unseen transfer case; label these design checks separately from evidence collected with learners.

Check the learning-design answers against the build ([learning-design.md](learning-design.md) §9):
- the build matches its audience: little copy and presenter controls for a presenter build; a probe, feedback, fading and transfer for a self-learner build;
- the predict stage does not show the answer;
- every `data-focus` and `data-ref` id resolves to a `data-part`;
- the focus guide can be turned off;
- ordered highlights never autoplay;
- each wrong option has misconception-specific feedback.

## Browser interaction and presentation

Before accepting the visual, apply the separate representation gate in [rendering-selection.md](rendering-selection.md). Check the actual subject silhouette, characteristic structures, material and section/fold depth against its reference. Record which upstream code or source assets are actually used. Input/reset tests do not establish visual quality, and a simplification disclaimer does not waive a requested detail level.

Use the project's existing browser tooling or bundled local scripts. Inspect:

- Desktop and 360px width: no clipped parts/labels/controls or horizontal scrolling.
- All supported themes: fills, small detail and focal parts remain readable.
- Pointer, touch-equivalent operation and keyboard: primary actions have equivalents, no stuck held controls, no shortcut interception in writing fields.
- Reduced motion and pause/step: stable states still demonstrate the result.
- Offscreen/unmount: loops stop and input/observers clean up.
- Console: no runtime exceptions, failed assets or hydration warnings.

Read the images you capture. A screenshot tool producing a PNG is not visual verification until inspected.

## Local bundled tools

See [upstream verify.md](../assets/anatomy/references/verify.md) for supported CLI flags. Run these from a work copy preserving `kit/`, `scripts/` and `examples/`; build outputs belong in that copy. Upstream browser scripts launch local Chrome/Chromium. Use an installed browser, setting `CHROME_PATH` if needed, rather than installing a browser without cause.

```sh
node scripts/capture.mjs page.html --out shots/desktop.png
node scripts/capture.mjs page.html --out shots/phone.png --width 360
node scripts/capture.mjs page.html --out shots/still.png --reduced
node scripts/capture.mjs page-light.html --out shots/light.png
node scripts/drive.mjs page.html --actions steps.json
```

`steps.json` contains supported action arrays (`key`, `click`, `drag`, `eval`, `until`, `shot`). Use real key and pointer input for interaction checks. Directly invoking a model/controller tests state changes but does not prove pointer capture or key handling. Put long evaluation expressions in the JSON file instead of shell-escaping them inline.

For a non-kit lesson frame, use `--select` on a capture to point at the figure; default selection is `.iso-plate`. Theme media emulation does not change a kit page's build-time `data-theme`; build the light variant.

## Mechanical and exploded geometry

Inspect assembled, mid-stroke/mid-explosion and apart views. Crop important contacts at 4×: gear mesh, joints, supports, pipe terminals, cutaway rims and screen openings. Look for intersections, unsupported parts, false joints from tangent outlines, depth inversions and ungrounded detail lines.

For models using the recorder, run the implemented `node build.mjs --audit` hook and require its failing checks to reach zero before claiming a geometry pass. Use the true drawn shapes. Correct geometry/routing/group order; do not hide a failure with a sort bias or proxy shape.

`node scripts/lines.mjs page.html --out shots/lines.png` checks line ends separately. Repeat in relevant apart/mid-stroke states via `drive.mjs` actions. A zero geometry audit is not proof of line quality or teaching validity.

## True 3D

Run a full orbit audit for all turns, hinge ranges and reachable clips when claiming full geometry verification. `--quick` and `--only` runs are iteration results, reported as quick or partial. They do not mean `turn audit passed`.

Browser checks are supported by `scripts/turn-check.mjs`: fidelity (against the builder), order (requires a verify build), pops, line ends and frame time/performance. Use the upstream guide's exact flags and state-file formats. Inspect orbit sheets and close-ups around depth-order changes in both themes. Measure the actual page at desktop and phone widths; don't quote upstream FPS as your measurement.

## WebGL

Check smooth start/stop and phase transitions, layer registration, clipping, and light-theme readability. Test `drive.mjs --no-webgl` and reduced-motion fallbacks. A shader that looks plausible is not validation of a physical field; the lesson's model must state its approximation.

## Report evidence accurately

Distinguish model checks, build/syntax checks, browser interaction checks, visual inspection and geometry audits. State limitations proportionally. Do not run expensive whole-scene checks for a simple config-only lesson change, and do not report a dense 3D mechanism as verified using only a static screenshot.

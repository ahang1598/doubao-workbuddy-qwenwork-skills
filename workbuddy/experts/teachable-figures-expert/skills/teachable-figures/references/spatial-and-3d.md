# Spatial motion and field effects

## What requires true 3D

First select the subject representation with [rendering-selection.md](rendering-selection.md). Projection and rotation cannot repair an incorrect subject shape. Organic reference meshes and cloth may need a different renderer from Anatomy's convex rigid-part engine.

Use `turning-3d` when rotation in depth, a changing viewpoint, joint articulation, or occlusion contributes to the lesson: a keyed fit inspected around its axis, connected links, or a rotating subject exposing previously hidden surfaces. A sliding drawer, flat dial needle or simple pressed key can stay projected SVG.

The bundled Anatomy turning engine is **beta**. It re-projects and re-shades true world-coordinate primitives each frame and computes painter's order. It is not a general CAD/physics engine. Its upstream performance examples are not guarantees for your figure; measure the actual scene.

For arbitrary anatomical or cloth meshes, use a renderer with suitable mesh support, normals and depth ordering. Keep source-relative transforms and separate the camera from lesson state. Record the asset source and local alterations; don't claim the Anatomy kit generated an organ or verified an unrelated mesh. WebGL is also a valid solid-mesh renderer when surface lighting and depth require it; the field-layer technique below is a separate capability.

Read [3d.md](../assets/anatomy/references/3d.md), especially model/API, part constraints, audit, performance and known limits. Open [turning-dial/build.mjs](../assets/anatomy/examples/turning-dial/build.mjs) and its `live.js` for a real implementation. Use signatures from the bundled revision, not a remembered package API.

## Authoring and runtime

- `kit/turn-build.mjs`: `turning(P, { recorder })`, group and primitive builders, stack, `T.build`.
- `kit/turn.mjs`: `TURN.mount`, controller state, group poses, screen/world anchors, materials, CSS.
- `kit/turn-audit.mjs`: geometry over reachable turn/hinge/clip states.
- `scripts/inline-kit.mjs`: `turnScript()` for a portable standalone runtime.

Rest geometry uses world coordinates with all group values at zero. Groups are `turn`, `slide`, `hinge`, or `free`; nested poses are relative to their parents. Keep model coordinates and geometry coordinates consistent. Define `follow(values)` to map one lesson input to coupled groups, rather than allowing physically connected pieces to drift independently.

Build a small moving subject first, keeping support clutter static. Use convex primitives; split U-brackets into prisms and notched wheels into suitable pieces. Treat flush/tangent contacts and coaxial joints as geometry constraints, not near-enough visual guesses. A tube crossing a joint must use the engine's supported joint/port pattern; do not stretch a single rigid cable across moving groups.

Provide all reachable joint ranges, combined poses, gesture clips and explode/return paths to `T.build` and the audit. Sampling the first turning group alone does not prove a hinge or free-body path. Fit the scene to bounds across those poses, not just the initial angle.

The controller owns projection and rendering, but the figure owns time and semantic state. Mount once; call `controller.set` when input or time changes state; destroy on cleanup. Offscreen or settled figures stop their loop. Continuous angular motion uses elapsed time rather than frame count. Under reduced motion, use explicit angle/phase steps and update the same readout.

For React, keep Node build/audit modules out of the client bundle. Serialize build data and initial stage markup, then mount the browser runtime in an effect. In an app without server components, precompute at build time or adapt geometry into browser-safe modules. Keep the initial pose deterministic to avoid hydration mismatches.

## Interaction that teaches space

Separate the mechanism's state from viewing controls. A view/orbit control should not alter the numerical result. Offer home view/reset and a small selection readout. For dragging a dial, project pointer input through the controller's `angleAt`; supply arrow keys or an equivalent native slider.

For multi-turn values, keep unwrapped angles in the model and wrap only the visual angle/label as appropriate. Define end stops or periodic motion explicitly. Add a textual observation for learners who cannot inspect the 3D stage, such as “the keyway is aligned; the hub can now seat.”

If a true 3D scene is too heavy at narrow width, reduce decorative part density or offer a simplified accessible view with equivalent controls/results. Do not silently substitute a flat scene while reporting completed 3D.

## Optional WebGL fields

WebGL earns a place for waves, fluid, heat, glow or light distributions that carry meaning. It is separate from true 3D: a field can sit in a static isometric scene, and a rotating solid can work without shaders.

Read [webgl.md](../assets/anatomy/references/webgl.md) and the relevant ripple-tank or engine example. Keep solids SVG and use a registered layer stack: back SVG → canvas → front SVG. Canvas is `pointer-events: none`. Shader points share the figure's world camera; a floating screen-space effect is not a valid mechanical field.

Drive uniforms from the same model as the readout. Fade attacks, decays and phase transitions continuously; spatial effects reach zero before canvas/region bounds. A window needs both its own-plane mask and the opening's mask. Effects anchored to a moving part follow its group; world-space smoke/light should stay in world space when appropriate.

Cap device ratio and stop rendering when inactive/offscreen. Provide an SVG or text fallback with the same semantic result for missing WebGL, reduced motion and unsupported devices. Design both themes rather than inverting a dark shader. If it is only an illustrative effect, label it; do not imply computational fluid dynamics or measured optical accuracy.

## Verification status

Read [verification.md](verification.md) and upstream 3D sections 13–16. Quick/subset runs support iteration; they cannot establish a full pass. For a claimed full 3D geometry check, run the full orbit audit with every reachable group and clip. Browser fidelity, order, discontinuity, lines and performance checks complement it. Record which checks actually ran and what remains unverified.

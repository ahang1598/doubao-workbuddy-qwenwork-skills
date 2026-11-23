# Mechanical models, cutaways and exploded assemblies

Use crafted solid geometry when the learner must understand contact, constraint, motion transmission, support, hidden structure, or component order. The point is a legible working mechanism. Do not turn every abstract lesson into an ornate machine.

## Read and reuse

The bundled Anatomy resources are a coherent tree at `assets/anatomy/`. Read:

- [craft.md](../assets/anatomy/references/craft.md) for part recipes, depth order, joints, pipe routing, explosion and face-local screens.
- [kit.md](../assets/anatomy/references/kit.md) for the actual API signatures; do not guess overloads.
- [motion.md](../assets/anatomy/references/motion.md) for loops, springs, input and moving-part sorting.

Open the closest source example, not every example:

| Example under `assets/anatomy/examples/` | Technique |
|---|---|
| `dial-indicator/build.mjs` | Small solid instrument, feet, stand, ticks, needle, HTML build |
| `desk-computer/build.mjs` | Working input and display drawn in a face plane |
| `arcade-cabinet/build.mjs` | Cutaway enclosure, hidden mechanism, signal cable, live parts |
| `raptor-engine/build.mjs` | Round bodies, pipes, explosion groups, recorder and audits |
| `test-rig/` | React spring rig, model/geometry/live separation |
| `spot-plate/` | A control changes the shape of several parts |
| `turning-dial/build.mjs` | True 3D; route through the 3D guide |
| `ripple-tank/build.mjs` | Shared physical model with WebGL field layers |

These examples teach techniques and can be large; reuse the relevant pattern rather than transplanting the entire object. The fused skill's teaching contract and host adapter take precedence over upstream style and density rules.

## Make a meaningful parts plan

Record each assembly's purpose, mount, rest coordinates, size, movement, limits, and model variable. Group parts into base/support, mechanism, control/input and observation/output. Every visible part has a mechanical or explanatory purpose; detail is not a quota.

Use consistent world units with x/y on the floor and z up. Keep supports and contacts real. Bearings align with shafts, springs attach to seats, gears have compatible geometry and spacing, pipes end at ports, and translating parts have end stops. If teeth are schematic, say so and avoid claiming a meshing/collision simulation. Rendering primitives do not solve gear mechanics for you.

Use `iso-kit.mjs` or `.ts` for slabs, cylinders, coils, knurls, ticks, face text and projection. Use `lathe.mjs` for bodies along arbitrary axes and `tube.mjs` for pipes/cables. The standalone route inlines runtime source through `scripts/inline-kit.mjs` so the output HTML has no external module dependency.

Copy the required kit and helper directories together into an output workspace. For reproducing an example, preserve:

```text
WORK/
  kit/
  scripts/
  examples/dial-indicator/build.mjs
  LICENSE
```

Then `node WORK/examples/dial-indicator/build.mjs` writes HTML alongside the build script; `--light` builds the light variant. Build in a work copy, not inside the installed skill. Node 20.10+ is upstream's minimum; browser verification scripts use global WebSocket, so use Node 22+ or check availability on an older runtime.

## Teach the hidden mechanism

Use a cutaway when an enclosure hides the causal parts. The cut has real rims, thickness and recess walls; do not simply make everything transparent. Clip displays and fields to both their own plane and the enclosing opening. Keep the control, transmission path and output visible from the chosen camera.

Use an exploded view to reveal assembly relationships. Each assembly has a rest pose, a travel vector and bounds. Keep a selected part's name/function in an adjacent readout or compact legend. Inspect at rest, intermediate fractions and fully apart. Outside parts must clear before inner parts leave, and returning order must also be safe. Motion is inspection, not evidence the machine could operate disconnected.

For real mechanisms, compute kinematics from constraints: gear ratios, coaxial axes, hinge limits, slider travel and linkage closure. For analogies, compute software/lesson state first and map it to travel/rotation. Do not use arbitrary springs to stand in for a physical solver unless the lesson explicitly concerns the simplified spring model.

If the request extends to physical fabrication, state units, material, critical dimensions, fit/tolerance assumptions and assembly sequence. A teaching SVG is not fabrication-ready CAD, a bill of materials, or a validated load calculation. Deliver those only when requested and supported by actual design data.

## Depth and honest verification

Static paths are computed once. Translating rigid groups can use `translateAlong`; rotating in depth requires re-projection through the turning runtime. Sort by actual depth, split a wrapping shape into back/front portions, and re-sort when moving assemblies cross.

With pipes, lathes or dense overlap, record the true rendered geometry using `audit.mjs`: recorder, `settle`, and `auditOrExit`. Include rest, intermediate and exploded states. Fix geometry/contact/routing when an audit fails; do not replace real shapes with proxies that silence it. Run the line-end check separately because the geometry audit does not inspect SVG line markup.

Read [the fused verification guide](verification.md) before claiming completion. For a small simple SVG, a model check and visual inspection can be sufficient; a dense rotating or exploded mechanism needs the corresponding audit coverage.

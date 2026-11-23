# Lightweight working isometric objects

Use this mode for a few box-like assemblies with functional keys, switches, drawers, screens or dials. It is projected SVG, not a rigid-body engine. For rotating solids, joint chains or dense intersecting geometry, switch to the mechanical/3D kit.

The bundled [calculator](../assets/iso-figure/examples/pocket-calculator.html) and [synth](../assets/iso-figure/examples/desk-synth.html) demonstrate the rendering/input technique. They are object examples, not finished teachable lessons: add the prediction, causal observation, explanation, caveat and sentence frame appropriate to the requested lesson.

## Decide output first

Name what an action produces before drawing: a computed number, typed content, signal, state trace, or changed mechanism. Decompose the object into a few boxes and face-local details. Record `(x, y, z, width, depth, height)` and which parts are operable. Extra box count has no inherent teaching value.

## Projection kernel

Adapted from iso-figure, MIT © 2026 Tolga Cohce; the full notice is in [assets/iso-figure/LICENSE](../assets/iso-figure/LICENSE). This kernel can be inlined into standalone HTML:

```js
const C = Math.cos(Math.PI / 6), S = Math.sin(Math.PI / 6);
const OX = 465, OY = 300; // fit these to the actual scene
const P = (x,y,z) => [(x-y)*C + OX, (x+y)*S - z + OY];
const D = (x,y,z) => [(x-y)*C, (x+y)*S - z];
const plane = (O,U,V) => {
  const o=P(...O), u=D(...U), v=D(...V);
  return `matrix(${u[0]} ${u[1]} ${v[0]} ${v[1]} ${o[0]} ${o[1]})`;
};
const TOP   = (x,y,z) => plane([x,y,z],[1,0,0],[0,1,0]);
const FRONT = (x,y,z) => plane([x,y,z],[1,0,0],[0,0,-1]);
const SIDE  = (x,y,z) => plane([x,y,z],[0,-1,0],[0,0,-1]);
const rect = (t,w,h,r=0,cls='face') =>
  `<g transform="${t}"><rect class="${cls}" width="${w}" height="${h}" rx="${r}"/></g>`;
const box = (x,y,z,w,d,h,r=0) =>
  rect(SIDE(x+w,y+d,z+h),d,h,Math.min(r,h/4)) +
  rect(FRONT(x,y+d,z+h),w,h,Math.min(r,h/4)) +
  rect(TOP(x,y,z+h),w,d,r,'face top');
```

Here +x goes down-right, +y down-left and +z up. The front face is `y=max`, the side face `x=max`. Draw ordinary rectangles, text and paths in a face's local coordinates, then apply its matrix; do not manually skew every point. This lightweight convention is different from Anatomy's adjustable camera. Do not mix coordinates or projection functions between them without converting.

Use opaque fills and `vector-effect: non-scaling-stroke` on stroked shapes. Round thin side faces no more than `height / 4`. Project all bounding corners at every legal control extreme and add a margin before selecting a `viewBox`; `OX/OY` above are examples, not fit constants.

For non-intersecting simple boxes, emitting farther boxes before nearer boxes and supporting surfaces before their details is often sufficient. Increasing `x+y` is a heuristic, not a general 3D depth proof. A tall part or interleaved components can break it. If the objects wrap or cross, split them where necessary and use the kit's recorder/depth audit rather than patching order by eye.

## Functional input

One state object and shared action functions serve pointer and keyboard. Wrap each pressable part and its face-local label in a group so they move together. Use class toggles for a brief press feedback; the actual output comes from the model, not the CSS transition.

In lessons, native controls outside the SVG are a reliable accessible equivalent for decorative keys/dials. Focus the figure for shortcuts; ignore text inputs, contenteditable, modifier combinations and unrelated page keys. The bundled copies use stage-scoped shortcuts and native controls. Keep that isolation when embedding them beside a writing exercise.

For held parts, use pointer capture, release on `pointerup`, `pointercancel` and window blur, and avoid stuck keys. Apply `touch-action: none` only to the draggable interaction area, not the entire lesson. For typed display text, use `textContent` where possible; otherwise escape user strings and clip to the window at the widest possible output.

For sound, initialize audio after a user gesture and provide mute and a visual signal/readout. Under reduced motion, remove press transitions and allow immediate state changes. A synth sound alone is not an accessible explanation.

The bundled synth adds short-note buttons, waveform and octave controls, reset, and mute. Held inputs have separate owners so one source cannot release another source's note. Reset, focus loss, and hiding the page release voices; the scope stops when idle, offscreen, hidden, or under reduced motion. The native controls are the mobile interaction route; the projected key faces are supplementary.

## Styling and delivery

Use product CSS variables for surfaces, structural/detail lines, and the active state. A restrained monochrome plate is a default, not a ban on meaningful semantic colors or learner labels. Standalone caption rows may contain figure number, title, input hint and live readout. In a host lesson card, reuse its title/readout/control layout rather than duplicating a four-corner frame.

A standalone HTML deliverable inlines its scripts/styles and runs from disk without a CDN. Include any copied MIT notices. In an app, split model, geometry and component code according to its conventions. Check a real action, display/readout agreement, clipping at maximum output, keyboard isolation, narrow layout and console errors.

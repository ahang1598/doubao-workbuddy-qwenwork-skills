# Choose a representation before a renderer

Teaching correctness and visual fidelity are independent requirements. A mathematically correct slider can still operate an unrecognizable subject. Start with what must be seen, then choose the implementation.

## Record the visual contract

In a short design note, record:

- **Subject and reference:** the specific object, organism, garment or abstract model; reference links and asset rights.
- **Fidelity:** schematic, crafted explanatory illustration, or reference mesh. Follow the user's requested detail and intended audience; do not assume every lesson needs realism.
- **Landmarks:** the few shapes and relationships that make the subject recognizable.
- **Surface evidence:** curvature, material response, thickness, folds, joints or layers that the learner needs to inspect.
- **Inspection and renderer:** which parts open, separate or rotate, and which upstream code or other renderer actually implements them.

Do not add these as unsupported fields to a host application's schema. They can live in a design note. Preserve source geometry alignment where relationships matter; independently centering or scaling each organ can invalidate an atlas assembly.

## Route by capability

| Request | Representation and useful capability | Implementation route | Reject |
| --- | --- | --- | --- |
| Calculator, keyboard, working screen, box-like teaching device | Functional face-local graphics and shallow depth | **iso-figure** projection/state workflow; read `simple-iso.md` and its working examples | Decorative boxes with dead controls; rebuilding a second projection for every face |
| Engine, pump, machine, pipe network, rigid assembly | Recognizable components, connected structure, metal/rubber distinction, section walls and clear inspection paths | **Anatomy** primitives, lathe/tube helpers, material craft and group inspection; read `mechanical-craft.md` and the relevant upstream example | A rocket icon presented as a detailed engine; unsupported pipes; fake sections without interiors |
| Human organs or other organic anatomy | Reference-based organ surfaces, subject-specific proportions and anatomical alignment | Licensed domain meshes or reference-based medical illustration; an arbitrary-mesh renderer if rotation is needed. Anatomy can inform inspection/craft but supplies no anatomical atlas | Ellipsoid organs inside a cylindrical torso; assuming the name Anatomy guarantees medical morphology |
| Garment, pleat, layered textile | Draped outline, overlapping fabric, fold ridges/valleys, hem thickness and material shading | Layered SVG/2.5D illustration or cloth mesh, chosen for inspection needs. An iso-figure projection may serve a local fold section; Anatomy contributes layer/section craft | Flat trapezoid plus parallel strokes; metal-like fabric; invented seams or historical construction presented as evidence |
| Mathematical solid and section | Exact geometry, visible section boundary and readable measurements | SVG or mesh projection according to the view needed; use a solid renderer with correct occlusion when rotating | Extra surface detail that hides the mathematical relationship; calling flat rotation 3D |
| Transformer architecture and data flow | Inspectable computation, stage connections, vectors and attention weights | Semantic diagram/SVG/DOM, driven by the actual model; isometric modules only if spatial placement adds information | Decorative 3D towers that hide or misrepresent computation |

The table routes capabilities within this fused skill; it does not imply that separate skills are automatically installed or invoked. Inspect available upstream APIs. If another tool or asset source is needed, state that dependency and preserve its attribution.

## Preserve craft without a part quota

Read [Anatomy's craft guide](../assets/anatomy/references/craft.md) for rigid objects. Keep its recognition, surface, assembly and lighting standards when removing upstream rules such as a minimum part count. A dozen well-chosen components can be enough; a dozen generic blocks may fail the subject.

Use material to expose shape: smooth highlights along a nozzle, subdued seam and flange edges, a lighter folded cloth ridge with a darker overlap valley. Do not use noise, gratuitous bolts or glow to conceal missing structure. Textile sheen is a visual reconstruction unless its exact weave is documented.

For sourced anatomy, provenance supplies the shape; rendering supplies depth/lighting; lesson state supplies the inspection and explanation. Keep these responsibilities explicit. A viewer is not a diagnosis tool or proof that a selected mesh is accurate for every person.

## Two acceptance gates

**Teaching:** operate the misconception, compare observable outcomes, and explain a new case. Check the quantitative model independently.

**Representation:** compare a stage close-up to the reference. Does the silhouette identify the subject? Are the characteristic structures present and aligned? Do curved surfaces, cut boundaries and fold overlaps read as volume? Are materials legible at the actual display size? Inspect closed, halfway and open/separated states, plus changed viewpoints when supported.

Read the screenshots. A successful browser run only proves operation. An automated geometry audit only covers its modeled geometry and configured states. Neither establishes recognizability, textile quality or anatomical fidelity. If visual requirements remain unmet, describe the output as a draft rather than treating a simplification caveat as acceptance.

## Routing evaluation cases

Use these prompts to review a skill revision; inspect its plan and rendered result, not just its prose.

| Prompt | Expected decision | Evidence to inspect |
| --- | --- | --- |
| “Make a working isometric synthesizer with keys and a scope.” | iso-figure; face-local graphics and one state flow | Keys produce the displayed signal; controls remain operable; faces share projection |
| “Let me take a liquid rocket engine apart and inspect its nozzle.” | Anatomy mechanical craft; actual built components and section/inspection groups | Chamber, throat, bell and connecting structure are recognizable; sections have walls; movement preserves identities |
| “Show me a realistic rotating human chest and removable organs.” | Domain anatomy source plus a mesh renderer; distinguish sourced and authored parts | Human torso contour, organ-specific shapes, common spatial frame, license/source manifest, valid views |
| “Explain a museum robe's pleats and overlapping front.” | Source-specific garment illustration or mesh, not a box renderer | Fold surfaces, overlap direction, depth/hem and close-up section; reconstruction distinguished from documented facts |
| “Use a simple line diagram to explain a 12:24 gear ratio.” | Keep the requested simple schematic | Correct turns/direction and explicit idealization; no unnecessary forced mechanical showcase |
| “Trace token data through a Transformer block.” | Inspectable computation diagram | Actual vectors/weights change causally; stage and numeric readouts agree |

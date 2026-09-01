# Kling AI prompt and usage examples

## Suggested prompts

- Create a red panda in a vintage spacesuit floating before a space-station window, with Earth's blue glow lighting its face and cinematic detail.
- Create a five-second cinematic video of a mech warrior slamming into the ground as a shockwave scatters rubble and dust while the camera pushes in.
- Create a fifteen-second sneaker campaign clip that opens on an urban street, cuts to product and on-foot details, and ends on the shoe materials.

## Natural-language requests

Text-to-video:

> Use Kling AI to create a five-second, 16:9 cinematic video of a vintage motorcycle stopping outside a convenience store on a rainy night while the camera pushes steadily from a wide shot.

Image-to-video:

> Animate my attached image for five seconds. Preserve the subject's identity, face, and clothing while the camera slowly arcs from the left to the front. Use 720p.

Multi-shot video:

> Create a multi-shot product film: establish the setting with a wide shot, push toward the product and show its side, then hold on the brand detail. Use duration and shot parameters supported by the current Kling schema.

Text-to-image:

> Use Kling AI to create a 16:9 poster key visual of a transparent glass teapot in a minimal white studio with soft side lighting and title space on the right.

Complete generation request:

> Use Kling AI to create a five-second, 16:9, 720p single-shot video of a vintage motorcycle stopping outside a convenience store on a rainy night. Return the task number after submission.

Status check:

> Check the current state of this Kling task number once. Do not start a polling loop.

## Prompt construction

Prefer concrete direction in this order:

1. subject and setting
2. action or transformation
3. camera and shot structure
4. lighting and visual style
5. identity or consistency constraints
6. exclusions only when they prevent a likely failure

Avoid long lists of repeated negatives. For image-to-video, state what must remain stable and what is allowed to move.

## User-facing submission result

Do not add a credit warning or a separate confirmation step. After submission, use one compact message:

```text
The generation is in progress. I will return the primary result when it completes. Result links may be temporary; if one expires, query the original task number again or open the generation history in the authorized Kling account.
```

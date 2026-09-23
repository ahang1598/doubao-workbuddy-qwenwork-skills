# Typography — Three-Case Rule

The default behavior for WorkRally 图片模型 is to compose freely, without artificially carving out empty space. Empty "reserved zones" cause the model to render flat color bands or dull gradients — which always look bad. Avoid forcing them.

There are exactly three cases:

## Case 1 — User specified concrete text to include in the image

If the user wrote exact words they want on the image (`"the headline should say 'New Drop'"`, `"add 'Sale ends Friday'"`, `"with the text 'Made with love'"`), include the text DIRECTLY in the prompt as part of the composition. WorkRally 图片模型 will render it as integrated typography inside the scene.

In the prompt, write something like:
```
[TYPOGRAPHY]
Integrated typography in the scene reads "New Drop" — set in {{font style: bold sans-serif / elegant serif / hand-lettered / clean modern}}, positioned {{naturally within the composition}}, color {{contrasting with background for legibility}}.
```

## Case 2 — User wants to overlay text themselves (in Figma, Canva, Photoshop)

If the user explicitly says they will add text afterward (`"I'll add the headline in Figma"`, `"leaving space for typography"`, `"need clear area for overlay"`), THEN — and only then — instruct the composition to leave a tonally uniform area:

```
[COMPOSITION FOR TEXT OVERLAY]
Leave one area of the frame visually calm and tonally uniform — natural soft gradient, atmospheric blur, or smooth surface — so the user can overlay typography in post-production. This area must still feel like part of the scene (sky, blurred background, surface), NOT a hard-edged empty rectangle.
```

The key word: **tonally uniform area within the natural scene**. Never `clean negative space` or `reserved white space` — those phrases trigger the model to draw a flat band.

## Case 3 — User said nothing about text (default)

Don't mention text or overlay zones at all. Let the model compose freely for maximum visual quality.

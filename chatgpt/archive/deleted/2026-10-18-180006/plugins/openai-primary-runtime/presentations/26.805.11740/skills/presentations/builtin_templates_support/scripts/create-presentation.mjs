import path from "node:path";
import { pathToFileURL } from "node:url";

import { Presentation, PresentationFile } from "@oai/artifact-tool";

export async function buildPresentation(layoutLibraryRoot) {
  const entrypoint = path.join(
    path.resolve(layoutLibraryRoot),
    "artifact-tool-compose",
    "index.mjs",
  );
  const { builders } = await import(pathToFileURL(entrypoint).href);
  if (!Array.isArray(builders) || builders.some((builder) => typeof builder !== "function")) {
    throw new Error(`Layout library does not export a builders array: ${entrypoint}`);
  }

  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });
  for (const buildSlide of builders) buildSlide(presentation);
  return presentation;
}

export async function exportPresentation(layoutLibraryRoot, outputPath) {
  const presentation = await buildPresentation(layoutLibraryRoot);
  const file = await PresentationFile.exportPptx(presentation);
  await file.save(outputPath);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [, , layoutLibraryRoot, outputPath] = process.argv;
  if (!layoutLibraryRoot || !outputPath) {
    throw new Error(
      "Usage: node create-presentation.mjs <layout-library-asset-root> <output-pptx>",
    );
  }
  await exportPresentation(layoutLibraryRoot, outputPath);
  console.log(outputPath);
}

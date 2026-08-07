#!/usr/bin/env node

// Helper used by render_slides.py to render PowerPoint decks through
// @oai/artifact-tool instead of calling LibreOffice/soffice directly.

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import {
  ensureArtifactToolWorkspace,
  importArtifactTool,
  parseArgs,
  requireArg,
  saveBlobToFile,
} from "./artifact_tool_utils.mjs";

function usage() {
  return [
    "Usage:",
    "  node container_tools/render_presentation.mjs --input <deck.pptx> --output_dir <dir> [options]",
    "",
    "Options:",
    "  --scale <number>     Render scale. Defaults to 1.",
    "  --workspace <dir>    Artifact-tool workspace. Defaults to a temp directory.",
  ].join("\n");
}

function slidesFromPresentation(presentation) {
  if (Array.isArray(presentation.slides?.items)) return presentation.slides.items;
  if (Number.isInteger(presentation.slides?.count) && typeof presentation.slides.getItem === "function") {
    return Array.from({ length: presentation.slides.count }, (_, index) => presentation.slides.getItem(index));
  }
  throw new Error("Could not enumerate imported presentation slides.");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    return;
  }

  const input = path.resolve(requireArg(args, "input"));
  const outputDir = path.resolve(requireArg(args, "output_dir"));
  const scale = args.scale ? Number.parseFloat(args.scale) : 1;
  const workspace = args.workspace
    ? path.resolve(args.workspace)
    : await fs.mkdtemp(path.join(os.tmpdir(), "presentation_render_workspace_"));

  await fs.mkdir(outputDir, { recursive: true });
  await ensureArtifactToolWorkspace(workspace);
  const { FileBlob, PresentationFile } = await importArtifactTool(workspace);
  const presentation = await PresentationFile.importPptx(await FileBlob.load(input));
  const slides = slidesFromPresentation(presentation);
  const paths = [];

  for (let index = 0; index < slides.length; index += 1) {
    const output = path.join(outputDir, `slide-${index + 1}.png`);
    const preview = await presentation.export({ slide: slides[index], format: "png", scale });
    await saveBlobToFile(preview, output);
    paths.push(output);
  }

  console.log(JSON.stringify({ input, outputDir, slideCount: slides.length, paths }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  console.error(usage());
  process.exit(1);
});

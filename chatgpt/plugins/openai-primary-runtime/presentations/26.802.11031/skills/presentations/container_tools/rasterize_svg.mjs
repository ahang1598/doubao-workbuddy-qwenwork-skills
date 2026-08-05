#!/usr/bin/env node

// Helper used by ensure_raster_image.py to rasterize SVG/SVGZ through the
// bundled Node + sharp runtime instead of requiring Inkscape.

import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith("--")) {
      throw new Error(`Unexpected positional argument: ${key}`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      args[key.slice(2)] = true;
      continue;
    }
    args[key.slice(2)] = value;
    index += 1;
  }
  return args;
}

function requireArg(args, key) {
  const value = args[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Missing required --${key}`);
  }
  return value;
}

function defaultRuntimeNodeModules() {
  return path.join(
    process.env.HOME || process.cwd(),
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "node",
    "node_modules",
  );
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const input = path.resolve(requireArg(args, "input"));
  const output = path.resolve(requireArg(args, "output"));
  const nodeModules = process.env.NODE_PATH || defaultRuntimeNodeModules();
  const requireFromRuntime = createRequire(path.join(nodeModules, "__runtime__.cjs"));
  const sharp = requireFromRuntime("sharp");

  await fs.mkdir(path.dirname(output), { recursive: true });
  await sharp(input, { limitInputPixels: false }).png().toFile(output);
  console.log(JSON.stringify({ input, output }));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});

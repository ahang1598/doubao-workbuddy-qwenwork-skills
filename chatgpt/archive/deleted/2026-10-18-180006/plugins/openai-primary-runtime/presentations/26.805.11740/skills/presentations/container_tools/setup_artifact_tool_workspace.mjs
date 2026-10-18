#!/usr/bin/env node

import path from "node:path";

import {
  ensureArtifactToolWorkspace,
  parseArgs,
  requireArg,
} from "./artifact_tool_utils.mjs";

const args = parseArgs(process.argv.slice(2));
if (args.help) {
  console.log("Usage: node setup_artifact_tool_workspace.mjs --workspace <dir>");
} else {
  const workspace = path.resolve(requireArg(args, "workspace"));
  await ensureArtifactToolWorkspace(workspace);
  console.log(workspace);
}

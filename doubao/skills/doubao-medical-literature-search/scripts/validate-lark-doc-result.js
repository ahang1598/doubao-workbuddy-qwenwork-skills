#!/usr/bin/env node

const fs = require("fs");

function usage() {
  console.error(
    "Usage: node scripts/validate-lark-doc-result.js [--operation create|update|media-insert|fetch] <result.json|->",
  );
}

let operation = null;
const positionalArgs = [];
for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg === "--operation") {
    operation = process.argv[index + 1];
    index += 1;
    continue;
  }
  if (arg.startsWith("--operation=")) {
    operation = arg.slice("--operation=".length);
    continue;
  }
  positionalArgs.push(arg);
}

const allowedOperations = ["create", "update", "media-insert", "fetch"];
if (operation && !allowedOperations.includes(operation)) {
  console.error(`Unsupported operation ${JSON.stringify(operation)}.`);
  usage();
  process.exit(2);
}

const inputPath = positionalArgs[0];
if (!inputPath || positionalArgs.length !== 1) {
  usage();
  process.exit(2);
}

let raw;
try {
  raw = inputPath === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(inputPath, "utf8");
} catch (error) {
  console.error(`Failed to read result: ${error.message}`);
  process.exit(2);
}

let outer;
try {
  outer = JSON.parse(raw);
} catch (error) {
  console.error(`Result is not valid JSON: ${error.message}`);
  process.exit(2);
}

const problems = [];
let payload = outer;

// Super Doubao and similar runners may wrap the lark-cli JSON in stdout.
if (
  payload &&
  typeof payload === "object" &&
  payload.ok === undefined &&
  typeof payload.stdout === "string"
) {
  if (payload.interrupted === true) {
    problems.push("runner reports interrupted=true");
  }
  if (typeof payload.stderr === "string" && payload.stderr.trim() !== "") {
    problems.push(`runner stderr is not empty: ${payload.stderr.trim()}`);
  }
  try {
    payload = JSON.parse(payload.stdout);
  } catch (error) {
    problems.push(`runner stdout is not valid lark-cli JSON: ${error.message}`);
  }
}

if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
  problems.push("lark-cli payload must be a JSON object");
} else {
  if (payload.ok !== true) {
    problems.push(`top-level ok must be true, got ${JSON.stringify(payload.ok)}`);
  }

  const result = payload.data && payload.data.result;
  if (result !== undefined && result !== "success") {
    problems.push(`data.result must be success when present, got ${JSON.stringify(result)}`);
  }

  const warnings = [];
  const addWarnings = (value) => {
    if (Array.isArray(value)) warnings.push(...value);
    else if (value !== undefined && value !== null && String(value).trim() !== "") warnings.push(value);
  };
  addWarnings(payload.warnings);
  if (payload.data) addWarnings(payload.data.warnings);
  if (warnings.length > 0) {
    problems.push(`warnings must be empty: ${warnings.map(String).join(" | ")}`);
  }

  const data = payload.data && typeof payload.data === "object" ? payload.data : {};
  const document = data.document && typeof data.document === "object" ? data.document : {};

  if (operation === "create") {
    if (!document.document_id) problems.push("create must return data.document.document_id");
    if (!document.url) problems.push("create must return data.document.url");

    const permissionGrant = data.permission_grant || document.permission_grant;
    if (
      permissionGrant &&
      permissionGrant.status &&
      permissionGrant.status !== "granted"
    ) {
      problems.push(
        `permission_grant.status must be granted when present, got ${JSON.stringify(permissionGrant.status)}`,
      );
    }
  }

  if (operation === "update") {
    if (data.result !== "success") {
      problems.push(`update requires data.result=success, got ${JSON.stringify(data.result)}`);
    }
    if (!(Number.isFinite(data.updated_blocks_count) && data.updated_blocks_count > 0)) {
      problems.push(
        `update requires updated_blocks_count > 0, got ${JSON.stringify(data.updated_blocks_count)}`,
      );
    }
  }

  if (operation === "media-insert") {
    const blockId = data.block_id || document.block_id || (data.block && data.block.block_id);
    const fileToken =
      data.file_token ||
      document.file_token ||
      (data.file && (data.file.file_token || data.file.token));
    const fileName =
      data.file_name ||
      document.file_name ||
      (data.file && (data.file.file_name || data.file.name));
    if (!blockId) problems.push("media-insert must return an attachment block_id");
    if (!fileToken && !fileName) {
      problems.push("media-insert must return a file token or file name");
    }
  }

  if (operation === "fetch") {
    if (typeof document.content !== "string" || document.content.trim() === "") {
      problems.push("fetch must return non-empty data.document.content");
    }
  }
}

if (problems.length > 0) {
  console.error("Lark document operation did not pass the delivery gate:");
  for (const problem of problems) console.error(`- ${problem}`);
  process.exit(1);
}

const result = payload.data && payload.data.result;
console.log(
  JSON.stringify(
    {
      valid: true,
      operation,
      ok: payload.ok,
      result: result === undefined ? null : result,
      warnings: 0,
      note: "Command result passed. Document content still requires a fetch/read-back check.",
    },
    null,
    2,
  ),
);

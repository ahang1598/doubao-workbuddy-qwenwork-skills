#!/usr/bin/env node

const fs = require("fs");
const crypto = require("crypto");

function usage() {
  console.error(
    "Usage: node scripts/validate-lark-doc-write-result.js " +
      "--operation create|update [--expect-document-id ID] " +
      "[--previous-revision N] [--report FILE] <result.json|->",
  );
}

function requireValue(flag, value) {
  if (value === undefined || value === "") {
    console.error(`${flag} requires a value.`);
    usage();
    process.exit(2);
  }
  return value;
}

let operation = null;
let expectedDocumentId = null;
let previousRevision = null;
let reportPath = null;
const positionalArgs = [];

for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg === "--operation") {
    operation = requireValue(arg, process.argv[index + 1]);
    index += 1;
    continue;
  }
  if (arg.startsWith("--operation=")) {
    operation = requireValue("--operation", arg.slice("--operation=".length));
    continue;
  }
  if (arg === "--expect-document-id") {
    expectedDocumentId = requireValue(arg, process.argv[index + 1]);
    index += 1;
    continue;
  }
  if (arg.startsWith("--expect-document-id=")) {
    expectedDocumentId = requireValue(
      "--expect-document-id",
      arg.slice("--expect-document-id=".length),
    );
    continue;
  }
  if (arg === "--previous-revision") {
    previousRevision = Number(requireValue(arg, process.argv[index + 1]));
    index += 1;
    continue;
  }
  if (arg.startsWith("--previous-revision=")) {
    previousRevision = Number(
      requireValue(
        "--previous-revision",
        arg.slice("--previous-revision=".length),
      ),
    );
    continue;
  }
  if (arg === "--report") {
    reportPath = requireValue(arg, process.argv[index + 1]);
    index += 1;
    continue;
  }
  if (arg.startsWith("--report=")) {
    reportPath = requireValue("--report", arg.slice("--report=".length));
    continue;
  }
  positionalArgs.push(arg);
}

if (!["create", "update"].includes(operation)) {
  console.error("--operation must be create or update.");
  usage();
  process.exit(2);
}
if (operation === "update" && !expectedDocumentId) {
  console.error("update requires --expect-document-id.");
  usage();
  process.exit(2);
}
if (
  operation === "update" &&
  !(Number.isInteger(previousRevision) && previousRevision > 0)
) {
  console.error(
    "update requires --previous-revision with the last positive revision.",
  );
  usage();
  process.exit(2);
}
if (positionalArgs.length !== 1) {
  usage();
  process.exit(2);
}

const inputPath = positionalArgs[0];
let raw;
try {
  raw = inputPath === "-"
    ? fs.readFileSync(0, "utf8")
    : fs.readFileSync(inputPath, "utf8");
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
let runnerStderr = "";

// Super Doubao and similar runners may wrap the lark-cli JSON in stdout.
if (payload && typeof payload === "object" && payload.ok === undefined) {
  let runner = payload;
  let wrappedStdout = payload.stdout;
  if (
    typeof wrappedStdout !== "string" &&
    payload.data &&
    typeof payload.data === "object" &&
    typeof payload.data.stdout === "string"
  ) {
    runner = payload.data;
    wrappedStdout = payload.data.stdout;
  }
  if (typeof wrappedStdout === "string") {
    if (runner.interrupted === true) {
      problems.push("runner reports interrupted=true");
    }
    if (typeof runner.stderr === "string" && runner.stderr.trim() !== "") {
      runnerStderr = runner.stderr.trim();
    }
    try {
      payload = JSON.parse(wrappedStdout);
    } catch (error) {
      problems.push(`runner stdout is not valid lark-cli JSON: ${error.message}`);
    }
  }
}

function documentIdFromUrl(value) {
  if (typeof value !== "string") return null;
  const match = value.match(/\/(?:docx|docs)\/([^/?#]+)/);
  return match ? match[1] : null;
}

let boundDocumentId = null;
let boundRevision = null;
let observedWarnings = [];

if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
  problems.push("lark-cli payload must be a JSON object");
} else {
  if (payload.ok !== true) {
    problems.push(`top-level ok must be true, got ${JSON.stringify(payload.ok)}`);
  }
  const data = payload.data && typeof payload.data === "object"
    ? payload.data
    : {};
  if (data.result !== undefined && data.result !== "success") {
    problems.push(
      `data.result must be success when present, got ${JSON.stringify(data.result)}`,
    );
  }

  const warnings = [];
  const addWarnings = (value) => {
    if (Array.isArray(value)) warnings.push(...value);
    else if (
      value !== undefined &&
      value !== null &&
      String(value).trim() !== ""
    ) {
      warnings.push(value);
    }
  };
  addWarnings(payload.warnings);
  addWarnings(payload.degrade_details);
  addWarnings(data.warnings);
  addWarnings(data.degrade_details);
  observedWarnings = warnings.map(String);

  const document = data.document && typeof data.document === "object"
    ? data.document
    : {};
  const explicitDocumentId =
    typeof document.document_id === "string" && document.document_id.trim()
      ? document.document_id.trim()
      : null;
  const urlDocumentId = documentIdFromUrl(document.url);
  if (
    explicitDocumentId &&
    urlDocumentId &&
    explicitDocumentId !== urlDocumentId
  ) {
    problems.push(
      `document_id ${JSON.stringify(explicitDocumentId)} does not match URL ` +
        `target ${JSON.stringify(urlDocumentId)}`,
    );
  }
  boundDocumentId = explicitDocumentId || urlDocumentId;
  boundRevision = document.revision_id;

  if (!boundDocumentId) {
    problems.push(
      `${operation} must identify the document by document_id or its /docx/ URL`,
    );
  }
  if (!(Number.isInteger(boundRevision) && boundRevision > 0)) {
    problems.push(
      `${operation} must return a positive data.document.revision_id, got ` +
        JSON.stringify(boundRevision),
    );
  }
  if (expectedDocumentId && boundDocumentId !== expectedDocumentId) {
    problems.push(
      `document target mismatch: expected ${JSON.stringify(expectedDocumentId)}, ` +
        `got ${JSON.stringify(boundDocumentId)}`,
    );
  }

  if (operation === "create" && !document.url) {
    problems.push("create must return data.document.url");
  }
  if (operation === "update") {
    if (data.result !== "success") {
      problems.push(
        `update requires data.result=success, got ${JSON.stringify(data.result)}`,
      );
    }
    if (!(Number.isFinite(data.updated_blocks_count) && data.updated_blocks_count > 0)) {
      problems.push(
        `update requires updated_blocks_count > 0, got ` +
          JSON.stringify(data.updated_blocks_count),
      );
    }
    if (
      Number.isInteger(boundRevision) &&
      boundRevision <= previousRevision
    ) {
      problems.push(
        `update revision must advance beyond ${previousRevision}, got ` +
          boundRevision,
      );
    }
  }
}

const validationReport = {
  valid: problems.length === 0,
  operation,
  ok: payload && payload.ok,
  identity: payload && payload.identity,
  document_id: boundDocumentId,
  revision_id: boundRevision,
  expected_document_id: expectedDocumentId,
  previous_revision: previousRevision,
  warnings: observedWarnings.length,
  warning_details: observedWarnings,
  blocking_errors: problems,
  input_sha256: crypto.createHash("sha256").update(raw).digest("hex"),
  runner_stderr_observed: runnerStderr || null,
  content_readback_performed: false,
  note: (
    "This gate checks only the create/update response, document target, and " +
    "revision. It does not fetch or validate persisted document content."
  ),
};

const validationReportText = JSON.stringify(validationReport, null, 2);
if (reportPath) {
  try {
    fs.writeFileSync(reportPath, `${validationReportText}\n`, "utf8");
  } catch (error) {
    console.error(`Failed to write validation report: ${error.message}`);
    process.exit(2);
  }
}

const consoleReport = reportPath
  ? {
    valid: validationReport.valid,
    operation: validationReport.operation,
    document_id: validationReport.document_id,
    revision_id: validationReport.revision_id,
    warnings: validationReport.warnings,
    blocking_error_count: validationReport.blocking_errors.length,
    content_readback_performed: false,
    report: reportPath,
    note: validationReport.note,
  }
  : validationReport;
console.log(JSON.stringify(consoleReport, null, 2));

if (problems.length > 0) {
  console.error("Lark document write did not pass the delivery gate:");
  for (const problem of problems.slice(0, 5)) {
    console.error(`- ${problem}`);
  }
  if (problems.length > 5) {
    console.error(
      `- ${problems.length - 5} additional errors are in ` +
        `${reportPath || "stdout"}`,
    );
  }
  process.exit(1);
}

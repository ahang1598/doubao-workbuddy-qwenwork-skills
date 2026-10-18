import { createHash, randomUUID } from "node:crypto";
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  renameSync,
  unlinkSync,
  writeSync,
} from "node:fs";
import path from "node:path";

// Keep this framing protocol aligned with google-drive/skills/google-slides/host/slides-stdin-receiver.pl.
const READY_MARKER = "TEMPLATE_EXPORT_READY";
const COMMITTED_MARKER = "TEMPLATE_EXPORT_COMMITTED";
const ERROR_MARKER = "TEMPLATE_EXPORT_ERROR";
const RECORD_SEPARATOR = "\u0003";
const MAX_RECORD_CHARS = 1024 * 1024;

let temporaryPath;
let outputHandle;

function cleanup() {
  if (outputHandle != null) {
    try {
      closeSync(outputHandle);
    } catch {
      // The handle may already be closed.
    }
    outputHandle = undefined;
  }
  if (temporaryPath != null && existsSync(temporaryPath)) {
    try {
      unlinkSync(temporaryPath);
    } catch {
      // Preserve the original failure.
    }
  }
}

function fail(code, reason) {
  cleanup();
  process.stderr.write(`${ERROR_MARKER} ${reason}\n`);
  process.exit(code);
}

const [outputArgument, workspaceArgument, expectedBytesArgument] =
  process.argv.slice(2);
if (
  outputArgument == null ||
  workspaceArgument == null ||
  expectedBytesArgument == null
) {
  fail(64, "invalid-arguments");
}
if (!/^\d+$/.test(expectedBytesArgument)) {
  fail(65, "invalid-expected-bytes");
}

const expectedBytes = Number(expectedBytesArgument);
const workspaceRoot = path.resolve(workspaceArgument);
const outputPath = path.resolve(outputArgument);
const relativeOutput = path.relative(workspaceRoot, outputPath);
if (
  expectedBytes <= 0 ||
  relativeOutput === "" ||
  relativeOutput === ".." ||
  relativeOutput.startsWith(`..${path.sep}`) ||
  path.isAbsolute(relativeOutput)
) {
  fail(65, "invalid-output");
}

try {
  mkdirSync(path.dirname(outputPath), { recursive: true });
  if (existsSync(outputPath)) {
    fail(66, "destination-exists");
  }
  temporaryPath = `${outputPath}.stream-${randomUUID()}.tmp`;
  outputHandle = openSync(temporaryPath, "wx", 0o600);
} catch {
  fail(67, "temporary-create-failed");
}

process.on("exit", cleanup);
process.on("SIGHUP", () => fail(129, "interrupted"));
process.on("SIGTERM", () => fail(143, "interrupted"));

let buffer = "";
let nextSequence = 0;
let bytesWritten = 0;
const sha256 = createHash("sha256");

function writePayload(payload) {
  if (payload.length % 4 !== 0) {
    fail(70, "invalid-base64");
  }
  const decoded = Buffer.from(payload, "base64");
  let offset = 0;
  try {
    while (offset < decoded.length) {
      const written = writeSync(
        outputHandle,
        decoded,
        offset,
        decoded.length - offset,
      );
      if (written <= 0) {
        fail(71, "write-failed");
      }
      offset += written;
    }
  } catch {
    fail(71, "write-failed");
  }
  bytesWritten += decoded.length;
  sha256.update(decoded);
}

function commit() {
  try {
    closeSync(outputHandle);
    outputHandle = undefined;
  } catch {
    fail(71, "close-failed");
  }
  if (bytesWritten !== expectedBytes) {
    fail(72, "byte-count-mismatch");
  }
  const digest = sha256.digest("hex");
  try {
    renameSync(temporaryPath, outputPath);
    temporaryPath = undefined;
  } catch {
    fail(75, "publish-failed");
  }
  process.stdout.write(`${COMMITTED_MARKER} ${bytesWritten} ${digest}\n`, () =>
    process.exit(0),
  );
}

function processRecord(record) {
  const data = /^D\t(\d+)\t([A-Za-z0-9+/]*={0,2})$/.exec(record);
  if (data) {
    if (Number(data[1]) !== nextSequence) {
      fail(70, "invalid-sequence");
    }
    writePayload(data[2]);
    nextSequence += 1;
    return;
  }
  if (record === "C") {
    commit();
    return;
  }
  if (record === "A") {
    fail(76, "aborted");
  }
  fail(77, "invalid-record");
}

if (process.stdin.isTTY && typeof process.stdin.setRawMode === "function") {
  process.stdin.setRawMode(true);
}
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  buffer += chunk;
  if (buffer.length > MAX_RECORD_CHARS) {
    fail(70, "record-too-large");
  }
  let separator = buffer.indexOf(RECORD_SEPARATOR);
  while (separator >= 0) {
    const record = buffer.slice(0, separator);
    buffer = buffer.slice(separator + RECORD_SEPARATOR.length);
    processRecord(record);
    separator = buffer.indexOf(RECORD_SEPARATOR);
  }
});
process.stdin.on("end", () => fail(78, "unexpected-eof"));
process.stdout.write(`${READY_MARKER}\n`);

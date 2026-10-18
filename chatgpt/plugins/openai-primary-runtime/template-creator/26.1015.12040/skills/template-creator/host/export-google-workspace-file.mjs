const READY_MARKER = "TEMPLATE_EXPORT_READY";
const COMMITTED_MARKER = "TEMPLATE_EXPORT_COMMITTED";
const RECORD_SEPARATOR = "\u0003";
const MAX_EXPORT_BYTES = 64 * 1024 * 1024;
const FRAME_CHARS = 480000;
const EXPORT_FORMATS = {
  "application/pdf": {
    base64Prefix: "JVBERi0",
    extension: ".pdf",
  },
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
    base64Prefix: "UEsDB",
    extension: ".xlsx",
  },
};

class GoogleWorkspaceExportError extends Error {
  constructor(message) {
    super(
      String(message).replace(/https?:\/\/[^\s\"'<>]+/gi, "[URL_REDACTED]"),
    );
    this.name = "GoogleWorkspaceExportError";
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new GoogleWorkspaceExportError(message);
  }
}

function isWindowsAbsolutePath(value) {
  return typeof value === "string" && /^(?:[A-Za-z]:[\\/]|\\\\)/.test(value);
}

function isAbsolutePath(value) {
  return (
    typeof value === "string" &&
    (value.startsWith("/") || isWindowsAbsolutePath(value))
  );
}

function quotePosix(value) {
  return `'${String(value).replace(/'/g, `'\"'\"'`)}'`;
}

function quotePowerShell(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function fileReceiverCommand({
  nodePath,
  receiverPath,
  outputPath,
  workspaceRoot,
  bytes,
}) {
  const args = [
    nodePath,
    receiverPath,
    outputPath,
    workspaceRoot,
    String(bytes),
  ];
  if (isWindowsAbsolutePath(nodePath)) {
    return `& ${args.map(quotePowerShell).join(" ")}`;
  }
  return args.map(quotePosix).join(" ");
}

function getGoogleDriveFetchToolName(tools) {
  // Keep this resolver aligned with google-drive/skills/google-slides/host/export-and-render-slides.mjs.
  const preferred = "mcp__codex_apps__google_drive_fetch";
  if (typeof tools?.[preferred] === "function") {
    return preferred;
  }
  const matches = Object.keys(tools ?? {}).filter(
    (name) =>
      typeof tools[name] === "function" &&
      String(name)
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "")
        .endsWith("googledrivefetch"),
  );
  assert(matches.length === 1, "Could not resolve the Google Drive fetch tool");
  return matches[0];
}

function getGoogleWorkspaceUrl(value) {
  assert(
    typeof value === "string" &&
      /^https:\/\/docs\.google\.com\/(?:document|presentation|spreadsheets)\/(?:u\/\d+\/)?d\/[A-Za-z0-9_-]+(?:[/?#]|$)/.test(
        value,
      ) &&
      !/[\u0000-\u0020\u007f]/.test(value),
    "sourceUrl must identify a Google Docs, Slides, or Sheets file",
  );
  return value;
}

function parseJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function unwrapToolResult(raw) {
  assert(raw?.isError !== true, "Google Drive fetch failed");
  if (raw?.structuredContent?.result !== undefined) {
    return raw.structuredContent.result;
  }
  if (raw?.structuredContent !== undefined) {
    return raw.structuredContent;
  }
  const value = Array.isArray(raw?.content)
    ? raw.content.find(
        (item) => item?.type === "text" && typeof item.text === "string",
      )?.text
    : null;
  return value ? (parseJson(value) ?? raw) : raw;
}

function findFilePayload(root, expectedMimeType) {
  const queue = [root];
  const seen = new Set();
  while (queue.length > 0 && seen.size < 10000) {
    const value = queue.shift();
    if (value == null || typeof value !== "object" || seen.has(value)) {
      continue;
    }
    seen.add(value);
    if (!Array.isArray(value)) {
      const mimeType = value.mimeType ?? value.mime_type ?? null;
      if (typeof value.b64_string === "string") {
        return { content: value.b64_string, mimeType };
      }
      if (
        typeof value.content === "string" &&
        (mimeType === expectedMimeType ||
          (value.base64Encoded === true && mimeType == null))
      ) {
        return { content: value.content, mimeType };
      }
    }
    for (const child of Array.isArray(value) ? value : Object.values(value)) {
      if (child != null && typeof child === "object") {
        queue.push(child);
      }
    }
  }
  throw new GoogleWorkspaceExportError(
    `Google Drive export did not contain inline base64 ${expectedMimeType} content`,
  );
}

function decodedBase64Bytes(value) {
  if (value.length === 0 || value.length % 4 !== 0) {
    return null;
  }
  const padding = value.endsWith("==") ? 2 : value.endsWith("=") ? 1 : 0;
  return (value.length / 4) * 3 - padding;
}

function validateFilePayload(value, mimeType) {
  const payload = findFilePayload(value, mimeType);
  const base64 = payload.content;
  const actualMimeType = payload.mimeType ?? payload.mime_type ?? mimeType;
  assert(
    actualMimeType === mimeType,
    `Export returned ${actualMimeType} instead of ${mimeType}`,
  );
  assert(
    /^[A-Za-z0-9+/]*={0,2}$/.test(base64),
    "Google Drive export contains invalid base64",
  );
  assert(
    base64.startsWith(EXPORT_FORMATS[mimeType].base64Prefix),
    `Google Drive export does not contain a valid ${EXPORT_FORMATS[mimeType].extension} header`,
  );
  const bytes = decodedBase64Bytes(base64);
  assert(
    Number.isInteger(bytes) && bytes > 0,
    "Google Drive export has an invalid decoded byte length",
  );
  assert(
    bytes <= MAX_EXPORT_BYTES,
    `Google Drive export exceeds the ${MAX_EXPORT_BYTES}-byte limit`,
  );
  return { base64, bytes };
}

async function waitForMarker(tools, initial, sessionId, marker) {
  let result = initial;
  let output = String(result?.output ?? "");
  for (let attempt = 0; attempt < 5; attempt += 1) {
    if (output.includes(marker) || result?.exit_code != null) {
      break;
    }
    result = await tools.write_stdin({
      session_id: sessionId,
      chars: "",
      yield_time_ms: 1000,
      max_output_tokens: 1000,
    });
    output += String(result?.output ?? "");
  }
  if (output.includes(marker)) {
    return { result, output };
  }
  throw new GoogleWorkspaceExportError(
    `File receiver did not report ${marker}`,
  );
}

async function writeBase64({
  base64,
  bytes,
  nodePath,
  receiverPath,
  outputPath,
  workspaceRoot,
  tools,
}) {
  const started = await tools.exec_command({
    cmd: fileReceiverCommand({
      nodePath,
      receiverPath,
      outputPath,
      workspaceRoot,
      bytes,
    }),
    shell: isWindowsAbsolutePath(nodePath) ? "powershell.exe" : "/bin/sh",
    workdir: workspaceRoot,
    login: false,
    tty: true,
    yield_time_ms: 1000,
    max_output_tokens: 1000,
  });
  const sessionId = started?.session_id;
  assert(
    Number.isInteger(sessionId),
    `Could not start file receiver: ${started?.output ?? "missing session"}`,
  );

  try {
    await waitForMarker(tools, started, sessionId, READY_MARKER);
    let sequence = 0;
    for (let offset = 0; offset < base64.length; offset += FRAME_CHARS) {
      const write = await tools.write_stdin({
        session_id: sessionId,
        chars: `D\t${sequence}\t${base64.slice(offset, offset + FRAME_CHARS)}${RECORD_SEPARATOR}`,
        yield_time_ms: 250,
        max_output_tokens: 1000,
      });
      assert(write?.exit_code == null, "File receiver exited before commit");
      sequence += 1;
    }
    const committed = await tools.write_stdin({
      session_id: sessionId,
      chars: `C${RECORD_SEPARATOR}`,
      yield_time_ms: 30000,
      max_output_tokens: 1000,
    });
    const completed = await waitForMarker(
      tools,
      committed,
      sessionId,
      COMMITTED_MARKER,
    );
    const receipt = /TEMPLATE_EXPORT_COMMITTED\s+(\d+)\s+([a-f0-9]{64})/i.exec(
      completed.output,
    );
    assert(receipt, "File receiver returned an invalid receipt");
    assert(
      Number(receipt[1]) === bytes,
      "File receiver wrote the wrong byte count",
    );
    assert(
      completed.result?.exit_code === 0,
      "File receiver did not exit cleanly",
    );
    return { path: outputPath, bytes, sha256: receipt[2].toLowerCase() };
  } catch (error) {
    try {
      await tools.write_stdin({
        session_id: sessionId,
        chars: `A${RECORD_SEPARATOR}`,
        yield_time_ms: 1000,
        max_output_tokens: 1000,
      });
    } catch {
      // Receiver may already have exited.
    }
    throw error;
  }
}

async function exportGoogleWorkspaceFile({
  sourceUrl,
  mimeType,
  nodePath,
  receiverPath,
  outputPath,
  workspaceRoot,
  tools,
} = {}) {
  const url = getGoogleWorkspaceUrl(sourceUrl);
  assert(
    Object.hasOwn(EXPORT_FORMATS, mimeType),
    "mimeType must be PDF or XLSX",
  );
  assert(isAbsolutePath(nodePath), "nodePath must be absolute");
  assert(isAbsolutePath(receiverPath), "receiverPath must be absolute");
  assert(isAbsolutePath(outputPath), "outputPath must be absolute");
  assert(isAbsolutePath(workspaceRoot), "workspaceRoot must be absolute");
  assert(
    outputPath.endsWith(EXPORT_FORMATS[mimeType].extension),
    `outputPath must end in ${EXPORT_FORMATS[mimeType].extension}`,
  );
  assert(
    tools &&
      typeof tools.exec_command === "function" &&
      typeof tools.write_stdin === "function",
    "Code-mode tools are required",
  );

  const connectorTool = getGoogleDriveFetchToolName(tools);
  const raw = await tools[connectorTool]({
    url,
    download_raw_file: true,
    include_base64: true,
    raw_export_mime_type: mimeType,
  });
  const payload = validateFilePayload(unwrapToolResult(raw), mimeType);
  const file = await writeBase64({
    base64: payload.base64,
    bytes: payload.bytes,
    nodePath,
    receiverPath,
    outputPath,
    workspaceRoot,
    tools,
  });
  return {
    status: "complete",
    connectorTool,
    mimeType,
    file,
  };
}

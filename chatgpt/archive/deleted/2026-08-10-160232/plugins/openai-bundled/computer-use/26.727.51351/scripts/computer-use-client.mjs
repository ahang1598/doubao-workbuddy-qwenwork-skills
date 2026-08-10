import { Buffer } from "node:buffer";
import * as fs from "node:fs/promises";
import { endianness, platform } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const FRAME_HEADER_BYTES = 4;
const COMPUTER_USE_APPROVAL_REQUEST_METHOD = "requestComputerUseApproval";
const NODE_REPL_NODE_MODULE_DIRS_ENV_VAR = "NODE_REPL_NODE_MODULE_DIRS";
const TOOL_SURFACE_META_KEY = "codex/toolSurface";
// Consumed by codex/codex-apps/webview/src/local-conversation/chrome-computer-use-suggestion-state.ts.
const CHROME_COMPUTER_USE_META_KEY = "codex/computerUseChrome";
const WINDOWS_PROCESS_APP_ID_PREFIX = "process:";
const WINDOWS_CHROME_APP_ID_PATTERN = /^(?:process:)?(?:.*[\\/])?chrome\.exe$/i;
const DOCUMENTATION_NAMES = new Set(["api", "confirmations", "guidance"]);
const WindowsComputerUseClientBase =
  platform() === "win32"
    ? (await import(pathToFileURL(getWindowsComputerUseClientBasePath()).href))
        .WindowsComputerUseClientBase
    : class {};
let activeSkyClient = null;

export async function setupComputerUseRuntime({ globals = globalThis } = {}) {
  if (platform() !== "win32") {
    const { sky } = await import("@oai/sky");
    return installComputerUseRuntime({ globals, sky });
  }

  await activeSkyClient?.close().catch(() => {});
  activeSkyClient = new NativePipeComputerUseClient({
    transport: await NativePipeComputerUseTransport.create(),
  });
  return installComputerUseRuntime({ globals, sky: activeSkyClient });
}

class NativePipeComputerUseClient extends WindowsComputerUseClientBase {
  documentation(name) {
    return readDocumentation(name);
  }

  async close() {
    try {
      await super.close();
    } finally {
      if (activeSkyClient === this) {
        activeSkyClient = null;
      }
    }
  }
}

class NativePipeComputerUseTransport {
  static async create() {
    if (platform() !== "win32") {
      throw new Error("Computer Use native pipe is only available on Windows");
    }
    const nativePipe = getComputerUsePrivilegedNodeRepl()?.nativePipe;
    if (
      nativePipe == null ||
      typeof nativePipe.createConnection !== "function"
    ) {
      throw new Error("Computer Use native pipe is unavailable");
    }

    const pipePath = getComputerUsePipePath();
    let transport = null;
    try {
      const socket = await nativePipe.createConnection(pipePath);
      transport = new NativePipeComputerUseTransport(socket);
      await transport.request("list_windows", {});
      return transport;
    } catch (error) {
      await transport?.close().catch(() => {});
      throw new Error(
        `Computer Use native pipe is unavailable: ${formatErrorMessage(error)}`,
      );
    }
  }

  constructor(socket) {
    this.nextRequestId = 1;
    this.pendingData = Buffer.alloc(0);
    this.pendingRequests = new Map();
    this.socket = socket;
    socket.on("data", (chunk) => this.handleData(chunk));
    socket.on("error", (error) => this.rejectPendingRequests(error));
    socket.on("close", () =>
      this.rejectPendingRequests(
        new Error("Computer Use native pipe closed before response"),
      ),
    );
  }

  async close() {
    if (this.socket == null) {
      return;
    }
    await this.sendMessage("close", {});
    this.socket.end();
    this.socket = null;
  }

  request(method, params, options = {}) {
    return this.sendMessage("request", {
      codexTurnMetadata: options.codexTurnMetadata,
      method,
      params,
    });
  }

  sendMessage(method, params) {
    if (this.socket == null) {
      throw new Error("Computer Use native pipe is closed");
    }

    const id = this.nextRequestId;
    this.nextRequestId += 1;
    const payload = JSON.stringify({
      id,
      jsonrpc: "2.0",
      method,
      params,
    });
    this.socket.write(encodeMessageFrame(payload));
    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { reject, resolve });
    });
  }

  handleData(chunk) {
    this.pendingData = Buffer.concat([this.pendingData, Buffer.from(chunk)]);
    const decoded = decodeMessageFrames(this.pendingData);
    this.pendingData = decoded.remainingData;

    for (const message of decoded.messages) {
      this.handleMessage(JSON.parse(message));
    }
  }

  handleMessage(message) {
    if (
      message.method === COMPUTER_USE_APPROVAL_REQUEST_METHOD &&
      message.id != null
    ) {
      void this.handleApprovalRequest(message);
      return;
    }

    const request =
      typeof message.id === "number"
        ? this.pendingRequests.get(message.id)
        : undefined;
    if (request == null) {
      return;
    }
    this.pendingRequests.delete(message.id);
    if (message.error != null) {
      request.reject(new Error(message.error.message));
      return;
    }
    request.resolve(message.result);
  }

  async handleApprovalRequest(message) {
    try {
      const createElicitation =
        getComputerUsePrivilegedNodeRepl()?.createElicitation;
      if (typeof createElicitation !== "function") {
        throw new Error(
          "Computer Use app approval UI is unavailable outside trusted node_repl",
        );
      }
      this.writeMessage({
        id: message.id,
        jsonrpc: "2.0",
        result: await createElicitation(message.params),
      });
    } catch (error) {
      this.writeMessage({
        error: {
          code: -32000,
          message: error instanceof Error ? error.message : String(error),
        },
        id: message.id,
        jsonrpc: "2.0",
      });
    }
  }

  rejectPendingRequests(error) {
    for (const request of this.pendingRequests.values()) {
      request.reject(error);
    }
    this.pendingRequests.clear();
  }

  writeMessage(message) {
    if (this.socket == null) {
      return;
    }
    this.socket.write(encodeMessageFrame(JSON.stringify(message)));
  }
}

function getComputerUsePrivilegedNodeRepl() {
  const nodeRepl = globalThis.nodeRepl;
  return nodeRepl?.config == null || nodeRepl?.nativePipe == null
    ? undefined
    : nodeRepl;
}

function getComputerUsePipePath() {
  const nativePipeDirectory =
    getComputerUsePrivilegedNodeRepl()?.env?.SKY_CUA_NATIVE_PIPE_DIRECTORY;
  if (typeof nativePipeDirectory === "string") {
    const trimmed = nativePipeDirectory.trim();
    if (trimmed) {
      return trimmed;
    }
  }

  throw new Error("Computer Use native pipe path is unavailable");
}

function formatErrorMessage(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

export async function readDocumentation(name) {
  if (!DOCUMENTATION_NAMES.has(name)) {
    throw new Error("Unsupported Computer Use documentation");
  }
  return await fs.readFile(
    new URL(`../docs/${name}.md`, import.meta.url),
    "utf8",
  );
}

function getWindowsComputerUseClientBasePath() {
  const nodeModulesEntry = getComputerUsePrivilegedNodeRepl()
    ?.env?.[NODE_REPL_NODE_MODULE_DIRS_ENV_VAR]?.split(path.delimiter)
    .find((value) => value.trim())
    ?.trim();
  if (nodeModulesEntry == null) {
    throw new Error("Windows Computer Use Sky runtime is unavailable");
  }
  const nodeModuleDir =
    path.basename(nodeModulesEntry) === "node_modules"
      ? nodeModulesEntry
      : path.join(nodeModulesEntry, "node_modules");
  return path.join(
    nodeModuleDir,
    "@oai/sky/dist/project/cua/sky_js/src/targets/windows/internal/computer_use_client_base.js",
  );
}

function installComputerUseRuntime({ globals, sky }) {
  const instrumentedSky = new Proxy(sky, {
    get(target, property, receiver) {
      const value = Reflect.get(target, property, receiver);
      if (typeof value !== "function") {
        return value;
      }

      return (...args) => {
        const app = getComputerUseAppReference(args[0]);
        globals.nodeRepl?.setResponseMeta({
          [TOOL_SURFACE_META_KEY]: {
            kind: "computerUse",
            app,
          },
          ...(isChromeComputerUseAppReference(app)
            ? { [CHROME_COMPUTER_USE_META_KEY]: true }
            : {}),
        });
        return Reflect.apply(value, target, args);
      };
    },
  });
  globals.sky = instrumentedSky;
  return instrumentedSky;
}

function isChromeComputerUseAppReference(app) {
  if (app?.kind === "appId") {
    return (
      app.appId === "Chrome" ||
      app.appId === "com.google.Chrome" ||
      WINDOWS_CHROME_APP_ID_PATTERN.test(app.appId)
    );
  }
  return (
    app?.kind === "displayName" &&
    ["chrome", "google chrome"].includes(app.displayName.trim().toLowerCase())
  );
}

function getComputerUseAppReference(value) {
  const app = value?.window?.app ?? value?.app;
  const trimmedApp = typeof app === "string" ? app.trim() : "";
  if (!trimmedApp) {
    return null;
  }

  // Sky accepts IDs returned by list_apps and human names such as "Notes".
  return looksLikeAppIdentifier(trimmedApp)
    ? { kind: "appId", appId: trimmedApp }
    : { kind: "displayName", displayName: trimmedApp };
}

function looksLikeAppIdentifier(value) {
  return (
    /^[a-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)+$/.test(value) ||
    value.toLowerCase().startsWith(WINDOWS_PROCESS_APP_ID_PREFIX) ||
    /(^|[\\/])[^\\/]+\.exe$/i.test(value) ||
    /[A-Za-z0-9][A-Za-z0-9.-]*_[A-Za-z0-9]+![A-Za-z0-9.-]+/.test(value)
  );
}

function encodeMessageFrame(message) {
  const payload = Buffer.from(message, "utf8");
  const frame = Buffer.alloc(FRAME_HEADER_BYTES + payload.length);
  if (endianness() === "LE") {
    frame.writeUInt32LE(payload.length, 0);
  } else {
    frame.writeUInt32BE(payload.length, 0);
  }
  payload.copy(frame, FRAME_HEADER_BYTES);
  return frame;
}

function decodeMessageFrames(buffer) {
  const messages = [];
  let offset = 0;

  while (buffer.length - offset >= FRAME_HEADER_BYTES) {
    const payloadLength =
      endianness() === "LE"
        ? buffer.readUInt32LE(offset)
        : buffer.readUInt32BE(offset);
    const frameLength = FRAME_HEADER_BYTES + payloadLength;
    if (buffer.length - offset < frameLength) {
      break;
    }
    messages.push(
      buffer
        .subarray(offset + FRAME_HEADER_BYTES, offset + frameLength)
        .toString("utf8"),
    );
    offset += frameLength;
  }

  return {
    messages,
    remainingData: buffer.subarray(offset),
  };
}

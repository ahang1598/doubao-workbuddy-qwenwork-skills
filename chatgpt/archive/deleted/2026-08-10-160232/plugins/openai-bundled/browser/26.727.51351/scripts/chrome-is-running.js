#!/usr/bin/env node
/* global console */
/* Detect whether a supported Chromium browser is currently running. */

let path;
let process;
let execFileSync;
let readlinkSync;
let readFileSync;
let getBrowserDiagnostics;
let parseBrowserFamilyArgs;

const CHROME_EXTENSION_ID_CONFIG_FILENAME = "extension-ids.json";

async function loadNodeModules() {
  path = await import("node:path");
  process = (await import("node:process")).default;
  ({ execFileSync } = await import("node:child_process"));
  ({ readFileSync, readlinkSync } = await import("node:fs"));
  ({ getBrowserDiagnostics, parseBrowserFamilyArgs } =
    await import("./chromium-browser-diagnostics.mjs"));
}

function usage() {
  console.error(
    "Usage: scripts/chrome-is-running.js [--browser chrome|edge] [--check] [--json]",
  );
}

function formatCommandError(command, args, error) {
  const commandDisplay = [command, ...args].join(" ");
  const details = [
    error?.code,
    typeof error?.status === "number" ? `exit ${error.status}` : null,
    error?.stderr?.toString().trim(),
    error?.message,
  ].filter(Boolean);
  return `Failed to run ${commandDisplay}: ${details.join("; ")}`;
}

function runCommand(command, args) {
  try {
    return execFileSync(command, args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
  } catch (error) {
    throw new Error(formatCommandError(command, args, error), { cause: error });
  }
}

function stripCommandArguments(command) {
  return command.trim().replace(/\s--.*$/, "");
}

function chromeProcessNameForCommand(browser, command) {
  const executable = stripCommandArguments(command);
  const processName = path.basename(executable);

  if (process.platform === "darwin") {
    if (
      !browser.macos.applicationNames.some((appName) =>
        executable.includes(`/${appName}/Contents/`),
      )
    )
      return processName;

    if (browser.macos.processNames.includes(processName)) return processName;
  }

  return processName;
}

function parseProcessList(browser, output, processNames) {
  if (!output) return [];

  const processes = [];
  for (const line of output.split(/\r?\n/)) {
    const match = line.match(/^\s*(\d+)\s+(.+?)\s*$/);
    if (!match) continue;

    const [, pid, command] = match;
    const processName = chromeProcessNameForCommand(browser, command);
    if (!processNames.has(processName)) continue;

    processes.push({
      pid: Number(pid),
      process_name: processName,
      command: stripCommandArguments(command),
    });
  }

  return processes;
}

function parseMacosApplicationProcessList(browser, output) {
  const processes = parseProcessList(
    browser,
    output,
    new Set(browser.macos.processNames),
  );

  return processes.filter((chromeProcess) => {
    return browser.macos.applicationNames.some((appName) =>
      chromeProcess.command.includes(`/${appName}/Contents/`),
    );
  });
}

function parseWindowsTaskList(browser, output) {
  if (!output) return [];

  const processes = [];
  for (const line of output.split(/\r?\n/)) {
    const match = line.match(/^"([^"]+)","(\d+)",/);
    if (
      !match ||
      !browser.windows.processNames.some(
        (processName) => processName.toLowerCase() === match[1].toLowerCase(),
      )
    )
      continue;

    processes.push({
      pid: Number(match[2]),
      process_name: match[1],
      command: match[1],
    });
  }

  return processes;
}

function getMacosChromeSingletonProcess(browser) {
  if (!process.env.HOME) return null;

  let singletonLockTarget;
  try {
    singletonLockTarget = readlinkSync(
      path.join(
        process.env.HOME,
        ...browser.macos.userDataDirectorySegments,
        "SingletonLock",
      ),
      "utf8",
    );
  } catch {
    return null;
  }

  const pidMatch = singletonLockTarget.match(/-(\d+)$/);
  if (!pidMatch) return null;

  const pid = Number(pidMatch[1]);
  if (!Number.isInteger(pid) || pid <= 0) return null;

  try {
    process.kill(pid, 0);
  } catch (error) {
    if (error?.code !== "EPERM") return null;
  }

  return {
    pid,
    process_name: browser.macos.processNames[0],
    command: browser.macos.processNames[0],
  };
}

function findRunningChromeProcesses(browser) {
  let platformConfig = browser.linux;
  if (process.platform === "darwin") platformConfig = browser.macos;
  else if (process.platform === "win32") platformConfig = browser.windows;
  const processNames = new Set(platformConfig.processNames);

  if (process.platform === "win32") {
    return parseWindowsTaskList(
      browser,
      runCommand("tasklist", ["/fo", "csv", "/nh"]),
    );
  }

  const singletonProcess =
    process.platform === "darwin"
      ? getMacosChromeSingletonProcess(browser)
      : null;

  let processList;
  try {
    processList = runCommand("ps", ["-A", "-o", "pid=", "-o", "comm="]);
  } catch (error) {
    if (singletonProcess != null) return [singletonProcess];

    throw error;
  }

  const processes = parseProcessList(browser, processList, processNames);
  if (processes.length > 0 || process.platform !== "darwin") return processes;

  try {
    return parseMacosApplicationProcessList(
      browser,
      runCommand("ps", ["-A", "-ww", "-o", "pid=", "-o", "command="]),
    );
  } catch (error) {
    if (singletonProcess != null) return [singletonProcess];

    throw error;
  }
}

function parseArgs(argv) {
  const flags = new Set(argv);
  if (flags.has("-h") || flags.has("--help")) {
    usage();
    process.exit(0);
  }

  const supportedFlags = new Set(["--check", "--json"]);
  const unsupportedFlags = argv.filter((arg) => !supportedFlags.has(arg));
  if (unsupportedFlags.length > 0) {
    usage();
    process.exit(2);
  }

  return {
    check: flags.has("--check"),
    json: flags.has("--json"),
  };
}

function printTextReport(result, check) {
  if (check) {
    console.log(`${result.browserName} running check`);
    console.log(`status: ${result.running ? "ok" : "not running"}`);
    console.log("");
  }

  console.log(
    `${result.browserName} running: ${result.running ? "yes" : "no"}`,
  );
  if (result.processes.length === 0) return;

  console.log("Processes:");
  for (const chromeProcess of result.processes) {
    console.log(`  - pid: ${chromeProcess.pid}`);
    console.log(`    process: ${chromeProcess.process_name}`);
  }
}

function main() {
  const { browserFamily, args: scriptArgs } = parseBrowserFamilyArgs(
    process.argv.slice(2),
  );
  const args = parseArgs(scriptArgs);
  const configPath = path.join(
    path.dirname(path.resolve(process.argv[1] || ".")),
    CHROME_EXTENSION_ID_CONFIG_FILENAME,
  );
  const browser = getBrowserDiagnostics(
    JSON.parse(readFileSync(configPath, "utf8")),
    browserFamily,
  );
  const processes = findRunningChromeProcesses(browser);
  const result = {
    browserFamily,
    browserName: browser.displayName,
    platform: process.platform,
    running: processes.length > 0,
    processes,
  };

  if (args.json) console.log(JSON.stringify(result, null, 2));
  else printTextReport(result, args.check);

  if (args.check && !result.running) process.exitCode = 1;
}

void loadNodeModules()
  .then(() => {
    main();
  })
  .catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    (process || globalThis.process)?.exit(2);
  });

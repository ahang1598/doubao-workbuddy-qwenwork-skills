#!/usr/bin/env node
/* global console */
/* Open a Chromium browser window for the profile selected by plugin checks. */

const CHROME_PREFERENCES_PATH_ENV = "CODEX_CHROME_PREFERENCES_PATH";
const CHROMIUM_PREFERENCES_PATH_ENV = "CODEX_CHROMIUM_PREFERENCES_PATH";
const CHROME_EXTENSION_ID_CONFIG_FILENAME = "extension-ids.json";
const ABOUT_BLANK_URL = "about:blank";

let fs;
let os;
let path;
let process;
let execFileSync;
let getBrowserDiagnostics;
let parseBrowserFamilyArgs;
let resolveBrowserUserDataDirectory;

async function loadNodeModules() {
  fs = await import("node:fs");
  os = await import("node:os");
  path = await import("node:path");
  process = (await import("node:process")).default;
  ({ execFileSync } = await import("node:child_process"));
  ({
    getBrowserDiagnostics,
    parseBrowserFamilyArgs,
    resolveBrowserUserDataDirectory,
  } = await import("./chromium-browser-diagnostics.mjs"));
}

function usage() {
  console.error(
    "Usage: scripts/open-chrome-window.js [--browser chrome|edge] [--dry-run] [--json]",
  );
  console.error("");
  console.error(
    "Optional profile-root override: CODEX_CHROMIUM_USER_DATA_DIR=/tmp/browser-root",
  );
  console.error(
    `Optional preferences-file override: ${CHROMIUM_PREFERENCES_PATH_ENV}=/tmp/Profile/Preferences`,
  );
}

function runCommand(args) {
  try {
    return execFileSync(args[0], args.slice(1), {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return null;
  }
}

function readWindowsRegistryValue(keyPath, valueName) {
  const args = ["reg", "query", keyPath, valueName == null ? "/ve" : "/v"];
  if (valueName != null) args.push(valueName);

  const output = runCommand(args);
  if (!output) return null;

  const label = valueName == null ? "(Default)" : valueName;
  for (const line of output.split(/\r?\n/)) {
    const match = line.match(/^\s*(.*?)\s+REG_\w+\s+(.+?)\s*$/);
    if (match && match[1] === label) return stripRegistryString(match[2]);
  }

  return null;
}

function stripRegistryString(value) {
  return value.replace(/^"(.*)"$/, "$1");
}

function resolveChromeUserDataDirectory(browser) {
  return resolveBrowserUserDataDirectory({
    browser,
    env: process.env,
    homedir: os.homedir(),
    path,
    platform: process.platform,
  });
}

function resolveChromePreferencesPath(browser) {
  const override =
    process.env[CHROMIUM_PREFERENCES_PATH_ENV] ??
    (browser.browserFamily === "chrome"
      ? process.env[CHROME_PREFERENCES_PATH_ENV]
      : undefined);
  if (override) return path.resolve(override);

  const userDataDirectory = resolveChromeUserDataDirectory(browser);
  const profileDirectory = resolveChromeProfileDirectory(userDataDirectory);
  return path.join(userDataDirectory, profileDirectory, "Preferences");
}

function resolveChromeProfileDirectory(userDataDirectory) {
  const localStateProfile =
    resolveChromeProfileDirectoryFromLocalState(userDataDirectory);
  if (localStateProfile) return localStateProfile;

  const latestProfile = findLatestChromeProfile(userDataDirectory);
  if (latestProfile) return latestProfile;

  throw new Error(
    `Could not find a browser profile directory with Preferences in ${userDataDirectory}.`,
  );
}

function resolveChromeProfileDirectoryFromLocalState(userDataDirectory) {
  const localState = readJsonFileIfPresent(
    path.join(userDataDirectory, "Local State"),
  );
  const profile = localState?.profile;
  if (!profile || typeof profile !== "object") return null;

  if (isUsableChromeProfile(userDataDirectory, profile.last_used))
    return profile.last_used;

  if (Array.isArray(profile.last_active_profiles)) {
    return chooseLatestUsableChromeProfile(
      userDataDirectory,
      profile.last_active_profiles,
    );
  }

  return null;
}

function chooseLatestUsableChromeProfile(
  userDataDirectory,
  profileDirectories,
) {
  const usableProfiles = profileDirectories.filter((profileDirectory) => {
    return isUsableChromeProfile(userDataDirectory, profileDirectory);
  });
  if (usableProfiles.length === 0) return null;

  return usableProfiles.sort(compareChromeProfileDirectories).at(-1);
}

function findLatestChromeProfile(userDataDirectory) {
  if (!fs.existsSync(userDataDirectory)) {
    throw new Error(
      `Browser user data directory does not exist: ${userDataDirectory}`,
    );
  }

  const profileDirectories = fs
    .readdirSync(userDataDirectory, { withFileTypes: true })
    .filter((entry) => {
      return (
        entry.isDirectory() &&
        (entry.name === "Default" || /^Profile \d+$/.test(entry.name))
      );
    })
    .map((entry) => entry.name);

  return chooseLatestUsableChromeProfile(userDataDirectory, profileDirectories);
}

function readJsonFileIfPresent(filePath) {
  if (!fs.existsSync(filePath)) return null;

  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function isUsableChromeProfile(userDataDirectory, profileDirectory) {
  if (typeof profileDirectory !== "string" || profileDirectory.length === 0)
    return false;

  return fs.existsSync(
    path.join(userDataDirectory, profileDirectory, "Preferences"),
  );
}

function compareChromeProfileDirectories(first, second) {
  return (
    chromeProfileDirectorySortKey(first) - chromeProfileDirectorySortKey(second)
  );
}

function chromeProfileDirectorySortKey(profileDirectory) {
  if (profileDirectory === "Default") return 0;

  const match = profileDirectory.match(/^Profile (\d+)$/);
  if (!match) return -1;

  return Number(match[1]);
}

function macosAppSearchDirs() {
  return [
    "/Applications",
    "/System/Applications",
    path.join(os.homedir(), "Applications"),
  ];
}

function readPlistKey(plistPath, key) {
  return runCommand(["plutil", "-extract", key, "raw", "-o", "-", plistPath]);
}

function readPlistJson(plistPath) {
  const output = runCommand([
    "plutil",
    "-convert",
    "json",
    "-o",
    "-",
    plistPath,
  ]);
  if (!output) return {};

  try {
    return JSON.parse(output);
  } catch {
    return {};
  }
}

function readBundleInfo(appPath) {
  const infoPath = path.join(appPath, "Contents", "Info.plist");
  if (!fs.existsSync(infoPath)) return {};

  const info = readPlistJson(infoPath);
  if (Object.keys(info).length > 0) return info;

  return {
    CFBundleIdentifier: readPlistKey(infoPath, "CFBundleIdentifier"),
  };
}

function macosAppCandidates(browser) {
  const candidates = [];
  for (const baseDir of macosAppSearchDirs()) {
    for (const appName of browser.macos.applicationNames)
      candidates.push(path.join(baseDir, appName));
  }
  return candidates;
}

function mdfindChromeApps(browser) {
  const output = runCommand([
    "mdfind",
    `kMDItemCFBundleIdentifier == '${browser.macos.bundleId}'`,
  ]);
  if (!output) return [];

  return output.split(/\r?\n/).filter((line) => line.endsWith(".app"));
}

function isChromeApp(browser, appPath, allowNamedFallback = false) {
  if (!fs.existsSync(appPath)) return false;

  const info = readBundleInfo(appPath);
  if (info.CFBundleIdentifier === browser.macos.bundleId) return true;

  return (
    allowNamedFallback &&
    browser.macos.applicationNames.includes(path.basename(appPath))
  );
}

function findMacosChromeAppPath(browser) {
  for (const appPath of macosAppCandidates(browser))
    if (isChromeApp(browser, appPath, true)) return appPath;

  for (const appPath of mdfindChromeApps(browser))
    if (isChromeApp(browser, appPath)) return appPath;

  for (const baseDir of macosAppSearchDirs()) {
    if (!fs.existsSync(baseDir)) continue;

    for (const entry of fs.readdirSync(baseDir, { withFileTypes: true })) {
      if (!entry.isDirectory() || !entry.name.endsWith(".app")) continue;

      const appPath = path.join(baseDir, entry.name);
      if (isChromeApp(browser, appPath)) return appPath;
    }
  }

  throw new Error(`Could not find the ${browser.displayName} app.`);
}

function commandPath(command) {
  if (process.platform === "win32")
    return runCommand(["where", command])?.split(/\r?\n/)[0] || null;

  return runCommand(["which", command]);
}

function windowsChromeInstallPaths(browser) {
  const executableName = browser.windows.commandNames[0];
  const appPathKeys = [
    `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${executableName}`,
    `HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${executableName}`,
    `HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${executableName}`,
  ];
  const candidates = appPathKeys
    .map((keyPath) => readWindowsRegistryValue(keyPath, null))
    .filter(Boolean);

  const localAppData =
    process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local");
  const standardRoots = [
    localAppData,
    process.env.PROGRAMFILES,
    process.env["PROGRAMFILES(X86)"],
  ].filter(Boolean);

  for (const root of standardRoots)
    candidates.push(path.join(root, ...browser.windows.installPathSegments));

  for (const command of browser.windows.commandNames) {
    const commandExecutable = commandPath(command);
    if (commandExecutable) candidates.push(commandExecutable);
  }

  const found = new Map();
  for (const candidate of candidates) {
    const executablePath = path.resolve(candidate);
    if (!fs.existsSync(executablePath)) continue;

    found.set(executablePath.toLowerCase(), executablePath);
  }

  return [...found.values()];
}

function findWindowsChromeExecutable(browser) {
  const executableNames = new Set(
    browser.windows.commandNames.map((command) => command.toLowerCase()),
  );
  for (const executablePath of windowsChromeInstallPaths(browser)) {
    if (executableNames.has(path.basename(executablePath).toLowerCase()))
      return executablePath;
  }

  throw new Error(`Could not find the ${browser.displayName} executable.`);
}

function getOpenChromeCommand(browser, profileDirectory) {
  const chromeArgs = [
    `--profile-directory=${profileDirectory}`,
    "--new-window",
    ABOUT_BLANK_URL,
  ];

  if (process.platform === "darwin") {
    return {
      command: "open",
      args: [
        "-n",
        "-a",
        findMacosChromeAppPath(browser),
        "--args",
        ...chromeArgs,
      ],
    };
  }

  if (process.platform === "win32") {
    return {
      command: "cmd.exe",
      args: [
        "/d",
        "/s",
        "/c",
        "start",
        '""',
        findWindowsChromeExecutable(browser),
        ...chromeArgs,
      ],
    };
  }

  return {
    command:
      browser.linux.commands.find((command) => commandPath(command) != null) ??
      browser.linux.commands[0],
    args: chromeArgs,
  };
}

function parseArgs(argv) {
  const flags = new Set(argv);
  if (flags.has("-h") || flags.has("--help")) {
    usage();
    process.exit(0);
  }

  const supportedFlags = new Set(["--dry-run", "--json"]);
  const unsupportedFlags = argv.filter((arg) => !supportedFlags.has(arg));
  if (unsupportedFlags.length > 0) {
    usage();
    process.exit(2);
  }

  return {
    dryRun: flags.has("--dry-run"),
    json: flags.has("--json"),
  };
}

function formatCommand(command, args) {
  return [command, ...args]
    .map((part) => (/\s/.test(part) ? JSON.stringify(part) : part))
    .join(" ");
}

function resolveSiblingScriptPath(filename) {
  const scriptPath = path.resolve(process.argv[1] || ".");
  return path.join(path.dirname(scriptPath), filename);
}

function printTextReport(result) {
  console.log(`${result.browserName} window open request`);
  console.log(`status: ${result.dryRun ? "dry run" : "opened"}`);
  console.log(`profile: ${result.profileDirectory}`);
  console.log(`command: ${formatCommand(result.command, result.args)}`);
}

function main() {
  const { browserFamily, args: scriptArgs } = parseBrowserFamilyArgs(
    process.argv.slice(2),
  );
  const args = parseArgs(scriptArgs);
  const configPath = resolveSiblingScriptPath(
    CHROME_EXTENSION_ID_CONFIG_FILENAME,
  );
  const browser = getBrowserDiagnostics(
    JSON.parse(fs.readFileSync(configPath, "utf8")),
    browserFamily,
  );
  const preferencesPath = resolveChromePreferencesPath(browser);
  const profileDirectory = path.basename(path.dirname(preferencesPath));
  const command = getOpenChromeCommand(browser, profileDirectory);
  const result = {
    browserFamily,
    browserName: browser.displayName,
    platform: process.platform,
    dryRun: args.dryRun,
    profileDirectory,
    command: command.command,
    args: command.args,
  };

  if (!args.dryRun) {
    execFileSync(command.command, command.args, {
      stdio: ["ignore", "ignore", "pipe"],
    });
  }

  if (args.json) console.log(JSON.stringify(result, null, 2));
  else printTextReport(result);
}

void loadNodeModules()
  .then(() => {
    main();
  })
  .catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    (process || globalThis.process)?.exit(2);
  });

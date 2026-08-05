#!/usr/bin/env node
/* global console */
/* Report the default browser and known installed internet browsers. */

let fs;
let os;
let path;
let process;
let execFileSync;
let knownBrowsers;

const DEFAULT_BROWSER_SCHEMES = ["http", "https"];

async function loadNodeModules() {
  fs = await import("node:fs");
  os = await import("node:os");
  path = await import("node:path");
  process = (await import("node:process")).default;
  ({ execFileSync } = await import("node:child_process"));

  const config = JSON.parse(
    fs.readFileSync(resolveSiblingScriptPath("extension-ids.json"), "utf8"),
  );
  knownBrowsers = config.browserDiagnostics.map((browser) => ({
    browserFamily: browser.browserFamily,
    name: browser.displayName,
    bundleIds: [browser.macos.bundleId],
    appNames: browser.macos.applicationNames,
    commands: browser.linux.commands,
    windowsCommandNames: browser.windows.commandNames,
    windowsInstallPathSegments: browser.windows.installPathSegments,
  }));
}

function resolveSiblingScriptPath(filename) {
  const scriptPath = process.argv[1]
    ? path.resolve(process.argv[1])
    : path.resolve("scripts/installed-browsers.js");
  return path.join(path.dirname(scriptPath), filename);
}

function macosAppSearchDirs() {
  return [
    "/Applications",
    "/System/Applications",
    path.join(os.homedir(), "Applications"),
  ];
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

function windowsBrowserInstallPaths(browser) {
  const appPathKeys = browser.windowsCommandNames
    .filter((command) => command.endsWith(".exe"))
    .flatMap((command) => [
      `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${command}`,
      `HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${command}`,
      `HKLM\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${command}`,
    ]);
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
    candidates.push(path.join(root, ...browser.windowsInstallPathSegments));

  for (const command of browser.windowsCommandNames) {
    const executable = commandPath(command);
    if (executable) candidates.push(executable);
  }

  const found = new Map();
  for (const candidate of candidates) {
    const executablePath = path.resolve(candidate);
    if (!fs.existsSync(executablePath)) continue;

    found.set(executablePath.toLowerCase(), executablePath);
  }

  return [...found.values()];
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
    CFBundleShortVersionString: readPlistKey(
      infoPath,
      "CFBundleShortVersionString",
    ),
  };
}

function knownBrowserByBundleId() {
  const byBundleId = new Map();
  for (const browser of knownBrowsers)
    for (const bundleId of browser.bundleIds) byBundleId.set(bundleId, browser);

  return byBundleId;
}

function macosAppCandidates(browser) {
  const candidates = [];
  for (const baseDir of macosAppSearchDirs()) {
    for (const appName of browser.appNames)
      candidates.push(path.join(baseDir, appName));
  }
  return candidates;
}

function mdfindAppsForBundleId(bundleId) {
  const output = runCommand([
    "mdfind",
    `kMDItemCFBundleIdentifier == '${bundleId}'`,
  ]);
  if (!output) return [];

  return output.split(/\r?\n/).filter((line) => line.endsWith(".app"));
}

function addMacosApp(
  installedByBundleId,
  browser,
  appPath,
  fallbackBundleId = null,
) {
  if (!fs.existsSync(appPath)) return;

  const info = readBundleInfo(appPath);
  const bundleId =
    info.CFBundleIdentifier || fallbackBundleId || browser.bundleIds[0];
  if (!bundleId) return;

  installedByBundleId.set(bundleId, {
    name: browser.name,
    bundle_id: bundleId,
    path: appPath,
    version: info.CFBundleShortVersionString || info.CFBundleVersion || null,
  });
}

function findMacosApps() {
  const installedByBundleId = new Map();

  for (const browser of knownBrowsers) {
    for (const appPath of macosAppCandidates(browser))
      addMacosApp(installedByBundleId, browser, appPath);

    for (const bundleId of browser.bundleIds) {
      for (const appPath of mdfindAppsForBundleId(bundleId))
        addMacosApp(installedByBundleId, browser, appPath, bundleId);
    }
  }

  const knownByBundleId = knownBrowserByBundleId();
  for (const baseDir of macosAppSearchDirs()) {
    if (!fs.existsSync(baseDir)) continue;

    for (const entry of fs.readdirSync(baseDir, { withFileTypes: true })) {
      if (!entry.isDirectory() || !entry.name.endsWith(".app")) continue;

      const appPath = path.join(baseDir, entry.name);
      const info = readBundleInfo(appPath);
      const browser = knownByBundleId.get(info.CFBundleIdentifier);
      if (!browser) continue;

      addMacosApp(
        installedByBundleId,
        browser,
        appPath,
        info.CFBundleIdentifier,
      );
    }
  }

  return [...installedByBundleId.values()].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
}

function resolveMacosAppByBundleId(bundleId) {
  for (const appPath of mdfindAppsForBundleId(bundleId)) {
    if (!fs.existsSync(appPath)) continue;

    const info = readBundleInfo(appPath);
    if (info.CFBundleIdentifier && info.CFBundleIdentifier !== bundleId)
      continue;

    return {
      name:
        info.CFBundleName ||
        info.CFBundleDisplayName ||
        path.basename(appPath, ".app"),
      bundle_id: bundleId,
      path: appPath,
      version: info.CFBundleShortVersionString || info.CFBundleVersion || null,
    };
  }

  return null;
}

function commandPath(command) {
  if (process.platform === "win32")
    return runCommand(["where", command])?.split(/\r?\n/)[0] || null;

  return runCommand(["which", command]);
}

function findCommandBrowsers() {
  const found = new Map();

  for (const browser of knownBrowsers) {
    for (const command of browser.commands) {
      const executable = commandPath(command);
      if (!executable) continue;

      found.set(browser.name, {
        name: browser.name,
        command,
        path: executable,
        bundle_id: browser.bundleIds[0] || null,
        version: null,
      });
      break;
    }
  }

  return [...found.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function findWindowsApps() {
  const found = new Map();

  for (const browser of knownBrowsers) {
    for (const executablePath of windowsBrowserInstallPaths(browser)) {
      found.set(executablePath.toLowerCase(), {
        name: browser.name,
        command: path.basename(executablePath),
        path: executablePath,
        bundle_id: null,
        version: null,
      });
    }
  }

  return [...found.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function loadLaunchServicesHandlers() {
  const plistPath = path.join(
    os.homedir(),
    "Library",
    "Preferences",
    "com.apple.LaunchServices",
    "com.apple.launchservices.secure.plist",
  );

  if (!fs.existsSync(plistPath)) return [];

  const output = runCommand([
    "plutil",
    "-extract",
    "LSHandlers",
    "json",
    "-o",
    "-",
    plistPath,
  ]);
  if (!output) return [];

  try {
    const handlers = JSON.parse(output);
    return Array.isArray(handlers) ? handlers : [];
  } catch {
    return [];
  }
}

function findDefaultBrowserMacos(installed) {
  const byBundleId = new Map(
    installed
      .filter((item) => item.bundle_id)
      .map((item) => [item.bundle_id, item]),
  );
  const knownByBundleId = knownBrowserByBundleId();
  const schemes = {};

  for (const handler of loadLaunchServicesHandlers()) {
    const scheme = handler.LSHandlerURLScheme;
    if (scheme !== "http" && scheme !== "https") continue;

    const bundleId = handler.LSHandlerRoleAll || handler.LSHandlerRoleViewer;
    if (!bundleId) continue;

    const installedMatch = byBundleId.get(bundleId);
    const knownMatch = knownByBundleId.get(bundleId);
    const resolvedMatch =
      installedMatch ||
      (knownMatch ? null : resolveMacosAppByBundleId(bundleId));
    schemes[scheme] = {
      scheme,
      bundle_id: bundleId,
      name:
        installedMatch?.name || knownMatch?.name || resolvedMatch?.name || null,
      path: installedMatch?.path || resolvedMatch?.path || null,
      version: installedMatch?.version || resolvedMatch?.version || null,
    };
  }

  return { source: "LaunchServices", schemes };
}

function findDefaultBrowserLinux() {
  return {
    source: "xdg-settings",
    desktop_file: runCommand(["xdg-settings", "get", "default-web-browser"]),
  };
}

function findDefaultBrowserWindows() {
  const schemes = {};

  for (const scheme of DEFAULT_BROWSER_SCHEMES) {
    const keyPath = `HKCU\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\${scheme}\\UserChoice`;
    const progId = readWindowsRegistryValue(keyPath, "ProgId");
    if (!progId) continue;

    schemes[scheme] = {
      scheme,
      prog_id: progId,
      name:
        knownBrowsers.find((browser) =>
          [browser.browserFamily, ...browser.windowsCommandNames].some(
            (identifier) =>
              progId
                .toLowerCase()
                .includes(identifier.toLowerCase().replace(/\.exe$/, "")),
          ),
        )?.name ?? null,
    };
  }

  return { source: "registry", schemes };
}

function collectInventory() {
  let installed;
  let defaultBrowser;

  if (process.platform === "darwin") {
    installed = findMacosApps();
    defaultBrowser = findDefaultBrowserMacos(installed);
  } else if (process.platform === "linux") {
    installed = findCommandBrowsers();
    defaultBrowser = findDefaultBrowserLinux();
  } else if (process.platform === "win32") {
    installed = findWindowsApps();
    defaultBrowser = findDefaultBrowserWindows();
  } else {
    installed = findCommandBrowsers();
    defaultBrowser = { source: "unsupported", platform: process.platform };
  }

  return {
    platform: process.platform,
    default_browser: defaultBrowser,
    installed_browsers: installed,
  };
}

function printTextReport(inventory, check) {
  if (check) {
    console.log("Browser plugin setup/configuration check");
    console.log("status: ok");
    console.log("");
  }

  console.log("Default browser");
  const defaultBrowser = inventory.default_browser;
  const schemes = defaultBrowser.schemes;
  if (schemes && Object.keys(schemes).length > 0) {
    for (const scheme of ["http", "https"]) {
      const item = schemes[scheme];
      if (!item) {
        console.log(`  ${scheme}: unknown`);
        continue;
      }
      const name = item.name || "unknown app";
      const identifier = item.bundle_id || item.prog_id || "unknown id";
      console.log(`  ${scheme}: ${name} (${identifier})`);
      if (item.path) console.log(`      path: ${item.path}`);
    }
  } else if (defaultBrowser.desktop_file)
    console.log(`  ${defaultBrowser.desktop_file}`);
  else if (defaultBrowser.prog_id) console.log(`  ${defaultBrowser.prog_id}`);
  else console.log(`  unknown (source: ${defaultBrowser.source || "unknown"})`);

  console.log("");
  console.log("Installed known internet browsers");
  if (inventory.installed_browsers.length === 0) {
    console.log("  none found");
    return;
  }

  for (const item of inventory.installed_browsers) {
    console.log(`  - ${item.name}`);
    if (item.bundle_id) console.log(`      bundle id: ${item.bundle_id}`);

    if (item.version) console.log(`      version: ${item.version}`);

    console.log(`      path: ${item.path}`);
  }
}

function parseArgs(argv) {
  const flags = new Set(argv);
  if (flags.has("-h") || flags.has("--help")) {
    console.log("Usage: installed-browsers.js [--check] [--json]");
    process.exit(0);
  }
  return {
    check: flags.has("--check"),
    json: flags.has("--json"),
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const inventory = collectInventory();

  if (args.json) console.log(JSON.stringify(inventory, null, 2));
  else printTextReport(inventory, args.check);

  if (args.check && inventory.installed_browsers.length === 0)
    process.exitCode = 1;
}

void loadNodeModules()
  .then(() => {
    main();
  })
  .catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    (process || globalThis.process)?.exit(2);
  });

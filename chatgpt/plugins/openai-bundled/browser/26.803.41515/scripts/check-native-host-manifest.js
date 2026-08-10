#!/usr/bin/env node
/* global console */

let fs;
let os;
let path;
let process;
let execFileSync;
let expectedExtensionIds;
let expectedHostName;
let expectedBrowsers;
let expectedWindowsNativeMessaging;
let scriptArgs;
let getBrowserDiagnostics;
let parseBrowserFamilyArgs;
let resolveLinuxNativeMessagingManifestPath;

const CHROMIUM_NATIVE_HOST_MANIFEST_PATH_ENV =
  "CODEX_CHROMIUM_NATIVE_HOST_MANIFEST_PATH";
const CHROME_NATIVE_HOST_MANIFEST_PATH_ENV =
  "CODEX_CHROME_NATIVE_HOST_MANIFEST_PATH";
const CHROME_EXTENSION_ID_CONFIG_FILENAME = "extension-ids.json";

function usage() {
  console.error(
    "Usage: scripts/check-native-host-manifest.js [--browser chrome|edge] [--json]",
  );
  console.error("");
  console.error(
    `Expected extension ID is read from scripts/${CHROME_EXTENSION_ID_CONFIG_FILENAME}.`,
  );
  console.error(
    `Optional manifest-file override: ${CHROMIUM_NATIVE_HOST_MANIFEST_PATH_ENV}=/path/to/native-host.json`,
  );
}

function getNativeHostManifestLocation(expectedBrowser) {
  const manifestOverride =
    process.env[CHROMIUM_NATIVE_HOST_MANIFEST_PATH_ENV] ??
    (expectedBrowser.browserFamily === "chrome"
      ? process.env[CHROME_NATIVE_HOST_MANIFEST_PATH_ENV]
      : undefined);
  if (manifestOverride) {
    return {
      manifestPath: path.resolve(manifestOverride),
      registryKey: null,
      registryManifestPath: null,
      registryKeyExists: null,
    };
  }

  if (process.platform === "darwin") {
    return {
      manifestPath: path.join(
        os.homedir(),
        ...expectedBrowser.macos.nativeMessagingManifestDirectories[0].split(
          "/",
        ),
        `${expectedHostName}.json`,
      ),
      registryKey: null,
      registryManifestPath: null,
      registryKeyExists: null,
    };
  }

  if (process.platform === "win32") {
    const registryKey = `${expectedWindowsNativeMessaging.registryRoot}\\${expectedHostName}`;
    const registryManifestPath = readWindowsRegistryDefaultValue(registryKey);

    return {
      manifestPath: registryManifestPath || getDefaultWindowsManifestPath(),
      registryKey,
      registryManifestPath,
      registryKeyExists: registryManifestPath != null,
    };
  }

  if (process.platform === "linux") {
    return {
      manifestPath: resolveLinuxNativeMessagingManifestPath({
        browser: expectedBrowser,
        env: process.env,
        homedir: os.homedir(),
        hostName: expectedHostName,
        path,
      }),
      registryKey: null,
      registryManifestPath: null,
      registryKeyExists: null,
    };
  }

  throw new Error(
    `Unsupported platform for native host manifest check: ${process.platform}.`,
  );
}

function getDefaultWindowsManifestPath() {
  return path.join(
    os.homedir(),
    ...expectedWindowsNativeMessaging.manifestDirectory.split("/"),
    `${expectedHostName}.json`,
  );
}

function readWindowsRegistryDefaultValue(registryKey) {
  let output;
  try {
    output = execFileSync("reg", ["query", registryKey, "/ve"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
  } catch {
    return null;
  }

  return readRegistryValue(output, "(Default)");
}

function readRegistryValue(output, valueName) {
  for (const line of output.split(/\r?\n/)) {
    const match = line.match(/^\s*(.*?)\s+REG_\w+\s+(.+?)\s*$/);
    if (match && match[1] === valueName) return stripRegistryString(match[2]);
  }

  return null;
}

function stripRegistryString(value) {
  return value.replace(/^"(.*)"$/, "$1");
}

function getNativeHostManifestLocationProblem(location, manifestExists) {
  const problems = [];

  if (location.registryKeyExists === false) {
    problems.push(
      `Windows native host registry key does not exist: ${location.registryKey}`,
    );
  }

  if (!manifestExists) {
    problems.push(
      `Native host manifest does not exist: ${location.manifestPath}`,
    );
  }

  return problems.length > 0 ? problems.join("; ") : null;
}

function readNativeHostManifest(filePath) {
  try {
    return readJsonFile(filePath);
  } catch (error) {
    throw new Error(
      `Could not read native host manifest ${filePath}: ${
        error instanceof Error ? error.message : String(error)
      }`,
      { cause: error },
    );
  }
}

function resolveSiblingScriptPath(filename) {
  const scriptPath = path.resolve(process.argv[1] || ".");
  return path.join(path.dirname(scriptPath), filename);
}

function loadExpectedChromeExtensionConfig() {
  const configPath = resolveSiblingScriptPath(
    CHROME_EXTENSION_ID_CONFIG_FILENAME,
  );
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  return config;
}

function loadExpectedHostName() {
  const config = loadExpectedChromeExtensionConfig();
  const scriptPath = resolveSiblingScriptPath("installManifest.mjs");
  if (!fs.existsSync(scriptPath)) {
    if (typeof config.extensionHostName === "string")
      return config.extensionHostName;

    throw new Error(`Could not find installManifest.mjs at ${scriptPath}.`);
  }

  const scriptSource = fs.readFileSync(scriptPath, "utf8");
  const match = scriptSource.match(/extensionHostName:"([^"]+)"/);
  if (!match || !match[1])
    throw new Error(`Could not read extensionHostName from ${scriptPath}.`);

  return match[1];
}

function readJsonFile(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function getNativeHostManifestStatus(expectedBrowser) {
  const location = getNativeHostManifestLocation(expectedBrowser);
  const expectedOrigins = expectedExtensionIds.map(
    (extensionId) => `chrome-extension://${extensionId}/`,
  );
  const exists = fs.existsSync(location.manifestPath);
  const locationProblem = getNativeHostManifestLocationProblem(
    location,
    exists,
  );

  if (locationProblem) {
    return {
      browserFamily: expectedBrowser.browserFamily,
      browserName: expectedBrowser.displayName,
      manifestPath: location.manifestPath,
      registryKey: location.registryKey,
      registryManifestPath: location.registryManifestPath,
      expectedHostName,
      expectedExtensionIds,
      expectedOrigins,
      exists,
      correct: false,
      problem: locationProblem,
    };
  }

  const manifest = readNativeHostManifest(location.manifestPath);
  const allowedOrigins = Array.isArray(manifest.allowed_origins)
    ? manifest.allowed_origins
    : [];
  const nameMatches = manifest.name === expectedHostName;
  const missingExpectedOrigins = expectedOrigins.filter(
    (origin) => !allowedOrigins.includes(origin),
  );
  const registryMatchesManifestPath =
    location.registryManifestPath == null ||
    path.resolve(location.registryManifestPath) ===
      path.resolve(location.manifestPath);
  const correct =
    nameMatches &&
    missingExpectedOrigins.length === 0 &&
    registryMatchesManifestPath;

  return {
    browserFamily: expectedBrowser.browserFamily,
    browserName: expectedBrowser.displayName,
    manifestPath: location.manifestPath,
    registryKey: location.registryKey,
    registryManifestPath: location.registryManifestPath,
    expectedHostName,
    actualHostName: manifest.name,
    expectedExtensionIds,
    expectedOrigins,
    allowedOrigins,
    exists,
    nameMatches,
    missingExpectedOrigins,
    registryMatchesManifestPath,
    correct,
    problem: correct
      ? null
      : describeManifestProblem({
          nameMatches,
          missingExpectedOrigins,
          registryMatchesManifestPath,
        }),
  };
}

function describeManifestProblem({
  nameMatches,
  missingExpectedOrigins,
  registryMatchesManifestPath,
}) {
  const problems = [];
  if (!nameMatches)
    problems.push(`manifest name does not match ${expectedHostName}`);
  if (missingExpectedOrigins.length > 0) {
    problems.push(
      `allowed_origins does not include ${missingExpectedOrigins.join(", ")}`,
    );
  }
  if (!registryMatchesManifestPath) {
    problems.push(
      "registry manifest path does not match checked manifest path",
    );
  }

  return problems.join("; ");
}

function main() {
  const args = scriptArgs;
  if (args.includes("-h") || args.includes("--help")) {
    usage();
    process.exit(0);
  }

  const json = args.includes("--json");
  const positionalArgs = args.filter((arg) => arg !== "--json");
  if (positionalArgs.length > 0) {
    usage();
    process.exit(2);
  }

  const browserResults = expectedBrowsers.map(getNativeHostManifestStatus);
  const result =
    browserResults.length === 1
      ? browserResults[0]
      : {
          correct: browserResults.every(({ correct }) => correct),
          browsers: browserResults,
        };
  if (json) console.log(JSON.stringify(result, null, 2));
  else {
    for (const browserResult of browserResults) {
      console.log(`Browser: ${browserResult.browserName}`);
      console.log(`Native host manifest: ${browserResult.manifestPath}`);
      if (browserResult.registryKey)
        console.log(`Windows registry key: ${browserResult.registryKey}`);
      if (browserResult.registryManifestPath) {
        console.log(
          `Windows registry manifest path: ${browserResult.registryManifestPath}`,
        );
      }
      console.log(`Expected host name: ${browserResult.expectedHostName}`);
      if (browserResult.actualHostName)
        console.log(`Actual host name: ${browserResult.actualHostName}`);
      console.log(
        `Expected extension IDs: ${browserResult.expectedExtensionIds.join(", ")}`,
      );
      console.log(
        `Expected allowed origins: ${browserResult.expectedOrigins.join(", ")}`,
      );
      if (browserResult.allowedOrigins) {
        console.log(
          `Allowed origins: ${browserResult.allowedOrigins.join(", ")}`,
        );
      }
      console.log(`Correct: ${browserResult.correct ? "yes" : "no"}`);
      if (browserResult.problem)
        console.log(`Problem: ${browserResult.problem}`);
    }
  }

  process.exit(result.correct ? 0 : 1);
}

try {
  Promise.all([
    import("node:fs"),
    import("node:os"),
    import("node:path"),
    import("node:process"),
    import("node:child_process"),
  ])
    .then(
      ([fsModule, osModule, pathModule, processModule, childProcessModule]) => {
        fs = fsModule;
        os = osModule;
        path = pathModule;
        process = processModule.default;
        ({ execFileSync } = childProcessModule);
        return import("./chromium-browser-diagnostics.mjs");
      },
    )
    .then((diagnosticsModule) => {
      ({
        getBrowserDiagnostics,
        parseBrowserFamilyArgs,
        resolveLinuxNativeMessagingManifestPath,
      } = diagnosticsModule);
      const parsedArgs = parseBrowserFamilyArgs(process.argv.slice(2));
      scriptArgs = parsedArgs.args;
      const config = loadExpectedChromeExtensionConfig();
      expectedBrowsers = process.argv
        .slice(2)
        .some((arg) => arg === "--browser" || arg.startsWith("--browser="))
        ? [getBrowserDiagnostics(config, parsedArgs.browserFamily)]
        : config.browserDiagnostics;
      expectedWindowsNativeMessaging = config.windowsNativeMessaging;
      expectedExtensionIds = config.extensionIds;
      if (expectedExtensionIds.length === 0) {
        throw new Error(
          "Native host diagnostics are unavailable until a runtime identity is configured.",
        );
      }
      expectedHostName = loadExpectedHostName();
      main();
    })
    .catch((error) => {
      console.error(error instanceof Error ? error.message : String(error));
      process.exit(2);
    });
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(2);
}

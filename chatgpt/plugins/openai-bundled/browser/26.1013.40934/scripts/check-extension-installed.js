#!/usr/bin/env node
/* global console */

let fs;
let os;
let path;
let process;
let getBrowserDiagnostics;
let parseBrowserFamilyArgs;
let resolveBrowserUserDataDirectory;

const CHROMIUM_PREFERENCES_PATH_ENV = "CODEX_CHROMIUM_PREFERENCES_PATH";
const CHROME_PREFERENCES_PATH_ENV = "CODEX_CHROME_PREFERENCES_PATH";
const CHROME_EXTENSION_ID_CONFIG_FILENAME = "extension-ids.json";
const EXIT_INSTALLED_AND_ENABLED = 0;
const EXIT_INSTALLED_NOT_ENABLED = 1;
const EXIT_NOT_INSTALLED = 2;
const EXIT_RUNTIME_ERROR = 3;

async function loadNodeModules() {
  fs = await import("node:fs");
  os = await import("node:os");
  path = await import("node:path");
  process = (await import("node:process")).default;
  ({
    getBrowserDiagnostics,
    parseBrowserFamilyArgs,
    resolveBrowserUserDataDirectory,
  } = await import("./chromium-browser-diagnostics.mjs"));
}

function usage() {
  console.error(
    "Usage: scripts/check-extension-installed.js [--browser chrome|edge] [--json]",
  );
  console.error("");
  console.error(
    `Browser extension IDs are configured in scripts/${CHROME_EXTENSION_ID_CONFIG_FILENAME}.`,
  );
  console.error(
    "Optional profile-root override: CODEX_CHROMIUM_USER_DATA_DIR=/path/to/browser-root",
  );
  console.error(
    `Optional preferences-file override: ${CHROMIUM_PREFERENCES_PATH_ENV}=/path/to/Profile/Preferences`,
  );
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

function getChromePreferencesPathOverride(browser) {
  const preferencesPath =
    process.env[CHROMIUM_PREFERENCES_PATH_ENV] ??
    (browser.browserFamily === "chrome"
      ? process.env[CHROME_PREFERENCES_PATH_ENV]
      : undefined);
  return preferencesPath ? path.resolve(preferencesPath) : null;
}

function loadDiagnosticsConfig() {
  const configPath = resolveSiblingScriptPath(
    CHROME_EXTENSION_ID_CONFIG_FILENAME,
  );
  return JSON.parse(fs.readFileSync(configPath, "utf8"));
}

function resolveSiblingScriptPath(filename) {
  const scriptPath = path.resolve(process.argv[1] || ".");
  return path.join(path.dirname(scriptPath), filename);
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

function listChromeProfileDirectories(userDataDirectory) {
  if (!fs.existsSync(userDataDirectory)) {
    throw new Error(
      `Browser user data directory does not exist: ${userDataDirectory}`,
    );
  }

  return fs
    .readdirSync(userDataDirectory, { withFileTypes: true })
    .filter((entry) => {
      return (
        entry.isDirectory() &&
        (entry.name === "Default" || /^Profile \d+$/.test(entry.name)) &&
        isUsableChromeProfile(userDataDirectory, entry.name)
      );
    })
    .map((entry) => entry.name)
    .sort(compareChromeProfileDirectories);
}

function getChromeExtensionInstallStatusForProfile(
  userDataDirectory,
  profileDirectory,
  extensionId,
  profilePathOverride,
) {
  const profilePath =
    profilePathOverride ?? path.join(userDataDirectory, profileDirectory);
  const preferences = getChromeExtensionPreferences(profilePath, extensionId);
  const extensionsDirectory = path.join(profilePath, "Extensions");
  const extensionPath = path.join(extensionsDirectory, extensionId);
  const versions =
    fs.existsSync(extensionPath) && fs.statSync(extensionPath).isDirectory()
      ? fs
          .readdirSync(extensionPath, { withFileTypes: true })
          .filter((entry) => entry.isDirectory())
          .map((entry) => entry.name)
          .sort()
      : [];
  const unpackedInstalled =
    preferences.path !== null &&
    fs.existsSync(preferences.path) &&
    fs.statSync(preferences.path).isDirectory();
  const installed = versions.length > 0 || unpackedInstalled;
  const disabled =
    preferences.state === 0 || preferences.disableReasons.length > 0;
  const enabled = installed && preferences.registered && !disabled;

  return {
    extensionId,
    profileDirectory,
    profilePath,
    preferencesPath: preferences.preferencesPath,
    extensionsDirectory,
    extensionPath,
    installed,
    registered: preferences.registered,
    enabled,
    disabled,
    state: preferences.state,
    disableReasons: preferences.disableReasons,
    versions,
  };
}

function getChromeExtensionInstallStatus(browserFamily) {
  const browser = getBrowserDiagnostics(loadDiagnosticsConfig(), browserFamily);
  const extensionIds = browser.extensionIds;
  if (!Array.isArray(extensionIds) || extensionIds.length === 0) {
    throw new Error(
      `${browser.displayName} extension diagnostics are unavailable until its store listing is published.`,
    );
  }
  const preferencesPathOverride = getChromePreferencesPathOverride(browser);
  const userDataDirectory =
    preferencesPathOverride == null
      ? resolveChromeUserDataDirectory(browser)
      : path.dirname(path.dirname(preferencesPathOverride));
  const selectedProfilePath =
    preferencesPathOverride == null
      ? null
      : path.dirname(preferencesPathOverride);
  const selectedProfileDirectory =
    preferencesPathOverride == null
      ? resolveChromeProfileDirectory(userDataDirectory)
      : path.basename(selectedProfilePath);
  const profileDirectories =
    preferencesPathOverride == null
      ? listChromeProfileDirectories(userDataDirectory)
      : [selectedProfileDirectory];
  if (profileDirectories.length === 0) {
    throw new Error(
      `Could not find a browser profile directory with Preferences in ${userDataDirectory}.`,
    );
  }

  const profiles = profileDirectories.map((profileDirectory) => {
    const profileStatuses = extensionIds.map((extensionId) =>
      getChromeExtensionInstallStatusForProfile(
        userDataDirectory,
        profileDirectory,
        extensionId,
        profileDirectory === selectedProfileDirectory
          ? selectedProfilePath
          : undefined,
      ),
    );
    const profileStatus =
      profileStatuses.find((status) => status.enabled) ??
      profileStatuses.find((status) => status.installed) ??
      profileStatuses[0];
    return {
      ...profileStatus,
      selected: profileDirectory === selectedProfileDirectory,
    };
  });
  const selectedProfile =
    profiles.find((profile) => profile.selected) ?? profiles[0];
  const installed = selectedProfile.installed;
  const enabled = selectedProfile.enabled;

  return {
    browserFamily,
    browserName: browser.displayName,
    extensionId: selectedProfile.extensionId,
    userDataDirectory,
    selectedProfileDirectory,
    installed,
    enabled,
    profiles,
    exitCode: getExitCode({ enabled, installed }),
  };
}

function getChromeExtensionPreferences(profilePath, extensionId) {
  const preferencesPaths = [
    path.join(profilePath, "Secure Preferences"),
    path.join(profilePath, "Preferences"),
  ];
  for (const preferencesPath of preferencesPaths) {
    const preferences = readJsonFileIfPresent(preferencesPath);
    const extensionSettings = preferences?.extensions?.settings?.[extensionId];
    if (!extensionSettings || typeof extensionSettings !== "object") continue;

    return {
      preferencesPath,
      registered: true,
      state:
        typeof extensionSettings.state === "number"
          ? extensionSettings.state
          : null,
      path:
        typeof extensionSettings.path === "string"
          ? extensionSettings.path
          : null,
      disableReasons: getDisableReasons(extensionSettings.disable_reasons),
    };
  }

  return {
    preferencesPath: null,
    registered: false,
    state: null,
    path: null,
    disableReasons: [],
  };
}

function getDisableReasons(disableReasons) {
  if (Array.isArray(disableReasons)) return disableReasons;
  if (typeof disableReasons === "number" && disableReasons !== 0)
    return [disableReasons];
  return [];
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

function getExitCode({ enabled, installed }) {
  if (enabled) return EXIT_INSTALLED_AND_ENABLED;
  if (installed) return EXIT_INSTALLED_NOT_ENABLED;
  return EXIT_NOT_INSTALLED;
}

function main() {
  const { browserFamily, args } = parseBrowserFamilyArgs(process.argv.slice(2));
  if (args.includes("-h") || args.includes("--help")) {
    usage();
    process.exit(0);
  }

  const json = args.includes("--json");
  const positionalArgs = args.filter((arg) => arg !== "--json");
  if (positionalArgs.length > 0) {
    usage();
    process.exit(EXIT_RUNTIME_ERROR);
  }

  const result = getChromeExtensionInstallStatus(browserFamily);
  if (json) console.log(JSON.stringify(result, null, 2));
  else {
    console.log(
      `Checked ${result.browserName} user data directory: ${result.userDataDirectory}`,
    );
    console.log(`Extension ID: ${result.extensionId}`);
    console.log(
      `Selected ${result.browserName} profile: ${result.selectedProfileDirectory ?? "none"}`,
    );
    console.log(`Installed in any profile: ${result.installed ? "yes" : "no"}`);
    console.log(`Enabled in any profile: ${result.enabled ? "yes" : "no"}`);
    for (const profile of result.profiles) {
      console.log("");
      console.log(
        `Profile: ${profile.profileDirectory}${profile.selected ? " (selected)" : ""}`,
      );
      console.log(`  Path: ${profile.profilePath}`);
      console.log(`  Extension path: ${profile.extensionPath}`);
      console.log(`  Installed: ${profile.installed ? "yes" : "no"}`);
      console.log(
        `  Registered in ${result.browserName} preferences: ${profile.registered ? "yes" : "no"}`,
      );
      console.log(`  Enabled: ${profile.enabled ? "yes" : "no"}`);
      if (profile.disabled)
        console.log(`  Disable reasons: ${profile.disableReasons.join(", ")}`);
      if (profile.versions.length > 0)
        console.log(`  Installed versions: ${profile.versions.join(", ")}`);
    }
  }

  process.exit(result.exitCode);
}

void loadNodeModules()
  .then(() => {
    main();
  })
  .catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    (process || globalThis.process)?.exit(EXIT_RUNTIME_ERROR);
  });

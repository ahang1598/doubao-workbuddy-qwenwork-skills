const DEFAULT_BROWSER_FAMILY = "chrome";

export function getBrowserDiagnostics(config, browserFamily) {
  const browser = config?.browserDiagnostics?.find(
    (candidate) => candidate.browserFamily === browserFamily,
  );
  if (browser == null) {
    throw new Error(
      `No generated diagnostics are available for browser family ${browserFamily}.`,
    );
  }
  return browser;
}

export function parseBrowserFamilyArgs(argv) {
  const args = [];
  let browserFamily = DEFAULT_BROWSER_FAMILY;

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--browser") {
      const value = argv[index + 1];
      if (value == null || value.startsWith("--"))
        throw new Error("Expected a browser family after --browser.");
      browserFamily = value;
      index += 1;
      continue;
    }
    if (arg.startsWith("--browser=")) {
      browserFamily = arg.slice("--browser=".length);
      continue;
    }
    args.push(arg);
  }

  return { browserFamily, args };
}

export function resolveBrowserUserDataDirectory({
  browser,
  env,
  homedir,
  path,
  platform,
}) {
  const override =
    env.CODEX_CHROMIUM_USER_DATA_DIR ??
    (browser.browserFamily === "chrome"
      ? env.CODEX_CHROME_USER_DATA_DIR
      : undefined);
  if (override) return path.resolve(override);

  if (platform === "darwin")
    return path.join(homedir, ...browser.macos.userDataDirectorySegments);

  if (platform === "win32") {
    const localAppData =
      env.LOCALAPPDATA ?? path.join(homedir, "AppData", "Local");
    return path.join(
      localAppData,
      ...browser.windows.userDataDirectorySegments,
    );
  }

  const segments = browser.linux.userDataDirectorySegments;
  if (segments[0] === ".config") {
    return path.join(
      getLinuxChromiumConfigHome({ browser, env, homedir, path }),
      ...segments.slice(1),
    );
  }
  return path.join(homedir, ...segments);
}

export function resolveLinuxNativeMessagingManifestPath({
  browser,
  env,
  homedir,
  hostName,
  path,
}) {
  const segments =
    browser.linux.nativeMessagingManifestDirectories[0].split("/");
  return path.join(
    getLinuxChromiumConfigHome({ browser, env, homedir, path }),
    ...(segments[0] === ".config" ? segments.slice(1) : segments),
    `${hostName}.json`,
  );
}

function getLinuxChromiumConfigHome({ browser, env, homedir, path }) {
  return (
    browser.linux.configHomeEnvironmentVariables
      .map((name) => env[name])
      .find((value) => value != null && value.length > 0) ??
    path.join(homedir, ".config")
  );
}

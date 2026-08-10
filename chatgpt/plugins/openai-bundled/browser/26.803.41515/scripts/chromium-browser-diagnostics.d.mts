import type { ChromiumBrowserDiagnostics } from "browser-common";

export function getBrowserDiagnostics(
  config: { browserDiagnostics?: ChromiumBrowserDiagnostics[] },
  browserFamily: string,
): ChromiumBrowserDiagnostics;

export function parseBrowserFamilyArgs(argv: string[]): {
  browserFamily: string;
  args: string[];
};

export function resolveBrowserUserDataDirectory(options: {
  browser: ChromiumBrowserDiagnostics;
  env: NodeJS.ProcessEnv;
  homedir: string;
  path: typeof import("node:path");
  platform: NodeJS.Platform;
}): string;

export function resolveLinuxNativeMessagingManifestPath(options: {
  browser: ChromiumBrowserDiagnostics;
  env: NodeJS.ProcessEnv;
  homedir: string;
  hostName: string;
  path: typeof import("node:path");
}): string;

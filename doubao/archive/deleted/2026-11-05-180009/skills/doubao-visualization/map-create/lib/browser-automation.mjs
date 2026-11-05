import { access } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import { delimiter, dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const playwrightPackages = [
  'playwright',
  '@playwright/test',
  'playwright-core',
];

const uniqueBy = (values, key) => {
  const seen = new Set();
  return values.filter(value => {
    const identity = key(value);
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
};

const canAccess = async file => {
  if (!file) return false;
  try {
    await access(file);
    return true;
  } catch {
    return false;
  }
};

const requireFrom = base => createRequire(join(resolve(base), 'package.json'));

const loadEntry = async entry => {
  const module = await import(pathToFileURL(entry).href);
  const chromium = module.chromium || module.default?.chromium;
  if (!chromium) throw new Error(`Playwright 模块 ${entry} 没有导出 chromium`);
  return chromium;
};

function defaultModuleBases({ cwd, environment, home, executable }) {
  const nodePathBases = (environment.NODE_PATH || '')
    .split(delimiter)
    .filter(Boolean)
    .map(path => ({ source: 'node-path', base: dirname(resolve(path)) }));
  return uniqueBy(
    [
      { source: 'project', base: cwd },
      ...nodePathBases,
      {
        source: 'node-runtime',
        base: resolve(dirname(executable), '..'),
      },
      {
        source: 'codex-runtime',
        base: resolve(
          home,
          '.cache/codex-runtimes/codex-primary-runtime/dependencies/node',
        ),
      },
    ],
    item => resolve(item.base),
  );
}

export async function loadPlaywright(options = {}) {
  const cwd = resolve(options.cwd || process.cwd());
  const environment = options.environment || process.env;
  const explicit = environment.MAP_CREATE_PLAYWRIGHT_MODULE;
  if (explicit) {
    try {
      const entry = requireFrom(cwd).resolve(explicit);
      return {
        chromium: await loadEntry(entry),
        module: { source: 'environment', package: explicit },
      };
    } catch (error) {
      throw new Error(
        `MAP_CREATE_PLAYWRIGHT_MODULE 无法加载：${error.message}`,
      );
    }
  }

  const bases =
    options.moduleBases ||
    defaultModuleBases({
      cwd,
      environment,
      home: options.home || homedir(),
      executable: options.executable || process.execPath,
    });
  const failures = [];
  for (const { source, base } of bases) {
    const require = requireFrom(base);
    for (const name of playwrightPackages) {
      let entry;
      try {
        entry = require.resolve(name);
      } catch {
        continue;
      }
      try {
        return {
          chromium: await loadEntry(entry),
          module: { source, package: name },
        };
      } catch (error) {
        failures.push(`${source}:${name}: ${error.message}`);
      }
    }
  }

  throw new Error(
    [
      '未找到可用的 Playwright 自动化模块。',
      '宿主可设置 MAP_CREATE_PLAYWRIGHT_MODULE，或通过项目依赖/NODE_PATH 提供 playwright、@playwright/test 或 playwright-core。',
      '不要在发现失败前默认安装浏览器。',
      ...(failures.length ? [`已发现但加载失败：${failures.join('；')}`] : []),
    ].join(' '),
  );
}

function defaultSystemBrowsers(platform, environment) {
  if (platform === 'darwin')
    return [
      {
        name: 'Google Chrome',
        executablePath:
          '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      },
      {
        name: 'Google Chrome for Testing',
        executablePath:
          '/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
      },
      {
        name: 'Chromium',
        executablePath: '/Applications/Chromium.app/Contents/MacOS/Chromium',
      },
      {
        name: 'Microsoft Edge',
        executablePath:
          '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
      },
    ];
  if (platform === 'win32') {
    const roots = [
      environment.LOCALAPPDATA,
      environment.PROGRAMFILES,
      environment['PROGRAMFILES(X86)'],
    ].filter(Boolean);
    return roots.flatMap(root => [
      {
        name: 'Google Chrome',
        executablePath: join(root, 'Google/Chrome/Application/chrome.exe'),
      },
      {
        name: 'Microsoft Edge',
        executablePath: join(root, 'Microsoft/Edge/Application/msedge.exe'),
      },
    ]);
  }
  return [
    { name: 'Google Chrome', executablePath: '/usr/bin/google-chrome' },
    {
      name: 'Google Chrome',
      executablePath: '/usr/bin/google-chrome-stable',
    },
    { name: 'Chromium', executablePath: '/usr/bin/chromium' },
    { name: 'Chromium', executablePath: '/usr/bin/chromium-browser' },
    { name: 'Microsoft Edge', executablePath: '/usr/bin/microsoft-edge' },
  ];
}

function pathBrowsers(environment, platform) {
  const names =
    platform === 'win32'
      ? ['chrome.exe', 'chromium.exe', 'msedge.exe']
      : [
          'chromium',
          'chromium-browser',
          'google-chrome',
          'google-chrome-stable',
        ];
  return (environment.PATH || '')
    .split(delimiter)
    .filter(Boolean)
    .flatMap(base =>
      names.map(name => ({ name, executablePath: resolve(base, name) })),
    );
}

export async function resolveBrowserLaunch(chromium, options = {}) {
  const environment = options.environment || process.env;
  const explicitExecutable = environment.MAP_CREATE_BROWSER_EXECUTABLE;
  if (explicitExecutable) {
    const executablePath = resolve(explicitExecutable);
    if (!(await canAccess(executablePath)))
      throw new Error(
        `MAP_CREATE_BROWSER_EXECUTABLE 指向的文件不存在：${executablePath}`,
      );
    return {
      launchOptions: { executablePath },
      browser: { source: 'environment', name: 'custom-executable' },
    };
  }

  const explicitChannel = environment.MAP_CREATE_BROWSER_CHANNEL;
  if (explicitChannel)
    return {
      launchOptions: { channel: explicitChannel },
      browser: { source: 'environment', name: explicitChannel },
    };

  const platform = options.platform || process.platform;
  const systemBrowsers = options.systemBrowsers || [
    ...defaultSystemBrowsers(platform, environment),
    ...pathBrowsers(environment, platform),
  ];
  const excluded = new Set(options.excludedExecutables || []);
  for (const candidate of systemBrowsers)
    if (
      !excluded.has(candidate.executablePath) &&
      (await canAccess(candidate.executablePath))
    )
      return {
        launchOptions: { executablePath: candidate.executablePath },
        browser: { source: 'system', name: candidate.name },
      };

  const bundledExecutable = chromium.executablePath?.();
  if (!excluded.has(bundledExecutable) && (await canAccess(bundledExecutable)))
    return {
      launchOptions: { executablePath: bundledExecutable },
      browser: { source: 'playwright', name: 'bundled-chromium' },
    };

  throw new Error(
    '已找到 Playwright，但没有可复用的系统浏览器或已缓存 Chromium。宿主可设置 MAP_CREATE_BROWSER_EXECUTABLE / MAP_CREATE_BROWSER_CHANNEL；确认两者都不可用后再安装浏览器。',
  );
}

export async function resolveBrowserAutomation(options = {}) {
  const playwright = await loadPlaywright(options);
  const browser = await resolveBrowserLaunch(playwright.chromium, options);
  return { ...playwright, ...browser };
}

export async function launchBrowserAutomation(
  automation,
  launchOptions = {},
  options = {},
) {
  const excludedExecutables = [];
  const failures = [];
  let candidate = automation;
  while (true) {
    try {
      const browser = await automation.chromium.launch({
        ...candidate.launchOptions,
        ...launchOptions,
        args: [
          ...(candidate.launchOptions?.args || []),
          ...(launchOptions.args || []),
        ],
      });
      automation.browser = candidate.browser;
      automation.launchOptions = candidate.launchOptions;
      return browser;
    } catch (error) {
      failures.push(`${candidate.browser.name}: ${error.message}`);
      if (candidate.browser.source === 'environment')
        throw new Error(`显式配置的浏览器启动失败：${failures.join('；')}`);
      excludedExecutables.push(candidate.launchOptions.executablePath);
      try {
        candidate = await resolveBrowserLaunch(automation.chromium, {
          ...options,
          excludedExecutables,
        });
      } catch (resolutionError) {
        throw new Error(
          `没有可启动的浏览器。${resolutionError.message} 启动失败：${failures.join('；')}`,
        );
      }
    }
  }
}

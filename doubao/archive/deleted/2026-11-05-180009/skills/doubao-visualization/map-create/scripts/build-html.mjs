import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  digest,
  integrity,
  readAsset,
  uploadAsset,
} from '../lib/cdn-assets.mjs';
import {
  args,
  readJson,
  safeError,
  writeJson,
  writeText,
} from '../lib/cli-utils.mjs';
import {
  checkRuntimeCompatibility,
  failOnErrors,
  loadComponentCatalog,
  prepareGraph,
  validateContract,
  verifyContractArtifacts,
} from '../lib/engine.mjs';
import { loadAMapRuntimeConfig } from '../lib/load-amap-runtime-config.mjs';
import { resolveContentMapKitAsset } from '../lib/load-content-map-kit-asset.mjs';
import { embedLocalPreview } from '../lib/local-preview.mjs';
import { validateBuildCompatibility } from '../lib/validate-build-compatibility.mjs';
import { deriveSource } from '../runtime/derive-source.mjs';
import { classifyFitGeometry } from '../runtime/fit-evidence.mjs';
import { resolveInitialCamera } from '../runtime/initial-camera.mjs';
import { classifyViewportEntries } from '../runtime/edge-navigation.mjs';
import { applyCompiledAppearance } from '../runtime/theme.mjs';
import { createSelectionController } from '../runtime/selection-controller.mjs';
import { installMapTelemetry } from '../runtime/telemetry.mjs';
import { sanitizeTelemetryError } from '../lib/telemetry-error.mjs';
import { readTelemetryTask } from '../lib/task-telemetry.mjs';
import { dependencyReporter } from '../lib/dependency-telemetry.mjs';
import { readSlardarSdk } from '../lib/slardar-sdk.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const options = args();
const startedAt = performance.now();

const htmlEscape = value =>
  String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

const scriptJson = value =>
  JSON.stringify(value)
    .replaceAll('<', '\\u003c')
    .replaceAll('\u2028', '\\u2028')
    .replaceAll('\u2029', '\\u2029');

function sourceHtml(sources) {
  if (!sources.length) return '来源：用户输入与地图配置';
  const parts = sources.map(source => {
    const label = htmlEscape(source.title || source.id);
    if (!source.url) return label;
    const url = new URL(source.url);
    if (!['http:', 'https:'].includes(url.protocol)) return label;
    return `<a href="${htmlEscape(url.href)}" target="_blank" rel="noreferrer">${label}</a>`;
  });
  return `来源：${parts.join(' · ')}`;
}

try {
  if (options.standalone && options.publish)
    throw new Error('本地独立预览不能作为 CDN 拆分发布');
  const height = options.height === undefined ? 720 : Number(options.height);
  if (!Number.isFinite(height) || height < 320 || height > 4096)
    throw new Error('HTML height 必须为 320–4096 CSS px');
  const heightMode =
    options['height-mode'] || (options.height === undefined ? 'auto' : 'fixed');
  if (!['auto', 'fixed', 'viewport'].includes(heightMode))
    throw new Error('HTML height-mode 必须为 auto、fixed 或 viewport');
  if (!options.graph || !options.out)
    throw new Error(
      '用法：node build-html.mjs --graph render-graph.json --out map.html [--config amap-config.json]',
    );
  const [graph, template, css, runtime, lock, catalog] = await Promise.all([
    readJson(options.graph),
    readFile(resolve(root, 'runtime/map.html.template'), 'utf8'),
    readFile(resolve(root, 'runtime/viewer.css'), 'utf8'),
    readFile(resolve(root, 'runtime/browser-runtime.js'), 'utf8'),
    readJson(resolve(root, 'vendor.lock.json')),
    loadComponentCatalog(options.catalog),
  ]);
  verifyContractArtifacts();
  failOnErrors(validateContract('renderGraph', graph, 'build'));
  prepareGraph(graph);
  const config = await loadAMapRuntimeConfig({ root, config: options.config });
  const contentMapKitAsset = resolveContentMapKitAsset(lock, {
    url: options['components-url'],
    sha256: options['components-sha256'],
  });
  const compatibility = validateBuildCompatibility(
    graph,
    catalog,
    lock,
    contentMapKitAsset.source,
  );

  const outputDir = dirname(resolve(options.out));
  await mkdir(outputDir, { recursive: true });
  const manifest = {
    version: 1,
    runtimeRelease: 'map-create-4',
    assets: {
      components: {
        url: contentMapKitAsset.url,
        sha256: contentMapKitAsset.sha256,
      },
    },
  };
  const sources = {
    data: ['json', JSON.stringify(graph)],
    style: ['css', css],
    runtime: [
      'js',
      `window.mapCreateInitialCamera = ${resolveInitialCamera.toString()};\nwindow.mapCreateApplyAppearance = ${applyCompiledAppearance.toString()};\nwindow.mapCreateViewportEntries = ${classifyViewportEntries.toString()};\nwindow.mapCreateClassifyFit = ${classifyFitGeometry.toString()};\nwindow.mapCreateSelectionController = ${createSelectionController.toString()};\nwindow.mapCreateCheckCompatibility = ${checkRuntimeCompatibility.toString()};\nwindow.mapCreatePrepareGraph = ${prepareGraph.toString()};\nwindow.mapCreateDeriveSource = ${deriveSource.toString()};\n${runtime}`,
    ],
    bootstrap: [
      'js',
      await readFile(resolve(root, 'runtime/bootstrap.js'), 'utf8'),
    ],
  };
  const previous = options.report
    ? await readJson(options.report).catch(error => {
        if (error.code === 'ENOENT') return null;
        throw error;
      })
    : null;
  let telemetry;
  if (options['telemetry-task']) {
    try {
      const task = await readTelemetryTask(options['telemetry-task']);
      const { files, lock: sdkLock } = readSlardarSdk();
      telemetry = {
        trace_id: task.trace_id,
        map_id: task.map_id,
        env: task.env,
        skill_version: task.skill_version,
        runtime_version: digest(sources.runtime[1]),
        component_version: contentMapKitAsset.sha256,
        artifact_id: digest(
          JSON.stringify({
            trace: task.trace_id,
            graph,
            sources,
            components: contentMapKitAsset.sha256,
            sdk: sdkLock.sha256,
            telemetry: installMapTelemetry.toString(),
            telemetryError: sanitizeTelemetryError.toString(),
            template,
            height,
            heightMode,
          }),
        ),
        disabled: Boolean(options.standalone),
      };
      sources.telemetry = [
        'js',
        `(function(){const exports={};\n${files['web.cjs']}\nwindow.mapCreateTelemetry?.connect(exports.createBrowserClient);})();`,
      ];
    } catch {
      process.stderr.write('MAP_TELEMETRY_UNAVAILABLE\n');
    }
  }
  const publication = await Promise.all(
    Object.entries(sources).map(async ([key, [extension, text]]) => {
      try {
        const bytes = Buffer.from(text);
        const sha256 = digest(bytes);
        const filename = `${key}.${sha256}.${extension}`;
        await writeFile(resolve(outputDir, filename), bytes);
        const cached = previous?.manifest?.assets?.[key];
        if (
          options.publish &&
          cached?.sha256 === sha256 &&
          /^https:\/\//.test(cached.url)
        ) {
          await readAsset(cached, undefined, extension);
          return [key, cached];
        }
        return [
          key,
          options.publish
            ? await uploadAsset(bytes, filename, { resourceType: key, onTelemetry: dependencyReporter(options['telemetry-task']) })
            : { url: filename, sha256, bytes: bytes.length },
        ];
      } catch (error) {
        if (key !== 'telemetry') throw error;
        process.stderr.write('MAP_TELEMETRY_RESOURCE_UNAVAILABLE\n');
        return [key, null];
      }
    }),
  );
  Object.assign(manifest.assets, Object.fromEntries(publication));
  if (telemetry && !manifest.assets.telemetry) {
    delete manifest.assets.telemetry;
    delete sources.telemetry;
    telemetry.disabled = true;
    telemetry.artifact_id = digest(
      telemetry.artifact_id + ':telemetry-unavailable',
    );
  }
  const replacements = new Map([
    [
      '__MAP_CREATE_TELEMETRY__',
      telemetry && manifest.assets.telemetry
        ? `<script>try { (${installMapTelemetry.toString()})(${scriptJson({ ...telemetry, sdk_url: manifest.assets.telemetry.url, sdk_integrity: integrity(manifest.assets.telemetry.sha256) })}, ${sanitizeTelemetryError.toString()}); } catch { document.documentElement.dataset.telemetryState = 'unavailable'; }</script>`
        : '',
    ],
    ['__MAP_CREATE_HEIGHT_MODE__', heightMode],
    ['__MAP_CREATE_TITLE__', htmlEscape(graph.title)],
    ['__MAP_CREATE_SOURCES__', sourceHtml(graph.sources || [])],
    ['__MAP_CREATE_AMAP_CONFIG__', scriptJson(config)],
    ['__MAP_CREATE_MANIFEST__', scriptJson(manifest)],
    [
      '__MAP_CREATE_HEIGHT_STYLE__',
      `--map-height:${height}px;height:${height}px`,
    ],
    ['__MAP_CREATE_BOOTSTRAP_URL__', htmlEscape(manifest.assets.bootstrap.url)],
    [
      '__MAP_CREATE_BOOTSTRAP_INTEGRITY__',
      integrity(manifest.assets.bootstrap.sha256),
    ],
  ]);
  let html = template;
  for (const [placeholder, value] of replacements)
    html = html.replaceAll(placeholder, () => value);
  const unresolvedPlaceholder = html.match(/__MAP_CREATE_[A-Z_]+__/);
  if (unresolvedPlaceholder)
    throw new Error(`HTML 模板仍包含未替换占位符 ${unresolvedPlaceholder[0]}`);
  if (!html.endsWith('\n')) html += '\n';
  if (options.standalone) html = embedLocalPreview(html, sources);
  await writeText(options.out, html);
  const report = {
    status: 'built',
    output: resolve(options.out),
    bytes: Buffer.byteLength(html),
    htmlSha256: createHash('sha256').update(html).digest('hex'),
    timings: { totalMs: Math.round(performance.now() - startedAt) },
    compatibility,
    ...(telemetry ? { telemetry } : {}),
    manifest,
    manifestSha256: digest(JSON.stringify(manifest)),
    contentMapKitAsset: {
      url: contentMapKitAsset.url,
      sha256: contentMapKitAsset.sha256,
      source: contentMapKitAsset.source,
    },
  };
  if (options.report) await writeJson(options.report, report);
  process.stdout.write(`${JSON.stringify(report)}\n`);
} catch (error) {
  process.stderr.write(
    `${JSON.stringify({ status: 'failed', error: safeError(error) })}\n`,
  );
  process.exitCode = 1;
}

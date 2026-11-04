import { execFile } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { safeLogId } from './dependency-telemetry.mjs';
import { bestEffortTelemetry, telemetryCode } from './task-telemetry.mjs';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, dirname, resolve } from 'node:path';
import { promisify } from 'node:util';
import { readLocalPreview } from './local-preview.mjs';

export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
export const integrity = sha256 =>
  'sha256-' + Buffer.from(sha256, 'hex').toString('base64');
const endpoint = 'https://content-map.bytedance.com/cdn/upload';
const mimeTypes = {
  js: 'javascript',
  css: 'text/css',
  json: 'application/json',
  html: 'text/html',
};
const execute = promisify(execFile);

async function request(url, upload) {
  const directory = await mkdtemp(resolve(tmpdir(), 'map-create-http-'));
  try {
    const body = resolve(directory, 'response');
    const headers = resolve(directory, 'headers');
    const argumentsList = [
      '--silent',
      '--show-error',
      '--fail-with-body',
      '--connect-timeout',
      '10',
      '--max-time',
      '30',
      '-D',
      headers,
      '-o',
      body,
    ];
    if (upload) {
      if (!/^[\w.-]+$/.test(upload.name))
        throw new Error('UPLOAD_NAME_INVALID');
      const file = resolve(directory, upload.name);
      await writeFile(file, upload.bytes);
      argumentsList.push('-F', 'file=@' + file);
    }
    try {
      await execute('curl', [...argumentsList, url], { timeout: 35000 });
    } catch (error) {
      const value = await readFile(headers, 'utf8').catch(() => '');
      error.http_status =
        Number([...value.matchAll(/^HTTP\/\S+\s+(\d+)/gm)].at(-1)?.[1]) ||
        undefined;
      error.logid = safeLogId(
        value.match(/^x-tt-logid:\s*([^\r\n]+)/im)?.[1]?.trim(),
      );
      error.code =
        error.killed || error.code === 28 ? 'CDN_TIMEOUT' : 'CDN_HTTP_FAILED';
      throw error;
    }
    return {
      bytes: await readFile(body),
      headers: await readFile(headers, 'utf8'),
    };
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

export async function uploadAsset(
  bytes,
  name,
  { resourceType = 'unknown', onTelemetry, transport = request } = {},
) {
  const started = performance.now();
  const eventId = randomUUID();
  const fields = {
    event_id: eventId,
    operation_id: randomUUID(),
    resource_type: resourceType,
    bytes: bytes.length,
    stage: 'upload',
    status: 'succeeded',
  };
  const logids = [];
  const observedTransport = async (...args) => {
    delete fields.logid;
    delete fields.http_status;
    const response = await transport(...args);
    const logid = safeLogId(
      response.headers?.match(/^x-tt-logid:\s*([^\r\n]+)/im)?.[1]?.trim(),
    );
    if (logid) {
      fields.logid = logid;
      logids.push(logid);
    }
    const status = Number(
      [...String(response.headers).matchAll(/^HTTP\/\S+\s+(\d+)/gm)].at(
        -1,
      )?.[1],
    );
    if (status) fields.http_status = status;
    return response;
  };
  try {
    const response = await observedTransport(endpoint, { bytes, name });
    const result = JSON.parse(response.bytes);
    if (result.code !== 0 || typeof result.data !== 'string')
      throw new Error('UPLOAD_RESPONSE_INVALID');
    const url = new URL(result.data);
    if (url.protocol !== 'https:' || url.username || url.password)
      throw new Error('UPLOAD_URL_INVALID');
    const asset = { url: url.href, sha256: digest(bytes), bytes: bytes.length };
    fields.stage = 'readback';
    await readAsset(
      asset,
      undefined,
      name.split('.').at(-1),
      observedTransport,
    );
    return asset;
  } catch (error) {
    fields.status = 'failed';
    fields.failure_id = eventId;
    if (error && typeof error === 'object' && Object.isExtensible(error))
      error.failure_id = eventId;
    fields.error_code = telemetryCode(error.code || error.message);
    if (/ASSET_(HASH|CORS|CONTENT_TYPE)/.test(fields.error_code))
      fields.stage = 'verify';
    if (error.http_status) fields.http_status = error.http_status;
    if (safeLogId(error.logid)) {
      fields.logid = error.logid;
      logids.push(error.logid);
    }
    throw error;
  } finally {
    fields.duration_ms = Math.round(performance.now() - started);
    if (logids.length) fields.logids = [...new Set(logids)].slice(-8).join(',');
    if (onTelemetry)
      await bestEffortTelemetry(() =>
        onTelemetry('cdn_publish_finished', fields),
      );
  }
}

export async function readAsset(
  asset,
  htmlFile,
  extension,
  transport = request,
) {
  if (!asset || !/^[a-f0-9]{64}$/.test(asset.sha256))
    throw new Error('ASSET_IDENTITY_INVALID');
  let bytes;
  if (/^https:\/\//.test(asset.url)) {
    const response = await transport(asset.url);
    if (!/access-control-allow-origin:\s*\*/i.test(response.headers))
      throw new Error('ASSET_CORS_REQUIRED');
    if (
      extension &&
      mimeTypes[extension] &&
      !response.headers.toLowerCase().includes(mimeTypes[extension])
    )
      throw new Error('ASSET_CONTENT_TYPE_INVALID:' + extension);
    bytes = response.bytes;
  } else {
    if (!htmlFile || basename(asset.url) !== asset.url)
      throw new Error('ASSET_URL_INVALID');
    bytes = await readFile(resolve(dirname(htmlFile), asset.url));
  }
  if (digest(bytes) !== asset.sha256) throw new Error('ASSET_HASH_MISMATCH');
  return bytes;
}

export function parseManifest(html) {
  const match = html.match(
    /<script id="map-create-manifest" type="application\/json">([\s\S]*?)<\/script>/,
  );
  if (!match) throw new Error('ASSET_MANIFEST_REQUIRED');
  const manifest = JSON.parse(match[1]);
  if (manifest.version !== 1 || manifest.runtimeRelease !== 'map-create-4')
    throw new Error('ASSET_MANIFEST_VERSION_UNSUPPORTED');
  for (const key of ['data', 'style', 'runtime', 'components', 'bootstrap'])
    if (!manifest.assets?.[key])
      throw new Error('ASSET_MANIFEST_INCOMPLETE:' + key);
  return manifest;
}

export async function readArtifact(html, htmlFile) {
  const manifest = parseManifest(html);
  const embedded = readLocalPreview(html, manifest);
  const types = {
    data: 'json',
    style: 'css',
    runtime: 'js',
    components: 'js',
    bootstrap: 'js',
  };
  const loaded = await Promise.all(
    Object.entries(types).map(async ([key, extension]) => [
      key,
      embedded?.[key] ||
        (await readAsset(manifest.assets[key], htmlFile, extension)),
    ]),
  );
  const graph = JSON.parse(
    loaded.find(([key]) => key === 'data')[1].toString(),
  );
  return { graph, manifest, manifestSha256: digest(JSON.stringify(manifest)) };
}

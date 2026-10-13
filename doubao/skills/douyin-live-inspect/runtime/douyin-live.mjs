import { BlockList, isIP } from 'node:net';

export const DOUYIN_PAGE_MAX_BYTES = 2 * 1024 * 1024;
export const DOUYIN_PAGE_TIMEOUT_MS = 15_000;

const DOUYIN_HOST = 'live.douyin.com';
const DOUYIN_WEB_HOST = 'www.douyin.com';
const DOUYIN_SHORT_HOST = 'v.douyin.com';
const DOUYIN_REFLOW_HOST = 'webcast.amemv.com';
const MIN_STREAM_VALIDITY_SECONDS = 60;
const QUALITY_KEYS = new Set(['ld', 'sd', 'hd', 'uhd', 'origin']);
const blockedAddresses = new BlockList();

for (const [address, prefix] of [
  ['0.0.0.0', 8], ['10.0.0.0', 8], ['100.64.0.0', 10], ['127.0.0.0', 8],
  ['169.254.0.0', 16], ['172.16.0.0', 12], ['192.0.0.0', 24], ['192.0.2.0', 24],
  ['192.31.196.0', 24], ['192.52.193.0', 24], ['192.88.99.0', 24], ['192.168.0.0', 16],
  ['192.175.48.0', 24], ['198.18.0.0', 15], ['198.51.100.0', 24], ['203.0.113.0', 24],
  ['224.0.0.0', 4],
]) blockedAddresses.addSubnet(address, prefix, 'ipv4');
for (const [address, prefix] of [
  ['::', 128], ['::1', 128], ['64:ff9b:1::', 48], ['100::', 64], ['2001::', 32],
  ['2001:2::', 48], ['2001:10::', 28], ['2001:20::', 28], ['2001:db8::', 32],
  ['fc00::', 7], ['fe80::', 10], ['ff00::', 8],
]) blockedAddresses.addSubnet(address, prefix, 'ipv6');

export class DouyinLiveError extends Error {
  constructor(message, code, retryable = false) {
    super(message);
    this.name = 'DouyinLiveError';
    this.code = code;
    this.retryable = retryable;
  }
}

function error(message, code, retryable = false) {
  return new DouyinLiveError(message, code, retryable);
}

export function validateDouyinLiveUrl(value) {
  let url;
  try { url = new URL(`${value ?? ''}`.trim()); } catch {
    throw error('douyin_url must be a valid Douyin live page URL', 'INVALID_INPUT');
  }
  if (url.protocol !== 'https:' || ![DOUYIN_HOST, DOUYIN_WEB_HOST, DOUYIN_SHORT_HOST].includes(url.hostname)
    || url.port || url.username || url.password) {
    throw error('douyin_url must use an official Douyin live or share URL without credentials or a custom port', 'INVALID_INPUT');
  }
  if (url.hostname !== DOUYIN_SHORT_HOST) {
    const match = url.pathname.match(url.hostname === DOUYIN_HOST ? /^\/(\d+)\/?$/ : /^\/follow\/live\/(\d+)\/?$/);
    // Explicit room identity survives changes to navigation paths; conflicting identities remain invalid.
    if (url.searchParams.has('live_web_rid')) {
      const roomIds = url.searchParams.getAll('live_web_rid');
      if (roomIds.length !== 1 || !/^[0-9]+$/.test(roomIds[0]) || (match && match[1] !== roomIds[0])) {
        throw error('Douyin URLs require one numeric live_web_rid consistent with the room path', 'INVALID_INPUT');
      }
      return `https://${DOUYIN_HOST}/${roomIds[0]}`;
    }
    if (!match) throw error('douyin_url must identify a live room through live_web_rid or a numeric live room path', 'INVALID_INPUT');
    return `https://${DOUYIN_HOST}/${match[1]}`;
  }
  const match = url.pathname.match(/^\/([A-Za-z0-9_-]{4,128})\/?$/);
  if (!match) throw error('douyin_url must use a valid https://v.douyin.com/<share-code> URL', 'INVALID_INPUT');
  return `https://${DOUYIN_SHORT_HOST}/${match[1]}/`;
}

function decodeHtmlAttribute(value) {
  return `${value || ''}`
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([\da-f]+);/gi, (_, code) => String.fromCodePoint(Number.parseInt(code, 16)))
    .replaceAll('&quot;', '"').replaceAll('&#39;', "'")
    .replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&');
}

function jsonContainer(value) {
  if (value && typeof value === 'object') return value;
  if (typeof value !== 'string' || !/^\s*[\[{]/.test(value)) return null;
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch { return null; }
}

export function addressIsBlocked(address) {
  const normalized = `${address}`.toLowerCase().replace(/^\[|\]$/g, '').split('%')[0];
  if (normalized.startsWith('::ffff:')) return addressIsBlocked(normalized.slice(7));
  const family = isIP(normalized);
  return family !== 0 && blockedAddresses.check(normalized, family === 4 ? 'ipv4' : 'ipv6');
}

function hostnameIsAdmin(hostname) {
  return /(?:^|[.-])admin(?:[.-]|$)/i.test(`${hostname || ''}`);
}

function streamKeyText(url) {
  const uniqueId = url.searchParams.get('unique_id') || '';
  try { return `${decodeURIComponent(url.pathname)} ${decodeURIComponent(uniqueId)}`; } catch {
    return `${url.pathname} ${uniqueId}`;
  }
}

export function extractDouyinStreamKey(value) {
  let url;
  try { url = new URL(`${value || ''}`); } catch { return null; }
  return streamKeyText(url).match(/(?:^|[\/_-])stream-(\d{8,})(?=$|[\s/_.-])/i)?.[1] || null;
}

function normalizeQuality(value) {
  const normalized = `${value || ''}`.toLowerCase().replace(/5$/, '');
  return QUALITY_KEYS.has(normalized) ? normalized : null;
}

function expirationTimestamps(value) {
  const raw = `${value ?? ''}`;
  const timestamps = [];
  if (/^\d+$/.test(raw)) timestamps.push(Number(raw));
  if (/^[\da-f]{8}$/i.test(raw)) timestamps.push(Number.parseInt(raw, 16));
  return timestamps.filter(Number.isSafeInteger);
}

function streamExpirationTimestamps(url) {
  // auth_key uses decimal expiry-random-uid-md5; preserve the complete URL for CDN authentication.
  if (url.searchParams.has('auth_key')) {
    const match = url.searchParams.get('auth_key').match(/^(\d+)-[A-Za-z0-9]+-\d+-[\da-f]{32}$/i);
    const timestamp = match ? Number(match[1]) : NaN;
    return Number.isSafeInteger(timestamp) ? [timestamp] : [];
  }
  const direct = expirationTimestamps(url.searchParams.get('expire') ?? url.searchParams.get('t'));
  if (direct.length) return direct;
  // Douyin CDN: wsTime is a hex signing timestamp; keeptime is a hex validity duration in milliseconds.
  const wsTime = url.searchParams.get('wsTime');
  if (wsTime && /^[\da-f]{8}$/i.test(wsTime)) {
    const signedAt = Number.parseInt(wsTime, 16);
    const keepTimeRaw = url.searchParams.get('keeptime');
    if (keepTimeRaw && /^[\da-f]+$/i.test(keepTimeRaw)) {
      const keepSeconds = Math.floor(Number.parseInt(keepTimeRaw, 16) / 1000);
      const expire = signedAt + keepSeconds;
      if (Number.isSafeInteger(expire)) return [expire];
    }
    if (Number.isSafeInteger(signedAt)) return [signedAt];
  }
  return [];
}

export function candidateFrom(value, context, now) {
  if (typeof value !== 'string' || value.length > 8_192) return null;
  let url;
  try { url = new URL(value); } catch { return null; }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password
    || addressIsBlocked(url.hostname) || hostnameIsAdmin(url.hostname)
    || !/\.flv$/i.test(url.pathname)) return null;
  const streamKey = extractDouyinStreamKey(url.toString());
  const minimumExpiration = Math.floor(now / 1_000) + MIN_STREAM_VALIDITY_SECONDS;
  const expirationIsValid = streamExpirationTimestamps(url)
    .some((expire) => expire >= minimumExpiration);
  if (!streamKey || !expirationIsValid) return null;
  return {
    url: url.toString(), streamKey, codec: context.codec,
    quality: normalizeQuality(context.quality), route: context.route,
    bitrate: Number.isFinite(Number(context.bitrate)) ? Number(context.bitrate) : null,
    resolution: `${context.resolution || ''}` || null, secure: url.protocol === 'https:',
  };
}

function collectCandidates(root, codec, now) {
  const output = [];
  const visit = (raw, context = {}, depth = 0) => {
    if (depth > 14) return;
    const value = jsonContainer(raw);
    if (!value) return;
    if (Array.isArray(value)) {
      for (const item of value) visit(item, context, depth + 1);
      return;
    }
    const sdk = jsonContainer(value.sdk_params ?? value.sdkParams) || {};
    const inherited = {
      ...context,
      bitrate: sdk.vbitrate ?? sdk.bitrate ?? sdk.bitrateKbps ?? context.bitrate ?? null,
      resolution: sdk.resolution ?? context.resolution ?? null,
    };
    for (const [key, item] of Object.entries(value)) {
      const lower = key.toLowerCase();
      const next = {
        ...inherited,
        quality: normalizeQuality(lower) ?? inherited.quality ?? null,
        route: ['main', 'backup'].includes(lower) ? lower : (inherited.route ?? null),
      };
      if (lower === 'flv') {
        const candidate = candidateFrom(item, { codec, ...next }, now);
        if (candidate) output.push(candidate);
      } else if (lower !== 'sdk_params' && lower !== 'sdkparams') visit(item, next, depth + 1);
    }
  };
  visit(root);
  return output;
}

function resolutionArea(value) {
  const match = `${value || ''}`.match(/^(\d+)x(\d+)$/i);
  return match ? Number(match[1]) * Number(match[2]) : Number.POSITIVE_INFINITY;
}

function sortSameTier(candidates, fallback = false) {
  return [...candidates].sort((left, right) => {
    if (left.secure !== right.secure) return left.secure ? -1 : 1;
    if (fallback) {
      const bitrateDelta = (left.bitrate ?? Infinity) - (right.bitrate ?? Infinity);
      if (bitrateDelta) return bitrateDelta;
      const areaDelta = resolutionArea(left.resolution) - resolutionArea(right.resolution);
      if (areaDelta) return areaDelta;
    }
    const rank = (route) => route === 'main' ? 0 : route === 'backup' ? 1 : 2;
    return rank(left.route) - rank(right.route);
  });
}

export function selectDouyinFlvCandidate(candidates) {
  const pools = [
    candidates.filter((item) => item.codec === 'h264' && item.quality === 'ld'),
    candidates.filter((item) => item.codec === 'h265' && item.quality === 'ld'),
    candidates.filter((item) => item.codec === 'h264'),
    candidates.filter((item) => item.codec === 'h265'),
  ];
  for (let index = 0; index < pools.length; index += 1) {
    const selected = sortSameTier(pools[index], index >= 2)[0];
    if (selected) return selected;
  }
  return null;
}

function rejectVerificationPage(text) {
  const title = text.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1] || '';
  if (/验证码中间页|安全验证|人机验证/.test(decodeHtmlAttribute(title))) {
    throw error('Douyin returned a verification page; check the page in the browser', 'DOUYIN_VERIFICATION_REQUIRED');
  }
}

export function parseDouyinLivePage(html, { now = Date.now() } = {}) {
  const text = `${html || ''}`;
  rejectVerificationPage(text);
  const configMatch = text.match(/<script\b[^>]*\bdata-config="([^"]*)"[^>]*>/i);
  if (!configMatch) {
    throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
  }
  let config;
  try { config = JSON.parse(decodeHtmlAttribute(configMatch[1])); } catch {
    throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
  }
  const streamData = config?.playerConfig?.pluginsConfig?.liveStream?.streamData
    ?? config?.basicPlayerProps?.pluginsConfig?.liveStream?.streamData
    ?? config?.basicPlayerProps?.pluginsConfigInternal?.liveStream?.streamData;
  if (!streamData || typeof streamData !== 'object') {
    throw error('Douyin player data is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
  }
  const candidates = [
    ...collectCandidates(streamData.h264PullData?.stream_data ?? streamData.h264PullData, 'h264', now),
    ...collectCandidates(streamData.h265PullData?.stream_data ?? streamData.h265PullData, 'h265', now),
  ];
  const selected = selectDouyinFlvCandidate(candidates);
  if (!selected) throw error('No supported FLV stream is available for this Douyin live room', 'DOUYIN_FLV_UNAVAILABLE');
  const roomName = `${config?.basicPlayerProps?.logOptions?.title
    ?? config?.roomInfo?.room?.title
    ?? config?.roomInfo?.title
    ?? config?.room?.title
    ?? ''}`.trim().slice(0, 100);
  const accountName = `${config?.basicPlayerProps?.playerAction?.anchorInfo?.nickname
    ?? config?.roomInfo?.anchor?.nickname
    ?? config?.anchor?.nickname
    ?? ''}`.trim().slice(0, 100);
  return { status: 'ready', streamUrl: selected.url, streamKey: selected.streamKey, roomName, accountName };
}

function decodeEmbeddedScriptText(value) {
  let decoded = decodeHtmlAttribute(value);
  for (let index = 0; index < 2; index += 1) {
    decoded = decoded
      .replace(/\\u([\da-f]{4})/gi, (_, code) => String.fromCodePoint(Number.parseInt(code, 16)))
      .replace(/\\x([\da-f]{2})/gi, (_, code) => String.fromCodePoint(Number.parseInt(code, 16)))
      .replace(/\\\//g, '/').replace(/\\"/g, '"');
  }
  return decoded;
}

export function parseDouyinReflowPage(html, { now = Date.now() } = {}) {
  rejectVerificationPage(`${html || ''}`);
  const decoded = decodeEmbeddedScriptText(`${html || ''}`);
  const matches = decoded.match(/https?:\/\/[^\s"'<>\\]+?\.flv(?:\?[^\s"'<>\\]+)?/gi) || [];
  const candidates = [];
  const seen = new Set();
  for (const value of matches) {
    if (seen.has(value)) continue;
    seen.add(value);
    let url;
    try { url = new URL(value); } catch { continue; }
    const quality = url.pathname.match(/(?:^|[\/_-])(ld|sd|hd|uhd|origin)(?=$|[\/_.-])/i)?.[1];
    const codec = /(?:h265|hevc)/i.test(`${url.pathname} ${url.search}`) ? 'h265' : 'h264';
    const candidate = candidateFrom(value, { codec, quality, route: null }, now);
    if (candidate) candidates.push(candidate);
  }
  const selected = selectDouyinFlvCandidate(candidates);
  if (selected) return { status: 'ready', streamUrl: selected.url, streamKey: selected.streamKey };
  if (/streamData|stream_data|room[_-]?id/i.test(decoded)) {
    throw error('No supported FLV stream is available for this Douyin live room', 'DOUYIN_FLV_UNAVAILABLE');
  }
  return { status: 'not_live' };
}

async function readResponseBody(response, maximum) {
  const declared = Number(response.headers.get('content-length') || 0);
  if (declared > maximum) throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
  if (!response.body?.getReader) {
    const buffer = Buffer.from(await response.arrayBuffer());
    if (buffer.byteLength > maximum) throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
    return buffer.toString('utf8');
  }
  const chunks = [];
  let size = 0;
  const reader = response.body.getReader();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
      chunks.push(Buffer.from(value));
    }
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks, size).toString('utf8');
}

async function fetchDouyinPage(fetchImpl, url, timeoutMs) {
  try {
    const response = await fetchImpl(url, {
      method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(timeoutMs),
      headers: {
        accept: 'text/html,application/xhtml+xml', 'accept-language': 'zh-CN,zh;q=0.9',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36',
      },
    });
    if (response.status >= 500) throw error('Douyin live page fetch failed', 'DOUYIN_FETCH_FAILED', true);
    return response;
  } catch (cause) {
    if (cause?.code) throw cause;
    throw error('Douyin live page fetch failed', 'DOUYIN_FETCH_FAILED', true);
  }
}

async function readDouyinHtml(response, maximumBytes) {
  if (response.status >= 300 && response.status < 400) {
    throw error('Douyin live page redirect is not supported', 'DOUYIN_PAGE_UNAVAILABLE');
  }
  if (!response.ok) throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
  const contentType = `${response.headers.get('content-type') || ''}`.toLowerCase();
  if (!contentType.includes('text/html') && !contentType.includes('application/xhtml+xml')) {
    throw error('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE');
  }
  try { return await readResponseBody(response, maximumBytes); } catch (cause) {
    if (cause?.code) throw cause;
    throw error('Douyin live page fetch failed', 'DOUYIN_FETCH_FAILED', true);
  }
}

export async function resolveDouyinLive(value, {
  fetchImpl = globalThis.fetch, now = Date.now, timeoutMs = DOUYIN_PAGE_TIMEOUT_MS,
  maximumBytes = DOUYIN_PAGE_MAX_BYTES,
} = {}) {
  const pageUrl = validateDouyinLiveUrl(value);
  const parsedPageUrl = new URL(pageUrl);
  const isShortUrl = parsedPageUrl.hostname === DOUYIN_SHORT_HOST;
  let response = await fetchDouyinPage(fetchImpl, pageUrl, timeoutMs);
  if (isShortUrl) {
    if (![301, 302, 303, 307, 308].includes(response.status)) {
      throw error('Douyin share URL did not redirect to a supported live page', 'DOUYIN_PAGE_UNAVAILABLE');
    }
    let landingUrl;
    try { landingUrl = new URL(response.headers.get('location') || '', pageUrl); } catch {
      throw error('Douyin share URL did not redirect to a supported live page', 'DOUYIN_PAGE_UNAVAILABLE');
    }
    if (landingUrl.protocol !== 'https:' || landingUrl.hostname !== DOUYIN_REFLOW_HOST
      || landingUrl.port || landingUrl.username || landingUrl.password
      || !/^\/douyin\/webcast\/reflow\/\d{8,}\/?$/.test(landingUrl.pathname)) {
      throw error('Douyin share URL did not redirect to a supported live page', 'DOUYIN_PAGE_UNAVAILABLE');
    }
    landingUrl.hash = '';
    response = await fetchDouyinPage(fetchImpl, landingUrl.toString(), timeoutMs);
    return parseDouyinReflowPage(await readDouyinHtml(response, maximumBytes), { now: now() });
  }

  const html = await readDouyinHtml(response, maximumBytes);
  try {
    return parseDouyinLivePage(html, { now: now() });
  } catch (cause) {
    if (cause?.code !== 'DOUYIN_FLV_UNAVAILABLE') throw cause;
  }
  const roomId = parsedPageUrl.pathname.slice(1);
  const reflowUrl = `https://${DOUYIN_REFLOW_HOST}/douyin/webcast/reflow/${roomId}`;
  response = await fetchDouyinPage(fetchImpl, reflowUrl, timeoutMs);
  const fallback = parseDouyinReflowPage(await readDouyinHtml(response, maximumBytes), { now: now() });
  if (fallback.status === 'not_live') {
    throw error('No supported FLV stream is available for this Douyin live room', 'DOUYIN_FLV_UNAVAILABLE');
  }
  return fallback;
}

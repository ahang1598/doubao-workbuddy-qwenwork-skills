import { fetchXiaohongshu } from './xiaohongshu-live.mjs';

const fail = code => Object.assign(new Error('B 站直播来源暂不可用'), { code, retryable: code === 'BILI_FETCH_FAILED' });
const api = 'https://api.live.bilibili.com';
const list = value => Array.isArray(value) ? value : [];
const roomId = value => (typeof value === 'string' && /^[1-9][0-9]*$/.test(value))
  || (Number.isSafeInteger(value) && value > 0);

export function isBilibiliUrl(value) {
  try { return ['live.bilibili.com', 'b23.tv'].includes(new URL(value).hostname); } catch { return false; }
}

export function validateBilibiliLiveUrl(value) {
  if (typeof value !== 'string' || value.length > 8192 || /[\u0000-\u0020]/.test(value)) throw fail('INVALID_INPUT');
  let url;
  try { url = new URL(value); } catch { throw fail('INVALID_INPUT'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.port) throw fail('INVALID_INPUT');
  const room = /^\/([1-9][0-9]*)\/?$/.exec(url.pathname);
  if (url.hostname === 'live.bilibili.com' && room) return `https://live.bilibili.com/${room[1]}`;
  if (url.hostname === 'b23.tv' && /^\/[A-Za-z0-9]+\/?$/.test(url.pathname)) return url.href;
  throw fail('INVALID_INPUT');
}

export function bilibiliCandidate(value, now = Date.now()) {
  if (typeof value !== 'string' || value.length > 8192 || /[\u0000-\u0020]/.test(value)) return null;
  let url;
  try { url = new URL(value); } catch { return null; }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash
    || (url.port && !['80', '443'].includes(url.port)) || !url.hostname.endsWith('.bilivideo.com')
    || !/\.flv$/i.test(url.pathname)) return null;
  for (const expiry of url.searchParams.getAll('expires')) {
    if (!/^[0-9]+$/.test(expiry) || Number(expiry) < now / 1000 + 60) return null;
  }
  return { url: value };
}

function roomData(payload) {
  if ([-101, -111, -352, -412].includes(payload?.code)) throw fail('BILI_AUTH_REQUIRED');
  if (payload?.code !== 0 || !payload.data || typeof payload.data !== 'object' || Array.isArray(payload.data)) throw fail('BILI_PAGE_UNAVAILABLE');
  const room = payload.data;
  if (!roomId(room.room_id)) throw fail('BILI_PAGE_UNAVAILABLE');
  if (room.is_hidden || room.is_locked || room.encrypted) throw fail('BILI_ROOM_UNAVAILABLE');
  if (room.live_status === 2) throw fail('BILI_REPLAY_UNSUPPORTED');
  if (![0, 1].includes(room.live_status)) throw fail('BILI_LIVE_STATE_UNKNOWN');
  return room;
}

export function parseBilibiliPlayInfo(payload, { now = Date.now(), expectedRoom } = {}) {
  const room = roomData(payload);
  if (expectedRoom !== undefined && String(room.room_id) !== String(expectedRoom)) throw fail('BILI_PAGE_UNAVAILABLE');
  if (room.live_status === 0) return { status: 'not_live', sourceType: 'bilibili' };
  const candidates = [];
  const seen = new Set();
  for (const stream of list(room.playurl_info?.playurl?.stream)) {
    if (stream?.protocol_name !== 'http_stream') continue;
    for (const format of list(stream.format)) {
      if (format?.format_name !== 'flv') continue;
      for (const codec of list(format.codec)) {
        if (codec?.codec_name !== 'avc' || codec.drm || typeof codec.base_url !== 'string' || !codec.base_url.startsWith('/')) continue;
        for (const info of list(codec.url_info)) {
          if (typeof info?.host !== 'string' || typeof info.extra !== 'string') continue;
          const candidate = bilibiliCandidate(info.host + codec.base_url + info.extra, now);
          if (candidate && !seen.has(candidate.url)) { seen.add(candidate.url); candidates.push(candidate); }
        }
      }
    }
  }
  if (!candidates.length) throw fail('BILI_STREAM_UNAVAILABLE');
  return { status: 'ready', sourceType: 'bilibili', streamUrl: candidates[0].url, candidates, roomName: '', accountName: '' };
}

export async function fetchBilibili(url, options) {
  try { return await fetchXiaohongshu(url, { ...options, platform: 'bilibili' }); }
  catch (error) { throw fail(error.code === 'INVALID_INPUT' ? error.code : error.code === 'XHS_PAGE_UNAVAILABLE' ? 'BILI_PAGE_UNAVAILABLE' : 'BILI_FETCH_FAILED'); }
}

export async function resolveBilibiliPage(value, { fetchPage = fetchBilibili, deadline = Date.now() + 15000 } = {}) {
  let page = validateBilibiliLiveUrl(value);
  for (let hop = 0; hop <= 4; hop++) {
    if (new URL(page).hostname === 'live.bilibili.com') return page;
    if (hop === 4) break;
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw fail('BILI_FETCH_FAILED');
    const response = await fetchPage(page, { timeoutMs: remaining });
    if (![301, 302, 303, 307, 308].includes(response.status) || !response.location) throw fail('BILI_PAGE_UNAVAILABLE');
    try { page = validateBilibiliLiveUrl(new URL(response.location, page).href); }
    catch { throw fail('INVALID_INPUT'); }
  }
  throw fail('BILI_PAGE_UNAVAILABLE');
}

export function validateBilibiliBrowserSource(page, source, now = Date.now()) {
  try {
    if (!source || validateBilibiliLiveUrl(source.page_url) !== page || !Number.isSafeInteger(source.captured_at)
      || source.captured_at > now + 5000 || now - source.captured_at > 120000) throw Error();
    if (source.status === 'not_live' && Object.keys(source).length === 3) {
      return {status: 'not_live', sourceType: 'bilibili', sourceMethod: 'browser'};
    }
    if (!bilibiliCandidate(source.stream_url, now)) throw Error();
  } catch { throw fail('INVALID_BROWSER_SOURCE'); }
  const text = value => typeof value === 'string' ? value.trim().slice(0, 100) : '';
  return { status: 'ready', sourceType: 'bilibili', sourceMethod: 'browser', streamUrl: source.stream_url,
    roomName: text(source.room_title), accountName: text(source.account_name) };
}

export async function resolveBilibiliLive(value, { browserSource, fetchPage = fetchBilibili, probe, now = Date.now, timeoutMs = 15000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  const page = await resolveBilibiliPage(value, { fetchPage, deadline });
  if (browserSource) {
    const source = validateBilibiliBrowserSource(page, browserSource, now());
    if (source.status === 'not_live') return source;
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw fail('BILI_FETCH_FAILED');
    try { await probe(source.streamUrl, { timeoutMs: Math.min(5000, remaining) }); }
    catch { throw fail('BILI_STREAM_UNAVAILABLE'); }
    return source;
  }
  const json = async path => {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw fail('BILI_FETCH_FAILED');
    const response = await fetchPage(api + path, { timeoutMs: remaining });
    if (response.status !== 200) throw fail([401, 403, 412].includes(response.status) ? 'BILI_AUTH_REQUIRED' : 'BILI_FETCH_FAILED');
    try { return JSON.parse(response.body); } catch { throw fail('BILI_PAGE_UNAVAILABLE'); }
  };
  const room = roomData(await json(`/room/v1/Room/room_init?id=${new URL(page).pathname.slice(1)}`));
  if (room.live_status === 0) return { status: 'not_live', sourceType: 'bilibili' };
  const source = parseBilibiliPlayInfo(await json(`/xlive/web-room/v2/index/getRoomPlayInfo?room_id=${room.room_id}&protocol=0&format=0&codec=0&qn=250&platform=web&ptype=8`), { now: now(), expectedRoom: room.room_id });
  if (source.status === 'not_live') return source;
  for (const candidate of source.candidates) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    try {
      await probe(candidate.url, { timeoutMs: Math.min(5000, remaining) });
      return { ...source, candidates: undefined, streamUrl: candidate.url, sourceMethod: 'anonymous' };
    } catch { /* A failed CDN must not hide a usable server-provided backup. */ }
  }
  throw fail('BILI_STREAM_UNAVAILABLE');
}

// Only consume observations from the host script, which checks both API room IDs.
export function bilibiliObservedSources(observation, now = Date.now()) {
  const page = validateBilibiliLiveUrl(observation?.page_url);
  if (new URL(page).hostname !== 'live.bilibili.com' || !Array.isArray(observation?.media_urls)
    || observation.media_urls.length > 64) throw fail('INVALID_BROWSER_SOURCE');
  if (observation.status === 'not_live') {
    const source = {page_url: page, captured_at: observation.captured_at, status: 'not_live'};
    validateBilibiliBrowserSource(page, source, now);
    throw Object.assign(fail('BILI_NOT_LIVE'), {browser_source: source});
  }
  const sources = [];
  for (const url of new Set(observation.media_urls)) {
    if (!bilibiliCandidate(url, now)) continue;
    const source = { page_url: page, captured_at: observation.captured_at, stream_url: url,
      page_title: typeof observation.page_title === 'string' ? observation.page_title.slice(0, 100) : '' };
    validateBilibiliBrowserSource(page, source, now);
    sources.push(source);
  }
  if (!sources.length) throw fail('BILI_STREAM_UNAVAILABLE');
  return sources;
}

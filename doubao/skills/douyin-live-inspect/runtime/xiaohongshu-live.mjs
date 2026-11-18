// 小红书响应解析；只消费服务端提供的候选，不根据房间号生成流地址。

const fail = (code, message = '小红书直播来源暂不可用') => Object.assign(new Error(message), { code, retryable: code === 'XHS_FETCH_FAILED' });

export function validateXiaohongshuLiveUrl(value) {
  let url;
  if (typeof value !== 'string' || value.length > 8192 || /[\u0000-\u0020]/.test(value)) throw fail('INVALID_INPUT');
  try { url = new URL(value); } catch { throw fail('INVALID_INPUT'); }
  if (url.hostname === 'xhslink.com' && url.protocol === 'http:' && !url.port) url.protocol = 'https:';
  if (url.protocol !== 'https:' || url.username || url.password || url.port) throw fail('INVALID_INPUT');
  const room = /^\/livestream\/(?:dynpath[A-Za-z0-9]+\/)?([0-9]+)\/?$/.exec(url.pathname);
  if (url.hostname === 'www.xiaohongshu.com' && room) {
    return `https://www.xiaohongshu.com/livestream/${room[1]}`;
  }
  if (url.hostname === 'xhslink.com' && /^\/[A-Za-z0-9_/-]+$/.test(url.pathname)) return url.href;
  throw fail('INVALID_INPUT');
}

export function xiaohongshuCandidate(value, now = Date.now()) {
  if (typeof value !== 'string' || value.length > 8192 || /[\u0000-\u0020]/.test(value)) return null;
  let url;
  try { url = new URL(value); } catch { return null; }
  if (value.includes('\\') || !/^https?:\/\//i.test(value) || !['http:', 'https:'].includes(url.protocol) || url.username || url.password
    || !url.hostname.endsWith('.xhscdn.com') || !/\.flv$/i.test(url.pathname)
    || url.searchParams.getAll('only_audio').includes('1')
    || url.hash || (url.port && !['80', '443'].includes(url.port))) return null;
  for (const expiry of url.searchParams.getAll('expire')) {
    if (!/^[0-9]+$/.test(expiry) || Number(expiry) < now / 1000 + 60) return null;
  }
  // 实测小红书配置允许无签名流；不能套用抖音必须带到期参数的规则。
  return { url: value };
}

export function parseXiaohongshuRoomInfo(payload, { now = Date.now() } = {}) {
  if (!payload || payload.success !== true || payload.code !== 0) throw fail('XHS_PAGE_UNAVAILABLE');
  const room = payload.data?.room_info;
  if (room?.status === 3) return { status: 'not_live', sourceType: 'xiaohongshu' };
  // 仅接受实际观测的开播/停播状态，未知状态不能推断 not_live。
  if (!room || room.status !== 2) throw fail('XHS_LIVE_STATE_UNKNOWN');
  let config;
  try { config = typeof room.pull_config === 'string' ? JSON.parse(room.pull_config) : room.pull_config; }
  catch { throw fail('XHS_STREAM_UNAVAILABLE'); }
  if (!Array.isArray(config?.streams)) throw fail('XHS_STREAM_UNAVAILABLE');
  const streams = config.streams.filter(s => s && typeof s === 'object');
  // 本次实测 EF4 为 H.264、EF5 为 HEVC；实际解码能力仍由下游探测验证。
  streams.sort((a, b) => Number(b.codec_v2 === 'EF4') - Number(a.codec_v2 === 'EF4'));
  const candidates = [];
  const seen = new Set();
  for (const stream of streams) {
    for (const value of [stream.master_url, ...(Array.isArray(stream.backup_urls) ? stream.backup_urls : [])]) {
      const candidate = xiaohongshuCandidate(value, now);
      if (candidate && !seen.has(candidate.url)) { seen.add(candidate.url); candidates.push(candidate); }
    }
  }
  if (!candidates.length) throw fail('XHS_STREAM_UNAVAILABLE');
  return { status: 'ready', sourceType: 'xiaohongshu', streamUrl: candidates[0].url, candidates,
    roomName: typeof room.room_title === 'string' ? room.room_title.trim().slice(0, 100) : '',
    accountName: typeof payload.data?.host_info?.nick_name === 'string' ? payload.data.host_info.nick_name.trim().slice(0, 100) : '' };
}

export function isXiaohongshuUrl(value) {
  try { return ['www.xiaohongshu.com', 'xhslink.com'].includes(new URL(value).hostname); } catch { return false; }
}

// Official Xiaohongshu room and share endpoints use the host network's HTTPS routing.
// Redirects are validated separately by resolveXiaohongshuPage.
export async function fetchXiaohongshu(url, { timeoutMs = 8000, platform = 'xiaohongshu' } = {}) {
  const { default: https } = await import('node:https');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await Promise.race([ (async () => {
      const target = new URL(url);
      if (target.protocol !== 'https:' || target.username || target.password || target.port
        || !(platform === 'bilibili' ? ['live.bilibili.com', 'b23.tv', 'api.live.bilibili.com'] : ['www.xiaohongshu.com', 'xhslink.com', 'live-room.xiaohongshu.com']).includes(target.hostname)) throw fail('INVALID_INPUT');
      if (target.hostname === 'xhslink.com') validateXiaohongshuLiveUrl(target.href);
      return await new Promise((resolve, reject) => {
        const request = https.get(target, { agent: false, signal: controller.signal,
          headers: { 'User-Agent': 'Mozilla/5.0', Accept: 'application/json,text/html' },
        }, response => {
          const chunks = []; let size = 0;
          response.on('data', chunk => {
            size += chunk.length;
            if (size > 2 * 1024 * 1024) { response.destroy(); reject(fail('XHS_PAGE_UNAVAILABLE')); }
            else chunks.push(chunk);
          });
          response.on('error', reject);
          response.on('end', () => resolve({ status: response.statusCode, location: response.headers.location,
            body: Buffer.concat(chunks).toString('utf8') }));
        });
        request.on('error', reject);
      });
    })(), new Promise((_, reject) => controller.signal.addEventListener('abort', () => reject(fail('XHS_FETCH_FAILED')), { once: true })) ]);
  } catch (error) {
    if (error?.code === 'INVALID_INPUT') throw error;
    throw fail(error?.code === 'XHS_PAGE_UNAVAILABLE' ? error.code : 'XHS_FETCH_FAILED');
  } finally { clearTimeout(timer); }
}

export async function resolveXiaohongshuPage(value, { fetchPage = fetchXiaohongshu, deadline = Date.now() + 15000 } = {}) {
  let page = validateXiaohongshuLiveUrl(value);
  for (let hop = 0; hop < 4; hop++) {
    if (new URL(page).hostname === 'www.xiaohongshu.com') return page;
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw fail('XHS_FETCH_FAILED');
    const response = await fetchPage(page, { timeoutMs: remaining });
    if (![301, 302, 303, 307, 308].includes(response.status) || !response.location) throw fail('XHS_PAGE_UNAVAILABLE');
    try { page = validateXiaohongshuLiveUrl(new URL(response.location, page).href); }
    catch { throw fail('INVALID_INPUT'); }
  }
  throw fail('XHS_PAGE_UNAVAILABLE');
}

function freshObservation(capturedAt, now) {
  return Number.isSafeInteger(capturedAt) && capturedAt <= now + 5000 && now - capturedAt <= 120000;
}

export function validateXiaohongshuBrowserSource(page, source, now = Date.now()) {
  let observedPage;
  try { observedPage = validateXiaohongshuLiveUrl(source?.page_url); } catch { throw fail('INVALID_BROWSER_SOURCE'); }
  if (!source || typeof source !== 'object' || Array.isArray(source)
    || !freshObservation(source.captured_at, now)
    || observedPage !== page) throw fail('INVALID_BROWSER_SOURCE');
  const candidate = xiaohongshuCandidate(source.stream_url, now);
  const room = new URL(page).pathname.split('/').pop();
  if (!candidate || !new RegExp('^/live/' + room + '(?:_[A-Za-z0-9_-]+)?\\.flv$').test(new URL(candidate.url).pathname)) throw fail('INVALID_BROWSER_SOURCE');
  const text = value => typeof value === 'string' ? value.trim().slice(0, 100) : '';
  return { status: 'ready', sourceType: 'xiaohongshu', sourceMethod: 'browser', streamUrl: candidate.url,
    roomName: text(source.room_title) || text(source.page_title).replace(/的小红书直播间$/, ''), accountName: text(source.account_name) };
}

// Only select URLs actually observed on this page; never derive a CDN URL from a room ID.
export function xiaohongshuObservedSources(observation, now = Date.now()) {
  const page = validateXiaohongshuLiveUrl(observation?.page_url);
  if (new URL(page).hostname !== 'www.xiaohongshu.com' || !Array.isArray(observation?.media_urls)
    || observation.media_urls.length > 64) throw fail('INVALID_BROWSER_SOURCE');
  const room = new URL(page).pathname.split('/').pop();
  if (observation.status === 'not_live') {
    if (!freshObservation(observation.captured_at, now)) throw fail('INVALID_BROWSER_SOURCE');
    throw fail('XHS_NOT_LIVE');
  }
  const sources = [];
  for (const url of new Set(observation.media_urls)) {
    if (!xiaohongshuCandidate(url, now)) continue;
    const path = new URL(url).pathname;
    if (!new RegExp(`^/live/${room}(?:_[A-Za-z0-9_-]+)?\\.flv$`).test(path)) continue;
    const source = { page_url: page, captured_at: observation.captured_at, stream_url: url,
      page_title: typeof observation.page_title === 'string' ? observation.page_title.slice(0, 100) : '' };
    validateXiaohongshuBrowserSource(page, source, now);
    sources.push(source);
  }
  if (!sources.length) throw fail('XHS_STREAM_UNAVAILABLE');
  return sources;
}

export async function resolveXiaohongshuLive(value, { browserSource, fetchPage = fetchXiaohongshu, now = Date.now, timeoutMs = 15000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  const page = await resolveXiaohongshuPage(value, { fetchPage, deadline });
  if (browserSource) {
    return validateXiaohongshuBrowserSource(page, browserSource, now());
  }
  const room = new URL(page).pathname.split('/').pop();
  const response = await fetchPage(`https://live-room.xiaohongshu.com/api/sns/red/live/web/v1/room/current_room_info?room_id=${room}&source=web_live&client_type=1`, { timeoutMs: Math.max(1, deadline - Date.now()) });
  if (response.status !== 200) {
    const code = response.status === 401 || response.status === 403 ? 'XHS_AUTH_REQUIRED' : 'XHS_FETCH_FAILED';
    throw fail(code, `小红书匿名房间接口返回 HTTP ${response.status}。请从当前直播页获取本房间的浏览器候选，继续正式版质检。`);
  }
  let payload;
  try { payload = JSON.parse(response.body); } catch { throw fail('XHS_PAGE_UNAVAILABLE'); }
  const source = parseXiaohongshuRoomInfo(payload, { now: now() });
  if (source.status === 'not_live') return source;
  return { ...source, candidates: undefined, sourceMethod: 'anonymous' };
}

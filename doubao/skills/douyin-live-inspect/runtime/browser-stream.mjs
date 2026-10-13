import http from 'node:http';
import https from 'node:https';
import { lookup as dnsLookup } from 'node:dns/promises';
import { isIP } from 'node:net';
import { addressIsBlocked, candidateFrom, resolveDouyinLive, validateDouyinLiveUrl } from './douyin-live.mjs';

const FALLBACK_ERRORS = new Set(['DOUYIN_VERIFICATION_REQUIRED', 'DOUYIN_PAGE_UNAVAILABLE', 'DOUYIN_FLV_UNAVAILABLE', 'DOUYIN_FETCH_FAILED']);
const fail = (code, message) => Object.assign(new Error(message), { code, retryable: false });

function titleText(value) {
  return typeof value === 'string' ? value.trim().slice(0, 100) : '';
}

export function validateBrowserSource(input, now = Date.now()) {
  const source = input.browser_source;
  const invalid = () => fail('INVALID_BROWSER_SOURCE', '浏览器取流信息无效或已过期，请在原直播页面重新获取。');
  if (!source || typeof source !== 'object' || Array.isArray(source)) throw invalid();
  if (validateDouyinLiveUrl(source.page_url) !== validateDouyinLiveUrl(input.douyin_url)) throw invalid();
  if (!Number.isSafeInteger(source.captured_at) || now - source.captured_at > 120000 || source.captured_at > now + 5000) throw invalid();
  const candidate = candidateFrom(source.stream_url, {}, now);
  if (!candidate) throw invalid();
  const url = new URL(candidate.url);
  if (!url.hostname.endsWith('.douyincdn.com') || (url.port && !['80', '443'].includes(url.port))) throw invalid();
  const pageTitle = typeof source.page_title === 'string'
    ? source.page_title.trim().replace(/\s*[-_|｜]\s*抖音直播\s*$/, '').trim() : '';
  const roomName = titleText(source.room_title) || (pageTitle === '抖音直播' ? '' : titleText(pageTitle));
  return { status: 'ready', streamUrl: candidate.url, streamKey: candidate.streamKey, sourceMethod: 'browser',
    roomName, accountName: titleText(source.account_name) };
}

// Validate container structure and actual audio/video tags, not just an HTTP status or suffix.
export function hasFlvMedia(buffer) {
  if (buffer.length < 13 || buffer.toString('ascii', 0, 3) !== 'FLV' || buffer[3] !== 1) return false;
  const offset = buffer.readUInt32BE(5);
  if (offset < 9 || offset > 1024) return false;
  let cursor = offset + 4;
  let audio = false;
  let video = false;
  while (cursor + 11 <= buffer.length) {
    const type = buffer[cursor] & 31;
    const size = buffer.readUIntBE(cursor + 1, 3);
    const end = cursor + 11 + size;
    if (end + 4 > buffer.length) break;
    if (buffer.readUInt32BE(end) !== 11 + size) return false;
    if (size > 0 && type === 8) audio = true;
    if (size > 0 && type === 9) video = true;
    if (audio && video) return true;
    cursor = end + 4;
  }
  return false;
}

export async function probeBrowserStream(value, { lookup = dnsLookup, timeoutMs = 12000, requestFor = protocol => protocol === 'https:' ? https : http } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const unavailable = () => fail('BROWSER_STREAM_UNAVAILABLE', '浏览器取得的流地址暂时无法独立读取音视频，本次未创建任务。');
  const run = async () => {
    let url = new URL(value);
    for (let hop = 0; hop <= 3; hop++) {
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || (url.port && !['80', '443'].includes(url.port))) throw unavailable();
      const host = url.hostname.replace(/^\[|\]$/g, '');
      const addresses = isIP(host) ? [{ address: host, family: isIP(host) }] : await lookup(host, { all: true });
      if (!addresses.length || addresses.some(item => !isIP(item.address) || addressIsBlocked(item.address)) || controller.signal.aborted) throw unavailable();
      const result = await new Promise((resolve, reject) => {
        // Pin the verified DNS answer; never forward browser credentials to the CDN or redirects.
        const selected = addresses[0];
        const request = requestFor(url.protocol).get(url, {
          agent: false, signal: controller.signal,
          headers: { 'User-Agent': 'InspectStreamProbe/1.0' },
          lookup: (_host, options, callback) => options.all ? callback(null, [selected]) : callback(null, selected.address, selected.family),
        }, response => {
          if ([301,302,303,307,308].includes(response.statusCode)) {
            const location = response.headers.location;
            response.destroy();
            return location ? resolve({ location }) : reject(unavailable());
          }
          if (response.statusCode !== 200) { response.destroy(); reject(unavailable()); return; }
          let buffer = Buffer.alloc(0);
          response.on('data', chunk => {
            if (buffer.length + chunk.length > 1024 * 1024) { response.destroy(); reject(unavailable()); return; }
            buffer = Buffer.concat([buffer, chunk]);
            if (buffer.length >= 3 && buffer.toString('ascii',0,3) !== 'FLV') { response.destroy(); reject(unavailable()); return; }
            if (hasFlvMedia(buffer)) { resolve({ ready: true }); response.destroy(); }
          });
          response.on('end', () => reject(unavailable()));
          response.on('error', reject);
        });
        request.on('error', reject);
      });
      if (result.ready) return;
      url = new URL(result.location, url);
    }
    throw unavailable();
  };
  try {
    await Promise.race([run(), new Promise((_, reject) => controller.signal.addEventListener('abort', () => reject(unavailable()), { once: true }))]);
  } catch { throw unavailable(); }
  finally { clearTimeout(timer); }
}

export async function resolveTaskSource(input, { resolveAnonymous = resolveDouyinLive, probe = probeBrowserStream, now = Date.now } = {}) {
  if (['activity_id', 'ActivityId', 'room_id', 'roomId'].some(key => input[key] !== undefined)) {
    throw fail('INVALID_INPUT', '暂不支持直播间 ID，请提供抖音直播页面链接或 FLV 流地址。');
  }
  if (input.live_pull_url !== undefined) {
    if (input.douyin_url !== undefined || input.browser_source !== undefined) {
      throw fail('INVALID_INPUT', '请只提供一个直播来源。');
    }
    const invalid = () => fail('INVALID_INPUT', '请提供有效的 HTTP(S) FLV 流地址。');
    if (typeof input.live_pull_url !== 'string') throw invalid();
    const streamUrl = input.live_pull_url.trim();
    let url;
    try { url = new URL(streamUrl); } catch { throw invalid(); }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.hash
      || !/\.flv$/i.test(url.pathname) || (url.port && !['80', '443'].includes(url.port))) throw invalid();
    // Reuse the bounded media probe, including DNS and redirect validation. Preserve signed query bytes.
    try { await probe(streamUrl); }
    catch { throw fail('FLV_STREAM_UNAVAILABLE', 'FLV 流地址暂时无法独立读取音视频，请提供有效流地址。本次未创建任务。'); }
    return { status: 'ready', streamUrl, sourceMethod: 'direct_flv', roomName: '', accountName: '' };
  }
  try { return await resolveAnonymous(input.douyin_url); }
  catch (cause) {
    if (!FALLBACK_ERRORS.has(cause?.code) || !input.browser_source) throw cause;
  }
  const source = validateBrowserSource(input, now());
  try { await probe(source.streamUrl); }
  catch { throw fail('BROWSER_STREAM_UNAVAILABLE', '浏览器取得的流地址暂时无法独立读取音视频，本次未创建任务。'); }
  return source;
}

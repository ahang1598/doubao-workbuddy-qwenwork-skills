// Execute in the host's current live page. Authentication stays inside that browser.
(async () => {
  const page = new URL(location.href);
  const match = /^\/([1-9][0-9]*)\/?$/.exec(page.pathname);
  if (page.protocol !== 'https:' || page.hostname !== 'live.bilibili.com' || !match) throw new Error('INVALID_BROWSER_SOURCE');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const get = async path => {
      const response = await fetch('https://api.live.bilibili.com' + path, { credentials: 'include', signal: controller.signal });
      if (!response.ok) throw new Error('BILI_PAGE_UNAVAILABLE');
      const body = await response.json();
      if (body.code !== 0 || !body.data) throw new Error('BILI_PAGE_UNAVAILABLE');
      return body.data;
    };
    const observation = () => ({ page_url: `https://live.bilibili.com/${match[1]}`,
      captured_at: Date.now(), page_title: document.title.slice(0, 100) });
    const offline = data => {
      if (!/^[1-9][0-9]*$/.test(String(data.room_id)) || data.is_hidden || data.is_locked || data.encrypted) {
        throw new Error('BILI_ROOM_UNAVAILABLE');
      }
      if (data.live_status === 2) throw new Error('BILI_REPLAY_UNSUPPORTED');
      if (data.live_status === 0) return true;
      if (data.live_status !== 1) throw new Error('BILI_LIVE_STATE_UNKNOWN');
      return false;
    };
    const room = await get(`/room/v1/Room/room_init?id=${match[1]}`);
    if (offline(room)) return {...observation(), status: 'not_live', media_urls: []};
    const info = await get(`/xlive/web-room/v2/index/getRoomPlayInfo?room_id=${room.room_id}&protocol=0&format=0&codec=0&qn=250&platform=web&ptype=8`);
    if (String(info.room_id) !== String(room.room_id)) throw new Error('BILI_ROOM_UNAVAILABLE');
    if (offline(info)) return {...observation(), status: 'not_live', media_urls: []};
    const urls = new Set();
    const list = value => Array.isArray(value) ? value : [];
    for (const stream of list(info.playurl_info?.playurl?.stream)) {
      if (stream?.protocol_name !== 'http_stream') continue;
      for (const format of list(stream.format)) {
        if (format?.format_name !== 'flv') continue;
        for (const codec of list(format.codec)) {
          if (codec?.codec_name !== 'avc' || codec.drm || typeof codec.base_url !== 'string' || !codec.base_url.startsWith('/')) continue;
          for (const item of list(codec.url_info)) {
            if (typeof item?.host !== 'string' || typeof item.extra !== 'string') continue;
            const value = item.host + codec.base_url + item.extra;
            if (value.length > 8192 || /[\u0000-\u0020]/.test(value)) continue;
            try {
              const url = new URL(value);
              if (['https:', 'http:'].includes(url.protocol) && !url.username && !url.password && !url.hash
                && (!url.port || ['80', '443'].includes(url.port)) && url.hostname.endsWith('.bilivideo.com')
                && /\.flv$/i.test(url.pathname) && urls.size < 64) urls.add(value);
            } catch { /* Ignore malformed candidates without exposing their signed URLs. */ }
          }
        }
      }
    }
    if (!urls.size) throw new Error('BILI_STREAM_UNAVAILABLE');
    return {...observation(), media_urls: [...urls]};
  } catch (error) {
    const allowed = ['INVALID_BROWSER_SOURCE', 'BILI_PAGE_UNAVAILABLE', 'BILI_ROOM_UNAVAILABLE', 'BILI_STREAM_UNAVAILABLE', 'BILI_REPLAY_UNSUPPORTED', 'BILI_LIVE_STATE_UNKNOWN'];
    throw new Error(allowed.includes(error.message) ? error.message : 'BILI_FETCH_FAILED');
  } finally { clearTimeout(timer); }
})()

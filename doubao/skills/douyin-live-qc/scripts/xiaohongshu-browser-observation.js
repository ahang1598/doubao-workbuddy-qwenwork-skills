// Run in the host browser's current page, never in Node or a separate browser.
(() => {
  const page = new URL(location.href);
  const room = /^\/livestream\/(?:dynpath[A-Za-z0-9]+\/)?([0-9]+)\/?$/.exec(page.pathname);
  if (page.protocol !== 'https:' || page.hostname !== 'www.xiaohongshu.com' || !room) {
    throw new Error('INVALID_BROWSER_SOURCE');
  }
  const observation = {page_url: `https://www.xiaohongshu.com/livestream/${room[1]}`,
    captured_at: Date.now(), page_title: document.title.slice(0, 100)};
  // Read rendered room/player notices only. Chat, titles and stale resource URLs are not room state.
  const ended = /^(?:直播已结束|本场直播已结束|直播已停播|主播已下播|已下播|已停播)[。！!]?$/;
  try {
    // An ended recommendation can share the page with the active room.
    const playerSelector = '[class*="player" i], [data-live-player]';
    const roomRoot = document.querySelector(`[data-room-id="${room[1]}"]`);
    const root = roomRoot || document.querySelector('main, [role="main"]');
    const players = root?.matches(playerSelector) ? [root] : [...(root?.querySelectorAll(playerSelector) || [])];
    const belongsToRoom = node => {
      const owner = node.closest('[data-room-id]');
      return (!owner || owner.getAttribute('data-room-id') === room[1]) &&
        !node.closest('a, aside, [class*="recommend" i]') && node.getClientRects().length;
    };
    const primary = players.filter(belongsToRoom);
    const outer = primary.filter(node => !primary.some(other => other !== node && other.contains(node)));
    const notices = outer.length === 1 ? outer[0].querySelectorAll('[class*="end" i], [class*="status" i], [class*="mask" i], [role="status"], [data-live-status]') : [];
    for (const notice of notices) {
      if (!belongsToRoom(notice) || getComputedStyle(notice).visibility !== 'visible') continue;
      if ((notice.innerText || '').split(/\r?\n/).some(line => ended.test(line.trim()))) {
        return {...observation, status: 'not_live', media_urls: []};
      }
    }
  } catch { /* DOM inspection may be unavailable. Continue with source extraction. */ }
  const urls = new Set();
  const add = value => {
    if (typeof value !== 'string' || value.length > 8192 || urls.size >= 64) return;
    const normalized = value.replace(/\\u0026/gi, '&').replace(/\\\//g, '/').replace(/\\+$/, '');
    try {
      const u = new URL(normalized);
      if (!['https:', 'http:'].includes(u.protocol) || u.username || u.password || u.hash
          || u.searchParams.getAll('only_audio').includes('1')
          || !u.hostname.endsWith('.xhscdn.com') || (u.port && !['80', '443'].includes(u.port))
          || !new RegExp(`^/live/${room[1]}(?:_[A-Za-z0-9_-]+)?\\.flv$`).test(u.pathname)) return;
      urls.add(normalized);
    } catch { /* Ignore non-media resources. */ }
  };
  // Each observation path must survive the other being unavailable in the host.
  try {
    for (const entry of performance.getEntriesByType('resource')) add(entry.name);
  } catch { /* Continue with page-provided data. */ }
  try {
    for (const script of document.querySelectorAll('script')) {
      const text = script.textContent || '';
      if (!text.includes('.flv')) continue;
      const decoded = text.replace(/\\\//g, '/');
      for (const value of decoded.match(/https?:\/\/[^\s"'<>]+\.flv[^\s"'<>]*/g) || []) add(value);
    }
  } catch { /* Keep resource candidates when DOM access is unavailable. */ }
  return {...observation, media_urls: [...urls]};
})()

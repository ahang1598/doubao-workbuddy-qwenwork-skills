import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { writeFile } from 'node:fs/promises';
import { xiaohongshuObservedSources, validateXiaohongshuBrowserSource } from '../runtime/xiaohongshu-live.mjs';
import { probeBrowserStream } from '../runtime/browser-stream.mjs';

// Non-page work only: the host browser supplies a minimal observation over stdin.
export async function prepareBrowserSource({
  observedSources = xiaohongshuObservedSources,
  validateSource = validateXiaohongshuBrowserSource,
  sourceType = 'xiaohongshu',
  unavailableCode = 'XHS_STREAM_UNAVAILABLE',
} = {}) {
  try {
    if (process.argv.length !== 4 || process.argv[2] !== '--output') throw { code: 'INVALID_INPUT' };
    let input = '';
    for await (const chunk of process.stdin) {
      input += chunk;
      if (Buffer.byteLength(input) > 65536) throw { code: 'INVALID_INPUT' };
    }
    const observation = JSON.parse(input);
    const sources = observedSources(observation);
    let selected = sources[0];
    if (sourceType === 'bilibili') {
      selected = undefined;
      const deadline = Date.now() + 15000;
      for (const source of sources) {
        const remaining = deadline - Date.now();
        if (remaining <= 0) break;
        try {
          await probeBrowserStream(source.stream_url, { timeoutMs: Math.min(5000, remaining) });
          selected = source;
          break;
        } catch { /* Try another observed candidate within the same budget. */ }
      }
    }
    if (!selected) throw { code: unavailableCode };
    validateSource(selected.page_url, selected);
    await writeFile(process.argv[3], JSON.stringify({ browser_source: selected }), { mode: 0o600, flag: 'wx' });
    console.log(JSON.stringify({ ok: true, source_type: sourceType, ...(sourceType === 'bilibili' && { media_probe: 'audio_video_tags' }), next_action: 'submit-browser-source' }));
  } catch (error) {
    const allowed = ['INVALID_INPUT', 'INVALID_BROWSER_SOURCE', 'XHS_NOT_LIVE', 'BILI_NOT_LIVE', unavailableCode];
    const code = error.code === 'EEXIST' ? 'INVALID_INPUT' : allowed.includes(error.code) ? error.code : 'INVALID_INPUT';
    console.log(JSON.stringify({ ok: false, ...(code === 'BILI_NOT_LIVE' ? {browser_source: error.browser_source} : {}), error: { code,
      message: code === 'BILI_NOT_LIVE' ? '当前 B 站直播已结束。' : code === 'XHS_NOT_LIVE' ? '当前小红书直播已结束。' : '未生成补流文件；检查当前房间、观测时间、媒体可读性及输出文件是否已存在。' } }));
    process.exitCode = 1;
  }
}

if (process.argv[1] && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1])) {
  await prepareBrowserSource();
}

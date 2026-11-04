import { writeFile } from 'node:fs/promises';
import { xiaohongshuObservedSources, validateXiaohongshuBrowserSource } from '../runtime/xiaohongshu-live.mjs';
import { probeBrowserStream } from '../runtime/browser-stream.mjs';

// Non-page work only: the host browser supplies a minimal observation over stdin.
try {
  if (process.argv.length !== 4 || process.argv[2] !== '--output') throw { code: 'INVALID_INPUT' };
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk;
    if (Buffer.byteLength(input) > 65536) throw { code: 'INVALID_INPUT' };
  }
  const sources = xiaohongshuObservedSources(JSON.parse(input));
  const deadline = Date.now() + 15000;
  let selected;
  for (const source of sources) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    try {
      await probeBrowserStream(source.stream_url, { timeoutMs: Math.min(5000, remaining) });
      selected = source;
      break;
    } catch { /* Try another observed candidate within the same budget. */ }
  }
  if (!selected) throw { code: 'XHS_STREAM_UNAVAILABLE' };
  validateXiaohongshuBrowserSource(selected.page_url, selected);
  await writeFile(process.argv[3], JSON.stringify({ browser_source: selected }), { mode: 0o600, flag: 'wx' });
  console.log(JSON.stringify({ ok: true, source_type: 'xiaohongshu', media_probe: 'audio_video_tags', next_action: 'submit-browser-source' }));
} catch (error) {
  const allowed = ['INVALID_INPUT', 'INVALID_BROWSER_SOURCE', 'XHS_STREAM_UNAVAILABLE'];
  const code = error.code === 'EEXIST' ? 'INVALID_INPUT' : allowed.includes(error.code) ? error.code : 'INVALID_INPUT';
  console.log(JSON.stringify({ ok: false, error: { code,
    message: '未生成补流文件；检查当前房间、观测时间、媒体可读性及输出文件是否已存在。' } }));
  process.exitCode = 1;
}

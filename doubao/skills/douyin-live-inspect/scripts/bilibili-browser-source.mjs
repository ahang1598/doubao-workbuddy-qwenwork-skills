import { bilibiliObservedSources, validateBilibiliBrowserSource } from '../runtime/bilibili-live.mjs';
import { prepareBrowserSource } from './xiaohongshu-browser-source.mjs';

await prepareBrowserSource({
  observedSources: bilibiliObservedSources,
  validateSource: validateBilibiliBrowserSource,
  sourceType: 'bilibili',
  unavailableCode: 'BILI_STREAM_UNAVAILABLE',
});

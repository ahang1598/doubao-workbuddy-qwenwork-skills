const CONTENT_MAP_KIT_CDN_PREFIX =
  'https://lf3-static.bytednsdoc.com/obj/eden-cn/ihswht/ljhwZthlaukjlkulzlp/doubao_work_visualization/';
const LEGACY_CDN_PREFIX =
  'https://lf3-static.bytednsdoc.com/obj/eden-cn/ihswht/ljhwZthlaukjlkulzlp/ai_poi_social/';
const SHA256_PATTERN = /^[a-f0-9]{64}$/;

export function resolveContentMapKitAsset(lock, options = {}) {
  const configured = lock.runtimeAssets?.contentMapKit;
  const overrideUrl = options.url || process.env.MAP_CREATE_CONTENT_MAP_KIT_URL;
  const overrideSha256 =
    options.sha256 || process.env.MAP_CREATE_CONTENT_MAP_KIT_SHA256;
  const asset = overrideUrl
    ? { url: overrideUrl, sha256: overrideSha256 }
    : configured;

  if (!asset || typeof asset.url !== 'string' || !asset.url.trim())
    throw new Error('vendor.lock.json 缺少 Content Map Kit CDN URL');
  if (!SHA256_PATTERN.test(asset.sha256 || ''))
    throw new Error('Content Map Kit CDN 资源缺少完整 SHA-256');

  const url = new URL(asset.url);
  const isLocalOverride =
    Boolean(overrideUrl) &&
    url.protocol === 'http:' &&
    ['127.0.0.1', 'localhost'].includes(url.hostname);
  if (url.protocol !== 'https:' && !isLocalOverride)
    throw new Error('Content Map Kit CDN URL 必须使用 HTTPS');
  if (url.username || url.password || url.search || url.hash)
    throw new Error('Content Map Kit CDN URL 不得包含凭据、查询参数或片段');
  const isPublishedAsset = url.href.startsWith(CONTENT_MAP_KIT_CDN_PREFIX);
  if (
    !overrideUrl &&
    !isPublishedAsset &&
    !url.href.startsWith(LEGACY_CDN_PREFIX)
  )
    throw new Error('Content Map Kit CDN URL 不属于受控发布目录');

  const shortHash = asset.sha256.slice(0, 12);
  if (isPublishedAsset) {
    const objectName = url.href.slice(CONTENT_MAP_KIT_CDN_PREFIX.length);
    if (!/^\d{8}T\d{6}Z-[a-f0-9]{32}\.js$/.test(objectName))
      throw new Error('Content Map Kit CDN 文件名不符合发布接口对象格式');
  } else if (!url.pathname.endsWith(`/browser.${shortHash}.js`))
    throw new Error('Content Map Kit CDN 文件名与 SHA-256 不一致');

  return {
    url: url.href,
    sha256: asset.sha256,
    integrity: `sha256-${Buffer.from(asset.sha256, 'hex').toString('base64')}`,
    source: overrideUrl ? 'override' : 'vendor-lock',
  };
}

export { CONTENT_MAP_KIT_CDN_PREFIX };

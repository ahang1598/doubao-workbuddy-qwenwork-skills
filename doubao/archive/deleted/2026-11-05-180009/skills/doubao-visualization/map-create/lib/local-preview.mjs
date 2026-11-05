import { createHash } from 'node:crypto';

export function embedLocalPreview(html, sources) {
  const assets = Object.fromEntries(
    Object.entries(sources).filter(([key]) => key !== 'bootstrap')
      .map(([key, [, text]]) => [key, Buffer.from(text).toString('base64')]),
  );
  const bootstrap = sources.bootstrap[1].replaceAll('</script', '<\\/script');
  const replacement = `<script id="map-create-local-assets" type="application/json">${JSON.stringify(assets)}</script>\n<script id="map-create-local-bootstrap">${bootstrap}</script>`;
  const pattern = /<script src="[^"]+" integrity="[^"]+" crossorigin="anonymous" async onerror="[^"]+"><\/script>/;
  if (!pattern.test(html)) throw new Error('LOCAL_PREVIEW_BOOTSTRAP_MISSING');
  return html.replace(pattern, () => replacement);
}

export function readLocalPreview(html, manifest) {
  const match = html.match(/<script id="map-create-local-assets" type="application\/json">([\s\S]*?)<\/script>/);
  if (!match) return null;
  const embedded = JSON.parse(match[1]);
  const bootstrap = html.match(/<script id="map-create-local-bootstrap">([\s\S]*?)<\/script>/);
  if (!bootstrap) throw new Error('LOCAL_PREVIEW_BOOTSTRAP_MISSING');
  const assets = {
    ...Object.fromEntries(['data', 'style', 'runtime'].map(key => [
      key, Buffer.from(embedded[key] || '', 'base64'),
    ])),
    bootstrap: Buffer.from(bootstrap[1].replaceAll('<\\/script', '</script')),
  };
  for (const [key, bytes] of Object.entries(assets))
    if (createHash('sha256').update(bytes).digest('hex') !== manifest.assets[key]?.sha256)
      throw new Error('LOCAL_PREVIEW_HASH_MISMATCH:' + key);
  return assets;
}

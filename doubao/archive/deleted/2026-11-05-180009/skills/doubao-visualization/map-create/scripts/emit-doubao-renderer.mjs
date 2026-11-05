import { assertDeliveryPolicy } from '../acceptance/startup-check.mjs';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { digest, parseManifest, readArtifact } from '../lib/cdn-assets.mjs';
import { args, readJson, safeError } from '../lib/cli-utils.mjs';
import { wrapCheckedArtifact } from '../lib/delivery-contract.mjs';

const options = args();
try {
  if (!options.html || !options.check)
    throw new Error(
      '用法：node emit-doubao-renderer.mjs --html map.html --check check-report.json',
    );
  const html = await readFile(resolve(options.html), 'utf8');
  if (/\b(?:localhost|127\.0\.0\.1)\b|\bfile:\/\//i.test(html))
    throw new Error('Renderer HTML 包含本地资源地址，不能交付');
  const report = await readJson(options.check);
  if (report.htmlSha256 !== digest(html))
    throw new Error('受检 HTML 与待交付 HTML 的 SHA-256 不一致');
  assertDeliveryPolicy(report);
  if (
    Object.values(parseManifest(html).assets).some(
      (asset) => !asset.url.startsWith('https://'),
    )
  )
    throw new Error('资源清单未发布');
  const artifact = await readArtifact(html, resolve(options.html));
  process.stdout.write(wrapCheckedArtifact(html, artifact, report));
} catch (error) {
  process.stderr.write(
    JSON.stringify({ status: 'failed', error: safeError(error) }) + '\n',
  );
  process.exitCode = 1;
}

import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import { compilerIdentity } from '../lib/engine.mjs';

const hashFiles = files => {
  const digest = createHash('sha256');
  for (const file of files)
    digest.update(file).update(readFileSync(new URL(file, import.meta.url)));
  return digest.digest('hex');
};
export function implementationIdentity() {
  return createHash('sha256')
    .update(checkerIdentity())
    .update(
      hashFiles([
        ...readdirSync(new URL('../runtime', import.meta.url))
          .filter(
            name =>
              /\.(m?js|css|template)$/.test(name) && !name.includes('.local.'),
          )
          .sort()
          .map(name => `../runtime/${name}`),
        '../vendor.lock.json',
        '../lib/map-workflow.mjs',
        '../lib/map-request.mjs',
        '../lib/map-task.mjs',
        '../lib/map-task-spec.mjs',
        '../lib/map-road-trip.mjs',
      ]),
    )
    .digest('hex');
}
export function checkerIdentity() {
  const checker = hashFiles([
    '../scripts/check-html.mjs',
    './check-policy.mjs',
    './startup-check.mjs',
    './check-navigation.mjs',
    './acceptance-identity.mjs',
    './rendered-elements.mjs',
    './ui-sections.mjs',
    './visual-readiness.mjs',
    './resource-readiness.mjs',
    './selection-shapes.mjs',
    './route-symbols.mjs',
    './polygon-evidence.mjs',
    './source-evidence.mjs',
    './elevated-geometry-evidence.mjs',
    './screen-geometry-evidence.mjs',
    './product-journeys.mjs',
    './region-journeys.mjs',
    './edge-navigation-journeys.mjs',
    './blank-target.mjs',
    './failure-diagnosis.mjs',
    '../lib/cdn-assets.mjs',
    '../lib/local-preview.mjs',
    '../lib/cli-utils.mjs',
    '../lib/delivery-contract.mjs',
    '../lib/engine.mjs',
    '../lib/load-engine.mjs',
    '../assets/engine/engine.lock.json',
    '../runtime/derive-source.mjs',
  ]);
  return createHash('sha256')
    .update(checker)
    .update(compilerIdentity())
    .digest('hex');
}

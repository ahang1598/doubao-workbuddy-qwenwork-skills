import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { readEngineArtifact, unpackEngineArtifact } from './load-engine.mjs';

const lockUrl = new URL('../assets/engine/engine.lock.json', import.meta.url);
const { artifact } = readEngineArtifact(lockUrl);
for (const [filename, contents] of Object.entries(artifact.files)) {
  if (!/^(contracts\/.*\.schema\.json|themes\/.*\.json)$/.test(filename))
    continue;
  if (
    !readFileSync(new URL('../' + filename, import.meta.url)).equals(
      Buffer.from(contents, 'base64'),
    )
  )
    throw new Error(
      `ENGINE_ARTIFACT_INVALID: 生成的模型参考文件与引擎不一致：${filename}`,
    );
}
const engine = unpackEngineArtifact(lockUrl);
export const engineRoot = engine.root;
const compilation = await import(engine.moduleUrl('compiler/index.mjs'));
export const { compileMap } = compilation;
export const { recommendOverview, withReadingRepresentatives } = compilation;
export function loadComponentCatalog(filename) {
  return compilation.loadComponentCatalog(
    filename ||
      fileURLToPath(
        new URL(
          '../assets/vendor/content-map-kit.catalog.json',
          import.meta.url,
        ),
      ),
  );
}
export const {
  CompileFailure,
  diagnostic,
  failOnErrors,
  resolveComponentNodes,
  validateOrganization,
  compilerIdentity,
  normalizeInputs,
  preflightInputs,
  validateProductGraph,
  resolveRuntimeRequirements,
  resolveViews,
  validateContract,
  verifyContractArtifacts,
  validateSemantics,
  protocolHash,
  validateTransform,
} = await import(engine.moduleUrl('validation.mjs'));
export const { prepareGraph, checkRuntimeCompatibility } = await import(
  engine.moduleUrl('runtime.mjs')
);

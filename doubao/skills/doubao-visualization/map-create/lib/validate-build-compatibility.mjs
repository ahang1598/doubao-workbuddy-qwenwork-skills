import { isDeepStrictEqual } from 'node:util';
import {
  diagnostic,
  failOnErrors,
  prepareGraph,
  resolveRuntimeRequirements,
} from './engine.mjs';

export function validateBuildCompatibility(graph, catalog, lock, assetSource) {
  const errors = [];
  const reject = (code, message) =>
    errors.push(diagnostic('error', code, 'componentRuntime', message));
  if (!catalog.sha256 || graph.trace?.componentCatalogSha256 !== catalog.sha256)
    reject(
      'BUILD_CATALOG_MISMATCH',
      'Graph 与构建 Catalog 的 SHA-256 不一致；请用同一 Catalog 重新编译',
    );
  if (graph.trace?.componentCatalogVersion !== catalog.version)
    reject('BUILD_PACKAGE_MISMATCH', 'Graph 与构建 Catalog 的版本不一致');
  if (assetSource === 'vendor-lock') {
    if (
      lock.packages?.[catalog.sourcePackage.name] !==
      catalog.sourcePackage.version
    )
      reject('BUILD_PACKAGE_MISMATCH', 'Catalog 与锁定组件资源的版本不一致');
    if (
      lock.files?.['assets/vendor/content-map-kit.catalog.json'] !==
      catalog.sha256
    )
      reject('BUILD_CATALOG_MISMATCH', 'Catalog 不属于当前锁定的组件资源');
  }
  const expected = resolveRuntimeRequirements(prepareGraph(graph), catalog);
  if (!isDeepStrictEqual(graph.runtimeRequirements, expected))
    reject(
      'BUILD_REQUIREMENTS_MISMATCH',
      'Graph 的组件能力要求与实际使用的能力不一致；请重新编译',
    );
  failOnErrors(errors);
  return {
    status: 'compatible',
    catalogSha256: catalog.sha256,
    package: catalog.sourcePackage,
    // SRI pins override bytes, but only the browser can inspect their exports.
    runtimeCheck: 'required-before-map-init',
  };
}

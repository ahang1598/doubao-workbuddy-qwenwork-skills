import { args, readJson, safeError, writeJson } from '../lib/cli-utils.mjs';
import { compileMap, loadComponentCatalog } from '../lib/engine.mjs';

const options = args();
const startedAt = performance.now();
const timings = {};
let report;
try {
  if (!options.spec || !options.plan || !options.out)
    throw new Error(
      '用法：node compile-map.mjs --spec canonical-map-spec.json --plan presentation-plan.json --out render-graph.json [--report report.json]',
    );
  if (
    ['audit-revision2', 'target-revision', 'decisions'].some(key =>
      Object.hasOwn(options, key),
    )
  )
    throw new Error('旧协议迁移选项已移除；仅支持显式 revision 3 输入');
  const [spec, plan, catalog] = await Promise.all([
    readJson(options.spec),
    readJson(options.plan),
    loadComponentCatalog(options.catalog),
  ]);
  timings.inputMs = Math.round(performance.now() - startedAt);
  const compileStartedAt = performance.now();
  const result = compileMap(spec, plan, catalog, {
    traceId: options['trace-id'],
  });
  report = result.report;
  timings.compileMs = Math.round(performance.now() - compileStartedAt);
  await writeJson(options.out, result.graph);
  report.timings = {
    ...timings,
    totalMs: Math.round(performance.now() - startedAt),
  };
  if (options.report) await writeJson(options.report, report);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} catch (error) {
  const detail = safeError(error);
  report = {
    status: 'failed',
    timings: { ...timings, totalMs: Math.round(performance.now() - startedAt) },
    error: detail,
    diagnostics: detail.diagnostics,
    finishedAt: new Date().toISOString(),
  };
  if (options.report) await writeJson(options.report, report);
  process.stderr.write(`${JSON.stringify(report, null, 2)}\n`);
  process.exitCode = 1;
}

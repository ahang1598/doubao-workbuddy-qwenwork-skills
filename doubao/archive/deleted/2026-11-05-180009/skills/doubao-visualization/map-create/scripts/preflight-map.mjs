import { basename, resolve } from 'node:path';
import { args, readJson, safeError, writeJson } from '../lib/cli-utils.mjs';
import {
  compileMap,
  loadComponentCatalog,
  preflightInputs,
} from '../lib/engine.mjs';

const options = args();
let report;
try {
  if (
    !options.spec ||
    !options.plan ||
    !options.report ||
    Object.keys(options).some(key => !['spec', 'plan', 'report'].includes(key))
  )
    throw new Error(
      '仅支持 --spec --plan --report；离线预检不查询工具、不构建、不验收、不发布',
    );
  if (
    [options.spec, options.plan].some(
      file => resolve(file) === resolve(options.report),
    ) ||
    [
      'workflow-report.json',
      'compiler-report.json',
      'check-report.json',
      'render-graph.json',
      'map.html',
      'delivery.renderer.md',
    ].includes(basename(options.report))
  ) {
    delete options.report;
    throw new Error(
      '预检报告不能覆盖输入或工作流产物，请使用 preflight-report.json',
    );
  }
  const [spec, plan] = await Promise.all([
    readJson(options.spec),
    readJson(options.plan),
  ]);
  report = preflightInputs(spec, plan);
  report.deliveryEligible = false;
  report.compile = {
    status: 'not-run',
    dependsOn: report.checks.map(check => check.id),
  };
  if (report.status === 'passed') {
    try {
      compileMap(spec, plan, await loadComponentCatalog());
      report.compile.status = 'passed';
    } catch (error) {
      report.status = 'failed';
      report.compile = { status: 'failed', error: safeError(error) };
      report.diagnostics.push(...(error.diagnostics || []));
    }
  }
} catch (error) {
  report = {
    status: 'failed',
    deliveryEligible: false,
    error: safeError(error),
  };
}
if (options.report) await writeJson(options.report, report);
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
if (report.status !== 'passed') process.exitCode = 1;

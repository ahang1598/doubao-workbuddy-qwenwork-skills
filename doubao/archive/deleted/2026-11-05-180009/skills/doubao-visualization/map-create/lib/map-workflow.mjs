import { execFile } from 'node:child_process';
import { mkdir, open, readFile, rm } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { implementationIdentity } from '../acceptance/acceptance-identity.mjs';
import { diagnoseFailure } from '../acceptance/failure-diagnosis.mjs';
import { digest, readArtifact, uploadAsset } from './cdn-assets.mjs';
import { readJson, safeError, writeJson, writeText } from './cli-utils.mjs';
import { compilerIdentity } from './engine.mjs';
import { resolveMapRequest } from './map-request.mjs';
import { readTelemetryTask, bestEffortTelemetry } from './task-telemetry.mjs';
import { dependencyReporter } from './dependency-telemetry.mjs';
import {
  assertRepairAllowed,
  recordRepairFailure,
  restoreRepairBudget,
} from './repair-budget.mjs';

const execute = promisify(execFile);
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export async function runMapWorkflow(
  input,
  { resolveRequest = resolveMapRequest } = {},
) {
  const options = { ...input };
  if (!options.out || typeof options.out !== 'string')
    throw new Error('需要 --out HTML 输出路径');
  if ((options.publish === true) === (options.local === true))
    throw new Error('必须选择 --publish 或 --local，不能同时使用');
  if (
    options.request
      ? options.spec || options.plan
      : !options.spec || !options.plan
  )
    throw new Error('使用 --request 或配对的 --spec/--plan，不能混用');
  const allowed = new Set([
    'request',
    'spec',
    'plan',
    'out',
    'publish',
    'local',
    'height',
    'height-mode',
    'telemetry-task',
  ]);
  if (Object.keys(options).some(key => !allowed.has(key)))
    throw new Error('存在不支持的工作流参数');
  const started = performance.now();
  const directory = dirname(resolve(options.out || 'build/map.html'));
  const stateFile = resolve(directory, 'workflow-report.json');
  await mkdir(directory, { recursive: true });
  const lockFile = resolve(directory, '.map-workflow.lock');
  const lock = await open(lockFile, 'wx').catch(error => {
    if (error.code === 'EEXIST')
      throw new Error('WORKFLOW_BUSY: 此输出目录已有任务运行');
    throw error;
  });
  const state = {
    status: 'running',
    phase: 'input',
    attempt: 1,
    stages: [],
    activeElapsedMs: 0,
  };
  const telemetry = options['telemetry-task'] ? await bestEffortTelemetry(() => readTelemetryTask(options['telemetry-task'])) : null;
  if (telemetry) state.traceId = telemetry.trace_id;
  const onTelemetry = dependencyReporter(options['telemetry-task']);
  try {
    const previous = await readJson(stateFile).catch(error => {
      if (error.code === 'ENOENT') return null;
      throw error;
    });
    if (previous)
      await writeJson(
        resolve(
          directory,
          'history',
          `workflow-${previous.attempt}-${Date.now()}.json`,
        ),
        previous,
      );
    state.attempt =
      previous?.status === 'pending'
        ? previous.attempt
        : previous?.status === 'failed'
          ? previous.attempt + 1
          : 1;
    state.repairBudget = restoreRepairBudget(previous);
    state.inputIdentity = digest(
      JSON.stringify(
        await Promise.all(
          [options.request || options.spec, options.plan]
            .filter(Boolean)
            .map(async file => [
              file,
              await readFile(file, 'utf8').catch(error => {
                if (error.code === 'ENOENT') return null;
                throw error;
              }),
            ]),
        ),
      ),
    );
    state.activeElapsedMs = ['pending', 'failed'].includes(previous?.status)
      ? previous.activeElapsedMs || 0
      : 0;
    if (state.activeElapsedMs >= 600000)
      throw new Error('TASK_TIMEOUT: 等待与处理总预算已耗尽');
    state.implementationIdentity = implementationIdentity();
    if (
      previous?.status === 'failed' &&
      (previous.diagnosis?.owner === 'maintenance' ||
        previous.maintenanceBlocked) &&
      previous.implementationIdentity === state.implementationIdentity
    ) {
      state.maintenanceBlocked = true;
      throw new Error('MAINTENANCE_REQUIRED: 实现未变化，停止修改输入重试');
    }
    if (options.request) {
      state.phase = 'prepare-input';
      assertRepairAllowed(state.repairBudget, state.phase, state.inputIdentity);
      await writeJson(stateFile, state);
      const begin = performance.now();
      const inputs = await resolveRequest(
        options.request,
        resolve(directory, 'input'),
        {
          onTelemetry,
          onPlaces: async places => {
            state.places = places;
            await writeJson(stateFile, state);
          },
        },
      );
      Object.assign(options, inputs);
      state.stages.push({
        phase: 'prepare-input',
        status: 'passed',
        elapsedMs: Math.round(performance.now() - begin),
      });
    }
    state.inputIdentity = digest(
      JSON.stringify({
        spec: digest(await readFile(options.spec)),
        plan: digest(await readFile(options.plan)),
        compiler: compilerIdentity(),
        vendor: digest(await readFile(resolve(root, 'vendor.lock.json'))),
      }),
    );
    state.compilerIdentity = compilerIdentity();
    state.implementationIdentity = implementationIdentity();
    const run = async (phase, script, argumentsList) => {
      state.phase = phase;
      assertRepairAllowed(state.repairBudget, phase, state.inputIdentity);
      await writeJson(stateFile, state);
      const begin = performance.now();
      const remaining = 600000 - state.activeElapsedMs - (begin - started);
      if (remaining <= 0) throw new Error('TASK_TIMEOUT');
      try {
        const result = await execute(
          process.execPath,
          [resolve(root, script), ...argumentsList],
          {
            timeout: Math.max(1, Math.floor(remaining)),
            maxBuffer: 16 * 1024 * 1024,
          },
        );
        state.stages.push({
          phase,
          elapsedMs: Math.round(performance.now() - begin),
          status: 'passed',
        });
        return result.stdout;
      } catch (error) {
        state.stages.push({
          phase,
          elapsedMs: Math.round(performance.now() - begin),
          status: 'failed',
        });
        throw error;
      }
    };
    const graph = resolve(directory, 'render-graph.json');
    const compiled = resolve(directory, 'compiler-report.json');
    const checked = resolve(directory, 'check-report.json');
    for (const [name, file] of [
      ['compiler', compiled],
      ['check', checked],
    ]) {
      const saved = await readJson(file).catch(error => {
        if (error.code === 'ENOENT') return null;
        throw error;
      });
      if (saved)
        await writeJson(
          resolve(
            directory,
            'history',
            `${name}-${state.attempt - 1}-${Date.now()}.json`,
          ),
          saved,
        );
    }
    await run('compile', 'scripts/compile-map.mjs', [
      '--spec',
      options.spec,
      '--plan',
      options.plan,
      '--out',
      graph,
      '--report',
      compiled,
      ...(telemetry ? ['--trace-id', telemetry.trace_id] : []),
    ]);
    await run(
      options.local ? 'build-local' : 'publish-resources',
      'scripts/build-html.mjs',
      [
        '--graph',
        graph,
        '--out',
        options.out,
        '--report',
        resolve(directory, 'build-report.json'),
        ...(options.publish ? ['--publish'] : []),
        ...(options.local ? ['--standalone'] : []),
        ...(options['telemetry-task'] ? ['--telemetry-task', options['telemetry-task']] : []),
        ...(options.height ? ['--height', String(options.height)] : []),
        ...(options['height-mode']
          ? ['--height-mode', options['height-mode']]
          : []),
      ],
    );
    await run('accept', 'scripts/check-html.mjs', [
      '--html',
      options.out,
      '--spec',
      options.spec,
      '--plan',
      options.plan,
      '--compiler-report',
      compiled,
      '--mode',
      'startup',
      '--report',
      checked,
    ]);
    const artifact = await readArtifact(
      await readFile(options.out, 'utf8'),
      options.out,
    );
    state.manifestSha256 = artifact.manifestSha256;
    await run('trace', 'scripts/write-trace.mjs', [
      '--dir',
      resolve(directory, 'trace'),
      '--spec',
      options.spec,
      '--plan',
      options.plan,
      '--graph',
      graph,
      '--compiler-report',
      compiled,
      '--html',
      options.out,
      '--check-report',
      checked,
      ...(telemetry ? ['--trace-id', telemetry.trace_id] : []),
    ]);
    if (options.local) {
      state.status = 'validated';
      state.phase = 'complete-local';
      state.preview = {
        type: 'standalone-local',
        requiresNetwork: true,
        path: resolve(options.out),
      };
      state.elapsedMs = Math.round(performance.now() - started);
      state.activeElapsedMs += state.elapsedMs;
      await writeJson(stateFile, state);
      return {
        state,
        output:
          JSON.stringify({
            status: 'validated',
            html: resolve(options.out),
            report: stateFile,
            preview: state.preview,
          }) + '\n',
      };
    }
    const output = await run('deliver', 'scripts/emit-doubao-renderer.mjs', [
      '--html',
      options.out,
      '--check',
      checked,
    ]);
    state.phase = 'publish-html';
    assertRepairAllowed(state.repairBudget, state.phase, state.inputIdentity);
    await writeJson(stateFile, state);
    const publishStarted = performance.now();
    const html = await readFile(options.out);
    state.htmlAsset = await uploadAsset(html, 'map.' + digest(html) + '.html', { resourceType: 'html', onTelemetry });
    state.stages.push({
      phase: 'publish-html',
      status: 'passed',
      elapsedMs: Math.round(performance.now() - publishStarted),
    });
    const payloadPath = resolve(directory, 'delivery.renderer.md');
    await writeText(payloadPath, output);
    state.delivery = {
      path: payloadPath,
      sha256: digest(output),
      htmlSha256: digest(html),
      checkSha256: digest(await readFile(checked)),
      inputIdentity: state.inputIdentity,
      format: 'html type="renderer"',
    };
    state.status = 'passed';
    state.elapsedMs = Math.round(performance.now() - started);
    state.activeElapsedMs += state.elapsedMs;
    await writeJson(stateFile, state);
    return { state, output };
  } catch (error) {
    state.status = /MAP_TASK_PENDING/.test(error.message)
      ? 'pending'
      : 'failed';
    state.error = safeError(error);
    const guarded =
      /^(REPAIR_LIMIT|REPAIR_REPEAT|MAINTENANCE_REQUIRED|TASK_TIMEOUT)/.test(
        error.message,
      );
    const reportFile =
      !guarded && state.phase === 'compile'
        ? 'compiler-report.json'
        : !guarded && state.phase === 'accept'
          ? 'check-report.json'
          : null;
    const failureReport = reportFile
      ? await readJson(resolve(directory, reportFile)).catch(() => null)
      : null;
    if (failureReport?.error) state.error = failureReport.error;
    if (state.status !== 'pending' && !guarded && state.repairBudget)
      recordRepairFailure(
        state.repairBudget,
        state.phase,
        state.inputIdentity,
        state.error,
      );
    state.diagnosis =
      state.status === 'pending'
        ? {
            code: 'MAP_TASK_PENDING',
            owner: 'provider',
            action: 'resume-poll',
            nextStep: '重跑同一命令继续查询；不修改输入，不重复提交。',
          }
        : diagnoseFailure(failureReport || state);
    state.elapsedMs = Math.round(performance.now() - started);
    state.activeElapsedMs += state.elapsedMs;
    await writeJson(stateFile, state);
    throw Object.assign(error, { workflow: state });
  } finally {
    await lock.close();
    await rm(lockFile);
  }
}

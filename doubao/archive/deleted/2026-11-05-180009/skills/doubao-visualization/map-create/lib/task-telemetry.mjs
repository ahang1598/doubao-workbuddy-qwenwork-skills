import { randomUUID, createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import {
  mkdir,
  open,
  readFile,
  readdir,
  rename,
  rm,
  writeFile,
} from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { sanitizeTelemetryError } from './telemetry-error.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const execute = promisify(execFile);
export const telemetryBid = 'lbs_map_create_skill';
const uuid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
const hash = /^[a-f0-9]{64}$/;
const eventNames = new Set([
  'task_started',
  'task_finished',
  'generation_attempt_finished',
  'generation_exception',
  'cdn_publish_finished',
  'tool_call_finished',
]);
const eventFields = new Set([
  'name',
  'event_id',
  'event_time',
  'schema_version',
  'producer',
  'env',
  'skill_version',
  'trace_id',
  'map_id',
  'generation_attempt_no',
  'artifact_id',
  'status',
  'stage',
  'duration_ms',
  'error_code',
  'exception',
  'failure_id',
  'operation_id',
  'resource_type',
  'tool_name',
  'api_name',
  'logid',
  'logids',
  'http_status',
  'request_count',
  'bytes',
  'fallback_used',
  'cache_hit',
]);
const stages = new Set([
  'input',
  'prepare-input',
  'compile',
  'publish-resources',
  'build-local',
  'accept',
  'trace',
  'deliver',
  'publish-html',
  'complete-local',
  'unknown',
  'upload',
  'readback',
  'verify',
  'submit',
  'poll',
  'result',
]);

export function telemetryCode(value) {
  return (
    String(value || '').match(/^[A-Z][A-Z0-9_]{2,79}(?=[:\s]|$)/)?.[0] ||
    'UNKNOWN_ERROR'
  );
}

export async function readTelemetryTask(path) {
  const state = JSON.parse(await readFile(path, 'utf8'));
  return validateTelemetryTask(state);
}

function validateTelemetryTask(state) {
  if (
    state.schema_version !== 1 ||
    !uuid.test(state.trace_id) ||
    state.map_id !== state.trace_id ||
    !['production', 'test'].includes(state.env) ||
    !hash.test(state.skill_version) ||
    !Array.isArray(state.pending) ||
    state.pending.length > 256
  )
    throw new Error('TELEMETRY_CONTEXT_INVALID');
  for (const event of state.pending) {
    if (event.name === 'generation_exception') {
      const safe = sanitizeTelemetryError(event.exception, true);
      if (!safe || JSON.stringify(safe) !== JSON.stringify(event.exception))
        throw new Error('TELEMETRY_EVENT_INVALID');
    } else if (event.exception !== undefined) {
      throw new Error('TELEMETRY_EVENT_INVALID');
    }
    if (
      !eventNames.has(event.name) ||
      !uuid.test(event.event_id) ||
      event.trace_id !== state.trace_id ||
      event.map_id !== state.map_id ||
      event.env !== state.env ||
      event.skill_version !== state.skill_version ||
      event.producer !== 'skill' ||
      event.schema_version !== 1 ||
      !Number.isSafeInteger(event.event_time) ||
      event.event_time < 0 ||
      Object.keys(event).some(key => !eventFields.has(key)) ||
      (event.status !== undefined &&
        !['failed', 'cancelled', 'succeeded', 'validated'].includes(
          event.status,
        )) ||
      (event.stage !== undefined && !stages.has(event.stage)) ||
      (event.error_code !== undefined &&
        !/^[A-Z][A-Z0-9_]{2,79}$/.test(event.error_code)) ||
      (event.artifact_id !== undefined && !hash.test(event.artifact_id)) ||
      ['failure_id', 'operation_id'].some(
        key => event[key] !== undefined && !uuid.test(event[key]),
      ) ||
      (event.logid !== undefined &&
        !/^[A-Za-z0-9_-]{1,256}$/.test(event.logid)) ||
      (event.logids !== undefined &&
        !/^[A-Za-z0-9_-]{1,256}(?:,[A-Za-z0-9_-]{1,256}){0,7}$/.test(
          event.logids,
        )) ||
      ['resource_type', 'tool_name', 'api_name'].some(
        key =>
          event[key] !== undefined &&
          !/^[a-z][a-z0-9_-]{0,40}$/.test(event[key]),
      ) ||
      ['cache_hit', 'fallback_used'].some(
        key => event[key] !== undefined && typeof event[key] !== 'boolean',
      ) ||
      [
        'generation_attempt_no',
        'duration_ms',
        'http_status',
        'request_count',
        'bytes',
      ].some(
        key =>
          event[key] !== undefined &&
          (!Number.isSafeInteger(event[key]) || event[key] < 0),
      )
    )
      throw new Error('TELEMETRY_EVENT_INVALID');
  }
  return state;
}

function enqueue(state, name, fields = {}) {
  if (state.pending.length >= 256) {
    state.dropped_events += 1;
    return;
  }
  state.pending.push({
    name,
    event_id: randomUUID(),
    event_time: Date.now(),
    schema_version: 1,
    producer: 'skill',
    env: state.env,
    skill_version: state.skill_version,
    trace_id: state.trace_id,
    map_id: state.map_id,
    ...fields,
  });
  return state.pending.at(-1).event_id;
}

const writes = new Map();
export async function recordDependencyEvent(path, name, fields) {
  if (!path || !['cdn_publish_finished', 'tool_call_finished'].includes(name))
    return;
  const previous = writes.get(path) || Promise.resolve();
  const next = previous
    .catch(() => {})
    .then(() =>
      bestEffortTelemetry(() =>
        mutate(path, state => {
          enqueue(state, name, {
            generation_attempt_no: state.generation_attempt_no,
            ...fields,
          });
        }),
      ),
    );
  writes.set(path, next);
  try {
    return await next;
  } finally {
    if (writes.get(path) === next) writes.delete(path);
  }
}

export async function startTelemetryTask(path, { env = 'production' } = {}) {
  if (!['production', 'test'].includes(env))
    throw new Error('TELEMETRY_ENV_INVALID');
  const traceId = randomUUID();
  const versionFiles = [
    'SKILL.md',
    'vendor.lock.json',
    'assets/engine/engine.lock.json',
    'assets/slardar/sdk.lock.json',
  ];
  for (const directory of ['lib', 'scripts', 'runtime']) {
    for (const file of await readdir(resolve(root, directory)))
      if (/\.(m?js|css|template)$/.test(file))
        versionFiles.push(`${directory}/${file}`);
  }
  const versionHash = createHash('sha256');
  for (const file of versionFiles.sort())
    versionHash.update(file).update(await readFile(resolve(root, file)));
  const state = {
    schema_version: 1,
    trace_id: traceId,
    map_id: traceId,
    env,
    skill_version: versionHash.digest('hex'),
    started_at: Date.now(),
    status: 'running',
    generation_attempt_no: 0,
    pending: [],
    dropped_events: 0,
  };
  enqueue(state, 'task_started');
  await mkdir(dirname(resolve(path)), { recursive: true });
  await writeFile(path, JSON.stringify(state, null, 2) + '\n', {
    flag: 'wx',
    mode: 0o600,
  });
  return state;
}

async function mutate(path, update) {
  const lockPath = path + '.lock';
  const lock = await open(lockPath, 'wx', 0o600);
  const temporary = path + '.' + randomUUID() + '.tmp';
  try {
    const state = await readTelemetryTask(path);
    await update(state);
    validateTelemetryTask(state);
    await writeFile(temporary, JSON.stringify(state, null, 2) + '\n', {
      mode: 0o600,
    });
    await rename(temporary, path);
    return state;
  } finally {
    await rm(temporary, { force: true });
    await lock.close();
    await rm(lockPath, { force: true });
  }
}

export async function beginGenerationAttempt(path) {
  return mutate(path, state => {
    if (state.status !== 'running') throw new Error('TELEMETRY_TASK_FINISHED');
    if (!state.active_attempt) {
      state.generation_attempt_no += 1;
      state.active_attempt = {
        number: state.generation_attempt_no,
        started_at: Date.now(),
      };
    }
  });
}

export async function finishGenerationAttempt(
  path,
  { status, stage, errorCode, artifactId, exception } = {},
) {
  if (!['succeeded', 'failed', 'validated'].includes(status))
    throw new Error('TELEMETRY_STATUS_INVALID');
  if (status === 'succeeded' && !/^[a-f0-9]{64}$/.test(artifactId || ''))
    throw new Error('TELEMETRY_ARTIFACT_REQUIRED');
  return mutate(path, state => {
    if (state.status !== 'running' || !state.active_attempt) return;
    const safe = status === 'failed' ? sanitizeTelemetryError(exception) : null;
    const eventId = randomUUID();
    const failureId = uuid.test(exception?.failure_id || '')
      ? exception.failure_id
      : eventId;
    enqueue(state, 'generation_attempt_finished', {
      event_id: eventId,
      generation_attempt_no: state.active_attempt.number,
      status,
      stage: stages.has(stage) ? stage : 'unknown',
      duration_ms: Math.max(0, Date.now() - state.active_attempt.started_at),
      ...(status === 'failed' ? { error_code: telemetryCode(errorCode) } : {}),
      ...(status === 'failed' ? { failure_id: failureId } : {}),
      ...(/^[a-f0-9]{64}$/.test(artifactId || '')
        ? { artifact_id: artifactId }
        : {}),
    });
    if (safe)
      enqueue(state, 'generation_exception', {
        generation_attempt_no: state.active_attempt.number,
        stage: stages.has(stage) ? stage : 'unknown',
        failure_id: failureId,
        exception: safe,
      });
    delete state.active_attempt;
    if (status === 'succeeded') {
      state.status = 'succeeded';
      enqueue(state, 'task_finished', {
        status,
        duration_ms: Date.now() - state.started_at,
        artifact_id: artifactId,
      });
    }
  });
}

export async function finishTelemetryTask(
  path,
  { status, stage, errorCode } = {},
) {
  if (!['failed', 'cancelled'].includes(status))
    throw new Error('TELEMETRY_STATUS_INVALID');
  return mutate(path, state => {
    if (state.status !== 'running') return;
    state.status = status;
    delete state.active_attempt;
    enqueue(state, 'task_finished', {
      status,
      stage: stages.has(stage) ? stage : 'unknown',
      error_code: telemetryCode(errorCode),
      duration_ms: Date.now() - state.started_at,
    });
  });
}

export async function flushTaskTelemetry(path) {
  if (process.env.MAP_CREATE_TELEMETRY_DISABLED === '1') return;
  return mutate(path, async state => {
    if (state.env !== 'production' || !state.pending.length) return;
    try {
      const { stdout } = await execute(
        process.execPath,
        [
          resolve(root, 'scripts/send-task-telemetry.mjs'),
          '--task',
          resolve(path),
        ],
        { timeout: 4000, killSignal: 'SIGKILL', maxBuffer: 128 * 1024 },
      );
      const acknowledged = new Set(JSON.parse(stdout).event_ids);
      state.pending = state.pending.filter(
        event => !acknowledged.has(event.event_id),
      );
      state.last_flush = {
        status: state.pending.length ? 'partial' : 'sent',
        time: Date.now(),
      };
    } catch (error) {
      state.last_flush = {
        status: 'pending',
        time: Date.now(),
        error_code: error.killed
          ? 'TELEMETRY_TIMEOUT'
          : error.stderr?.match(/\bTELEMETRY_[A-Z_]+\b/)?.[0] ||
            'TELEMETRY_SEND_FAILED',
      };
    }
  });
}

export async function bestEffortTelemetry(operation) {
  try {
    return await operation();
  } catch {
    process.stderr.write('MAP_TELEMETRY_UNAVAILABLE\n');
    return null;
  }
}

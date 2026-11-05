import { requestTrace, toolCall } from './tool-diagnostics.mjs';
import { observeTool } from './dependency-telemetry.mjs';
import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const samePoint = (left, right) => left[0] === right[0] && left[1] === right[1];

// 沿用 map_mark 的 unknown 距离规则，不把 unknown 传给路线接口。
export function connectionMode(origin, destination) {
  const radians = value => (value * Math.PI) / 180;
  const [lng1, lat1] = origin.map(radians);
  const [lng2, lat2] = destination.map(radians);
  const haversine =
    Math.sin((lat2 - lat1) / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin((lng2 - lng1) / 2) ** 2;
  const distance = 6371000 * 2 * Math.asin(Math.sqrt(Math.min(1, haversine)));
  return distance <= 2000
    ? 'walking'
    : distance <= 5000
      ? 'cycling'
      : 'driving';
}

const requireResult = (condition, message) => {
  if (!condition) throw new Error(message);
};

function requireUnambiguous(payload) {
  requireResult(
    ![payload, ...(payload?.entity_list || [])].some(
      value =>
        value?.unresolved_waypoints?.length ||
        value?.origin_alternatives?.length ||
        value?.destination_alternatives?.length,
    ),
    'CONNECTION_AMBIGUOUS: 补线端点需先消歧',
  );
}

function routePending(payload) {
  return payload?.entity_list?.some(entity =>
    ['created', 'progressing', 'pending', 'running'].includes(entity.status),
  );
}

function requireSuccessfulState(payload) {
  requireResult(
    !payload?.entity_list?.some(
      entity =>
        entity.status &&
        ![
          'completed',
          'success',
          'succeeded',
          'created',
          'progressing',
          'pending',
          'running',
        ].includes(entity.status),
    ),
    'RESULT_INVALID: 补线路线服务返回失败状态',
  );
}

// 多条 entity 是同一次起终点查询的路线候选；保持服务排序，仅取第一个方案。
function selectConnectionCandidate(payload, entityId) {
  requireUnambiguous(payload);
  const entities = payload?.entity_list;
  requireResult(Array.isArray(entities) && entities.length > 0,
    'RESULT_INVALID: 补线需返回唯一实体或有效路线候选');
  if (entityId) {
    const matches = entities.filter(entity => entity.entity_id === entityId);
    requireResult(matches.length === 1, 'RESULT_INVALID: 补线 entity_id 不匹配');
    return { ...payload, entity_list: matches };
  }
  // 沿用服务推荐顺序，仅使用第一个方案；后续校验其状态、方式和轨迹。
  return { ...payload, entity_list: [entities[0]] };
}

async function loadState(file) {
  try {
    return JSON.parse(await readFile(file, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

async function saveState(file, state) {
  await writeFile(`${file}.tmp`, `${JSON.stringify(state, null, 2)}\n`);
  await rename(`${file}.tmp`, file);
}

async function planConnection(link, options) {
  const { directory, parseResponse, signal, retryMs, onTelemetry } = options;
  const file = join(directory, `${link.id}.json`);
  const fingerprint = createHash('sha256')
    .update(JSON.stringify({ link, policy: 'unknown-fallback-v1' }))
    .digest('hex');
  let state = await loadState(file);
  requireResult(
    !state || state.fingerprint === fingerprint,
    'TASK_INPUT_CHANGED: 补线请求发生变化，请使用新的工作目录',
  );
  state ||= { fingerprint, status: 'new' };
  // 旧版把合法多候选当成失败。复用原响应修复，不重新请求服务。
  const retryCandidates = state.result?.degraded && state.response &&
    state.result.error === 'RESULT_INVALID: 补线需返回唯一实体';
  if (state.result && !retryCandidates) return state.result;
  const observation = observeTool(state, 'route_plan_v2', options.request, onTelemetry);
  const request = observation.request;
  try {
    if (!state.response) {
      requireResult(
        state.status === 'new',
        'SUBMIT_UNCERTAIN: 补线提交状态不明，不能自动重新提交',
      );
      signal.throwIfAborted();
      state.status = 'submitting';
      await saveState(file, state);
      state.response = await request(
        'route_plan',
        {
          origin: routeLocation(link.origin),
          destination: routeLocation(link.destination),
          modes: [link.mode],
        },
        signal,
      );
      state.status = 'submitted';
      await saveState(file, state);
    }
    let payload = selectConnectionCandidate(parseResponse(state.response));
    requireUnambiguous(payload);
    requireSuccessfulState(payload);
    const submittedEntity = payload?.entity_list?.[0];
    requireResult(
      payload?.entity_list?.length === 1,
      'RESULT_INVALID: 补线需返回唯一实体',
    );
    if (submittedEntity.entity_id) {
      requireResult(
        /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(submittedEntity.entity_id),
        'RESULT_INVALID: 补线 entity_id 无效',
      );
      state.entityId = submittedEntity.entity_id;
      await saveState(file, state);
    }
    if (
      (routePending(payload) || !submittedEntity.routes?.length) &&
      state.entityId
    ) {
      while (true) {
        signal.throwIfAborted();
        let response;
        try {
          response = await request(
            'get_entity',
            { entity_id: state.entityId },
            signal,
          );
        } catch (error) {
          if (
            !['ECONNRESET', 'ETIMEDOUT', 'EAI_AGAIN', 'ECONNREFUSED'].includes(
              error.code,
            )
          )
            throw error;
        }
        payload = response
          ? selectConnectionCandidate(parseResponse(response, true), state.entityId)
          : null;
        if (payload) {
          requireUnambiguous(payload);
          requireSuccessfulState(payload);
          requireResult(
            payload.entity_list?.length === 1 &&
              payload.entity_list[0].entity_id === state.entityId,
            'RESULT_INVALID: 补线 entity_id 不匹配',
          );
          if (!routePending(payload)) {
            state.resultTrace = requestTrace('result', 'get_entity', response, state.entityId);
            break;
          }
        }
        await delay(retryMs, undefined, { signal });
      }
    }
    const entity = payload?.entity_list?.[0];
    requireResult(
      !routePending(payload),
      'RESULT_INVALID: 补线未完成且没有可恢复的 entity_id',
    );
    requireResult(
      payload?.entity_list?.length === 1 &&
        entity &&
        (!state.entityId || entity.entity_id === state.entityId),
      'RESULT_INVALID: 补线 entity_id 不匹配',
    );
    requireUnambiguous(payload);
    const route = entity.routes?.[0];
    requireResult(
      !entity.routes || Array.isArray(entity.routes),
      'RESULT_INVALID: routes 无效',
    );
    requireResult(
      route || (Array.isArray(entity.routes) && !entity.routes.length),
      'RESULT_INVALID: 补线结果缺少 routes',
    );
    requireResult(
      !entity.mode || entity.mode === link.mode,
      'RESULT_INVALID: 补线交通方式与请求不符',
    );
    requireResult(
      !route?.mode || route.mode === link.mode,
      'RESULT_INVALID: 补线交通方式与请求不符',
    );
    const retrievedAt = new Date().toISOString();
    const geometry = route
      ? routeGeometry(route, link, link.mode)
      : {
          type: 'LineString',
          coordinates: [link.origin.position, link.destination.position],
          status: 'schematic',
          derivation: 'round-trip-direct-fallback',
        };
    const distance = entity.distance ?? route?.distance;
    const duration = entity.duration ?? route?.time;
    state.result = {
      mode: link.mode,
      retrievedAt,
      geometry,
      degraded: !route,
      ...(!route ? { error: '没有可用路线；使用端点直线示意' } : {}),
      ...(route && Number.isFinite(distance) && distance >= 0
        ? { distance }
        : {}),
      ...(route && Number.isFinite(duration) && duration >= 0
        ? { duration }
        : {}),
      ...(state.entityId ? { entityId: state.entityId } : {}),
    };
    state.result.toolCalls = [toolCall('route_plan_v2', state.entityId ? [state.entityId] : [], [
      requestTrace('submit', 'route_plan', state.response),
      ...(state.resultTrace ? [state.resultTrace] : []),
    ])];
    state.status = 'completed';
    await observation.finish(route ? null : new Error('ROUTE_EMPTY'), !route);
    await saveState(file, state);
    return state.result;
  } catch (error) {
    await observation.finish(signal.aborted ? new Error('TOOL_TIMEOUT') : error, true);
    // 补线失败只降级连接几何，始终保留已确认的端点，不重新搜索地点。
    state.result = {
      mode: link.mode,
      retrievedAt: new Date().toISOString(),
      geometry: {
        type: 'LineString',
        coordinates: [link.origin.position, link.destination.position],
        status: 'schematic',
        derivation: 'round-trip-direct-fallback',
      },
      degraded: true,
      error: signal.aborted ? '补线查询超时，使用端点直线示意' : error.message,
      ...(state.entityId ? { entityId: state.entityId } : {}),
    };
    state.result.toolCalls = [toolCall('route_plan_v2', state.entityId ? [state.entityId] : [], [
      requestTrace('submit', 'route_plan', state.response),
      ...(state.resultTrace ? [state.resultTrace] : []),
    ])];
    state.status = 'completed';
    await saveState(file, state);
    return state.result;
  }
}

export async function planRoundTripRoutes(
  connections,
  {
    directory,
    request,
    parseResponse,
    timeoutMs,
    retryMs,
    onTelemetry,
  },
) {
  requireResult(
    typeof directory === 'string' && directory.length > 0,
    '补线需要持久化工作目录',
  );
  requireResult(
    Number.isFinite(timeoutMs) && timeoutMs > 0 && timeoutMs <= 10000,
    '补线轮询预算需在 0–10000ms 内',
  );
  requireResult(
    Number.isFinite(retryMs) && retryMs >= 0,
    '补线重试间隔无效',
  );
  const ids = new Set();
  for (const link of connections) {
    requireResult(
      /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(link.id) && !ids.has(link.id),
      '补线 ID 无效或重复',
    );
    ids.add(link.id);
    requireResult(
      ['driving', 'walking', 'cycling'].includes(link.mode),
      'CONNECTION_MODE_REQUIRED: 补线需有明确交通方式',
    );
    for (const place of [link.origin, link.destination])
      requireResult(
        place?.position?.length === 2 &&
          place.position.every(Number.isFinite) &&
          Math.abs(place.position[0]) <= 180 &&
          Math.abs(place.position[1]) <= 85,
        '补线端点坐标无效',
      );
  }
  await mkdir(directory, { recursive: true });
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const results = new Array(connections.length);
  let next = 0;
  let failure;
  try {
    await Promise.all(
      Array.from({ length: Math.min(4, connections.length) }, async () => {
        while (!failure && next < connections.length) {
          const index = next++;
          try {
            results[index] = await planConnection(connections[index], {
              directory,
              request,
              parseResponse,
              retryMs,
              onTelemetry,
              signal: controller.signal,
            });
          } catch (error) {
            failure ||= error;
            controller.abort();
          }
        }
      }),
    );
    if (failure) throw failure;
    return results;
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}

function routeLocation(place) {
  const id = String(place.properties?.poiId ?? '').trim();
  return {
    type: id ? 'id' : 'coordinate',
    value: {
      ...(id ? { text: id } : {}),
      longitude: place.position[0],
      latitude: place.position[1],
    },
  };
}

function routeGeometry(route, link, mode) {
  const lines = [],
    parts = [];
  let last = link.origin.position;
  const append = (points, status, partMode) => {
    const previous = parts.at(-1);
    if (
      previous?.status === status &&
      previous.mode === partMode &&
      samePoint(lines.at(-1).at(-1), points[0])
    ) {
      lines.at(-1).push(...points.slice(1));
      return;
    }
    lines.push(points);
    parts.push({ mode: partMode, status });
  };
  if (!route.steps?.length) throw new Error('路线轨迹为空');
  for (const step of route.steps) {
    if (typeof step.path !== 'string' || !step.path.trim())
      throw new Error('路线分段轨迹为空');
    const points = step.path
      .split(';')
      .map(token => {
        const values = token.split(',').map(value => value.trim());
        const point = values.map(Number);
        if (
          values.length !== 2 ||
          values.some(value => !value) ||
          !point.every(Number.isFinite) ||
          Math.abs(point[0]) > 180 ||
          Math.abs(point[1]) > 85
        )
          throw new Error('路线轨迹坐标无效');
        return point;
      })
      .filter(
        (point, index, all) => !index || !samePoint(point, all[index - 1]),
      );
    if (points.length < 2) throw new Error('路线分段轨迹不足两个点');
    if (!samePoint(last, points[0]))
      append([last, points[0]], 'schematic', mode);
    append(points, 'resolved', mode);
    last = points.at(-1);
  }
  if (!samePoint(last, link.destination.position))
    append([last, link.destination.position], 'schematic', mode);
  return {
    type: 'MultiLineString',
    coordinates: lines,
    parts,
    status: parts.some(part => part.status === 'schematic')
      ? 'schematic'
      : 'resolved',
    derivation: 'route_plan_v2',
  };
}

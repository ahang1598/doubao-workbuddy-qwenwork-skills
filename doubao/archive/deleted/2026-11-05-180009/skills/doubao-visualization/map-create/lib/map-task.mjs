import { requestTrace, toolCall, mergeToolCalls } from './tool-diagnostics.mjs';
import { observeTool } from './dependency-telemetry.mjs';
import { createHash } from 'node:crypto';
import { mkdir, open, readFile, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { validateContract } from './engine.mjs';
import { decode, requestGateway } from './entity-gateway.mjs';
import { finishRoadTrip, roadTripConnections } from './map-road-trip.mjs';
import {
  applyPlanDescriptions,
  createMapMarkSpec,
  createRouteSpec,
  createTaskPlan,
  prepareTask,
  isRoadTrip,
  selectRouteEntities,
} from './map-task-spec.mjs';
import { planRoundTripRoutes } from './round-trip-routes.mjs';

const check = (ok, message) => {
  if (!ok) throw new Error(message);
};
const pendingStates = ['created', 'progressing', 'pending', 'running'];
async function readOptional(file) {
  try {
    return JSON.parse(await readFile(file, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}
async function save(file, value) {
  await writeFile(`${file}.tmp`, `${JSON.stringify(value, null, 2)}\n`);
  await rename(`${file}.tmp`, file);
}

// 只有明确的缓存未就绪和临时传输失败可重试；不重发规划请求。
export function gatewayPayload(response, polling = false) {
  if (polling && (response.status === 429 || response.status >= 500))
    return null;
  check(
    response.status >= 200 && response.status < 300,
    `HTTP_ERROR: ${response.status}`,
  );
  const outer = decode(response.body);
  const data = outer.data ?? outer;
  const service = decode(data.resp ?? data);
  if (
    polling &&
    /redis:\s*nil/i.test(
      [outer.msg, outer.message, service.BaseResp?.StatusMessage].join(' '),
    )
  )
    return null;
  check(
    outer.code == null || outer.code === 0,
    `GATEWAY_ERROR: ${outer.code} ${outer.msg || ''}`,
  );
  check(data.success !== false, 'GATEWAY_ERROR: success=false');
  check(
    service.BaseResp?.StatusCode == null || service.BaseResp.StatusCode === 0,
    `SERVICE_ERROR: ${service.BaseResp?.StatusCode} ${service.BaseResp?.StatusMessage || ''}`,
  );
  return decode(
    service.entity_info ??
      service.structured_content ??
      service.structuredContent ??
      service.content ??
      service,
  );
}

async function poll(task, state, request, timeoutMs, retryMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await Promise.all(
      state.entityIds.map(async entityId => {
        const api =
          task.tool === 'map_mark' ? 'get_map_mark_task' : 'get_entity';
        while (!controller.signal.aborted) {
          let response;
          try {
            response = await request(
              api,
              { entity_id: entityId },
              controller.signal,
            );
          } catch (error) {
            if (
              ![
                'ECONNRESET',
                'ETIMEDOUT',
                'EAI_AGAIN',
                'ECONNREFUSED',
              ].includes(error.code)
            )
              throw error;
          }
          if (response) {
            const payload = gatewayPayload(response, true);
            if (payload) {
              const entities = payload.entity_list?.filter(
                entity => entity.entity_id === entityId,
              );
              check(
                entities?.length === 1 && payload.entity_list.length === 1,
                'RESULT_INVALID: entity_id 不匹配',
              );
              if (task.tool === 'route_plan_v2') {
                payload.toolRequestTrace = requestTrace('result', api, response, entityId);
                return payload;
              }
              const entity = entities[0];
              if (entity.status === 'completed') {
                payload.toolRequestTrace = requestTrace('result', api, response, entityId);
                return payload;
              }
              check(
                pendingStates.includes(entity.status),
                `MAP_TASK_FAILED: ${entity.status} ${entity.status_message || ''}`,
              );
            }
          }
          await delay(retryMs, undefined, { signal: controller.signal });
        }
        throw new Error('PENDING');
      }),
    );
  } catch (error) {
    if (controller.signal.aborted)
      throw new Error(
        'MAP_TASK_PENDING: 轮询已超时，重跑同一命令继续查询，勿重新提交',
      );
    throw error;
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}

/** 同目录按输入指纹隔离缓存。request 可注入用于离线协议测试。 */
export async function runMapTask(
  input,
  outputDir,
  { request = requestGateway, timeoutMs = 10000, retryMs = 500, onPlaces, onTelemetry } = {},
) {
  const started = Date.now();
  const task = prepareTask(input);
  check(
    Number.isFinite(timeoutMs) && timeoutMs > 0 && timeoutMs <= 10000,
    '轮询预算需在 0–10000ms 内',
  );
  const providerTask = { ...task };
  delete providerTask.overviewPreference;
  const fingerprint = createHash('sha256')
    .update(JSON.stringify(providerTask))
    .digest('hex');
  await mkdir(outputDir, { recursive: true });
  // Each input owns its provider results and generated inputs. The lock stays
  // at the workflow provider root, so changed inputs cannot submit concurrently.
  let serviceDir = path.join(outputDir, 'requests', fingerprint);
  const file = name => path.join(serviceDir, name);
  // 防止两次并发执行对同一个目录重复提交。
  const lock = await open(path.join(outputDir, '.map-task.lock'), 'wx').catch(error => {
    if (error.code === 'EEXIST')
      throw new Error(
        'TASK_BUSY: 工作目录被占用；确认旧进程退出后才能移除 .map-task.lock',
      );
    throw error;
  });
  let observation;
  let state;
  const providerRequest = request;
  try {
    // Reuse legacy caches only when both the input and provider strategy match.
    const legacyDir = isRoadTrip(task)
      ? path.join(outputDir, 'service-travel-plan-v1')
      : outputDir;
    if (!(await readOptional(file('task-state.json')))) {
      const legacy = await readOptional(path.join(legacyDir, 'task-state.json'));
      if (legacy?.fingerprint === fingerprint) serviceDir = legacyDir;
    }
    await mkdir(serviceDir, { recursive: true });
    state = await readOptional(file('task-state.json'));
    if (state)
      check(
        state.fingerprint === fingerprint,
        'TASK_CACHE_MISMATCH: 缓存身份不匹配，请保留记录并报告维护问题',
      );
    else {
      state = {
        fingerprint,
        tool: task.tool,
        status: 'new',
        createdAt: new Date().toISOString(),
      };
      await save(file('task-input.json'), task);
      await save(file('task-state.json'), state);
    }
    observation = observeTool(state, task.tool, providerRequest, onTelemetry);
    request = observation.request;
    if (!state.entityIds) {
      let response = await readOptional(file('submit-response.json'));
      if (!response) {
        check(
          state.status === 'new',
          'SUBMIT_UNCERTAIN: 先确认服务端任务，不能自动重新提交',
        );
        state.status = 'submitting';
        await save(file('task-state.json'), state);
        // 提交也有独立的 10 秒上限；超时不代表服务端没有接收。
        const parameters = structuredClone(task.parameters);
        if (task.tool === 'map_mark') {
          if (isRoadTrip(task)) parameters.map_data.scene = 'travel_plan';
          for (const plan of parameters.map_data.plans) delete plan.description;
        }
        response = await request(
          task.tool === 'map_mark' ? 'start_map_mark_async' : 'route_plan',
          parameters,
          AbortSignal.timeout(10000),
        );
        await save(file('submit-response.json'), response);
      }
      const payload = gatewayPayload(response);
      const entities =
        task.tool === 'map_mark'
          ? payload.entity_list
          : selectRouteEntities(task, payload);
      check(
        entities?.length && (task.tool !== 'map_mark' || entities.length === 1),
        'SUBMIT_INVALID: 缺少唯一地图任务',
      );
      check(
        entities.every(entity =>
          /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(entity.entity_id || ''),
        ),
        'SUBMIT_INVALID: entity_id 无效',
      );
      state.entityIds = entities.map(entity => entity.entity_id);
      state.status = 'submitted';
      await save(file('task-state.json'), state);
    }
    let results = await readOptional(file('task-results.json'));
    if (!results) {
      results = await poll(task, state, request, timeoutMs, retryMs);
      await save(file('task-results.json'), results);
    }
    // Match stable group/point IDs before validation so omitted places remain
    // visible in the workflow report even when input preparation fails.
    if (task.tool === 'map_mark' && onPlaces) {
      const entity = results[0]?.entity_list?.find(
        item => item.entity_id === state.entityIds[0],
      );
      const places = task.parameters.map_data.plans.flatMap(plan => {
        const returned = entity?.plan?.find(item => item.id === plan.id);
        return plan.points.map(point => ({
          requested: point.name,
          resolved: returned?.points?.find(item => item.id === point.id)?.name
            || '工具未返回',
        }));
      });
      await onPlaces(places);
    }
    state.retrievedAt ||= new Date().toISOString();
    await save(file('task-state.json'), state);
    let spec =
      task.tool === 'map_mark'
        ? createMapMarkSpec(
            task,
            results[0],
            state.entityIds[0],
            state.retrievedAt,
          )
        : createRouteSpec(task, results, state.retrievedAt);
    const submitResponse = await readOptional(file('submit-response.json'));
    const calls = [toolCall(task.tool, state.entityIds, [
      requestTrace('submit', task.tool === 'map_mark' ? 'start_map_mark_async' : 'route_plan', submitResponse),
      ...results.map((result, index) => result.toolRequestTrace ||
        requestTrace('result', task.tool === 'map_mark' ? 'get_map_mark_task' : 'get_entity', null, state.entityIds[index])),
    ])];
    await observation.finish();
    await save(file('task-state.json'), state);
    if (isRoadTrip(task)) {
      const { connections } = roadTripConnections(spec);
      const connectionRoutes = await planRoundTripRoutes(connections, {
        directory: file('connection-routes-unknown-v1'),
        request: providerRequest,
        onTelemetry,
        parseResponse: gatewayPayload,
        timeoutMs,
        retryMs,
      });
      calls.push(...connectionRoutes.flatMap(result => result.toolCalls || []));
      spec = finishRoadTrip(spec, connections, connectionRoutes);
      const errors = validateContract('mapSpec', spec);
      check(
        !errors.length,
        errors.map(error => `${error.path}: ${error.message}`).join('\n'),
      );
      state.connections = connections.map(
        ({ id, groupId, prepend }, index) => ({
          id,
          groupId,
          prepend,
          degraded: connectionRoutes[index].degraded,
        }),
      );
    }
    spec.metadata ||= {};
    spec.metadata.diagnostics = { tool_calls: mergeToolCalls(calls) };
    applyPlanDescriptions(spec, task);
    const plan = createTaskPlan(task, spec);
    const planErrors = validateContract('presentationPlan', plan);
    check(
      !planErrors.length,
      planErrors.map(error => `${error.path}: ${error.message}`).join('\n'),
    );
    await save(file('presentation-plan.json'), plan);
    await save(file('canonical-map-spec.json'), spec);
    await save(file('task-input.json'), task);
    state.status = 'completed';
    await save(file('task-state.json'), state);
    const summary = {
      status: 'completed',
      spec: path.resolve(file('canonical-map-spec.json')),
      plan: path.resolve(file('presentation-plan.json')),
      elapsedMs: Date.now() - started,
      entityIds: state.entityIds,
      ...(isRoadTrip(task) ? { connections: state.connections } : {}),
      counts: {
        places: spec.entities.places.length,
        routes: spec.entities.routes.length,
      },
      places: spec.entities.places.map(({ id, name, properties }) => ({
        id,
        name,
        address: properties?.address,
      })),
      routes: spec.entities.routes.map(({ id, name, mode, properties }) => ({
        id,
        name,
        mode,
        description: properties?.description,
        distance: properties?.distance,
        duration: properties?.duration,
        durationBreakdown: properties?.durationBreakdown,
        budget: properties?.budget,
        timeContext: properties?.timeContext,
      })),
      task: spec.task,
      groups: spec.groups.map(({ id, title, kind, routeIds }) => ({
        id,
        title,
        kind,
        routeIds,
      })),
      views: spec.views,
      next: '基础 Presentation Plan 已生成；核对阅读目的并按需补充展示偏好，再编译和验收。',
    };
    await save(file('task-summary.json'), summary);
    return summary;
  } catch (error) {
    if (!/^MAP_TASK_PENDING/.test(error.message)) await observation?.finish(error);
    if (state) await save(file('task-state.json'), state);
    throw error;
  } finally {
    await lock.close();
    await rm(path.join(outputDir, '.map-task.lock'));
  }
}

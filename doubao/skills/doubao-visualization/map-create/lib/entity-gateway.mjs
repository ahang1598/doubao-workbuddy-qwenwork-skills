import { requestTrace, toolCall } from './tool-diagnostics.mjs';
import https from 'node:https';
import { setTimeout as delay } from 'node:timers/promises';

const requireValue = (ok, message) => {
  if (!ok) throw new Error(message);
};
const GATEWAY = 'https://mp.oceancloudapi.com/api/doubao/do_action_v2';

export function decode(value) {
  for (let depth = 0; depth < 4 && typeof value === 'string'; depth++) {
    try {
      value = JSON.parse(value);
    } catch {
      try {
        value = JSON.parse(JSON.parse(`"${value}"`));
      } catch {
        throw new Error('ENTITY_RESPONSE_INVALID: JSON 格式无效');
      }
    }
  }
  return value;
}

export function requestGateway(apiName, params, signal) {
  const body = JSON.stringify({
    scene: 'FPA_Location_MCP',
    ext: { trace_id: '' },
    payload: JSON.stringify({ api_name: apiName, params }),
  });
  return new Promise((resolve, reject) => {
    const req = https.request(
      GATEWAY,
      {
        method: 'POST',
        signal,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
        },
      },
      res => {
        const chunks = [];
        res.on('data', chunk => chunks.push(chunk));
        res.on('error', reject);
        res.on('end', () =>
          resolve({
            status: res.statusCode,
            logid: typeof res.headers['x-tt-logid'] === 'string'
              ? res.headers['x-tt-logid'] : null,
            body: Buffer.concat(chunks).toString('utf8'),
          }),
        );
      },
    );
    req.on('error', reject);
    req.end(body);
  });
}

export function requestEntity(entityId, signal, apiName = 'get_entity') {
  return requestGateway(apiName, { entity_id: entityId }, signal);
}

// 一次导入的全部实体共享 10 秒预算；网络响应和等待都可被取消。
export async function fetchRouteEntities(
  mapping,
  { request = requestEntity, timeoutMs = 10000, retryMs = 500 } = {},
) {
  requireValue(
    Array.isArray(mapping.routes) && mapping.routes.length,
    '缺少路线映射',
  );
  const ids = [...new Set(mapping.routes.map(item => item.entityId))];
  requireValue(
    ids.every(id => typeof id === 'string' && id.trim()),
    '缺少 entity_id',
  );
  const controller = new AbortController();
  const { signal } = controller;
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const traces = new Map();
  try {
    const entities = await Promise.all(
      ids.map(async id => {
        while (!signal.aborted) {
          let response;
          try {
            response = await request(id, signal);
          } catch (error) {
            if (signal.aborted) throw error;
            if (
              ![
                'ECONNRESET',
                'ETIMEDOUT',
                'EAI_AGAIN',
                'ECONNREFUSED',
              ].includes(error.code)
            ) {
              throw new Error('ENTITY_NETWORK_ERROR: 无法请求路线实体');
            }
          }
          if (response) {
            const { status, body } = response;
            if (status !== 429 && status < 500) {
              requireValue(
                status >= 200 && status < 300,
                `ENTITY_HTTP_ERROR: HTTP ${status}`,
              );
              const envelope = decode(body);
              requireValue(
                envelope?.code == null || envelope.code === 0,
                `ENTITY_GATEWAY_ERROR: code=${envelope?.code}`,
              );
              const data = envelope?.data ?? envelope;
              requireValue(
                data?.success !== false,
                'ENTITY_GATEWAY_ERROR: success=false',
              );
              const service = decode(data?.resp ?? data);
              requireValue(
                service?.BaseResp?.StatusCode == null ||
                  service.BaseResp.StatusCode === 0,
                `ENTITY_SERVICE_ERROR: code=${service?.BaseResp?.StatusCode}`,
              );
              // 空实体可能尚未完成异步保存；格式错误和业务错误不盲目重试。
              if (service?.entity_info) {
                const payload = decode(service.entity_info);
                requireValue(
                  !payload?.unresolved_waypoints?.length,
                  '存在未解析途经点',
                );
                requireValue(
                  Array.isArray(payload?.entity_list),
                  'ENTITY_RESPONSE_INVALID: 缺少 entity_list',
                );
                const matches = payload.entity_list.filter(
                  entity => entity.entity_id === id,
                );
                requireValue(
                  matches.length === 1,
                  'ENTITY_RESPONSE_INVALID: entity_id 不匹配',
                );
                traces.set(id, requestTrace('result', 'get_entity', response, id));
                return matches[0];
              }
            }
          }
          await delay(retryMs, undefined, { signal });
        }
        throw new Error('ENTITY_TIMEOUT');
      }),
    );
    return { entity_list: entities, diagnostics: { tool_calls: [toolCall('route_plan_v2', ids, ids.map(id => traces.get(id)))] } };
  } catch (error) {
    if (signal.aborted)
      throw new Error(
        `ENTITY_TIMEOUT: 获取路线超过 ${timeoutMs / 1000} 秒，未写入输出`,
      );
    throw error;
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}

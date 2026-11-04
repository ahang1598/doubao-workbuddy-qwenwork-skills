import { randomUUID } from 'node:crypto';
import {
  bestEffortTelemetry,
  recordDependencyEvent,
  telemetryCode,
} from './task-telemetry.mjs';

export function safeLogId(value) {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,256}$/.test(value)
    ? value
    : undefined;
}

export function dependencyReporter(task) {
  return task
    ? (name, fields) => recordDependencyEvent(task, name, fields)
    : undefined;
}

export function observeTool(state, toolName, request, onTelemetry) {
  const observation = (state.telemetry ||= {
    operation_id: randomUUID(),
    started_at: Date.now(),
    request_count: 0,
    logids: [],
  });
  return {
    async request(api, parameters, signal) {
      observation.request_count += 1;
      observation.api_name = api;
      delete observation.http_status;
      delete observation.logid;
      let response;
      try {
        response = await request(api, parameters, signal);
      } catch (error) {
        capture(error);
        throw error;
      }
      capture(response);
      return response;
    },
    async finish(error, fallbackUsed = false) {
      if (observation.finished || !observation.request_count) return;
      const eventId = (observation.event_id ||= randomUUID());
      const failureId = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(error?.failure_id || '')
        ? error.failure_id
        : eventId;
      if (error && typeof error === 'object' && Object.isExtensible(error))
        error.failure_id = failureId;
      const fields = {
        event_id: eventId,
        operation_id: observation.operation_id,
        tool_name: toolName,
        api_name: observation.api_name,
        status: error ? 'failed' : 'succeeded',
        stage:
          observation.api_name === 'route_plan' ||
          observation.api_name === 'start_map_mark_async'
            ? 'submit'
            : 'result',
        duration_ms: Math.max(0, Date.now() - observation.started_at),
        request_count: observation.request_count,
        fallback_used: fallbackUsed,
        cache_hit: false,
        ...(error
          ? {
              failure_id: failureId,
              error_code: telemetryCode(error.code || error.message),
            }
          : {}),
        ...(observation.logid ? { logid: observation.logid } : {}),
        ...(observation.logids.length
          ? { logids: observation.logids.join(',') }
          : {}),
        ...(observation.http_status
          ? { http_status: observation.http_status }
          : {}),
      };
      const result = onTelemetry
        ? await bestEffortTelemetry(() =>
            onTelemetry('tool_call_finished', fields),
          )
        : undefined;
      observation.finished = result !== null;
    },
  };
  function capture(response) {
    const status = response?.http_status ?? response?.status;
    if (Number.isInteger(status)) observation.http_status = status;
    const logid = safeLogId(response?.logid);
    if (logid) {
      observation.logid = logid;
      observation.logids = [...new Set([...observation.logids, logid])].slice(
        -8,
      );
    }
  }
}

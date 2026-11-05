import { requestTrace, toolCall, mergeToolCalls } from '../lib/tool-diagnostics.mjs';
import { realpathSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';
import { pathToFileURL } from 'node:url';
import { args, readJson, writeJson } from '../lib/cli-utils.mjs';
import { decode, requestEntity } from '../lib/entity-gateway.mjs';
import {
  finishImportIntent,
  validateImportIntent,
} from '../lib/import-intent.mjs';
import { formatDistance, formatDuration } from '../lib/route-plan-metrics.mjs';

const check = (ok, text) => {
  if (!ok) throw new Error(text);
};
const validPoint = p =>
  Array.isArray(p) &&
  p.length === 2 &&
  p.every(Number.isFinite) &&
  Math.abs(p[0]) <= 180 &&
  Math.abs(p[1]) <= 85 &&
  (p[0] !== 0 || p[1] !== 0);
const idPart = value => {
  check(
    typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value),
    '无效实体/plan/point/path ID',
  );
  return value;
};
const upsert = (items, value) => {
  const i = items.findIndex(x => x.id === value.id);
  if (i < 0) items.push(value);
  else items[i] = value;
};

export async function fetchMapMark(
  entityId,
  { request = requestEntity, timeoutMs = 10000, retryMs = 500 } = {},
) {
  idPart(entityId);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    while (!controller.signal.aborted) {
      let response;
      try {
        response = await request(
          entityId,
          controller.signal,
          'get_map_mark_task',
        );
      } catch (error) {
        if (
          !['ECONNRESET', 'ETIMEDOUT', 'EAI_AGAIN', 'ECONNREFUSED'].includes(
            error.code,
          )
        )
          throw error;
      }
      if (response && response.status !== 429 && response.status < 500) {
        check(
          response.status >= 200 && response.status < 300,
          `HTTP ${response.status}`,
        );
        const outer = decode(response.body);
        check(outer.code == null || outer.code === 0, `网关错误 ${outer.code}`);
        const data = outer.data ?? outer;
        check(data.success !== false, '网关返回失败');
        const service = decode(data.resp ?? data);
        check(
          service.BaseResp?.StatusCode == null ||
            service.BaseResp.StatusCode === 0,
          '服务返回失败',
        );
        const result = decode(
          service.structured_content ?? service.structuredContent ?? service,
        );
        const entities = result.entity_list?.filter(
          e => e.entity_id === entityId,
        );
        check(entities?.length === 1, '响应 entity_id 不匹配');
        const entity = entities[0];
        if (entity.status === 'completed') {
          result.diagnostics = { tool_calls: [toolCall('map_mark', [entityId], [requestTrace('result', 'get_map_mark_task', response, entityId)])] };
          return result;
        }
        check(
          ['created', 'progressing', 'pending', 'running'].includes(
            entity.status,
          ),
          `地图任务未成功：${entity.status} ${entity.status_message || ''}`,
        );
      }
      await delay(retryMs, undefined, { signal: controller.signal });
    }
  } catch (error) {
    if (controller.signal.aborted)
      throw new Error(
        `MAP_MARK_PENDING: 等待超过 ${timeoutMs / 1000} 秒；继续查询 ${entityId}，未修改文件`,
      );
    throw error;
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}

// 整个 path 是一个业务系列；各段坐标保持分离，分段方式和指标保存于 properties。
export function importMapMark(spec, response, mapping) {
  validateImportIntent(spec, mapping, 'map_mark');
  const payload = decode(
    response.structuredContent ?? response.structured_content ?? response,
  );
  check(
    spec.coordinateSystem === 'GCJ-02' && mapping.coordinateSystem === 'GCJ-02',
    '需确认输入和 MapSpec 均为 GCJ-02',
  );
  const entityId = idPart(mapping.entityId);
  const matched = payload.entity_list?.filter(e => e.entity_id === entityId);
  check(
    matched?.length === 1 && matched[0].status === 'completed',
    '需要 completed 的唯一实体结果',
  );
  const entity = matched[0];
  check(entity.plan?.length, '没有可导入的 plan');
  const result = structuredClone(spec),
    warnings = [];
  const sourceId = `mapmark:${entityId}`;
  upsert(result.sources, {
    id: sourceId,
    provider: 'connector',
    title: entity.title || '地图规划结果',
    reference: 'map_mark',
    retrievedAt: mapping.retrievedAt || new Date().toISOString(),
  });
  const seen = new Set();
  function importPlans(plans, prefix = entityId) {
    for (const p of plans) {
      const scope = `${prefix}:${idPart(p.id)}`;
      check(!seen.has(scope), '重复 plan ID');
      seen.add(scope);
      const groupId =
        mapping.groups?.[scope] || mapping.groups?.[p.id] || scope;
      check(!seen.has(`group:${groupId}`), '多个 plan 映射到同一分组');
      seen.add(`group:${groupId}`);
      if (spec.contractRevision === 3)
        check(
          result.groups.some(g => g.id === groupId),
          `plan ${p.id} 没有映射到骨架分组，未写入文件`,
        );
      const oldGroup = result.groups.find(g => g.id === groupId);
      const group = {
        ...oldGroup,
        id: groupId,
        kind: oldGroup?.kind || mapping.groupKind || 'collection',
        title: oldGroup?.title || p.plan_name || p.id,
        members: [],
        routeIds: [],
      };
      const pointMap = new Map();
      for (const point of p.points || []) {
        const pid = idPart(point.id),
          placeId = `${scope}:place:${pid}`,
          memberId = `${scope}:member:${pid}`;
        check(!pointMap.has(pid), '重复 point ID');
        const position = [point.longitude, point.latitude];
        if (!validPoint(position)) {
          warnings.push(`${scope}/${pid}: 地点坐标缺失`);
          continue;
        }
        const oldPlace = result.entities.places.find(x => x.id === placeId);
        upsert(result.entities.places, {
          ...oldPlace,
          id: placeId,
          name: oldPlace?.name || point.text_name || point.name,
          position,
          sourceRefs: [...new Set([...(oldPlace?.sourceRefs || []), sourceId])],
          properties: {
            ...oldPlace?.properties,
            poiId: point.poi_id,
            address: point.address,
          },
        });
        const oldMember = oldGroup?.members?.find(x => x.id === memberId);
        const day = mapping.days?.[p.id] ?? oldMember?.day;
        check(
          day == null || (Number.isInteger(day) && day > 0),
          'day 必须为正整数',
        );
        group.members.push({
          ...oldMember,
          ...(day == null ? {} : { day }),
          id: memberId,
          placeId,
          role: oldMember?.role || 'visit',
          order: group.members.length + 1,
          routeIds: [],
        });
        pointMap.set(pid, memberId);
      }
      const pathsSeen = new Set();
      for (const path of p.paths || []) {
        const pathId = idPart(path.id);
        check(!pathsSeen.has(pathId), '重复 path ID');
        pathsSeen.add(pathId);
        const routeId = `${scope}:route:${pathId}`,
          lines = [],
          segments = [],
          memberIds = [];
        for (const segment of path.complex_lines || []) {
          if (
            !segment.point_ids?.length ||
            !segment.point_ids.every(id => pointMap.has(id)) ||
            segment.line?.length < 2 ||
            !segment.line?.every(validPoint)
          ) {
            warnings.push(`${routeId}/${segment.id}: 缺少地点关联或有效轨迹`);
            continue;
          }
          lines.push(segment.line);
          for (const id of segment.point_ids) {
            const mid = pointMap.get(id);
            if (!memberIds.includes(mid)) memberIds.push(mid);
          }
          segments.push({
            id: segment.id,
            memberIds: segment.point_ids.map(id => pointMap.get(id)),
            ...segment.attributes,
          });
        }
        if (!lines.length || memberIds.length < 2) {
          warnings.push(`${routeId}: 未导入路线`);
          continue;
        }
        const modes = [
          ...new Set(segments.map(s => s.transport_mod).filter(Boolean)),
        ];
        const oldRoute = result.entities.routes.find(x => x.id === routeId);
        const properties = {
          ...oldRoute?.properties,
          segments,
          mapMarkEntityId: entityId,
          geometryNotice: '工具返回轨迹，可能包含端点接线或降级示意段',
        };
        delete properties.distance;
        delete properties.duration;
        if (segments.every(s => Number.isFinite(s.distance) && s.distance >= 0))
          properties.distance = formatDistance(
            segments.reduce((n, s) => n + s.distance, 0),
          );
        if (segments.every(s => Number.isFinite(s.time) && s.time > 0))
          properties.duration = formatDuration(
            segments.reduce((n, s) => n + s.time, 0) * 60,
          );
        upsert(result.entities.routes, {
          ...oldRoute,
          id: routeId,
          name: oldRoute?.name || p.plan_name || p.id,
          mode: modes.length === 1 ? modes[0] : 'mixed',
          memberIds,
          geometry: {
            type: lines.length === 1 ? 'LineString' : 'MultiLineString',
            status: 'supplied',
            derivation: 'map_mark',
            coordinates: lines.length === 1 ? lines[0] : lines,
            sourceRefs: [sourceId],
          },
          properties,
          sourceRefs: [sourceId],
        });
        group.routeIds.push(routeId);
        for (const m of group.members)
          if (memberIds.includes(m.id)) m.routeIds.push(routeId);
      }
      if (!group.routeIds.length) {
        group.routeOptional = true;
        group.routeOptionalReason = '工具未返回可导入路线';
      } else {
        delete group.routeOptional;
        delete group.routeOptionalReason;
      }
      upsert(result.groups, group);
      if (p.child_plan?.length) importPlans(p.child_plan, scope);
    }
  }
  importPlans(entity.plan);
  const importedGroups = [...seen]
    .filter(x => x.startsWith('group:'))
    .map(x => x.slice(6));
  const imported = result.groups.filter(g => importedGroups.includes(g.id));
  if (payload.diagnostics?.tool_calls) {
    result.metadata ||= {};
    result.metadata.diagnostics = { tool_calls: mergeToolCalls(spec.metadata?.diagnostics?.tool_calls || [], payload.diagnostics.tool_calls) };
  }
  finishImportIntent(
    result,
    mapping,
    importedGroups,
    imported.flatMap(g => g.routeIds),
    imported.flatMap(g => g.members.map(m => m.placeId)),
  );
  return {
    spec: result,
    warnings,
    groupIds: [...seen]
      .filter(x => x.startsWith('group:'))
      .map(x => x.slice(6)),
  };
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href
) {
  try {
    const o = args();
    check(
      o.spec && o.mapping && o.out,
      '用法：--spec spec.json --mapping mapping.json --out spec.json [--response decoded.json]',
    );
    const mapping = await readJson(o.mapping);
    const spec = await readJson(o.spec);
    validateImportIntent(spec, mapping, 'map_mark');
    const response = o.response
      ? await readJson(o.response)
      : await fetchMapMark(mapping.entityId);
    const result = importMapMark(spec, response, mapping);
    await writeJson(o.out, result.spec);
    console.log(
      JSON.stringify({
        status: result.warnings.length ? 'partial_success' : 'success',
        output: o.out,
        groupIds: result.groupIds,
        warnings: result.warnings,
      }),
    );
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

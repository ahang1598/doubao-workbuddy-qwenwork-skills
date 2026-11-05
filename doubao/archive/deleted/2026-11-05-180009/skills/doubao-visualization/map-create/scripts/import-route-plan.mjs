import { mergeToolCalls } from '../lib/tool-diagnostics.mjs';
import { realpathSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { fetchRouteEntities } from '../lib/entity-gateway.mjs';
import {
  finishImportIntent,
  validateImportIntent,
} from '../lib/import-intent.mjs';

export { fetchRouteEntities } from '../lib/entity-gateway.mjs';

import { args, readJson, writeJson } from '../lib/cli-utils.mjs';
import {
  routePlanDescription,
  routePlanMetrics,
} from '../lib/route-plan-metrics.mjs';

const requireValue = (condition, message) => {
  if (!condition) throw new Error(message);
};
const samePoint = (a, b) => a[0] === b[0] && a[1] === b[1];
const nearPoint = (a, b) =>
  a.every((value, axis) => Math.abs(value - b[axis]) <= 0.00001);

function parsePath(path) {
  requireValue(
    typeof path === 'string' && path.trim(),
    '路线缺少 steps.path，不能生成真实轨迹',
  );
  const points = [];
  for (const token of path.split(';')) {
    const pair = token.split(',').map(part => part.trim());
    requireValue(pair.length === 2 && pair.every(Boolean), 'path 坐标格式无效');
    const point = pair.map(Number);
    requireValue(
      point.every(Number.isFinite) &&
        Math.abs(point[0]) <= 180 &&
        Math.abs(point[1]) <= 85 &&
        !samePoint(point, [0, 0]),
      'path 坐标无效',
    );
    if (!points.length || !samePoint(points.at(-1), point)) points.push(point);
  }
  requireValue(points.length >= 2, '每个 step 必须包含至少两个不同坐标');
  return points;
}

// 仅按明确映射更新已有 Route；行程安排、候选消歧和方案选择由调用者完成。
export function importRoutePlan(spec, response, mapping) {
  validateImportIntent(spec, mapping, 'route_plan_v2');
  requireValue(!response?.isError, 'MCP 返回错误');
  let payload = response?.structuredContent ?? response;
  if (typeof payload === 'string') payload = JSON.parse(payload);
  requireValue(
    !payload?.unresolved_waypoints?.length,
    '存在未解析途经点，先确认实际路线',
  );
  requireValue(
    Array.isArray(payload?.entity_list),
    '需要完整 structuredContent.entity_list，文本摘要不能代替轨迹',
  );
  requireValue(
    spec.coordinateSystem === 'GCJ-02' && mapping.coordinateSystem === 'GCJ-02',
    '仅接受已确认的 GCJ-02 轨迹；其他或未知坐标系须先可靠转换',
  );
  requireValue(
    Array.isArray(mapping.routes) && mapping.routes.length > 0,
    '缺少路线映射',
  );
  const source = mapping.source;
  requireValue(
    source?.id &&
      source?.title &&
      ['api', 'connector', 'demo'].includes(source.provider) &&
      source.retrievedAt &&
      Number.isFinite(Date.parse(source.retrievedAt)),
    'source 必须包含 id、title、provider、retrievedAt',
  );
  requireValue(
    source.reference === 'route_plan_v2',
    'source.reference 必须是 route_plan_v2',
  );
  const mock = response._mock === true || payload._mock === true;
  requireValue(
    !mock || source.provider === 'demo',
    '模拟响应必须使用 demo 来源，不能冒充真实查询',
  );
  requireValue(
    !spec.sources.some(
      item => item.id === source.id && item.reference !== source.reference,
    ),
    '来源 ID 冲突',
  );
  const result = structuredClone(spec);
  const seen = new Set();
  for (const selection of mapping.routes) {
    requireValue(!seen.has(selection.routeId), '同一 Route 不能重复映射');
    seen.add(selection.routeId);
    const matches = result.entities.routes.filter(
      item => item.id === selection.routeId,
    );
    requireValue(matches.length === 1, '目标 Route 必须唯一且已存在');
    const target = matches[0];
    requireValue(
      Array.isArray(target.memberIds) && target.memberIds.length >= 2,
      '目标 Route 缺少 memberIds',
    );
    const members = result.groups.flatMap(group => group.members || []);
    requireValue(
      target.memberIds.every(id => members.some(member => member.id === id)),
      'memberIds 必须引用已有 Group Member',
    );
    const entities = payload.entity_list.filter(
      item => item?.entity_id === selection.entityId,
    );
    requireValue(
      selection.entityId && entities.length === 1,
      '必须选择唯一的真实 entity_id',
    );
    const entity = entities[0];
    requireValue(
      ['driving', 'walking', 'cycling', 'transit'].includes(entity.mode),
      '不支持或缺少出行方式',
    );
    requireValue(
      target.mode === entity.mode,
      '方案出行方式与目标 Route 不一致',
    );
    const indexes =
      selection.routeIndexes ?? (entity.routes?.length === 1 ? [0] : undefined);
    requireValue(
      Array.isArray(indexes) &&
        indexes.length === 1 &&
        new Set(indexes).size === indexes.length,
      '每条目标路线必须选择一个 routeIndexes；不同候选分别映射',
    );
    const routes = indexes.map(index => {
      requireValue(
        Number.isInteger(index) && index >= 0 && entity.routes?.[index],
        'routeIndexes 超出范围',
      );
      return entity.routes[index];
    });
    const route = routes[0];
    const metrics = routePlanMetrics(route);
    const hasFlight = route.segments?.some(
      segment => segment.transit_mode === 'PLANE',
    );
    const hasTransportParts =
      hasFlight ||
      route.segments?.some(segment => segment.transit_mode === 'RAILWAY');
    if (route.segments?.length)
      requireValue(
        route.segments.length === route.steps?.length,
        '路线 segments 与 steps 不匹配，不能猜测分段位置',
      );
    const lines = [];
    const parts = [];
    let connectorCount = 0;
    for (const route of routes) {
      requireValue(
        Array.isArray(route.steps) && route.steps.length > 0,
        '选中路段缺少 steps，不用站点或摘要补线',
      );
      // 不跨 routes 合并，以免把独立方案或不同交通段连接起来。
      let current;
      for (const [index, step] of route.steps.entries()) {
        const segment = route.segments?.[index];
        const flight = hasFlight && segment.transit_mode === 'PLANE';
        // 航空段只能使用接口明确返回的机场位置，不使用请求的城市/机场替代。
        const points = flight
          ? parsePath(
              `${segment.start_location ?? segment.transit?.on_station?.location};${segment.end_location ?? segment.transit?.off_station?.location}`,
            )
          : parsePath(step?.path);
        if (flight) {
          const path = parsePath(step?.path);
          requireValue(
            nearPoint(path[0], points[0]) &&
              nearPoint(path.at(-1), points.at(-1)),
            '航空段与 steps 端点不匹配，不能覆盖其他交通轨迹',
          );
        }
        // 接线只连接同一候选的相邻分段，不移动原端点，不参与接口指标计算。
        if (current && !samePoint(current.at(-1), points[0])) {
          lines.push([current.at(-1), points[0]]);
          parts.push({ mode: 'connector', status: 'schematic' });
          connectorCount += 1;
        }
        if (
          !hasTransportParts &&
          current &&
          samePoint(current.at(-1), points[0])
        )
          points.slice(1).forEach(point => current.push(point));
        else {
          current = points;
          lines.push(current);
          // RAILWAY 只声明铁路，不根据方案标题或车次猜测高铁子类型。
          parts.push({
            mode: flight
              ? 'flight'
              : segment?.transit_mode === 'RAILWAY'
                ? 'train'
                : entity.mode,
            status: flight ? 'schematic' : mock ? 'supplied' : 'resolved',
          });
        }
      }
    }
    target.geometry = {
      type:
        hasTransportParts || lines.length > 1
          ? 'MultiLineString'
          : 'LineString',
      status:
        hasFlight || connectorCount
          ? 'schematic'
          : mock
            ? 'supplied'
            : 'resolved',
      derivation: mock ? 'route-plan-mock' : 'route_plan_v2',
      coordinates: hasTransportParts || lines.length > 1 ? lines : lines[0],
      ...(hasTransportParts || connectorCount ? { parts } : {}),
      sourceRefs: [source.id],
    };
    // 保留原行程描述；删除可能来自旧示意路线的指标，再写实际返回指标。
    const properties = { ...target.properties };
    for (const key of ['distance', 'duration', 'budget'])
      delete properties[key];
    for (const [field, output, unit] of [
      ['distance', 'distance', mapping.units?.distance],
      ['cost', 'budget', mapping.units?.cost],
    ]) {
      const values = routes.map(route => route[field]);
      requireValue(
        values.every(
          value =>
            value == null ||
            (typeof value === 'number' && Number.isFinite(value) && value >= 0),
        ),
        `${field} 数值无效`,
      );
      if (values.every(value => value != null) && unit) {
        requireValue(typeof unit === 'string', '指标单位必须是字符串');
        // 部分上游结构的 cost 默认值为 0，不能直接解释为免费。
        if (field !== 'cost' || values.every(value => value > 0))
          properties[output] = `${values.reduce((a, b) => a + b, 0)} ${unit}`;
      }
    }
    properties.duration = metrics.duration;
    properties.durationNote = metrics.durationNote;
    properties.durationBreakdown = metrics;
    properties.description = routePlanDescription(entity, metrics);
    if (hasFlight)
      properties.description += '；航空段为示意曲线，非实际飞行轨迹';
    if (connectorCount)
      properties.description += `；含${connectorCount}处直线接驳示意，非实际通行路径，未计入耗时、距离及费用`;
    properties.routePlan = {
      entityId: selection.entityId,
      routeIndexes: indexes,
      connectorCount,
      mock,
      reportedSummary: entity.simple_summary,
      rawMetrics: routes.map(({ distance, time, cost }) => ({
        distance,
        time,
        cost,
      })),
    };
    target.properties = properties;
    target.sourceRefs = [...new Set([...(target.sourceRefs || []), source.id])];
    for (const group of result.groups.filter(
      group => group.routeIds?.length === 1 && group.routeIds[0] === target.id,
    )) {
      group.summary ||= {};
      group.summary.description = properties.description;
      for (const view of result.views.filter(view => view.groupId === group.id))
        view.summary = { ...view.summary, description: properties.description };
    }
  }
  const sourceIndex = result.sources.findIndex(item => item.id === source.id);
  if (sourceIndex < 0) result.sources.push(structuredClone(source));
  else result.sources[sourceIndex] = structuredClone(source);
  const importedRoutes = mapping.routes.map(r => r.routeId);
  const importedGroups = result.groups.filter(g =>
    g.members.some(m =>
      result.entities.routes.some(
        r => importedRoutes.includes(r.id) && r.memberIds.includes(m.id),
      ),
    ),
  );
  if (payload.diagnostics?.tool_calls) {
    result.metadata ||= {};
    result.metadata.diagnostics = { tool_calls: mergeToolCalls(spec.metadata?.diagnostics?.tool_calls || [], payload.diagnostics.tool_calls) };
  }
  finishImportIntent(
    result,
    mapping,
    importedGroups.map(g => g.id),
    importedRoutes,
    importedGroups.flatMap(g =>
      g.members
        .filter(m =>
          result.entities.routes.some(
            r => importedRoutes.includes(r.id) && r.memberIds.includes(m.id),
          ),
        )
        .map(m => m.placeId),
    ),
  );
  return result;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href
) {
  try {
    const options = args();
    requireValue(
      options.spec && options.mapping && options.out,
      '用法：node import-route-plan.mjs --spec spec.json --mapping mapping.json --out routed-spec.json [--response response.json]',
    );
    const spec = await readJson(options.spec);
    const mapping = await readJson(options.mapping);
    validateImportIntent(spec, mapping, 'route_plan_v2');
    const response = options.response
      ? await readJson(options.response)
      : await fetchRouteEntities(mapping);
    const result = importRoutePlan(spec, response, mapping);
    await writeJson(options.out, result);
    process.stdout.write(
      `${JSON.stringify({ status: 'success', output: options.out, routesUpdated: mapping.routes.length })}\n`,
    );
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

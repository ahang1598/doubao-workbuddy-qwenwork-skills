import { importMapMark } from '../scripts/import-map-mark.mjs';
import { importRoutePlan } from '../scripts/import-route-plan.mjs';
import {
  recommendOverview,
  validateContract,
  verifyContractArtifacts,
  withReadingRepresentatives,
} from './engine.mjs';

const requireValue = (value, message) => {
  if (!value) throw new Error(message);
};
const validId = value =>
  typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(value);
export const isRoadTrip = task =>
  task.tool === 'map_mark' &&
  task.parameters?.map_data?.scene === 'travel_route';

const organizations = [
  'route',
  'itinerary',
  'days',
  'alternatives',
  'distribution',
];

export function prepareTask(input) {
  const task = structuredClone(input);
  requireValue(
    ['map_mark', 'route_plan_v2'].includes(task.tool),
    'tool 需为 map_mark 或 route_plan_v2',
  );
  requireValue(
    typeof task.title === 'string' && task.title.trim(),
    '缺少 title',
  );
  requireValue(
    organizations.includes(task.organization),
    '缺少明确的 organization',
  );
  requireValue(
    ['single', 'per-group'].includes(task.views),
    'views 需为 single 或 per-group',
  );
  requireValue(
    typeof task.reason === 'string' && task.reason.trim(),
    'reason 需说明组织及 View 决策依据',
  );
  requireValue(
    task.summary === undefined ||
      (typeof task.summary === 'string' && task.summary.trim()),
    'summary 需为非空的公开简介',
  );
  requireValue(
    task.round_trip == null || typeof task.round_trip === 'boolean',
    'round_trip 需为布尔值',
  );
  if (task.overviewPreference !== undefined) {
    const preference = task.overviewPreference;
    requireValue(
      preference && typeof preference === 'object' && !Array.isArray(preference) &&
        Object.keys(preference).every(key => ['mode', 'origin', 'reference'].includes(key)) &&
        ['content', 'collection'].includes(preference.mode) &&
        preference.origin === 'user-request' &&
        typeof preference.reference === 'string' && preference.reference.trim(),
      'overviewPreference 需包含 mode、origin:user-request 和用户原始要求 reference；模型判断不得冒充用户偏好',
    );
  }
  task.id ||= 'map-task';
  requireValue(validId(task.id), '任务 id 无效');
  requireValue(
    task.parameters &&
      typeof task.parameters === 'object' &&
      !Array.isArray(task.parameters),
    '缺少 parameters',
  );
  if (task.tool === 'map_mark') {
    const data = task.parameters.map_data;
    requireValue(
      data?.plans?.length && data.text?.trim(),
      'map_data 需要 text 和非空 plans',
    );
    data.title ||= task.title;
    // 旧输入只在未声明 scene 时映射；显式场景始终优先。
    if (data.scene === undefined && task.round_trip) data.scene = 'travel_route';
    requireValue(
      ['travel_plan', 'travel_route'].includes(data.scene),
      'map_data.scene 无效',
    );
    if (data.scene === 'travel_route')
      requireValue(
        ['route', 'itinerary', 'days'].includes(task.organization),
        '自驾行程需使用 route、itinerary 或 days 组织',
      );
    const ids = new Set();
    for (const [index, plan] of data.plans.entries()) {
      plan.id ||= `plan-${index + 1}`;
      requireValue(validId(plan.id) && !ids.has(plan.id), 'plan ID 无效或重复');
      ids.add(plan.id);
      requireValue(
        plan.name?.trim() && plan.points?.length,
        'plan 需要 name 和 points',
      );
      requireValue(
        plan.description == null || typeof plan.description === 'string',
        'plan.description 需为文本',
      );
      const pointIds = new Set();
      for (const [pointIndex, point] of plan.points.entries()) {
        point.id ||= `p${pointIndex + 1}`;
        requireValue(
          validId(point.id) && !pointIds.has(point.id) && point.name?.trim(),
          'point ID 或名称无效',
        );
        pointIds.add(point.id);
      }
    }
    requireValue(
      task.organization !== 'route' || data.plans.length === 1,
      'route 组织只接受一个 plan',
    );
  } else {
    requireValue(
      ['route', 'alternatives'].includes(task.organization),
      '交通路线使用 route 或 alternatives 组织',
    );
    requireValue(
      ['recommended', 'all'].includes(task.selection),
      'selection 需为 recommended 或 all',
    );
    requireValue(
      task.selection !== 'all' || task.organization === 'alternatives',
      '保留全部候选需明确 alternatives',
    );
    requireValue(
      (task.parameters.modes?.length || 0) <= 1 || task.selection === 'all',
      '多方式查询需 selection: all，避免丢失比较结果',
    );
    requireValue(
      task.parameters.origin && task.parameters.destination,
      '请明确起终点；当前位置须先取得可靠定位',
    );
    for (const anchor of [
      task.parameters.origin,
      ...(task.parameters.waypoints || []),
      task.parameters.destination,
    ]) {
      requireValue(
        ['place', 'id', 'coordinate', 'current_location'].includes(
          anchor?.type,
        ),
        '地点 type 无效',
      );
      if (['place', 'id'].includes(anchor.type))
        requireValue(anchor.value?.text?.trim(), '地点名称/ID 不能为空');
      if (anchor.type === 'coordinate')
        requireValue(
          [anchor.value?.longitude, anchor.value?.latitude].every(
            Number.isFinite,
          ) &&
            Math.abs(anchor.value.longitude) <= 180 &&
            Math.abs(anchor.value.latitude) <= 85 &&
            (anchor.value.longitude !== 0 || anchor.value.latitude !== 0),
          '坐标无效',
        );
      if (anchor.type === 'current_location')
        requireValue(
          Number.isFinite(task.parameters.locale_info?.longitude) &&
            Number.isFinite(task.parameters.locale_info?.latitude),
          '当前位置需要可靠 locale_info 坐标',
        );
    }
    if (task.parameters.modes)
      requireValue(
        Array.isArray(task.parameters.modes) &&
          task.parameters.modes.length &&
          task.parameters.modes.every(mode =>
            ['driving', 'walking', 'cycling', 'transit'].includes(mode),
          ),
        'modes 无效',
      );
    requireValue(
      (task.parameters.waypoints?.length || 0) <= 15,
      '途经点超过15个，请拆分请求',
    );
    requireValue(
      !(task.parameters.departure_time && task.parameters.arrival_time),
      '出发时间与到达时间互斥',
    );
    task.parameters.locale_info ||= {};
  }
  return task;
}

export function applyPlanDescriptions(spec, task) {
  if (task.tool !== 'map_mark') return;
  for (const plan of task.parameters.map_data.plans) {
    const description = plan.description?.trim();
    if (!description) continue;
    const group = spec.groups.find(item => item.id === plan.id);
    requireValue(group, `分组 ${plan.id} 不存在，不能绑定攻略`);
    group.summary = { ...group.summary, description };
    for (const view of spec.views.filter(
      item => item.kind === 'group-detail' && item.groupId === plan.id,
    ))
      view.summary = { ...view.summary, description };
  }
}

function createSpec(task) {
  const purpose = {
    days: 'itinerary',
    itinerary: 'itinerary',
    alternatives: 'comparison',
    distribution: 'distribution',
    route: 'route',
  }[task.organization];
  const supports = task.organization === 'distribution' ? [] : ['visit-order'];
  if (task.organization === 'days') supports.push('schedule');
  if (task.organization === 'alternatives') supports.push('alternatives');
  if (task.views === 'per-group') supports.push('view-split');
  return {
    specVersion: '2.0',
    contractRevision: 3,
    id: task.id,
    title: task.title,
    coordinateSystem: 'GCJ-02',
    sources: [],
    entities: { places: [], routes: [], regions: [] },
    groups: [],
    views: [],
    task: {
      purpose,
      ...(task.tool === 'map_mark'
        ? { travelScene: task.parameters.map_data.scene }
        : {}),
      ...(task.overviewPreference
        ? { overviewPreference: structuredClone(task.overviewPreference) }
        : {}),
      evidence: supports.length
        ? [
            {
              id: 'task-intent',
              origin: 'adopted-data',
              reference: `task-input.json: ${task.reason}`,
              supports,
              objectIds: [task.id],
            },
          ]
        : [],
      primaryContent: [],
    },
  };
}

function addGroup(spec, task, id, title, description) {
  const kind =
    { days: 'day', alternatives: 'alternative', distribution: 'collection' }[
      task.organization
    ] || 'route';
  const group = {
    id,
    kind,
    title,
    summary: { description },
    members: [],
    routeIds: [],
  };
  spec.groups.push(group);
  return group;
}

function addViews(spec, task) {
  spec.views = [
    {
      id: 'all',
      kind: 'overview',
      title: task.title,
      groupIds: spec.groups.map(group => group.id),
      ...(typeof task.summary === 'string' && task.summary.trim()
        ? { summary: { description: task.summary.trim() } }
        : {}),
    },
  ];
  if (task.views === 'per-group')
    spec.views.push(
      ...spec.groups.map(group => ({
        id: `view-${group.id}`,
        kind: 'group-detail',
        title: group.title,
        groupId: group.id,
        groupIds: [group.id],
        summary: group.summary,
      })),
    );
}

export function createTaskPlan(task, spec) {
  const overview = spec.views.find(view => view.kind === 'overview');
  const evidenceRefs =
    task.evidenceRefs ??
    (spec.task.evidence.some(item => item.id === 'task-intent')
      ? ['task-intent']
      : []);
  const recommendation = recommendOverview(spec, {
    scene: task.parameters?.map_data?.scene,
  });
  const { collectionEntries = [], ...overviewDecision } = recommendation || {};
  return {
    contractRevision: 3,
    planVersion: '1.0',
    mapSpecId: spec.id,
    dataSources: [],
    encodings: [],
    organization: {
      dimension: task.organization,
      evidenceRefs: [...evidenceRefs],
      ...(overview
        ? {
            overview: overviewDecision,
          }
        : {}),
      viewPurposes: Object.fromEntries(
        spec.views.map(view => [
          view.id,
          {
            reason: task.reason,
            evidenceRefs: [...evidenceRefs],
          },
        ]),
      ),
    },
    views: Object.fromEntries(
      spec.views.map(view => [
        view.id,
        {
          layers: [],
          filters: [],
          metrics: [],
          componentNodes:
            view.id === overview?.id
              ? collectionEntries.map(entry => ({
                  id: `collection-${entry.groupId}`,
                  componentId: 'collection-card',
                  binding: { source: 'group', groupId: entry.groupId },
                  presentation: { variant: 'bigger' },
                }))
              : [],
          ...(view.id === overview?.id && collectionEntries.length
            ? { collectionEntries }
            : {}),
        },
      ]),
    ),
  };
}

function checkMapResult(task, response, entityId) {
  const entity = response.entity_list?.find(
    item => item.entity_id === entityId,
  );
  requireValue(entity?.status === 'completed', '地图任务尚未成功');
  const submitted = task.parameters.map_data.plans;
  requireValue(Array.isArray(entity.plan), '返回 plan 需为数组');
  const submittedIds = new Set(submitted.map(plan => plan.id));
  const returned = entity.plan;
  const returnedIds = new Set(returned.map(plan => plan.id));
  const missing = submitted.filter(plan => !returnedIds.has(plan.id));
  const unexpected = returned.filter(plan => !submittedIds.has(plan.id));
  const duplicateIds = [...returnedIds].filter(id =>
    returned.filter(plan => plan.id === id).length > 1,
  );
  const describePlan = plan =>
    `${JSON.stringify(plan.name || plan.plan_name || '未命名分组')}（${plan.id ?? '缺少 ID'}）`;
  const planErrors = [];
  if (missing.length)
    planErrors.push(`缺失分组：${missing.map(describePlan).join('、')}`);
  if (unexpected.length)
    planErrors.push(`未提交的分组：${unexpected.map(describePlan).join('、')}`);
  if (duplicateIds.length)
    planErrors.push(`重复分组：${duplicateIds.map(id => describePlan(submitted.find(plan => plan.id === id) || returned.find(plan => plan.id === id))).join('、')}`);
  for (const plan of returned)
    if (plan.child_plan?.length)
      planErrors.push(`分组 ${describePlan(plan)} 包含未支持的嵌套分组`);
  requireValue(
    !planErrors.length,
    `返回分组不匹配：提交 ${submitted.length} 组，服务返回 ${entity.plan.length} 组。\n${planErrors.join('\n')}\n请检查服务响应与提交分组的映射，不要修改 scene 或行程绕过。`,
  );
  entity.plan = submitted.map(input => returned.find(plan => plan.id === input.id));
  const pointErrors = [];
  for (const plan of entity.plan) {
    const input = submitted.find(item => item.id === plan.id);
    requireValue(
      input && !plan.child_plan?.length,
      '返回未支持的分组结构，未生成 Spec',
    );
    const points = plan.points || [];
    requireValue(Array.isArray(points), `分组 ${plan.id} points 需为数组`);
    const inputIds = new Set(input.points.map(point => point.id));
    const returnedIds = new Set(points.map(point => point.id));
    const missing = input.points.filter(point => !returnedIds.has(point.id));
    const unexpected = points.filter(point => !inputIds.has(point.id));
    const duplicateIds = [...returnedIds].filter(
      id => points.filter(point => point.id === id).length > 1,
    );
    const describePoint = point =>
      `${JSON.stringify(point.name || '未命名地点')}（${point.id ?? '缺少 ID'}）`;
    const details = [];
    if (missing.length)
      details.push(`服务未返回地点：${missing.map(describePoint).join('、')}`);
    if (unexpected.length)
      details.push(
        `返回未提交的地点 ID：${unexpected.map(describePoint).join('、')}`,
      );
    if (duplicateIds.length)
      details.push(`返回重复地点 ID：${duplicateIds.join('、')}`);
    if (details.length)
      pointErrors.push(
        `分组 ${JSON.stringify(input.name)}（${plan.id}）：提交 ${input.points.length} 个地点，返回 ${points.length} 个；${details.join('；')}`,
      );
  }
  requireValue(
    !pointErrors.length,
    `地图地点缺失或不匹配：\n${pointErrors.join('\n')}\n请核实缺失地点名称，必要时补充城市或景区限定后重试；ID 不匹配时请检查服务返回结果。`,
  );
  return entity;
}

export function createMapMarkSpec(task, response, entityId, retrievedAt) {
  const unordered = task.organization === 'distribution';
  response = structuredClone(response);
  const entity = checkMapResult(task, response, entityId);
  // 后端数组顺序不作为访问顺序；按已提交的稳定 ID 恢复输入顺序。
  for (const plan of entity.plan) {
    const input = task.parameters.map_data.plans.find(
      item => item.id === plan.id,
    );
    plan.points = input.points.map(point =>
      plan.points.find(item => item.id === point.id),
    );
    // 行程只导入地点和路线；单点方案可能附带区域及无轨迹的占位路线。
    plan.regions = [];
    if (unordered) plan.paths = [];
    if (plan.points.length === 1)
      plan.paths = (plan.paths || []).filter(
        path =>
          !(
            path.complex_lines?.length > 0 &&
            path.complex_lines.every(
              segment =>
                segment.point_ids?.length === 1 &&
                segment.point_ids[0] === plan.points[0].id &&
                Array.isArray(segment.line) &&
                segment.line.length === 0,
            )
          ),
      );
  }
  const spec = createSpec(task);
  const mapping = {
    entityId,
    coordinateSystem: 'GCJ-02',
    retrievedAt,
    groups: {},
    days: {},
    order: unordered
      ? { purpose: 'none' }
      : { purpose: 'visit', evidenceRef: 'task-intent' },
    primaryKinds: unordered ? ['place'] : ['route', 'place'],
  };
  for (const [index, plan] of task.parameters.map_data.plans.entries()) {
    addGroup(
      spec,
      task,
      plan.id,
      plan.name,
      plan.points.map(point => point.name).join(unordered ? '、' : ' → '),
    );
    mapping.groups[plan.id] = plan.id;
    if (task.organization === 'days') mapping.days[plan.id] = index + 1;
  }
  addViews(spec, task);
  const result = importMapMark(spec, response, mapping);
  requireValue(
    !result.warnings.length,
    `地图数据不完整：${result.warnings.join('; ')}`,
  );
  for (const plan of task.parameters.map_data.plans) {
    const group = result.spec.groups.find(item => item.id === plan.id);
    const connected = plan.points.filter(point => point.level !== 'recommend');
    requireValue(
      unordered || connected.length < 2 || group.routeIds.length > 0,
      `分组 ${plan.id} 缺少路线`,
    );
    for (const point of connected) {
      const member = group.members.find(item =>
        item.id.endsWith(`:member:${point.id}`),
      );
      requireValue(
        unordered || connected.length < 2 || member?.routeIds.length,
        `地点 ${point.name} 未关联路线`,
      );
    }
    for (const member of group.members) {
      const point = plan.points.find(item =>
        member.id.endsWith(`:member:${item.id}`),
      );
      if (point?.level === 'recommend') {
        delete member.order;
        delete member.orderPurpose;
        delete member.orderEvidenceRef;
        member.role = 'poi';
      }
    }
  }
  return validateSpec(withReadingRepresentatives(result.spec));
}

export function checkRouteResolution(payload) {
  requireValue(
    !payload.unresolved_waypoints?.length,
    '存在未解析途经点，请明确地点后重试',
  );
  requireValue(
    !payload.origin_alternatives?.length &&
      !payload.destination_alternatives?.length,
    '存在地点候选，请明确起终点后重试',
  );
}

function routePlaces(task, payload) {
  checkRouteResolution(payload);
  const waypoints = payload.waypoints || [];
  requireValue(
    waypoints.length === (task.parameters.waypoints?.length || 0),
    '返回途经点不完整，不能忽略',
  );
  return [payload.origin, ...waypoints, payload.destination].map(
    (anchor, index) => {
      const value = anchor?.value;
      const position = [value?.longitude, value?.latitude];
      requireValue(
        position.every(Number.isFinite) &&
          Math.abs(position[0]) <= 180 &&
          Math.abs(position[1]) <= 85 &&
          position.some(number => number !== 0),
        `第 ${index + 1} 个地点缺少可靠坐标，不从轨迹端点推算`,
      );
      const requested = [
        task.parameters.origin,
        ...(task.parameters.waypoints || []),
        task.parameters.destination,
      ][index];
      const name =
        value.text?.trim() ||
        requested.value?.text?.trim() ||
        (index === 0
          ? '起点'
          : index === waypoints.length + 1
            ? '终点'
            : `途经点 ${index}`);
      return { name, position };
    },
  );
}

export function selectRouteEntities(task, payload) {
  checkRouteResolution(payload);
  const entities = payload.entity_list;
  requireValue(
    Array.isArray(entities) && entities.length,
    '路线规划未返回实体',
  );
  if (task.selection === 'all' && task.parameters.modes?.length) {
    requireValue(
      task.parameters.modes.every(mode =>
        entities.some(entity => entity.mode === mode),
      ),
      '部分交通方式没有返回路线，不能当作完整比较',
    );
  }
  const selected = task.selection === 'all' ? entities : entities.slice(0, 1);
  requireValue(
    selected.every(entity => validId(entity.entity_id)) &&
      new Set(selected.map(entity => entity.entity_id)).size ===
        selected.length,
    '路线实体 ID 缺失或重复',
  );
  return selected;
}

export function createRouteSpec(task, payloads, retrievedAt) {
  const spec = createSpec(task);
  const source = {
    id: 'route-query',
    provider: 'connector',
    title: '路线规划结果',
    reference: 'route_plan_v2',
    retrievedAt,
  };
  const mapping = {
    coordinateSystem: 'GCJ-02',
    source,
    units: { distance: '米', duration: '秒', cost: '元' },
    primaryKinds: ['route', 'place'],
    routes: [],
  };
  const entities = [];
  const sharedPlaces = new Map();
  for (const payload of payloads) {
    const points = routePlaces(task, payload);
    requireValue(
      payload.entity_list?.length === 1,
      '每次实体查询应返回唯一实体',
    );
    const entity = payload.entity_list[0];
    entities.push(entity);
    requireValue(entity.routes?.length, '实体没有路线');
    requireValue(
      entity.routes.length === 1 || task.selection === 'all',
      '实体有多个候选，需要明确比较选择',
    );
    for (const [routeIndex, route] of entity.routes.entries()) {
      const groupId = `route-${mapping.routes.length + 1}`;
      const transportSegments = (route.segments || [])
        .map((segment, index) => ({ ...segment, index }))
        .filter(segment => segment.transit && segment.transit_mode !== 'WALK');
      const primary =
        transportSegments.find(segment => segment.transit_mode === 'PLANE') ||
        transportSegments.find(segment => segment.transit_mode === 'RAILWAY');
      const transport =
        primary?.transit_mode === 'PLANE'
          ? '飞机'
          : primary?.transit_mode === 'RAILWAY'
            ? /^[GDC]\d/.test(primary.transit.name || '')
              ? '高铁 / 动车'
              : '普通火车'
            : {
                driving: '自驾',
                walking: '步行',
                cycling: '骑行',
                transit: '公共交通',
              }[entity.mode];
      const label = `${transport}${primary?.transit.name ? ` · ${primary.transit.name}` : ''} · 方案 ${mapping.routes.length + 1}`;
      const group = addGroup(
        spec,
        task,
        groupId,
        label,
        entity.simple_summary || label,
      );
      for (const [index, point] of points.entries()) {
        const identity = JSON.stringify([point.name, point.position]);
        const placeId =
          sharedPlaces.get(identity) || `${groupId}-p${index + 1}`;
        const memberId = `${groupId}-m${index + 1}`;
        if (!sharedPlaces.has(identity))
          spec.entities.places.push({
            id: placeId,
            ...point,
            sourceRefs: [source.id],
          });
        sharedPlaces.set(identity, placeId);
        group.members.push({
          id: memberId,
          placeId,
          role:
            index === 0
              ? 'origin'
              : index === points.length - 1
                ? 'destination'
                : 'waypoint',
          order: index + 1,
          orderPurpose: 'display',
          routeIds: [groupId],
          properties: {
            transport,
            description: `${index === 0 ? '出发地' : index === points.length - 1 ? '目的地' : '途经地'}：${point.name}`,
          },
        });
      }
      const transferMembers = [];
      for (
        let segmentIndex = 1;
        segmentIndex < transportSegments.length;
        segmentIndex += 1
      ) {
        const incoming = transportSegments[segmentIndex - 1];
        const outgoing = transportSegments[segmentIndex];
        const station = outgoing.transit.on_station;
        const position = String(
          station?.location || outgoing.start_location || '',
        )
          .split(',')
          .map(Number);
        if (
          !station?.name ||
          position.length !== 2 ||
          !position.every(Number.isFinite) ||
          Math.abs(position[0]) > 180 ||
          Math.abs(position[1]) > 85 ||
          position.every(value => value === 0)
        )
          continue;
        const identity = JSON.stringify(['station', station.name, position]);
        const placeId =
          sharedPlaces.get(identity) || `${groupId}-transfer-${segmentIndex}`;
        if (!sharedPlaces.has(identity))
          spec.entities.places.push({
            id: placeId,
            name: station.name,
            position,
            sourceRefs: [source.id],
          });
        sharedPlaces.set(identity, placeId);
        transferMembers.push({
          id: `${groupId}-transfer-${segmentIndex}`,
          placeId,
          role: 'transfer',
          orderPurpose: 'display',
          routeIds: [groupId],
          transfer: {
            incomingRouteId: groupId,
            outgoingRouteId: groupId,
            incomingSegmentIndex: incoming.index,
            outgoingSegmentIndex: outgoing.index,
          },
          properties: {
            transport: `${incoming.transit.name} → ${outgoing.transit.name}`,
            description: `${incoming.transit.name} → ${outgoing.transit.name}`,
            detail: `${incoming.transit.off_station?.name === station.name ? `在${station.name}换乘` : `从${incoming.transit.off_station?.name || '上一段下车点'}接驳至${station.name}`}，乘坐${outgoing.transit.name}前往${outgoing.transit.off_station?.name || outgoing.transit.estop || '下一站'}。接驳与候乘时间以实际信息为准。`,
          },
        });
      }
      group.members.splice(group.members.length - 1, 0, ...transferMembers);
      group.members.forEach((member, index) => {
        member.order = index + 1;
      });
      group.routeIds = [groupId];
      spec.entities.routes.push({
        id: groupId,
        name: label,
        mode: entity.mode,
        relation: 'transport',
        memberIds: group.members.map(member => member.id),
        properties: {
          description: entity.simple_summary || '',
          transport,
          detail: entity.detail_summary || '',
          policies: route.policies,
          segments: route.segments,
          departureTime: entity.departure_time,
          arrivalTime: entity.arrival_time,
          timeContext: entity.time_context,
          restriction: entity.restriction_info,
          preference: entity.preference,
          routePolicy: entity.route_policy,
        },
      });
      mapping.routes.push({
        routeId: groupId,
        entityId: entity.entity_id,
        routeIndexes: [routeIndex],
      });
    }
  }
  addViews(spec, task);
  const result = importRoutePlan(spec, { entity_list: entities }, mapping);
  for (const group of result.groups) {
    const route = result.entities.routes.find(
      candidate => candidate.id === group.routeIds[0],
    );
    const properties = route.properties;
    group.summary = {
      description: `${properties.transport} · ${pointsLabel(result, group)}`,
      transport: properties.transport,
      duration: properties.duration,
      ...(properties.budget ? { budget: properties.budget } : {}),
    };
    for (const member of group.members) {
      Object.assign(member.properties, {
        journeyDuration: properties.duration,
        journeyBudget: properties.budget,
        durationNote: properties.durationNote,
      });
    }
    const detail = result.views.find(view => view.groupId === group.id);
    if (detail) detail.summary = group.summary;
  }
  return validateSpec(result);
}

function pointsLabel(spec, group) {
  return [group.members[0], group.members.at(-1)]
    .map(
      member =>
        spec.entities.places.find(place => place.id === member.placeId)?.name,
    )
    .join(' → ');
}

function validateSpec(spec) {
  verifyContractArtifacts();
  const errors = validateContract('mapSpec', spec);
  requireValue(
    !errors.length,
    errors.map(error => `${error.path}: ${error.message}`).join('\n'),
  );
  return spec;
}

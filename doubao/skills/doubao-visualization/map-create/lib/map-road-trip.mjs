import { connectionMode } from './round-trip-routes.mjs';
import { formatDistance, formatDuration } from './route-plan-metrics.mjs';

const check = (ok, message) => {
  if (!ok) throw new Error(`ROAD_TRIP_INVALID: ${message}`);
};
const poiId = place => String(place.properties?.poiId ?? '').trim();
const samePosition = (a, b) =>
  a.position?.length === 2 &&
  b.position?.length === 2 &&
  a.position.every(
    (value, index) => Number.isFinite(value) && value === b.position[index],
  );

// 缺失 ID 与存在 ID 不混合判重；不按名称、距离或坐标精度猜测同一地点。
export function sameTripPlace(a, b) {
  const left = poiId(a),
    right = poiId(b);
  return left && right ? left === right : !left && !right && samePosition(a, b);
}

export function roadTripConnections(spec) {
  const places = new Map(spec.entities.places.map(place => [place.id, place]));
  const days = spec.groups.map(group => {
    check(
      group.routeIds.length <= 1,
      `分组 ${group.id} 有多条 path，不能自动解释为连续行程`,
    );
    const members = group.members.filter(
      member => member.orderPurpose === 'visit',
    );
    // 纯展示日保留视图，不作为跨天路线端点。
    if (!members.length) return null;
    return {
      group,
      first: places.get(members[0].placeId),
      last: places.get(members.at(-1).placeId),
    };
  }).filter(Boolean);
  const connections = [];
  for (let index = 0; index < days.length - 1; index++) {
    const current = days[index],
      next = days[index + 1];
    if (sameTripPlace(current.last, next.first)) continue;
    connections.push({
      id: `link-${index + 1}`,
      groupId: next.group.id,
      prepend: true,
      origin: current.last,
      destination: next.first,
      mode: connectionMode(current.last.position, next.first.position),
    });
  }
  return { connections };
}

function addConnection(spec, link, result) {
  const group = spec.groups.find(item => item.id === link.groupId);
  const sourceId = `connection-${link.id}`;
  spec.sources.push({
    id: sourceId,
    provider: 'connector',
    title: result.degraded
      ? '补线失败，使用端点直线示意'
      : '跨天路线规划',
    reference: 'route_plan_v2',
    retrievedAt: result.retrievedAt,
    ...(result.error ? { error: result.error } : {}),
  });
  const addition = {
    id: sourceId,
    name: `${link.origin.name} → ${link.destination.name}`,
    mode: result.mode,
    geometry: { ...result.geometry, sourceRefs: [sourceId] },
    sourceRefs: [sourceId],
    properties: {
      segments: [
        {
          id: sourceId,
          mode: result.mode,
          geometryStatus: result.geometry.status,
          ...(result.degraded
            ? { degraded: true, description: '路线示意，非实际通行路径' }
            : {}),
          ...(result.distance == null ? {} : { distance: result.distance }),
          ...(result.duration == null ? {} : { time: result.duration / 60 }),
        },
      ],
      ...(result.distance == null
        ? {}
        : { distance: formatDistance(result.distance) }),
      ...(result.duration == null
        ? {}
        : { duration: formatDuration(result.duration) }),
    },
  };
  const targets = [link.origin, link.destination];
  const ordered = group.members.filter(
    member => member.orderPurpose === 'visit',
  );
  const members = targets.map((target, index) => {
    if (index === 1) {
      const member = ordered[0];
      check(
        member?.placeId === targets[index].id,
        `连接 ${link.id} 的访问顺序不匹配`,
      );
      return member;
    }
    const member = {
      id: `${group.id}:connection:${link.id}:${index}`,
      placeId: targets[index].id,
      role: 'waypoint',
      order: 0,
      orderPurpose: 'visit',
      orderEvidenceRef: 'task-intent',
      ...(ordered[0]?.day == null ? {} : { day: ordered[0].day }),
      routeIds: [],
    };
    group.members.unshift(member);
    return member;
  });
  addition.memberIds = members.map(member => member.id);
  addition.properties.segments[0].memberIds = addition.memberIds;
  let route = spec.entities.routes.find(item => item.id === group.routeIds[0]);
  if (!route) {
    addition.name = group.title;
    spec.entities.routes.push(addition);
    group.routeIds = [addition.id];
    route = addition;
  } else {
    const pair = [addition, route];
    const lines = pair.flatMap(item =>
      item.geometry.type === 'LineString'
        ? [item.geometry.coordinates]
        : item.geometry.coordinates,
    );
    const segments = pair.flatMap(item => item.properties.segments || []);
    const completeSegments = pair.every(
      item => item.properties.segments?.length,
    );
    const ids = [...pair[0].memberIds, ...pair[1].memberIds.slice(1)];
    const parts = pair.flatMap(
      item =>
        item.geometry.parts ||
        (item.geometry.type === 'LineString'
          ? [item.geometry.coordinates]
          : item.geometry.coordinates
        ).map(() => ({ mode: item.mode, status: item.geometry.status })),
    );
    route.geometry = {
      ...route.geometry,
      type: 'MultiLineString',
      coordinates: lines,
      parts,
      status: parts.some(part => part.status === 'schematic')
        ? 'schematic'
        : 'supplied',
      sourceRefs: [
        ...new Set(pair.flatMap(item => item.geometry.sourceRefs || [])),
      ],
    };
    route.sourceRefs = [
      ...new Set(pair.flatMap(item => item.sourceRefs || [])),
    ];
    route.memberIds = ids;
    route.mode = pair[0].mode === pair[1].mode ? pair[0].mode : 'mixed';
    route.properties.segments = segments;
    delete route.properties.distance;
    delete route.properties.duration;
    if (
      completeSegments &&
      segments.every(
        segment => Number.isFinite(segment.distance) && segment.distance >= 0,
      )
    )
      route.properties.distance = formatDistance(
        segments.reduce((sum, segment) => sum + segment.distance, 0),
      );
    if (
      completeSegments &&
      segments.every(
        segment => Number.isFinite(segment.time) && segment.time > 0,
      )
    )
      route.properties.duration = formatDuration(
        segments.reduce((sum, segment) => sum + segment.time, 0) * 60,
      );
  }
  delete group.routeOptional;
  delete group.routeOptionalReason;
}

export function finishRoadTrip(spec, connections, results = []) {
  check(
    !connections.length || results?.length === connections.length,
    '补线结果数量不匹配',
  );
  spec = structuredClone(spec);
  for (const [index, link] of connections.entries())
    addConnection(spec, link, results[index]);
  const unique = [],
    aliases = new Map();
  for (const place of spec.entities.places) {
    const prior = unique.find(item => sameTripPlace(item, place));
    aliases.set(place.id, prior?.id || place.id);
    if (!prior) unique.push(place);
    else
      prior.sourceRefs = [
        ...new Set([...(prior.sourceRefs || []), ...(place.sourceRefs || [])]),
      ];
  }
  spec.entities.places = unique;
  const allMembers = spec.groups.flatMap(group => group.members);
  for (const member of allMembers) member.placeId = aliases.get(member.placeId);
  const tripOrders = new Map();
  for (const group of spec.groups) {
    let order = 0;
    for (const member of group.members) {
      if (member.orderPurpose === 'visit') member.order = ++order;
      if (member.orderPurpose === 'visit') {
        if (!tripOrders.has(member.placeId))
          tripOrders.set(member.placeId, tripOrders.size + 1);
        member.properties = {
          ...member.properties,
          tripOrder: tripOrders.get(member.placeId),
        };
      }
      member.routeIds = spec.entities.routes
        .filter(route => route.memberIds.includes(member.id))
        .map(route => route.id);
      if (member.routeIds.length) {
        const route = spec.entities.routes.find(
          item => item.id === member.routeIds[0],
        );
        member.role =
          route.memberIds[0] === member.id
            ? 'origin'
            : route.memberIds.at(-1) === member.id
              ? 'destination'
              : 'waypoint';
      }
      if (member.orderPurpose === 'visit' &&
          allMembers.filter(item => item.placeId === member.placeId && item.orderPurpose === 'visit').length > 1)
        member.properties = { ...member.properties, sharedTripMarker: true };
    }
  }
  // 同一地点兼有行程访问和纯展示记录时，总览使用普通共享节点；
  // 每日访问顺序仍由 order 表达，展示日不继承路线编号。
  const displayPlaces = new Set(allMembers
    .filter(member => member.orderPurpose !== 'visit')
    .map(member => member.placeId));
  for (const member of allMembers) {
    if (!displayPlaces.has(member.placeId)) continue;
    if (member.properties) delete member.properties.tripOrder;
    if (allMembers.filter(item => item.placeId === member.placeId).length > 1)
      member.properties = { ...member.properties, sharedTripMarker: true };
  }
  const places = new Map(spec.entities.places.map(place => [place.id, place]));
  for (const group of spec.groups) {
    const description = group.members
      .filter(member => member.orderPurpose === 'visit')
      .map(member => places.get(member.placeId).name)
      .join(' → ');
    group.summary = { ...group.summary, description };
    for (const route of spec.entities.routes.filter(item =>
      group.routeIds.includes(item.id),
    ))
      route.properties.description = description;
  }
  spec.task.primaryContent = [
    ...spec.entities.places.map(place => ({ kind: 'place', id: place.id })),
    ...spec.entities.routes.map(route => ({ kind: 'route', id: route.id })),
  ];
  for (const view of spec.views) {
    if (view.kind === 'overview') continue;
    const groupIds = [
      ...new Set([view.groupId, ...(view.groupIds || [])].filter(Boolean)),
    ];
    if (groupIds.length !== 1) continue;
    const group = spec.groups.find(item => item.id === groupIds[0]);
    if (group) view.summary = { ...view.summary, ...group.summary };
  }
  return spec;
}

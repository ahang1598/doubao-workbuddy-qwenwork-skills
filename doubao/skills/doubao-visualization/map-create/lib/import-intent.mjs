import { validateContract, verifyContractArtifacts } from './engine.mjs';

const reject = errors => {
  if (errors.length)
    throw new Error(`IMPORT_CONFIG_INVALID:\n${errors.join('\n')}`);
};
export const groupOrder = (mapping, id) =>
  mapping.memberOrders?.[id] ?? mapping.order;
const supports = (spec, ref, purpose, id) =>
  spec.task?.evidence?.some(
    e =>
      e.id === ref &&
      e.supports?.includes(purpose) &&
      (e.objectIds?.includes(id) || e.objectIds?.includes(spec.id)),
  );

// 骨架中的意图由模型决定。网络请求前一次报告缺失配置，不推断旅游/分日场景。
export function validateImportIntent(spec, mapping, tool) {
  if (spec.contractRevision !== 3) return;
  const errors = [];
  if (!spec.task?.purpose) errors.push('spec.task.purpose 缺失');
  if (!Array.isArray(spec.task?.evidence))
    errors.push('spec.task.evidence 缺失');
  if (!Array.isArray(spec.task?.primaryContent))
    errors.push('spec.task.primaryContent 必须是数组，可先留空');
  if (!spec.views?.length) errors.push('先在 spec.views 确定展示范围');
  if (
    !Array.isArray(mapping.primaryKinds) ||
    mapping.primaryKinds.some(k => !['place', 'route'].includes(k))
  )
    errors.push(
      'mapping.primaryKinds 必须声明导入的主要内容类型，例如 ["route"]；仅补充数据可用 []',
    );
  const groupIds =
    tool === 'map_mark'
      ? Object.values(mapping.groups || {})
      : spec.groups
          .filter(g =>
            g.members.some(m =>
              mapping.routes?.some(s =>
                spec.entities.routes
                  .find(r => r.id === s.routeId)
                  ?.memberIds.includes(m.id),
              ),
            ),
          )
          .map(g => g.id);
  if (tool === 'map_mark' && !groupIds.length)
    errors.push('mapping.groups 必须将工具 plan ID 映射到已有骨架分组');
  for (const id of new Set(groupIds)) {
    const group = spec.groups.find(g => g.id === id);
    if (!group) {
      errors.push(`分组 ${id} 不在骨架中`);
      continue;
    }
    const order = groupOrder(mapping, id);
    if (
      tool === 'map_mark' ||
      group.members.some(m => m.order !== undefined && !m.orderPurpose)
    ) {
      if (!['visit', 'display', 'rank', 'none'].includes(order?.purpose))
        errors.push(`分组 ${id} 缺少 order.purpose（visit/display/rank/none）`);
      if (
        order?.purpose === 'visit' &&
        !supports(spec, order.evidenceRef, 'visit-order', id)
      )
        errors.push(`分组 ${id} 的访问顺序缺少适用的 evidenceRef`);
    }
    if (
      group.kind === 'day' &&
      !spec.task?.evidence?.some(
        e =>
          ['user-request', 'adopted-data'].includes(e.origin) &&
          e.supports?.includes('schedule') &&
          e.objectIds?.includes(spec.id),
      )
    )
      errors.push(`分组 ${id} 分日缺少任务级 schedule 依据`);
    if (!spec.views.some(v => [v.groupId, ...(v.groupIds || [])].includes(id)))
      errors.push(`分组 ${id} 未关联任何 View；在骨架 View 中填写 groupIds`);
  }
  reject(errors);
}

export function finishImportIntent(
  spec,
  mapping,
  groupIds,
  routeIds,
  placeIds,
) {
  if (spec.contractRevision !== 3) return spec;
  for (const g of spec.groups.filter(g => groupIds.includes(g.id))) {
    const order = groupOrder(mapping, g.id);
    for (const m of g.members) {
      if (m.order !== undefined && !m.orderPurpose) {
        if (order?.purpose === 'none') {
          delete m.order;
          delete m.orderEvidenceRef;
        } else {
          m.orderPurpose = order?.purpose;
          if (order?.purpose === 'visit')
            m.orderEvidenceRef = order.evidenceRef;
        }
      }
      const routes = spec.entities.routes.filter(r =>
        r.memberIds.includes(m.id),
      );
      if (!m.role || m.role === 'visit')
        m.role = !routes.length
          ? 'poi'
          : routes.some(r => r.memberIds[0] === m.id)
            ? 'origin'
            : routes.some(r => r.memberIds.at(-1) === m.id)
              ? 'destination'
              : 'waypoint';
      m.routeIds = routes.map(r => r.id);
    }
  }
  for (const kind of mapping.primaryKinds || []) {
    for (const id of new Set(kind === 'route' ? routeIds : placeIds)) {
      if (!spec.task.primaryContent.some(r => r.kind === kind && r.id === id))
        spec.task.primaryContent.push({ kind, id });
    }
  }
  // 保留用户选定的 View；只展开它已引用分组中的数据，不新增 View 或更改 kind。
  for (const v of spec.views) {
    const selected = spec.groups.filter(
      g =>
        groupIds.includes(g.id) &&
        [v.groupId, ...(v.groupIds || [])].includes(g.id),
    );
    if (!selected.length) continue;
    v.groupIds = [
      ...new Set([...(v.groupIds || []), ...(v.groupId ? [v.groupId] : [])]),
    ];
    // 不写 placeIds：分组成员与裸地点同时绑定会重复绘点。
  }
  verifyContractArtifacts();
  const diagnostics = validateContract('mapSpec', spec);
  const errors = diagnostics.map(d => `${d.path}: ${d.message}`);
  for (const g of spec.groups)
    for (const m of g.members) {
      if (m.order !== undefined && !m.orderPurpose)
        errors.push(`${m.id}: orderPurpose 缺失`);
      if (
        m.orderPurpose === 'visit' &&
        !supports(spec, m.orderEvidenceRef, 'visit-order', g.id)
      )
        errors.push(`${m.id}: 访问顺序依据不适用`);
    }
  reject(errors);
  return spec;
}

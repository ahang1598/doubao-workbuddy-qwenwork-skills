// Executed inside the inspected page. Read the current native overlays and
// measured UI independently of fitState.safeRect/outside; never mutate a map.
export function inspectElevatedGeometry() {
  const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
  const runtime = window.mapCreateRuntime;
  const view = graph.views.find(
    item => item.id === window.mapCreateState.activeViewId,
  );
  const elements = runtime.layer
    .getElements()
    .filter(
      element =>
        element.visible !== false &&
        element.type === 'heatmap' &&
        element.mode === 'hexbin-3d',
    );
  const result = {
    status: 'not-applicable',
    projectionStatus: null,
    coverage: 'not-run',
    cells: [],
    reservations: [],
    errors: [],
  };
  if (!elements.length) return result;
  if (
    !graph.runtimeRequirements?.capabilities?.includes(
      'heatmap.elevated-projection@1',
    )
  )
    return { ...result, status: 'legacy-ground-only' };
  const requiresFit =
    view.viewport.strategy === 'fit-elements' &&
    view.viewport.fitOnActivate !== false &&
    window.mapCreateState.cameraContext?.follow !== false;
  const projectionScope = requiresFit
    ? view.viewport.elementIds || view.elementIds
    : view.elementIds;
  const projection = runtime.layer.getElevatedGeometry(projectionScope);
  result.projectionStatus = projection.status;
  const rect = document.querySelector('#map').getBoundingClientRect();
  const scope = new Set(view.viewport.elementIds || view.elementIds);
  const overlays = runtime.map.getAllOverlays('polygon');
  const activeIds = new Set(
    elements
      .filter(element => projectionScope.includes(element.id))
      .map(element => element.id),
  );
  const columns = overlays.filter(column =>
    activeIds.has(column.getExtData()?.elementId),
  );
  const identity = value => JSON.stringify([value.elementId, value.featureId]);
  if (
    ['unsupported', 'invalid'].includes(projection.status) ||
    (requiresFit && projection.status === 'clipped')
  )
    result.errors.push(
      `三维投影不可验证：${projection.code || projection.status}`,
    );
  if (projection.status === 'empty' && columns.length)
    result.errors.push('原生柱体存在，但投影为空');
  if (
    requiresFit &&
    window.mapCreateState.fitState?.outcome !== 'applied' &&
    projection.status !== 'empty'
  )
    result.errors.push('三维初始全览未完成，不能以地面范围作为通过证据');

  for (const selector of [
    '#map-controls',
    '#map-legend',
    '#selection-details',
    '#content-map-ui',
    '#map-sources',
    '#heatmap-controls',
    '.amap-logo',
    '.amap-copyright',
  ]) {
    for (const node of document.querySelectorAll(selector)) {
      const style = getComputedStyle(node);
      const box = node.getBoundingClientRect();
      if (
        style.display === 'none' ||
        style.visibility === 'hidden' ||
        Number(style.opacity) === 0 ||
        !box.width ||
        !box.height
      )
        continue;
      const reservation = {
        selector,
        left: Math.max(0, box.left - rect.left),
        top: Math.max(0, box.top - rect.top),
        right: Math.min(rect.width, box.right - rect.left),
        bottom: Math.min(rect.height, box.bottom - rect.top),
      };
      if (
        reservation.right > reservation.left &&
        reservation.bottom > reservation.top
      )
        result.reservations.push(reservation);
    }
  }
  if (projection.status === 'ready') {
    const expectedIds = projection.cells.map(identity).sort();
    const actualIds = columns
      .map(column => identity(column.getExtData()))
      .sort();
    if (JSON.stringify(expectedIds) !== JSON.stringify(actualIds))
      result.errors.push('三维投影与原生柱体的 elementId / cellId 集合不一致');
    for (const cell of projection.cells) {
      const column = columns.find(
        item => identity(item.getExtData()) === identity(cell),
      );
      const nativeHeight = column?.getOptions().extrusionHeight;
      if (
        typeof nativeHeight !== 'number' ||
        Math.abs(nativeHeight - cell.heightMeters) > 0.001
      )
        result.errors.push(
          `${cell.elementId}/${cell.featureId} 投影高度与原生柱高不一致`,
        );
      const bounds = cell.bounds;
      const outside =
        bounds.left < 0 ||
        bounds.top < 0 ||
        bounds.right > rect.width ||
        bounds.bottom > rect.height;
      const obstructedBy = result.reservations
        .filter(
          box =>
            bounds.left < box.right &&
            bounds.right > box.left &&
            bounds.top < box.bottom &&
            bounds.bottom > box.top,
        )
        .map(box => box.selector);
      const required = requiresFit && scope.has(cell.elementId);
      if (required && (outside || obstructedBy.length))
        result.errors.push(
          `${cell.elementId}/${cell.featureId} 完整柱体${outside ? '越界' : `被 ${obstructedBy.join(', ')} 遮挡`}`,
        );
      result.cells.push({
        elementId: cell.elementId,
        featureId: cell.featureId,
        heightMeters: cell.heightMeters,
        nativeHeight,
        bounds,
        outside,
        obstructedBy,
        coverageRequired: required,
      });
    }
  }
  result.status = result.errors.length ? 'failed' : 'passed';
  result.coverage = result.errors.length
    ? 'failed'
    : projection.status === 'empty'
      ? 'no-elevated-data'
      : requiresFit
        ? 'verified-elevated-screen'
        : 'camera-intent-preserved';
  return result;
}

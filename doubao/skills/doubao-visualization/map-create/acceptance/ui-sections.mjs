// Expectations come from Graph + state, never from Runtime's own render report.
export function compareUiSections(
  view,
  state,
  actual,
  hasSelectionContainer,
  { singlePanel = false } = {},
) {
  const expected = { sidebar: [], selection: [] };
  const showingDetails =
    singlePanel &&
    (Boolean(state.selectedFeatureId) ||
      view.ui.sections.some(
        section =>
          section.source === 'selected.properties' &&
          !section.empty &&
          section.items?.some(
            item => item.ownerElementId === state.selectedElementId,
          ),
      ));
  for (const section of view.ui.sections) {
    const selected = section.source === 'selected.properties';
    const items = (section.items || []).filter(
      item => !selected || item.ownerElementId === state.selectedElementId,
    );
    const hasSummary =
      section.componentId === 'semi.card' &&
      typeof section.props.description === 'string' &&
      section.props.description.length > 0;
    const empty = section.empty || (!items.length && !hasSummary);
    const contentRendered = empty
      ? !selected && section.source !== 'view.recommendations'
      : section.componentId !== 'semi.tabs' ||
        Math.min(items.length, section.props.maxItems ?? items.length) >= 2;
    const rendered =
      contentRendered &&
      !(showingDetails && !selected && section.source !== 'map.views');
    const slot = selected && hasSelectionContainer ? 'selection' : 'sidebar';
    // Sidebar keeps section wrappers even when its optional content is absent.
    if (slot === 'selection' && !rendered) continue;
    expected[slot].push({ id: section.id, source: section.source, rendered });
  }
  const errors = [];
  for (const slot of ['sidebar', 'selection']) {
    const records = actual.filter(item => item.slot === slot);
    if (
      JSON.stringify(records.map(item => item.id)) !==
      JSON.stringify(expected[slot].map(item => item.id))
    )
      errors.push(`${slot}: section 身份、数量或顺序不符`);
    for (const [index, record] of records.entries()) {
      const target = expected[slot][index];
      if (record.viewId !== view.id)
        errors.push(`${slot}/${record.id}: 其他 View 残留或缺少 View 身份`);
      if (
        target &&
        (record.source !== target.source || record.rendered !== target.rendered)
      )
        errors.push(`${slot}/${record.id}: 数据源或当前状态可见性不符`);
      const section = view.ui.sections.find(item => item.id === record.id);
      if (
        target?.rendered &&
        section?.source === 'selected.properties' &&
        section.componentId === 'semi.descriptions'
      ) {
        const clearCount = section.actions?.some(
          action => action.type === 'clear-selection',
        )
          ? 1
          : 0;
        if (!record.hasContent || record.clearSelectionCount !== clearCount)
          errors.push(`${slot}/${record.id}: 详情内容或清除操作与契约不符`);
      }
    }
  }
  for (const record of actual.filter(
    item => !['sidebar', 'selection'].includes(item.slot),
  ))
    errors.push(`${record.id}: section 位于未知渲染区域`);
  return {
    status: errors.length ? 'failed' : 'passed',
    method: 'section-identity-state-slot',
    expected,
    actual,
    errors,
  };
}

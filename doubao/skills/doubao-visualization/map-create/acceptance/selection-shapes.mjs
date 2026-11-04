/** Observe real SVG parts for each applicable point kind; no screenshot/self-reported shape. */
export async function inspectSelectionShapes(page, viewId, waitForStable) {
  const candidates = await page.evaluate(id => {
    const types = new Set();
    const view = window.mapCreateGraph.views.find(item => item.id === id);
    return window.mapCreateGraph.elements
      .filter(element => {
        if (
          element.viewId !== id ||
          view?.entryActions?.[element.id] ||
          element.props.selectable === false ||
          element.props.interaction?.selectable === false ||
          types.has(element.rendererType) ||
          ![
            'poi_marker',
            'number_waypoint',
            'common_waypoint',
            'origin',
            'destination',
            'transfer_point',
          ].includes(element.rendererType)
        )
          return false;
        const node = [...document.querySelectorAll('[data-element-id]')].find(
          candidate => candidate.getAttribute('data-element-id') === element.id,
        );
        if (
          !node?.getBoundingClientRect().width ||
          getComputedStyle(node).display === 'none'
        )
          return false;
        types.add(element.rendererType);
        return true;
      })
      .map(element => ({
        id: element.id,
        type: element.rendererType,
        hasLabel:
          Boolean(element.props.label) && element.props.showLabel !== false,
      }));
  }, viewId);
  const snapshot = elementId =>
    page.evaluate(id => {
      const node = [...document.querySelectorAll('[data-element-id]')].find(
        candidate => candidate.getAttribute('data-element-id') === id,
      );
      if (!node) throw new Error('Selected element DOM is missing');
      const parts = selector =>
        [...node.querySelectorAll(selector)]
          .map(part => part.outerHTML)
          .join('');
      return {
        markup: node.innerHTML,
        fixed: parts('[data-part="icon"], [data-part="anchor"]'),
        label: parts('[data-part="label"]'),
        description: [...node.querySelectorAll('[data-part="description"]')]
          .map(part => [
            part.tagName,
            part.textContent,
            part.getAttribute('fill'),
            part.getAttribute('stroke'),
          ])
          .map(value => JSON.stringify(value))
          .join(''),
        iconWidths: [...node.querySelectorAll('image[data-part="icon"]')].map(
          image => Number(image.getAttribute('width')),
        ),
        labelContainer: Boolean(
          node.querySelector('path[data-part="label"],rect[data-part="label"]'),
        ),
      };
    }, elementId);
  const checks = [];
  for (const candidate of candidates) {
    await page.evaluate(() => window.mapCreateRuntime.selectElement(null));
    await waitForStable(page, viewId);
    const before = await snapshot(candidate.id);
    await page
      .locator(`[data-element-id="${candidate.id}"]`)
      .dispatchEvent('click');
    await page.waitForFunction(
      id => window.mapCreateState.selectedElementId === id,
      candidate.id,
      { timeout: 5000 },
    );
    await waitForStable(page, viewId);
    const selected = await snapshot(candidate.id),
      errors = [];
    if (candidate.type === 'poi_marker') {
      if (!selected.iconWidths.includes(60))
        errors.push('POI 专用选中图标未绘制');
      if (candidate.hasLabel && !selected.labelContainer)
        errors.push('POI 名称容器缺失');
      // A collapsed base may legitimately expand its previously absent description.
      if (before.description && before.description !== selected.description)
        errors.push('POI 描述不应随名称反色');
    } else if (
      candidate.type !== 'number_waypoint' &&
      before.fixed !== selected.fixed
    )
      errors.push('选中不应改变固定图标或锚点');
    if (candidate.hasLabel && before.label === selected.label)
      errors.push('名称标签没有选中变化');
    await page.evaluate(() => window.mapCreateRuntime.selectElement(null));
    await waitForStable(page, viewId);
    if ((await snapshot(candidate.id)).markup !== before.markup)
      errors.push('取消选择未恢复基础形态');
    checks.push({
      elementId: candidate.id,
      type: candidate.type,
      status: errors.length ? 'failed' : 'passed',
      errors,
    });
  }
  return {
    status: checks.some(check => check.status === 'failed')
      ? 'failed'
      : 'passed',
    applicable: checks.length > 0,
    checks,
  };
}

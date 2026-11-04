export async function checkRegionJourneys(page, graph, view) {
  const regions = graph.elements.filter(
    element => element.viewId === view.id && ['polygon', 'circle'].includes(element.componentId),
  );
  const snapshot = id =>
    page.evaluate(elementId => {
      const node = document.querySelector(
        `[data-element-id="${CSS.escape(elementId)}"]`,
      );
      if (!node) throw new Error('REGION_DOM_MISSING:' + elementId);
      return {
        markup: node.innerHTML,
        fills: [...node.querySelectorAll('path[fill-rule="evenodd"]')].map(
          path => ({
            fill: path.getAttribute('fill'),
            opacity: Number(path.getAttribute('fill-opacity')),
            geometry: path.getAttribute('d'),
          }),
        ),
        selectedBorder: Boolean(
          node.querySelector('[data-border-role="selection"]'),
        ),
      };
    }, id);
  const stable = () =>
    page.evaluate(() => window.mapCreateRuntime.waitForStable());
  const expectSelected = async (id, source) => {
    try {
      await page.waitForFunction(
        elementId => window.mapCreateState.selectedElementId === elementId,
        id,
        { timeout: 5000 },
      );
    } catch {
      const actual = await page.evaluate(() => ({
        id: window.mapCreateState.selectedElementId,
        width: innerWidth,
      }));
      throw new Error(
        'REGION_SELECTION_MISMATCH:' + JSON.stringify({ id, source, actual }),
      );
    }
  };
  const checks = [];
  for (const region of regions) {
    const before = await snapshot(region.id);
    if (
      !before.fills.length ||
      before.fills.some(
        fill =>
          fill.fill?.toUpperCase() !== region.props.fillColor?.toUpperCase() ||
          fill.opacity !== region.props.fillOpacity,
      )
    )
      throw new Error('REGION_FILL_NOT_RENDERED:' + region.id);
    if (region.props.interaction?.selectable === false) {
      checks.push({
        elementId: region.id,
        fill: 'passed',
        selection: 'not-applicable',
      });
      continue;
    }
    const button = page
      .locator(`#content-map-ui button[data-linked-element-id="${region.id}"]`)
      .first();
    const hasEntry = await button.count();
    if (hasEntry) {
      await button.click();
      await expectSelected(region.id, 'list');
      await stable();
      const selected = await snapshot(region.id);
      if (
        !selected.selectedBorder ||
        JSON.stringify(selected.fills) !== JSON.stringify(before.fills)
      )
        throw new Error('REGION_SELECTION_VISUAL_MISSING:' + region.id);
      await page
        .locator('[data-content-map-details] button[aria-label="关闭详情"]')
        .click();
      await stable();
      if ((await snapshot(region.id)).markup !== before.markup)
        throw new Error('REGION_CLEAR_NOT_RESTORED:' + region.id);
    }
    const hit = await page.evaluate(id => {
      const node = document.querySelector(
        `[data-element-id="${CSS.escape(id)}"]`,
      );
      const shapes = [
        ...document.querySelectorAll(
          '#map [data-element-id] path[fill-rule="evenodd"]',
        ),
      ].reverse();
      const fractions = [
        0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9, 0.05, 0.95,
      ];
      for (const path of node?.querySelectorAll('path[fill-rule="evenodd"]') ||
        []) {
        const box = path.getBoundingClientRect();
        const matrix = path.getScreenCTM();
        if (!matrix) continue;
        for (const row of fractions)
          for (const column of fractions) {
            const screenX = Math.round(box.left + box.width * column);
            const screenY = Math.round(box.top + box.height * row);
            const top = document.elementFromPoint(screenX, screenY);
            if (
              !top?.closest('#map') ||
              !path.isPointInFill(
                new DOMPoint(screenX, screenY).matrixTransform(
                  matrix.inverse(),
                ),
              )
            )
              continue;
            const hitShape = shapes.find(shape => {
              const transform = shape.getScreenCTM();
              return (
                transform &&
                shape.isPointInFill(
                  new DOMPoint(screenX, screenY).matrixTransform(
                    transform.inverse(),
                  ),
                )
              );
            });
            if (
              hitShape
                ?.closest('[data-element-id]')
                ?.getAttribute('data-element-id') !== id
            )
              continue;
            return { x: screenX, y: screenY };
          }
      }
      return null;
    }, region.id);
    if (!hit) throw new Error('REGION_NOT_HITTABLE:' + region.id);
    await page.mouse.click(hit.x, hit.y);
    await expectSelected(region.id, 'map');
    await stable();
    const selected = await snapshot(region.id);
    if (
      !selected.selectedBorder ||
      JSON.stringify(selected.fills) !== JSON.stringify(before.fills)
    )
      throw new Error('REGION_SELECTION_VISUAL_MISSING:' + region.id);
    const details = page.locator('[data-content-map-details]');
    const title = graph.entityIndex?.find?.(
      item => item.id === region.businessRef.id,
    )?.name;
    if (
      hasEntry &&
      (!(await details.isVisible()) || !(await details.innerText()).trim())
    )
      throw new Error('REGION_DETAIL_NOT_LINKED:' + region.id);
    if (title && hasEntry && !(await details.innerText()).includes(title))
      throw new Error('REGION_DETAIL_IDENTITY_MISMATCH:' + region.id);
    if (await details.locator('button[aria-label="关闭详情"]').count())
      await details.locator('button[aria-label="关闭详情"]').click();
    else await page.evaluate(() => window.mapCreateRuntime.selectElement(null));
    await stable();
    if ((await snapshot(region.id)).markup !== before.markup)
      throw new Error('REGION_CLEAR_NOT_RESTORED:' + region.id);
    checks.push({
      elementId: region.id,
      fill: 'passed',
      listToMap: hasEntry ? 'passed' : 'not-applicable:no-list',
      mapToDetails: hasEntry ? 'passed' : 'not-applicable:no-list',
      selection: 'passed',
      clear: 'passed',
    });
  }
  return checks;
}

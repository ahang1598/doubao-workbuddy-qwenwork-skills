export async function checkEdgeNavigationJourneys(page, graph) {
  if (!graph.runtimeRequirements.capabilities.includes('ui.edge-navigation@1'))
    return [];
  const initial = await page.evaluate(() => {
    const state = window.mapCreateState;
    const map = window.mapCreateRuntime.map;
    const center = map.getCenter();
    return {
      camera: {
        center: [center.getLng(), center.getLat()],
        zoom: map.getZoom(),
      },
      viewId: state.activeViewId,
      selectedElementId: state.selectedElementId,
      selectedSeriesId: state.selectedSeriesId,
      selectedFeatureId: state.selectedFeatureId,
      entries: [...document.querySelectorAll('.content-map-kit-edge-sign')]
        .filter(button => !button.closest('[hidden]'))
        .flatMap(button => JSON.parse(button.dataset.edgeIds || '[]')),
    };
  });
  const evidence = [];
  for (const id of initial.entries) {
    await page.evaluate(
      camera =>
        window.mapCreateRuntime.map.setZoomAndCenter(
          camera.zoom,
          camera.center,
          true,
        ),
      initial.camera,
    );
    await page.evaluate(() => window.mapCreateRuntime.waitForStable());
    const direction = await page.evaluate(
      id =>
        [...document.querySelectorAll('.content-map-kit-edge-sign')]
          .find(button =>
            JSON.parse(button.dataset.edgeIds || '[]').includes(id),
          )
          ?.closest('[data-edge-direction]')?.dataset.edgeDirection,
      id,
    );
    if (!direction) throw new Error('EDGE_ENTRY_MISSING:' + id);
    const trigger = page.locator(
      `[data-edge-direction="${direction}"] .content-map-kit-edge-sign`,
    );
    await trigger.focus();
    await page.keyboard.press('ArrowDown');
    await page
      .locator('[data-edge-item-id=' + JSON.stringify(id) + ']')
      .click();
    await page.evaluate(() => window.mapCreateRuntime.waitForStable());
    const actual = await page.evaluate(id => {
      const state = window.mapCreateState;
      const node = document.querySelector(
        '[data-element-id="' + CSS.escape(id) + '"]',
      );
      const mapBox = document.getElementById('map').getBoundingClientRect();
      const text =
        node?.querySelector(
          'text[data-part="label"], [data-part="label"] text',
        ) || node;
      const box = text?.getBoundingClientRect();
      let clickable = false;
      if (box) {
        const left = Math.max(box.left, mapBox.left),
          right = Math.min(box.right, mapBox.right);
        const top = Math.max(box.top, mapBox.top),
          bottom = Math.min(box.bottom, mapBox.bottom);
        if (right > left && bottom > top)
          for (const horizontal of [0.25, 0.5, 0.75])
            for (const vertical of [0.25, 0.5, 0.75])
              if (
                document
                  .elementFromPoint(
                    left + (right - left) * horizontal,
                    top + (bottom - top) * vertical,
                  )
                  ?.closest('[data-element-id]')
                  ?.getAttribute('data-element-id') === id
              )
                clickable = true;
      }
      return {
        viewId: state.activeViewId,
        selectedElementId: state.selectedElementId,
        selectedSeriesId: state.selectedSeriesId,
        selectedFeatureId: state.selectedFeatureId,
        visible: Boolean(
          box &&
            box.width &&
            box.height &&
            box.right > mapBox.left &&
            box.left < mapBox.right &&
            box.bottom > mapBox.top &&
            box.top < mapBox.bottom,
        ),
        fitIds: state.fitState?.elementIds,
        fitOutcome: state.fitState?.outcome,
        clickable,
      };
    }, id);
    if (
      !actual.visible ||
      !actual.clickable ||
      actual.fitOutcome !== 'applied' ||
      actual.viewId !== initial.viewId ||
      actual.selectedElementId !== initial.selectedElementId ||
      actual.selectedSeriesId !== initial.selectedSeriesId ||
      actual.selectedFeatureId !== initial.selectedFeatureId ||
      actual.fitIds?.join() !== id
    )
      throw new Error(
        'EDGE_LOCATE_FAILED:' + id + ':' + JSON.stringify(actual),
      );
    evidence.push({
      elementId: id,
      direction,
      locate: 'passed',
      selectionPreserved: true,
    });
  }
  if (initial.entries.length) {
    await page.evaluate(
      camera =>
        window.mapCreateRuntime.map.setZoomAndCenter(
          camera.zoom,
          camera.center,
          true,
        ),
      initial.camera,
    );
    await page.evaluate(() => window.mapCreateRuntime.fitCurrentView());
    await page.evaluate(() => window.mapCreateRuntime.waitForStable());
  }
  return evidence;
}

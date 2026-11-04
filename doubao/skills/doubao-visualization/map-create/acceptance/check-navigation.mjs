/** Exercise public UI paths. Calling activateView here would hide missing links. */
export async function checkNavigation(
  page,
  waitForStable,
  requestedIds,
  inspectView,
) {
  const graph = await page.evaluate(() => window.mapCreateGraph);
  const edges = new Map(
    graph.views.map(view => {
      const links = [];
      for (const section of view.ui.sections) {
        if (
          section.componentId !== 'semi.tabs' ||
          !section.actions.some(action => action.type === 'activate-view')
        )
          continue;
        for (const item of section.items.slice(
          0,
          section.props.maxItems ?? Infinity,
        )) {
          links.push({
            from: view.id,
            to: item.viewId,
            selector: `[data-ui-section-id=${JSON.stringify(section.id)}] [data-view-id=${JSON.stringify(item.viewId)}]`,
            kind: 'tab',
          });
        }
      }
      for (const [id, action] of Object.entries(view.entryActions ?? {}))
        links.push({
          from: view.id,
          to: action.viewId,
          selector: `[data-element-id=${JSON.stringify(id)}]`,
          kind: 'map-entry',
        });
      return [view.id, links];
    }),
  );
  const path = (from, to) => {
    const queue = [[from, []]],
      seen = new Set([from]);
    for (const [id, steps] of queue) {
      if (id === to) return steps;
      for (const link of edges.get(id) ?? [])
        if (!seen.has(link.to)) {
          seen.add(link.to);
          queue.push([link.to, [...steps, link]]);
        }
    }
    throw new Error(`VIEW_UNREACHABLE: ${from} -> ${to}`);
  };
  const evidence = [];
  const go = async target => {
    const current = await page.evaluate(
      () => window.mapCreateState.activeViewId,
    );
    for (const step of path(current, target)) {
      // Playwright click checks visibility, scrolling and occlusion; synthetic
      // dispatchEvent would pass even for an inaccessible navigation control.
      await page.locator(step.selector).first().click({ timeout: 5000 });
      await page.waitForFunction(
        id =>
          window.mapCreateState?.activeViewId === id &&
          window.mapCreateState?.status === 'ready',
        step.to,
        { timeout: 10000 },
      );
      await waitForStable(page, step.to);
      evidence.push({ from: step.from, to: step.to, trigger: step.kind });
    }
  };
  const visited = new Set([graph.initialViewId]);
  for (const id of requestedIds) {
    await go(id);
    visited.add(id);
    if (inspectView) await inspectView(id);
    await go(graph.initialViewId);
  }
  return {
    status: 'passed',
    method: 'visible-ui-click',
    initialViewId: graph.initialViewId,
    visitedViewIds: [...visited],
    returnedToInitialView: true,
    transitions: evidence,
  };
}

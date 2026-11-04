import { findBlankMapTarget } from './blank-target.mjs';
import { checkRegionJourneys } from './region-journeys.mjs';

export async function checkProductJourneys(
  page,
  graph,
  { viewIds, navigate = true } = {},
) {
  const evidence = [];
  const shell = await page.evaluate(() => {
    const body = document.body.getBoundingClientRect();
    const canvas = document.getElementById('map').getBoundingClientRect();
    const header = document.querySelector('header').getBoundingClientRect();
    return {
      bodyHeight: body.height,
      expectedHeight:
        document.documentElement.dataset.mapHeightMode === 'viewport'
          ? window.innerHeight
          : Number.parseFloat(
              getComputedStyle(document.documentElement).getPropertyValue(
                '--map-height',
              ),
            ),
      headerHeight: header.height,
      bottomGap: body.bottom - canvas.bottom,
      sourcesPresent: Boolean(document.querySelector('#map-sources summary')),
    };
  });
  if (
    !Number.isFinite(shell.expectedHeight) ||
    Math.abs(shell.bodyHeight - shell.expectedHeight) > 2 ||
    Math.abs(shell.headerHeight - 76) > 2 ||
    Math.abs(shell.bottomGap) > 2 ||
    !shell.sourcesPresent
  )
    throw new Error('SHELL_HEIGHT_INVALID:' + JSON.stringify(shell));
  for (const view of graph.views.filter(
    item => !viewIds || viewIds.includes(item.id),
  )) {
    if (!navigate) {
      const active = await page.evaluate(
        () => window.mapCreateState.activeViewId,
      );
      if (active !== view.id) throw new Error('VIEW_NOT_ACTIVE:' + view.id);
    }
    if (graph.views.length > 1) {
      const tab = page.locator(
        '[data-view-id=' + JSON.stringify(view.id) + ']',
      );
      if (navigate) {
        await tab.click();
        await page.waitForFunction(
          id => window.mapCreateState.activeViewId === id,
          view.id,
        );
        await page.evaluate(() => window.mapCreateRuntime.waitForStable());
      }
      const visible = await tab.evaluate(node => {
        const item = node.closest('[role="tab"]');
        const bar = node.closest('[role="tablist"]');
        if (!item || !bar) return false;
        const box = item.getBoundingClientRect();
        const bounds = bar.getBoundingClientRect();
        const sidebar = document
          .getElementById('content-map-ui')
          .getBoundingClientRect();
        const left = Math.max(bounds.left + bar.clientLeft, sidebar.left, 0);
        const right = Math.min(
          bounds.left + bar.clientLeft + bar.clientWidth,
          sidebar.right,
          innerWidth,
        );
        if (right <= left || box.width <= 0) return false;
        if (box.width > bar.clientWidth + 1)
          return Math.abs(box.left - left) <= 1 && box.right > left;
        return box.left >= left - 1 && box.right <= right + 1;
      });
      if (!visible) throw new Error('ACTIVE_TAB_OFFSCREEN:' + view.id);
    }
    const overflow = await page
      .locator('#content-map-ui .content-map-kit-item-meta')
      .evaluateAll(nodes =>
        nodes
          .filter(node => {
            const bounds = node.getBoundingClientRect();
            const parent = node
              .closest(
                '.content-map-kit-item-button, .content-map-kit-item-static',
              )
              ?.getBoundingClientRect();
            return (
              parent &&
              (bounds.left < parent.left - 1 ||
                bounds.right > parent.right + 1 ||
                node.scrollWidth > node.clientWidth + 1)
            );
          })
          .map(node => node.textContent),
      );
    if (overflow.length)
      throw new Error('SIDEBAR_COMPARISON_OVERFLOW:' + view.id);
    let summary = 'not-applicable';
    const overviewEntries = view.ui?.sections.find(
      section =>
        section.source === 'view.groups' &&
        section.actions.some(action => action.type === 'activate-view'),
    );
    if (overviewEntries) {
      if (
        view.ui.sections.some(section =>
          ['view.stops', 'view.routes', 'view.entityRelations'].includes(
            section.source,
          ),
        )
      )
        throw new Error('OVERVIEW_DETAIL_SCOPE_INVALID:' + view.id);
      for (const item of overviewEntries.items) {
        const button = page.locator(
          '#content-map-ui [data-ui-source="view.groups"] [data-target-view-id=' +
            JSON.stringify(item.viewId) +
            ']',
        );
        await button.click();
        await page.waitForFunction(
          id =>
            window.mapCreateState.activeViewId === id &&
            window.mapCreateState.selectedElementId === null,
          item.viewId,
        );
        await page.evaluate(() => window.mapCreateRuntime.waitForStable());
        const target = graph.views.find(
          candidate => candidate.id === item.viewId,
        );
        const scope = await page
          .locator('#content-map-ui [data-ui-source="view.stops"]')
          .innerText()
          .catch(() => '');
        for (const stop of target.detail?.stops || [])
          if (!scope.includes(stop.name))
            throw new Error('ENTRY_STOPS_NOT_RENDERED:' + item.viewId);
        if (
          target.detail?.description &&
          !(
            await page
              .locator('#content-map-ui [data-ui-source="view.summary"]')
              .innerText()
          ).includes(target.detail.description)
        )
          throw new Error('ENTRY_SUMMARY_NOT_RENDERED:' + item.viewId);
        await page
          .locator('[data-view-id=' + JSON.stringify(view.id) + ']')
          .click();
        await page.waitForFunction(
          id => window.mapCreateState.activeViewId === id,
          view.id,
        );
        await page.evaluate(() => window.mapCreateRuntime.waitForStable());
      }
      evidence.push({
        viewId: view.id,
        overviewEntries: overviewEntries.items.length,
        entryNavigation: 'passed',
        returnNavigation: 'passed',
      });
    }
    if (view.detail?.description) {
      const card = page.locator(
        '#content-map-ui [data-ui-source="view.summary"]',
      );
      if (
        !(await card.isVisible()) ||
        !(await card.innerText()).includes(view.detail.description)
      )
        throw new Error('VIEW_SUMMARY_NOT_RENDERED:' + view.id);
      summary = 'passed';
    }
    const regionChecks = await checkRegionJourneys(page, graph, view);
    const candidates = graph.elements.filter(
      element =>
        element.viewId === view.id &&
        ['place', 'member'].includes(element.businessRef?.type) &&
        element.props?.interaction?.selectable !== false,
    );
    const hit = await page.evaluate(
      ids => {
        for (const id of ids) {
          const node = document.querySelector(
            '[data-element-id="' + CSS.escape(id) + '"]',
          );
          for (const part of node?.querySelectorAll('circle,text,rect,path') ||
            []) {
            const box = part.getBoundingClientRect();
            if (box.width < 2 || box.height < 2) continue;
            const x = box.left + box.width / 2,
              y = box.top + box.height / 2;
            if (
              document
                .elementFromPoint(x, y)
                ?.closest('[data-element-id]')
                ?.getAttribute('data-element-id') === id
            )
              return { id, x, y };
          }
        }
        return null;
      },
      candidates.map(element => element.id),
    );
    const candidate = candidates.find(element => element.id === hit?.id);
    if (!candidate) {
      if (candidates.length) throw new Error('POINT_NOT_HITTABLE:' + view.id);
      evidence.push({
        viewId: view.id,
        navigation: 'passed',
        summary,
        shellHeight: 'passed',
        point: 'not-applicable',
        regions: regionChecks,
      });
      continue;
    }
    await page.mouse.click(hit.x, hit.y);
    const pointEntry = view.entryActions?.[candidate.id];
    if (pointEntry) {
      await page.waitForFunction(
        id => window.mapCreateState.activeViewId === id && window.mapCreateState.selectedElementId === null,
        pointEntry.viewId,
      );
      await page.evaluate(() => window.mapCreateRuntime.waitForStable());
      await page.locator('[data-view-id=' + JSON.stringify(view.id) + ']').click();
      await page.evaluate(() => window.mapCreateRuntime.waitForStable());
      evidence.push({ viewId: view.id, pointEntry: candidate.id, targetViewId: pointEntry.viewId, pointNavigation: 'passed', returnNavigation: 'passed' });
      continue;
    }
    await page
      .waitForFunction(
        id => window.mapCreateState.selectedElementId === id,
        candidate.id,
      )
      .catch(async error => {
        throw new Error(
          'POINT_SELECT:' +
            candidate.id +
            ':' +
            JSON.stringify(await page.evaluate(() => window.mapCreateState)) +
            ':' +
            error.message,
        );
      });
    await page.evaluate(() => window.mapCreateRuntime.waitForStable());
    if (
      await page.evaluate(() => window.mapCreateState.selectedSeriesId !== null)
    )
      throw new Error('POINT_SELECTED_ROUTE:' + candidate.id);
    if (!(await page.locator('[data-content-map-details]').innerText()).trim())
      throw new Error('DETAIL_EMPTY:' + candidate.id);
    const expectedFields =
      view.ui?.sections
        .find(section => section.source === 'selected.properties')
        ?.items.filter(
          item => item.ownerElementId === candidate.id && item.label !== '名称',
        ) || [];
    const detailText = await page
      .locator('[data-content-map-details]')
      .innerText();
    for (const field of expectedFields)
      if (field.value && !detailText.includes(String(field.value)))
        throw new Error(
          'DETAIL_FACT_NOT_RENDERED:' + candidate.id + ':' + field.label,
        );
    const detailPosition = await page.evaluate(() => {
      const shell = document
        .getElementById('map-shell')
        .getBoundingClientRect();
      const details = document
        .getElementById('content-map-ui')
        .getBoundingClientRect();
      const overlaps = [
        'map-legend',
        'map-controls',
        'heatmap-controls',
      ].filter(id => {
        const node = document.getElementById(id);
        const rect = node.getBoundingClientRect();
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          Math.min(rect.right, details.right) -
            Math.max(rect.left, details.left) >
            1 &&
          Math.min(rect.bottom, details.bottom) -
            Math.max(rect.top, details.top) >
            1
        );
      });
      return {
        left: details.left - shell.left,
        top: details.top - shell.top,
        width: details.width,
        height: details.height,
        inside:
          details.left >= shell.left &&
          details.top >= shell.top &&
          details.right <= shell.right &&
          details.bottom <= shell.bottom,
        singlePanel:
          document.querySelector('.content-map-kit-reading-panel')?.dataset
            .panelPage === 'details',
        overlaps,
      };
    });
    if (
      !detailPosition.inside ||
      !detailPosition.singlePanel ||
      detailPosition.width <= 0 ||
      detailPosition.height <= 0 ||
      detailPosition.overlaps.length
    )
      throw new Error(
        'DETAIL_POSITION_INVALID:' + JSON.stringify(detailPosition),
      );
    const blank = await page.evaluate(findBlankMapTarget);
    if (blank) await page.mouse.click(blank.x, blank.y);
    else
      await page
        .locator('[data-content-map-details] button[aria-label="关闭详情"]')
        .click();
    await page
      .waitForFunction(
        () => window.mapCreateState.selectedElementId === null,
        null,
        { timeout: 3000 },
      )
      .catch(async error => {
        throw new Error(
          'BLANK_CLEAR:' +
            view.id +
            ':' +
            JSON.stringify(await page.evaluate(() => window.mapCreateState)) +
            ':' +
            error.message,
        );
      });
    let routeToggle = 'not-applicable';
    const route = page
      .locator('#map-legend button[data-series-id]:enabled')
      .first();
    const disclosure = page.locator(
      '#map-legend details:not([open]) > summary',
    );
    const expandLegend = (await route.count()) && (await disclosure.count());
    if (expandLegend) await disclosure.click();
    if (
      (await route.count()) &&
      (await route.isVisible()) &&
      (await route.isEnabled())
    ) {
      await route.click();
      await page.waitForFunction(
        () => window.mapCreateState.selectedSeriesId !== null,
      );
      await page.evaluate(() => window.mapCreateRuntime.waitForStable());
      const activeSeries = await page.evaluate(() => window.mapCreateState.selectedSeriesId);
      const relatedIds = candidates.filter(element => element.relatedSeriesIds?.includes(activeSeries)).map(element => element.id);
      const relatedHit = await page.evaluate(ids => {
        for (const id of ids) {
          const node = document.querySelector('[data-element-id="' + CSS.escape(id) + '"]');
          for (const part of node?.querySelectorAll('circle,text,rect,path') || []) {
            const box = part.getBoundingClientRect();
            if (box.width < 2 || box.height < 2) continue;
            const x = box.left + box.width / 2;
            const y = box.top + box.height / 2;
            if (document.elementFromPoint(x, y)?.closest('[data-element-id]')?.getAttribute('data-element-id') === id) return { id, x, y };
          }
        }
        return null;
      }, relatedIds);
      if (relatedIds.length && !relatedHit) throw new Error('ROUTE_MEMBER_NOT_HITTABLE:' + activeSeries);
      if (relatedHit) {
        await page.mouse.click(relatedHit.x, relatedHit.y);
        await page.waitForFunction(({ id, seriesId }) => window.mapCreateState.selectedElementId === id && window.mapCreateState.selectedSeriesId === seriesId, { id: relatedHit.id, seriesId: activeSeries });
        evidence.push({ viewId: view.id, routeMemberSelection: 'passed', seriesId: activeSeries, memberId: relatedHit.id });
      }
      await route.click();
      await page.waitForFunction(
        () =>
          window.mapCreateState.selectedElementId === null &&
          window.mapCreateState.selectedSeriesId === null,
      );
      routeToggle = 'passed';
    }
    if (expandLegend)
      await page.locator('#map-legend details[open] > summary').click();
    await page.evaluate(() => window.mapCreateRuntime.waitForStable());
    evidence.push({
      viewId: view.id,
      navigation: 'passed',
      summary,
      shellHeight: 'passed',
      point: candidate.id,
      regions: regionChecks,
      details: 'passed',
      blankClear: blank ? 'passed' : 'not-applicable:no-blank-map-target',
      pointDoesNotSelectRoutes: 'passed',
      routeToggle,
    });
  }
  return evidence;
}

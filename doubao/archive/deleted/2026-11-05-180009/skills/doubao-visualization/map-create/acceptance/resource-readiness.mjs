/** Non-pixel readiness: resource completion, fonts, layout and camera revisions.
 * Deliberately makes no claim about basemap coverage or GPU pixel correctness. */
export function createResourceReadinessProbe(page) {
  const pending = new Set(),
    failures = [];
  let revision = 0,
    changedAt = performance.now();
  const relevant = request =>
    ['image', 'font', 'stylesheet', 'script', 'fetch', 'xhr'].includes(
      request.resourceType(),
    );
  const changed = () => {
    revision++;
    changedAt = performance.now();
  };
  const started = request => {
    if (relevant(request)) {
      pending.add(request);
      changed();
    }
  };
  const finished = request => {
    if (pending.delete(request)) changed();
  };
  const failed = request => {
    if (
      pending.has(request) &&
      request.failure()?.errorText !== 'net::ERR_ABORTED'
    )
      failures.push(request.resourceType());
    finished(request);
  };
  const response = value => {
    if (relevant(value.request()) && value.status() >= 400)
      failures.push(`${value.request().resourceType()}:${value.status()}`);
  };
  page.on('request', started);
  page.on('requestfinished', finished);
  page.on('requestfailed', failed);
  page.on('response', response);
  return {
    async wait(viewId, { timeoutMs = 10000, quietMs = 250 } = {}) {
      const start = performance.now();
      let previous,
        stableSince = start,
        matchingFrames = 0,
        pendingConditions = [];
      while (performance.now() - start < timeoutMs) {
        let timer;
        const observed = await Promise.race([
          page.evaluate(async id => {
            await document.fonts.ready;
            await new Promise(resolve =>
              requestAnimationFrame(() => requestAnimationFrame(resolve)),
            );
            const runtime = window.mapCreateRuntime,
              state = window.mapCreateState;
            if (state?.status === 'error')
              throw new Error(
                'MAP_RUNTIME_ERROR: ' +
                  JSON.stringify({
                    viewId: id,
                    errors: state.errors,
                    fitState: state.fitState,
                  }),
              );
            const map = runtime?.map,
              layout = runtime?.layer.getLayoutState?.();
            const box = document.querySelector('#map')?.getBoundingClientRect();
            const center = map?.getCenter();
            const blockers = [];
            if (state?.activeViewId !== id || state?.status !== 'ready')
              blockers.push('runtime-view');
            if (!box?.width || !box?.height) blockers.push('map-size');
            if (layout?.status !== 'ready') blockers.push('layout');
            if (
              state?.pendingCameraFit ||
              state?.modeTransition?.status === 'preparing'
            )
              blockers.push('transaction');
            if (
              [...document.images].some(
                image => !image.complete || image.naturalWidth === 0,
              )
            )
              blockers.push('image');
            if (
              [
                ...document.querySelectorAll(
                  '[data-heatmap-engine="maplibre"]',
                ),
              ].some(
                node =>
                  getComputedStyle(node).display !== 'none' &&
                  node.dataset.heatmapReady !== 'true',
              )
            )
              blockers.push('native-layer');
            return {
              blockers,
              signature: JSON.stringify([
                state?.activeViewId,
                state?.revision,
                state?.cameraEventRevision,
                layout,
                state?.heatmapModes,
                center?.lng ?? center?.getLng?.(),
                center?.lat ?? center?.getLat?.(),
                map?.getZoom(),
                map?.getPitch?.(),
                map?.getRotation?.(),
                box?.width,
                box?.height,
              ]),
            };
          }, viewId),
          new Promise((resolve, reject) => {
            timer = setTimeout(
              () =>
                reject(
                  new Error(
                    `RESOURCE_NOT_READY: ${viewId}; browser timeout; blockers=${pendingConditions.join(',')}`,
                  ),
                ),
              Math.max(1, timeoutMs - (performance.now() - start)),
            );
          }),
        ]).finally(() => clearTimeout(timer));
        const now = performance.now(),
          signature = JSON.stringify([observed.signature, revision]);
        pendingConditions = [
          ...observed.blockers,
          ...(pending.size ? ['pending-resources'] : []),
        ];
        if (failures.length)
          throw new Error(`RESOURCE_NOT_READY: ${failures.join(',')}`);
        if (pendingConditions.length || signature !== previous) {
          stableSince = now;
          matchingFrames = 0;
        } else matchingFrames++;
        previous = signature;
        if (
          !pendingConditions.length &&
          matchingFrames >= 2 &&
          now - stableSince >= quietMs &&
          now - changedAt >= quietMs
        )
          return {
            status: 'passed',
            viewId,
            evidence: 'resources-fonts-camera-layout-stable',
            matchingFrames,
            networkRevision: revision,
            elapsedMs: Math.round(now - start),
            basemapCompleteness: 'not-assessed',
            gpuPixels: 'not-assessed',
          };
      }
      throw new Error(
        `RESOURCE_NOT_READY: ${viewId}; ${pendingConditions.join(',')}; pending=${pending.size}`,
      );
    },
    dispose() {
      page.off('request', started);
      page.off('requestfinished', finished);
      page.off('requestfailed', failed);
      page.off('response', response);
      pending.clear();
    },
  };
}

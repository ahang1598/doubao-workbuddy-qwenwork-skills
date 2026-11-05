import { createHash } from 'node:crypto';

/** Observe the browser, not a Runtime assertion that its own rendering is done.
 * Pixel/network quiescence is evidence for capture, never proof of tile coverage:
 * a permanently missing tile can be stable and still fails visual review. */
export function createVisualReadinessProbe(page) {
  const pending = new Set();
  let networkRevision = 0;
  let changedAt = performance.now();
  const failed = [];
  const relevant = request =>
    ['image', 'font', 'stylesheet', 'script', 'fetch', 'xhr'].includes(
      request.resourceType(),
    );
  const started = request => {
    if (!relevant(request)) return;
    pending.add(request);
    networkRevision++;
    changedAt = performance.now();
  };
  const finished = request => {
    if (!pending.delete(request)) return;
    networkRevision++;
    changedAt = performance.now();
  };
  const failure = request => {
    if (
      pending.has(request) &&
      request.failure()?.errorText !== 'net::ERR_ABORTED'
    )
      failed.push({
        resourceType: request.resourceType(),
        reason: 'request-failed',
      });
    finished(request);
  };
  const received = response => {
    if (relevant(response.request()) && response.status() >= 400)
      failed.push({
        resourceType: response.request().resourceType(),
        status: response.status(),
      });
  };
  page.on('request', started);
  page.on('requestfinished', finished);
  page.on('requestfailed', failure);
  page.on('response', received);

  return {
    async wait(viewId, { timeoutMs = 10000, quietMs = 250 } = {}) {
      const startedAt = performance.now();
      let previous;
      let anchorPixels;
      let anchorHash;
      let pixelsSince = startedAt;
      let matchingFrames = 0;
      let blockers = ['first-frame'];
      let pixelComparison = { changedPixels: 0, maxChannelDelta: 0 };
      let lastPixelComparison = null;
      const timeoutError = operation => {
        const error = new Error(
          `画面未就绪：View ${viewId}，浏览器操作超时或就绪预算耗尽；阶段 ${operation}；阻塞 ${blockers.join(', ')}；待完成资源 ${pending.size}；稳定帧 ${matchingFrames}`,
        );
        error.diagnostics = {
          viewId,
          operation,
          elapsedMs: Math.round(performance.now() - startedAt),
          blockers,
          pendingRequests: pending.size,
          matchingFrames,
          lastPixelComparison,
          resourceFailures: failed.slice(-20),
        };
        return error;
      };
      const bounded = async (operation, stage) => {
        let timer;
        try {
          return await Promise.race([
            operation(),
            new Promise((_, reject) => {
              timer = setTimeout(
                () => reject(timeoutError(stage)),
                Math.max(1, timeoutMs - (performance.now() - startedAt)),
              );
            }),
          ]);
        } catch (error) {
          if (error.name === 'TimeoutError') throw timeoutError(stage);
          throw error;
        } finally {
          clearTimeout(timer);
        }
      };
      const read = () =>
        page.evaluate(id => {
          const runtime = window.mapCreateRuntime;
          const state = window.mapCreateState;
          const map = runtime?.map;
          const center = map?.getCenter();
          const box = document.querySelector('#map').getBoundingClientRect();
          const continuousIds = (runtime?.layer.getElements() || [])
            .filter(
              element =>
                element.visible !== false &&
                element.type === 'heatmap' &&
                element.mode === 'continuous',
            )
            .map(element => element.id)
            .sort();
          const hosts = [
            ...document.querySelectorAll('[data-heatmap-engine="maplibre"]'),
          ].filter(node => getComputedStyle(node).display !== 'none');
          const nativeReady = continuousIds.every(elementId =>
            hosts.some(node => {
              try {
                return (
                  JSON.parse(node.dataset.heatmapElementIds || '[]').includes(
                    elementId,
                  ) && node.dataset.heatmapReady === 'true'
                );
              } catch {
                return false;
              }
            }),
          );
          const blockers = [];
          if (state?.activeViewId !== id) blockers.push('view');
          if (state?.status !== 'ready') blockers.push('runtime');
          if (state?.pendingCameraFit) blockers.push('camera-fit');
          if (state?.modeTransition?.status === 'preparing')
            blockers.push('mode-transition');
          if (!nativeReady) blockers.push('native-layer');
          return {
            applicable: blockers.length === 0,
            blockers,
            signature: JSON.stringify([
              state?.activeViewId,
              state?.revision,
              state?.cameraEventRevision,
              state?.heatmapModes,
              center?.lng ?? center?.getLng?.(),
              center?.lat ?? center?.getLat?.(),
              map?.getZoom(),
              map?.getPitch?.(),
              map?.getRotation?.(),
              box.width,
              box.height,
            ]),
          };
        }, viewId);
      while (performance.now() - startedAt < timeoutMs) {
        const before = await bounded(read, 'state-before');
        const networkBefore = networkRevision;
        const pixels = await bounded(
          () =>
            page.locator('#map').screenshot({
              timeout: Math.max(1, timeoutMs - (performance.now() - startedAt)),
            }),
          'capture',
        );
        const after = await bounded(read, 'state-after');
        const hash = createHash('sha256').update(pixels).digest('hex');
        const signature = JSON.stringify([after.signature, networkRevision]);
        blockers = [...(before.blockers || []), ...(after.blockers || [])];
        if (!before.applicable || !after.applicable)
          blockers.push('state-not-ready');
        if (before.signature !== after.signature || signature !== previous)
          blockers.push('state-changed');
        if (networkBefore !== networkRevision) blockers.push('network-changed');
        if (pending.size) blockers.push('resources-pending');
        if (blockers.length === 0 && anchorHash !== hash) {
          // PNG byte identity is not pixel stability: GPU/compositor rounding
          // can toggle one RGB level on a few gradient-edge pixels. Decode in
          // the browser (no private Playwright codec or new dependency). Bound
          // both amplitude (1/255) and area (0.001%); alpha must be identical.
          // Compare to the window's first frame, never a moving previous frame,
          // so a slow fade or cumulative drift cannot pass pairwise comparisons.
          lastPixelComparison = await bounded(
            () =>
              page.evaluate(
                async ({ previousPng, currentPng }) => {
                  const decode = async base64 => {
                    const bytes = Uint8Array.from(atob(base64), value =>
                      value.charCodeAt(0),
                    );
                    const bitmap = await createImageBitmap(
                      new Blob([bytes], { type: 'image/png' }),
                    );
                    try {
                      const canvas = new OffscreenCanvas(
                        bitmap.width,
                        bitmap.height,
                      );
                      const context = canvas.getContext('2d', {
                        willReadFrequently: true,
                      });
                      context.drawImage(bitmap, 0, 0);
                      return context.getImageData(
                        0,
                        0,
                        bitmap.width,
                        bitmap.height,
                      );
                    } finally {
                      bitmap.close();
                    }
                  };
                  const [a, b] = await Promise.all([
                    decode(previousPng),
                    decode(currentPng),
                  ]);
                  if (a.width !== b.width || a.height !== b.height)
                    return { stable: false, reason: 'dimensions' };
                  let changedPixels = 0,
                    maxChannelDelta = 0,
                    alphaChanged = false;
                  for (let i = 0; i < a.data.length; i += 4) {
                    let changed = false;
                    for (let channel = 0; channel < 4; channel++) {
                      const delta = Math.abs(
                        a.data[i + channel] - b.data[i + channel],
                      );
                      changed ||= delta !== 0;
                      if (channel === 3) alphaChanged ||= delta !== 0;
                      else maxChannelDelta = Math.max(maxChannelDelta, delta);
                    }
                    if (changed) changedPixels++;
                  }
                  const totalPixels = a.width * a.height;
                  return {
                    stable:
                      !alphaChanged &&
                      maxChannelDelta <= 1 &&
                      changedPixels <= Math.floor(totalPixels / 100000),
                    changedPixels,
                    maxChannelDelta,
                    alphaChanged,
                    totalPixels,
                  };
                },
                {
                  previousPng: anchorPixels.toString('base64'),
                  currentPng: pixels.toString('base64'),
                },
              ),
            'pixel-comparison',
          );
          if (!lastPixelComparison.stable) blockers.push('pixels-changing');
          else
            pixelComparison = {
              ...lastPixelComparison,
              changedPixels: Math.max(
                pixelComparison.changedPixels,
                lastPixelComparison.changedPixels,
              ),
              maxChannelDelta: Math.max(
                pixelComparison.maxChannelDelta,
                lastPixelComparison.maxChannelDelta,
              ),
            };
        }
        // Decoding is asynchronous too. An interaction or a new tile request
        // during comparison invalidates this frame before it can be accepted.
        const finalState = await bounded(read, 'state-after-comparison');
        if (!finalState.applicable || finalState.signature !== after.signature)
          blockers.push('state-changed');
        if (networkBefore !== networkRevision || pending.size)
          blockers.push('resources-pending');
        const now = performance.now();
        if (blockers.length) {
          matchingFrames = 0;
          pixelsSince = now;
          anchorPixels = pixels;
          anchorHash = hash;
          pixelComparison = { changedPixels: 0, maxChannelDelta: 0 };
        } else matchingFrames++;
        previous = signature;
        if (
          matchingFrames >= 2 &&
          now - pixelsSince >= quietMs &&
          now - changedAt >= quietMs
        ) {
          if (failed.length)
            throw new Error(`地图资源加载失败：${JSON.stringify(failed)}`);
          return {
            evidence: 'camera-network-pixels-stable',
            viewId,
            matchingFrames,
            elapsedMs: Math.round(now - startedAt),
            networkRevision,
            pendingRequests: 0,
            mapPixelsSha256: hash,
            pixelComparison: {
              ...pixelComparison,
              policy: 'rgb-1lsb-area-0.001pct-alpha-exact',
              reference: 'stable-window-anchor',
            },
            basemapCompleteness: 'requires-visual-review',
          };
        }
        await bounded(
          () =>
            page.evaluate(
              () =>
                new Promise(resolve =>
                  requestAnimationFrame(() => requestAnimationFrame(resolve)),
                ),
            ),
          'animation-frame',
        );
      }
      throw timeoutError('settling');
    },
    dispose() {
      page.off('request', started);
      page.off('requestfinished', finished);
      page.off('requestfailed', failure);
      page.off('response', received);
      pending.clear();
    },
  };
}

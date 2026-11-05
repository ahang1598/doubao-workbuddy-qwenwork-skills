(() => {
  if (document.currentScript?.dataset.mapCreateCancelled === 'true') return;
  window.mapCreateBootstrapResource?.();
  if (window.mapCreateBootstrapStart) return;
  window.mapCreateBootstrapStart = async () => {
    const root = document.documentElement;
    if (root.dataset.captureError) return;
    window.mapCreateGraph = undefined;
    const attempt = window.mapCreateLoadAttempt;
    const mask = document.getElementById('map-loading');
    const controller = new AbortController();
    const assertActive = () => {
      if (controller.signal.aborted) throw controller.signal.reason;
      if (attempt !== window.mapCreateLoadAttempt) throw new Error('LOAD_SUPERSEDED');
    };
    window.mapCreateAbortLoading = code => controller.abort(new Error(code));
    const deadline = setTimeout(
      () =>
        controller.abort(
          new Error(
            root.dataset.mapSizeState === 'waiting'
              ? 'MAP_SIZE_TIMEOUT'
              : 'RESOURCE_TIMEOUT',
          ),
        ),
      45000,
    );
    const pending = new Set();
    const resources = new Set();
    const localAssets = document.getElementById('map-create-local-assets');
    let embedded = null;
    const localUrls = [];
    window.mapCreateReleaseResources = () => {
      controller.abort(new Error('RETRY_REQUESTED'));
      for (const node of resources) {
        node.dataset.mapCreateCancelled = 'true';
        node.remove();
      }
      resources.clear();
      for (const url of localUrls.splice(0)) URL.revokeObjectURL(url);
    };
    const assetUrl = (asset, kind) => {
      if (!embedded?.[kind]) return asset.url;
      const bytes = Uint8Array.from(atob(embedded[kind]), value =>
        value.charCodeAt(0),
      );
      const url = URL.createObjectURL(
        new Blob([bytes], {
          type:
            kind === 'style'
              ? 'text/css'
              : kind === 'data'
                ? 'application/json'
                : 'text/javascript',
        }),
      );
      localUrls.push(url);
      return url;
    };
    const integrity = hash =>
      'sha256-' +
      btoa(
        hash
          .match(/../g)
          .map(value => String.fromCharCode(parseInt(value, 16)))
          .join(''),
      );
    const load = (asset, kind) =>
      new Promise((resolve, reject) => {
        const report = window.mapCreateTelemetry?.resource(kind);
        if (controller.signal.aborted) {
          report?.(controller.signal.reason, { cancelled: true });
          reject(controller.signal.reason);
          return;
        }
        const node = document.createElement(kind === 'style' ? 'link' : 'script');
        pending.add(node);
        resources.add(node);
        node.dataset.mapCreateAttempt = String(attempt);
        if (kind === 'style') {
          node.rel = 'stylesheet';
          node.href = assetUrl(asset, kind);
        } else {
          node.src = assetUrl(asset, kind);
          node.async = true;
        }
        node.integrity = integrity(asset.sha256);
        node.crossOrigin = 'anonymous';
        const cleanup = () => {
          pending.delete(node);
          controller.signal.removeEventListener('abort', abort);
          node.onload = null;
          node.onerror = null;
        };
        const abort = () => {
          report?.(controller.signal.reason, { cancelled: true });
          cleanup();
          node.dataset.mapCreateCancelled = 'true';
          node.remove();
          reject(controller.signal.reason);
        };
        node.onload = () => {
          report?.();
          cleanup();
          resolve();
        };
        node.onerror = () => {
          cleanup();
          node.remove();
          const error = new Error('RESOURCE_LOAD_FAILED:' + kind);
          report?.(error);
          reject(error);
        };
        controller.signal.addEventListener('abort', abort, { once: true });
        document.head.append(node);
      });
    const waitForSize = () =>
      new Promise((resolve, reject) => {
        if (controller.signal.aborted) {
          reject(controller.signal.reason);
          return;
        }
        const map = document.getElementById('map');
        let observer;
        let frameId;
        const cleanup = () => {
          observer?.disconnect();
          cancelAnimationFrame(frameId);
          controller.signal.removeEventListener('abort', abort);
        };
        const abort = () => {
          cleanup();
          reject(controller.signal.reason);
        };
        const measure = () => {
          const bounds = map.getBoundingClientRect();
          if (bounds.width > 0 && bounds.height > 0) {
            root.dataset.mapSizeState = 'ready';
            cleanup();
            resolve();
          } else {
            root.dataset.mapSizeState = 'waiting';
          }
        };
        observer = new ResizeObserver(() => {
          cancelAnimationFrame(frameId);
          frameId = requestAnimationFrame(measure);
        });
        controller.signal.addEventListener('abort', abort, { once: true });
        observer.observe(map);
        measure();
      });
    window.mapCreateWaitForSize = waitForSize;
    try {
      let manifest;
      try {
        embedded = localAssets ? JSON.parse(localAssets.textContent) : null;
        manifest = JSON.parse(document.getElementById('map-create-manifest').textContent);
      } catch {
        throw new Error('RESOURCE_MANIFEST_INVALID:json');
      }
      if (manifest?.version !== 1 || manifest.runtimeRelease !== 'map-create-4')
        throw new Error('RESOURCE_RELEASE_MISMATCH');
      for (const kind of ['data', 'style', 'components', 'runtime']) {
        const asset = manifest.assets?.[kind];
        if (!asset || !/^[a-f0-9]{64}$/.test(asset.sha256 || '') || typeof asset.url !== 'string')
          throw new Error('RESOURCE_MANIFEST_INVALID:' + kind);
        let pathname;
        try {
          pathname = new URL(asset.url, location.href).pathname;
        } catch {
          throw new Error('RESOURCE_URL_INVALID:' + kind);
        }
        const extension = kind === 'data' ? '.json' : kind === 'style' ? '.css' : '.js';
        if (!pathname.endsWith(extension))
          throw new Error('RESOURCE_URL_INVALID:' + kind);
      }
      root.dataset.bootstrapPhase = 'resources';
      const reportData = window.mapCreateTelemetry?.resource('data');
      let dataStatus;
      const [data] = await Promise.all([
        fetch(assetUrl(manifest.assets.data, 'data'), {
          signal: controller.signal,
        }).then(async response => {
          dataStatus = response.status;
          if (!response.ok) throw new Error('DATA_HTTP_' + response.status);
          const bytes = await response.arrayBuffer();
          const hash = Array.from(
            new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
          )
            .map(value => value.toString(16).padStart(2, '0'))
            .join('');
          if (hash !== manifest.assets.data.sha256)
            throw new Error('DATA_HASH_MISMATCH');
          try {
            return JSON.parse(new TextDecoder().decode(bytes));
          } catch {
            throw new Error('DATA_INVALID');
          }
        }).then(data => {
          reportData?.(null, { httpStatus: dataStatus });
          return data;
        }).catch(error => {
          reportData?.(error, {
            httpStatus: dataStatus,
            cancelled: controller.signal.aborted,
          });
          throw error;
        }),
        load(manifest.assets.style, 'style'),
        load(manifest.assets.components, 'components'),
      ]);
      assertActive();
      window.mapCreateGraph = data;
      root.dataset.bootstrapPhase = 'container-size';
      await waitForSize();
      assertActive();
      root.dataset.bootstrapPhase = 'runtime';
      await load(manifest.assets.runtime, 'runtime');
      assertActive();
      if (!window.mapCreateStarted) throw new Error('RUNTIME_START_MISSING');
      await Promise.race([
        window.mapCreateStarted.then(async () => {
          assertActive();
          await waitForSize();
          // Production startup confirms mounting, not layout convergence.
          assertActive();
        }),
        new Promise((resolve, reject) =>
          controller.signal.addEventListener(
            'abort',
            () => reject(controller.signal.reason),
            { once: true },
          ),
        ),
      ]);
      assertActive();
      if (root.dataset.captureError) throw new Error(root.dataset.captureError);
      if (!window.mapCreateRuntime?.map || !window.mapCreateRuntime?.layer)
        throw new Error('RUNTIME_START_MISSING');
      const bounds = document.getElementById('map').getBoundingClientRect();
      if (!bounds.width || !bounds.height) throw new Error('NO_MAP_SIZE');
      mask.hidden = true;
      root.dataset.bootstrapPhase = 'ready';
      document.documentElement.dataset.captureState = 'ready';
      window.mapCreateTelemetry?.ready();
      clearTimeout(window.mapCreateBootstrapDeadline);
    } catch (error) {
      controller.abort(error);
      for (const node of pending) node.remove();
      if (attempt !== window.mapCreateLoadAttempt) return;
      await window.mapCreateFail(
        error.code || error.message || 'RESOURCE_LOAD_FAILED',
        error.message === 'MAP_SIZE_TIMEOUT'
          ? '地图容器尺寸暂不可用（MAP_SIZE_TIMEOUT）。请展开预览或调整窗口大小后重新加载。'
          : /^RESOURCE_(MANIFEST|URL)_INVALID/.test(error.message)
            ? `地图资源信息无效（${error.message}）。请让助手重新生成这张地图。`
            : `地图初始化失败（${error.message || 'RESOURCE_LOAD_FAILED'}；阶段：${root.dataset.bootstrapPhase || 'manifest'}）。请保留此错误码。可能涉及资源访问、完整性校验或宿主加载时序，尚不能确定为网络问题。`,
        error,
      );
    } finally {
      clearTimeout(deadline);
      for (const url of localUrls.splice(0)) URL.revokeObjectURL(url);
      if (attempt === window.mapCreateLoadAttempt) {
        delete window.mapCreateAbortLoading;
        delete window.mapCreateWaitForSize;
      }
    }
  };
  window.mapCreateBootstrapRun = window.mapCreateBootstrapStart();
})();

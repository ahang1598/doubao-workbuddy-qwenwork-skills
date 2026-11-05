(() => {
  const entry = document.currentScript;
  if (entry?.dataset.mapCreateCancelled === 'true') return;
  if (entry?.dataset.mapCreateAttempt && Number(entry.dataset.mapCreateAttempt) !== window.mapCreateLoadAttempt) return;
  (window.mapCreateRuntime?.dispose || window.mapCreateDispose)?.();
  window.mapCreateRuntime = undefined;
  let graph;
  try {
    graph = window.mapCreatePrepareGraph
      ? window.mapCreatePrepareGraph(window.mapCreateGraph)
      : window.mapCreateGraph;
  } catch {
    window.mapCreateState = {
      status: 'error',
      code: 'GRAPH_BINDING_INVALID',
      message: '地图协议引用无效，无法初始化',
    };
    document.querySelector('#status').textContent =
      window.mapCreateState.message;
    return;
  }
  const systemTheme = window.matchMedia?.('(prefers-color-scheme: dark)');
  window.mapCreateApplyAppearance?.(
    graph,
    window.mapCreateHostTheme,
    systemTheme?.matches === true,
  );
  const config = window.mapCreateAMapConfig;
  const mapContainer = document.querySelector('#map');
  const status = document.querySelector('#status');
  const uiContainer = document.querySelector('#content-map-ui');
  const legend = document.querySelector('#map-legend');
  const controlsContainer = document.querySelector('#map-controls');
  const sourceContainer = document.querySelector('#map-sources');
  const hoverContainer = document.querySelector('#map-hover');
  const modeTransitionContainer = document.querySelector('#map-transition');
  const viewById = new Map(graph.views.map(view => [view.id, view]));
  const elementById = new Map(
    graph.elements.map(element => [element.id, element]),
  );
  let shellTheme = graph.visualTheme?.shell || {};
  const rootStyle = document.documentElement.style;
  function applyShellTheme() {
    document.documentElement.dataset.mapTone = shellTheme.tone || 'light';
    for (const [name, value] of Object.entries({
      '--shell-canvas': shellTheme.canvas,
      '--shell-panel': shellTheme.panel,
      '--shell-card': shellTheme.card,
      '--shell-subtle': shellTheme.subtle,
      '--shell-border': shellTheme.border,
      '--shell-text': shellTheme.text,
      '--shell-muted-text': shellTheme.mutedText,
      '--shell-quiet-text': shellTheme.quietText,
      '--shell-neutral-accent': shellTheme.neutralAccent,
      '--shell-accent-surface-start': shellTheme.surfaceStartWeight,
      '--shell-accent-surface-end': shellTheme.surfaceEndWeight,
      '--shell-accent-border': shellTheme.borderWeight,
    }))
      if (value) rootStyle.setProperty(name, value);
  }
  applyShellTheme();
  let map;
  let initialCamera;
  let layer;
  let uiRuntime;
  let controlsRuntime;
  let edgeNavigation;
  let edgeFrame;
  let viewportEntries = { groups: {}, entries: [] };
  let heatmapControls;
  let choroplethLegend;
  const heatmapModes = new Map();
  let syncingUi = false;
  let activeViewId = graph.initialViewId;
  let selectedElementId = null;
  let selectedSeriesId = null;
  let selectedFeatureId = null;
  let selectedFeature = null;
  let revision = 0;
  let selectionRevision = 0;
  let fitCount = 0;
  let fitState = null;
  let cameraEventRevision = 0;
  let cameraFitRequest = 0;
  let pendingCameraFit = false;
  const cameraContexts = new Map();
  let cameraViewId = null;
  let gestureCamera = null;
  let interactionNotice = null;
  let cameraNotice = null;
  const hiddenElementIds = new Set();
  const runtimeErrors = new Map();
  const entryContexts = new Map();
  const filterStates = new Map();
  let filterRevision = 0;
  let visibilityRevision = 0;
  let modeSequence = 0;
  let modeDraft = null;
  let modeTransition = { sequence: 0, status: 'idle' };
  let disposed = false;
  let terminalState;
  const frames = new Set();
  const pendingWaits = new Set();
  const cleanups = new Set();
  let layoutSnapshot = null;
  let observedPanelState = null;
  let layoutFrame;
  let layoutRevision = 0;
  let legendCollapsed = true;
  const detailCollapsed = false;
  let layoutDegradations = [];
  const disposedError = () =>
    Object.assign(new Error('地图已关闭'), { code: 'RUNTIME_DISPOSED' });

  function showModeTransition(active) {
    if (active) hideHover();
    if (modeTransitionContainer) modeTransitionContainer.hidden = !active;
    mapContainer.setAttribute('aria-busy', String(active));
  }

  function scheduleFrame(callback) {
    if (disposed) return;
    const id = window.requestAnimationFrame(time => {
      frames.delete(id);
      if (!disposed) callback(time);
    });
    frames.add(id);
    return id;
  }

  // All asynchronous waits settle on teardown, including a hidden tab where
  // animation frames stop. SDK callbacks and timers share the same cleanup.
  function waitForResource(register, timeoutMs, message) {
    if (disposed) return Promise.reject(disposedError());
    return new Promise((resolve, reject) => {
      let settled = false,
        cleanup;
      const finish = (error, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        pendingWaits.delete(cancel);
        cleanup?.();
        if (error) reject(error);
        else resolve(value);
      };
      const cancel = () => finish(disposedError());
      const timer = setTimeout(() => finish(new Error(message)), timeoutMs);
      pendingWaits.add(cancel);
      try {
        cleanup = register(
          value => finish(null, value),
          error => finish(error),
        );
        if (settled) cleanup?.();
      } catch (error) {
        finish(error);
      }
    });
  }

  function nextFrame(timeoutMs = 10000) {
    return waitForResource(
      resolve => {
        const id = scheduleFrame(resolve);
        return () => {
          window.cancelAnimationFrame(id);
          frames.delete(id);
        };
      },
      timeoutMs,
      '等待地图绘制超时',
    );
  }

  function onMap(name, callback) {
    const currentMap = map;
    const listener = (...args) => {
      if (!disposed) callback(...args);
    };
    currentMap.on(name, listener);
    cleanups.add(() => currentMap.off(name, listener));
  }

  function syncReservations() {
    if (
      disposed ||
      !graph.runtimeRequirements?.capabilities?.includes(
        'layout.reservations@1',
      )
    )
      return null;
    const box = mapContainer.getBoundingClientRect();
    const reservations = [];
    const items = [
      [controlsContainer, 'controls', 'control', 'right'],
      [legend, 'legend', 'legend', null],
      [
        document.getElementById('heatmap-controls'),
        'analysis-controls',
        'control',
        null,
      ],
      [uiContainer, 'content-panel', 'detail', null],
      [sourceContainer, 'sources', 'control', null],
      ...[...mapContainer.querySelectorAll('.amap-logo,.amap-copyright')].map(
        (node, index) => [
          node,
          `attribution-${index}`,
          'attribution',
          'bottom',
        ],
      ),
    ];
    for (const [node, id, role, edge] of items) {
      if (
        !node ||
        node.hidden ||
        getComputedStyle(node).display === 'none' ||
        getComputedStyle(node).visibility === 'hidden'
      )
        continue;
      const rect = node.getBoundingClientRect();
      const left = Math.max(box.left, rect.left),
        top = Math.max(box.top, rect.top);
      const right = Math.min(box.right, rect.right),
        bottom = Math.min(box.bottom, rect.bottom);
      if (
        ![left, top, right, bottom].every(Number.isFinite) ||
        right <= left ||
        bottom <= top
      )
        continue;
      reservations.push({
        id,
        role,
        rect: {
          x: left - box.left,
          y: top - box.top,
          width: right - left,
          height: bottom - top,
        },
        placement: edge ? { kind: 'dock', edge } : { kind: 'floating' },
        blocksLabels: id !== 'content-panel',
        blocksPointer: true,
      });
    }
    const value = {
      mapRect: { x: 0, y: 0, width: box.width, height: box.height },
      reservations,
    };
    if (
      !Number.isFinite(box.width) ||
      !Number.isFinite(box.height) ||
      box.width < 0 ||
      box.height < 0
    )
      throw new Error('地图容器尺寸无效');
    const signature = JSON.stringify(value);
    if (layoutSnapshot?.signature === signature) return layoutSnapshot;
    layer?.setLayoutReservations(
      reservations
        .filter(item => item.blocksLabels)
        .map(item => ({ id: item.id, rect: item.rect })),
    );
    layoutSnapshot = {
      ...value,
      revision: ++layoutRevision,
      signature,
      status:
        box.width >= 160 && box.height >= 120 ? 'ready' : 'insufficient-space',
    };
    return layoutSnapshot;
  }

  function scheduleReservations() {
    if (
      layoutFrame !== undefined ||
      disposed ||
      !layer ||
      !graph.runtimeRequirements?.capabilities?.includes(
        'layout.reservations@1',
      )
    )
      return;
    layoutFrame = scheduleFrame(() => {
      layoutFrame = undefined;
      try {
        const previous = layoutRevision;
        const previousSize = layoutSnapshot?.mapRect;
        const previousPanelState = observedPanelState;
        observedPanelState = {
          mode: [
            uiContainer?.dataset.panelLayout,
            uiContainer?.dataset.panelCollapsed,
            uiContainer?.dataset.panelExpanded,
          ].join(':'),
          selectionRevision,
          viewId: activeViewId,
        };
        syncReservations();
        const nextSize = layoutSnapshot?.mapRect;
        if (
          previousSize &&
          nextSize &&
          (previousSize.width !== nextSize.width ||
            previousSize.height !== nextSize.height ||
            (previousPanelState &&
              previousPanelState.viewId === observedPanelState.viewId &&
              previousPanelState.selectionRevision === selectionRevision &&
              previousPanelState.mode !== observedPanelState.mode)) &&
          nextSize.width >= 160 &&
          nextSize.height >= 120 &&
          currentView().viewport.strategy === 'fit-elements' &&
          cameraContexts.get(activeViewId)?.follow !== false
        ) {
          setCamera(currentView().viewport);
        }
        if (previous !== layoutRevision)
          publish({ reason: 'layout-reservations' });
      } catch (error) {
        recordError('LAYOUT_RESERVATION_ERROR', error.message, error);
      }
    });
  }

  function reservationInsets(snapshot, initial = {}) {
    const inset = { top: 0, right: 0, bottom: 0, left: 0, ...initial };
    for (const item of snapshot.reservations) {
      if (item.placement.kind !== 'dock') continue;
      const { edge } = item.placement;
      const { rect } = item;
      const amount =
        edge === 'top'
          ? rect.y + rect.height
          : edge === 'bottom'
            ? snapshot.mapRect.height - rect.y
            : edge === 'left'
              ? rect.x + rect.width
              : snapshot.mapRect.width - rect.x;
      inset[edge] = Math.max(inset[edge], amount + 8);
    }
    return inset;
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    modeDraft = null;
    modeSequence++;
    cameraFitRequest++;
    pendingCameraFit = false;
    for (const cancel of [...pendingWaits]) cancel();
    for (const id of frames) window.cancelAnimationFrame(id);
    frames.clear();
    let cleanupFailed = false;
    const release = cleanup => {
      try {
        cleanup();
      } catch {
        cleanupFailed = true;
      }
    };
    for (const cleanup of cleanups) release(cleanup);
    cleanups.clear();
    for (const resource of [
      edgeNavigation,
      choroplethLegend,
      heatmapControls,
      controlsRuntime,
      uiRuntime,
      layer,
      map,
    ])
      release(() => resource?.destroy?.());
    choroplethLegend =
      heatmapControls =
      controlsRuntime =
      uiRuntime =
      layer =
      map =
        null;
    for (const cache of [
      heatmapModes,
      cameraContexts,
      hiddenElementIds,
      entryContexts,
      filterStates,
      runtimeErrors,
    ])
      cache.clear();
    legend.replaceChildren();
    const sourceContent = document.getElementById('sources');
    sourceContainer.replaceChildren(...(sourceContent ? [sourceContent] : []));
    document.getElementById('heatmap-controls').replaceChildren();
    hideHover();
    showModeTransition(false);
    document.getElementById('heatmap-controls').removeAttribute('aria-busy');
    status.textContent = cleanupFailed
      ? '地图已关闭，部分资源释放失败'
      : '地图已关闭';
    terminalState = {
      status: 'disposed',
      activeViewId,
      code: cleanupFailed ? 'RUNTIME_DISPOSE_FAILED' : 'RUNTIME_DISPOSED',
    };
    window.mapCreateState = terminalState;
  }

  // Teardown is available during SDK loading without exposing a half-ready API.
  window.mapCreateDispose = dispose;
  const onPageHide = event => {
    if (!event.persisted) dispose();
  };
  window.addEventListener('pagehide', onPageHide);
  cleanups.add(() => window.removeEventListener('pagehide', onPageHide));
  const pageTitle = document.querySelector('#map-app > header h1');
  const showFullTitle = () => {
    if (window.matchMedia?.('(max-width: 760px)').matches)
      window.alert(pageTitle.textContent);
  };
  pageTitle?.addEventListener('click', showFullTitle);
  cleanups.add(() => pageTitle?.removeEventListener('click', showFullTitle));


  function updateVisibilityUi() {
    if (
      !graph.runtimeRequirements?.capabilities?.includes(
        'ui.controlled-visibility@1',
      )
    )
      return;
    const excluded = new Set(excludedPointElements());
    uiRuntime?.setVisibilitySnapshot({
      viewId: activeViewId,
      revision: ++visibilityRevision,
      elements: currentView().elementIds.map(elementId => ({
        elementId,
        visible: isVisible(elementId),
        toggleable:
          !excluded.has(elementId) &&
          elementById.get(elementId)?.props.visible !== false,
      })),
    });
  }

  function filterSnapshot(view = currentView()) {
    if (filterStates.has(view.id)) return filterStates.get(view.id);
    const state = {
      groups: (view.analysisFilters || []).map(group => ({
        definition: group,
        selected: group.fields.map(() => null),
        pointIds: group.rows.map(row => row.pointId),
        ...(group.sourceRows
          ? window.mapCreateDeriveSource(
              { rows: group.sourceRows },
              group.fields,
              group.fields.map(() => null),
              group.metricDefinitions,
            )
          : {}),
      })),
      revision: filterRevision,
    };
    filterStates.set(view.id, state);
    return state;
  }

  function excludedPointElements() {
    return filterSnapshot().groups.flatMap(group => {
      const included = new Set(group.pointIds);
      return group.definition.pointElements
        .filter(item => !included.has(item.pointId))
        .map(item => item.elementId);
    });
  }

  function updateFilterUi() {
    const state = filterSnapshot();
    if (
      !currentView().analysisFilters?.length &&
      !uiRuntime?.setAnalysisFilters
    )
      return;
    uiRuntime?.setAnalysisFilters({
      viewId: activeViewId,
      revision: state.revision,
      excludedElementIds: excludedPointElements(),
      groups: state.groups.map(group => ({
        sourceId: group.definition.sourceId,
        title: group.definition.title,
        sourceCount: group.definition.rows.length,
        effectiveCount: group.pointIds.length,
        metrics: group.metrics || [],
        fields: group.definition.fields.map((field, index) => ({
          ...field,
          selected: group.selected[index],
        })),
      })),
    });
  }

  function setAnalysisFilter({ sourceId, fieldId, selected }) {
    const state = filterSnapshot();
    const group = state.groups.find(
      group => group.definition.sourceId === sourceId,
    );
    if (!group) throw new Error('筛选数据源不属于当前 View');
    const fieldIndex = group.definition.fields.findIndex(
      field => field.id === fieldId,
    );
    if (fieldId === undefined ? selected !== null : fieldIndex < 0)
      throw new Error('筛选字段或重置请求无效');
    if (
      !group.definition.sourceRows &&
      selected !== null &&
      (!Array.isArray(selected) ||
        new Set(selected).size !== selected.length ||
        selected.some(
          index =>
            !Number.isInteger(index) ||
            index < 0 ||
            index >= group.definition.fields[fieldIndex].options.length,
        ))
    )
      throw new Error('筛选选项无效，保留上一次合法状态');
    const next = group.selected.map((value, index) =>
      fieldId === undefined
        ? null
        : index === fieldIndex
          ? selected === null
            ? null
            : structuredClone(selected)
          : value,
    );
    const derived = group.definition.sourceRows
      ? window.mapCreateDeriveSource(
          { rows: group.definition.sourceRows },
          group.definition.fields,
          next,
          group.definition.metricDefinitions,
        )
      : null;
    const pointIds =
      derived?.pointIds ??
      group.definition.rows
        .filter(row =>
          group.definition.fields.every(
            (field, index) =>
              next[index] === null ||
              next[index].some(
                option => field.options[option].value === row.values[index],
              ),
          ),
        )
        .map(row => row.pointId);
    // Validate the next aggregate using the Kit's existing resolver before
    // committing predicates, metrics or selections. Do not duplicate its grid.
    if (group.definition.sourceRows) {
      for (const id of group.definition.elementIds) {
        const element = elementById.get(id).props;
        window.ContentMapKit.getHeatmapRenderExtent({
          ...element,
          mode: heatmapModes.get(id) || element.mode,
          filter: {
            pointIds,
            scalePopulation: group.definition.scalePopulation,
          },
        });
      }
    }
    cancelModeTransition();
    cancelCameraFit();
    group.selected = next;
    group.pointIds = pointIds;
    group.metrics = derived?.metrics || [];
    state.revision = ++filterRevision;
    // Invalidate stale query statistics before submitting the new population.
    // No fit: even an empty result preserves the user's camera.
    clearFeatureSelection();
    selectedElementId = null;
    selectedSeriesId = null;
    layer.setElements(currentElements());
    layer.setSelected(null);
    layer.setSeriesSelected(null);
    syncingUi = true;
    uiRuntime.selectElement(null);
    syncingUi = false;
    updateFilterUi();
    updateVisibilityUi();
    updateHeatmapControls();
    renderLegend();
    revision += 1;
    publish({ reason: 'analysis-filter' });
  }

  const currentView = () => viewById.get(activeViewId);
  const isVisible = id =>
    currentView().elementIds.includes(id) &&
    !hiddenElementIds.has(id) &&
    !excludedPointElements().includes(id) &&
    elementById.get(id)?.props.visible !== false;
  const currentElements = () => {
    return currentView()
      .elementIds.map(id => elementById.get(id))
      .filter(Boolean)
      .map(element => ({
        ...element.props,
        ...(element.componentId === 'heatmap'
          ? {
              modes: element.props.modes,
              mode: heatmapModes.get(element.id) || element.props.mode,
              ...(() => {
                const group = filterSnapshot().groups.find(group =>
                  group.definition.elementIds.includes(element.id),
                );
                return group
                  ? {
                      filter: {
                        pointIds: group.pointIds,
                        scalePopulation: group.definition.scalePopulation,
                      },
                    }
                  : {};
              })(),
            }
          : {}),
        visible: isVisible(element.id),
        collisionPriority: element.collisionPriority,
        partCollisionPriorities: element.partCollisionPriorities,
        zIndex: element.zIndex,
      }));
  };

  function updateHeatmapControls() {
    choroplethLegend?.update(
      currentElements().filter(
        element => element.type === 'choropleth' && element.visible,
      ),
    );
    heatmapControls?.update(
      currentElements().filter(
        element => element.type === 'heatmap' && element.visible,
      ),
    );
  }

  function readCamera() {
    const center = map.getCenter();
    return {
      center: [center.lng ?? center.getLng(), center.lat ?? center.getLat()],
      zoom: map.getZoom(),
      pitch: map.getPitch(),
      rotation: map.getRotation?.() || 0,
    };
  }

  function restoreCamera(camera) {
    map.setZoomAndCenter(camera.zoom, camera.center, true);
    map.setRotation?.(camera.rotation, true);
    setCameraPitch(camera.pitch);
  }

  function setCameraPitch(pitch) {
    // Avoid redundant camera events and preserve 2D-only host compatibility.
    if (map.getPitch() !== pitch) map.setPitch(pitch, true);
  }

  function markUserCamera() {
    cancelModeTransition({ preserveCamera: true });
    cancelCameraFit();
    const context = cameraContexts.get(activeViewId);
    if (context) {
      context.userChanged = true;
      context.follow = false;
    }
    gestureCamera = null;
  }

  function observeCameraIntent() {
    if (
      gestureCamera &&
      JSON.stringify(gestureCamera) !== JSON.stringify(readCamera())
    ) {
      window.mapCreateTelemetry?.interaction(
        gestureCamera.zoom !== readCamera().zoom ? 'zoom_map' : 'pan_map',
        'map',
      );
      markUserCamera();
    }
  }

  function compatibleAnalysisModes(elements) {
    const visible = elements.filter(
      element => element.visible && element.type === 'heatmap',
    );
    return !(
      visible.some(element => element.mode === 'continuous') &&
      visible.some(element => element.mode === 'hexbin-3d')
    );
  }

  function setElementVisibility(id, visible) {
    if (!currentView().elementIds.includes(id)) return false;
    if (
      elementById.get(id)?.props.visible === false ||
      excludedPointElements().includes(id)
    ) {
      updateVisibilityUi();
      return false;
    }
    cancelModeTransition();
    const next = currentElements().map(element =>
      element.id === id
        ? {
            ...element,
            visible:
              visible !== false && elementById.get(id).props.visible !== false,
          }
        : element,
    );
    if (!compatibleAnalysisModes(next)) {
      interactionNotice =
        '连续热力与三维蜂窝不能同时显示；请先调整另一图层的模式或显隐。';
      publish({ reason: 'visibility-rejected' });
      return false;
    }
    interactionNotice = null;
    cancelCameraFit();
    if (visible === false) hiddenElementIds.add(id);
    else hiddenElementIds.delete(id);
    layer.setVisible(id, isVisible(id));
    applyHeatmapPitch();
    if (selectedElementId === id && visible === false) selectElement(null);
    renderLegend();
    updateHeatmapControls();
    updateVisibilityUi();
    revision += 1;
    publish({ reason: 'element-visibility' });
    window.mapCreateTelemetry?.interaction('toggle_visibility', 'sidebar');
    return true;
  }

  function applyHeatmapPitch({ restoreView = false } = {}) {
    const raised = currentElements().some(e => e.visible && e.type === 'heatmap' && e.mode === 'hexbin-3d');
    let context = cameraContexts.get(activeViewId);
    if (!context) {
      context = {dimension:'planar',planar:null,last:null,userChanged:false,follow:currentView().viewport.strategy==='fit-elements'};
      cameraContexts.set(activeViewId,context);
    }
    if (restoreView && context.last) restoreCamera({...context.last,pitch:0});
    context.dimension = raised ? '3d' : 'planar';
    cameraViewId = activeViewId;
    // Fixed tilt belongs to the Canvas renderer; the SDK stays planar.
    if (map.getPitch() !== 0) map.setPitch(0,true);
  }


  function restoreModeSelection(snapshot, mode) {
    selectedElementId = snapshot.selectedElementId;
    selectedSeriesId = snapshot.selectedSeriesId;
    selectedFeatureId = snapshot.selectedFeatureId;
    selectedFeature = snapshot.selectedFeature;
    if (selectedFeature?.elementId === snapshot.id && mode === 'continuous') {
      selectedElementId = null;
      selectedFeatureId = null;
      selectedFeature = null;
    }
    layer.setSelected(selectedFeature ? null : selectedElementId);
    layer.setSeriesSelected(selectedSeriesId);
    if (selectedFeature)
      layer.setFeatureSelected(selectedElementId, selectedFeatureId);
    syncingUi = true;
    try {
      uiRuntime?.selectElement(selectedElementId);
      if (selectedFeature) showFeatureDetails();
    } finally {
      syncingUi = false;
    }
  }

  function cancelModeTransition({ preserveCamera = false } = {}) {
    if (!modeDraft) return;
    const snapshot = modeDraft;
    modeDraft = null;
    modeTransition = { sequence: ++modeSequence, status: 'idle' };
    cancelCameraFit();
    heatmapModes.clear();
    for (const [id, mode] of snapshot.modes) heatmapModes.set(id, mode);
    cameraContexts.set(activeViewId, structuredClone(snapshot.context));
    const current = preserveCamera ? readCamera() : null;
    restoreCamera(
      current ? { ...current, pitch: snapshot.camera.pitch } : snapshot.camera,
    );
    fitState = snapshot.fitState;
    layer.setElements(currentElements());
    restoreModeSelection(snapshot);
    updateHeatmapControls();
    renderLegend();
    document.getElementById('heatmap-controls').removeAttribute('aria-busy');
    showModeTransition(false);
    interactionNotice = null;
    publish({ reason: 'heatmap-mode-cancelled' });
  }

  async function completeModeTransition(snapshot, mode) {
    const started = performance.now();
    let previous,
      stableFrames = 0;
    try {
      while (modeDraft === snapshot) {
        const remaining = 10000 - (performance.now() - started);
        if (remaining <= 0) throw new Error('MODE_TRANSITION_TIMEOUT');
        await nextFrame(remaining);
        if (modeDraft !== snapshot) return;
        const contentLayout = assertLayoutBudget();
        const native = layer.getAnalysisRenderState();
        if (snapshot.error || native.status === 'failed')
          throw new Error('MODE_TRANSITION_RENDER_FAILED');
        const signature = JSON.stringify([
          native.revision,
          native.nativeRevision,
          readCamera(),
          cameraEventRevision,
          contentLayout,
        ]);
        const ready =
          native.status === 'ready' &&
          !pendingCameraFit &&
          contentLayout?.status !== 'pending';
        stableFrames = ready && signature === previous ? stableFrames + 1 : 0;
        previous = signature;
        if (stableFrames < 2) continue;
        modeDraft = null;
        modeTransition = {
          sequence: snapshot.sequence,
          status: 'ready',
          targetLayerId: snapshot.id,
          targetMode: mode,
        };
        restoreModeSelection(snapshot, mode);
        updateHeatmapControls();
        renderLegend();
        document
          .getElementById('heatmap-controls')
          .removeAttribute('aria-busy');
        showModeTransition(false);
        interactionNotice = null;
        revision++;
        publish({ reason: 'heatmap-mode' });
        return;
      }
    } catch {
      if (modeDraft !== snapshot) return;
      let restored = true;
      try {
        cancelModeTransition();
      } catch {
        restored = false;
        document
          .getElementById('heatmap-controls')
          .removeAttribute('aria-busy');
        recordError('MODE_ROLLBACK_FAILED', '模式恢复失败，请重新加载地图。');
      }
      showModeTransition(false);
      modeTransition = {
        sequence: modeSequence,
        status: 'failed',
        targetLayerId: snapshot.id,
        targetMode: mode,
      };
      interactionNotice = restored
        ? '展示方式切换失败，已恢复上一次模式；可重试或选择其他展示方式。'
        : '展示方式切换及恢复失败，请重新加载地图。';
      publish({ reason: 'heatmap-mode-failed' });
    }
  }

  function setHeatmapMode(id, mode) {
    cancelModeTransition();
    const element = currentElements().find(
      element => element.id === id && element.type === 'heatmap',
    );
    if (!element || !element.modes.includes(mode))
      throw new Error('不支持的热力展示模式');
    if (element.mode === mode) return;
    if (
      !compatibleAnalysisModes(
        currentElements().map(item =>
          item.id === id ? { ...item, mode } : item,
        ),
      )
    ) {
      interactionNotice =
        '连续热力与三维蜂窝不能同时显示；请先将另一层切换为蜂窝 2D 或隐藏该层。';
      publish({ reason: 'heatmap-mode-rejected' });
      return false;
    }
    interactionNotice = null;
    cancelCameraFit();
    if (
      graph.runtimeRequirements?.capabilities?.includes(
        'heatmap.render-state@1',
      )
    ) {
      const snapshot = {
        id,
        sequence: ++modeSequence,
        modes: new Map(heatmapModes),
        camera: readCamera(),
        context: structuredClone(cameraContexts.get(activeViewId)),
        fitState,
        selectedElementId,
        selectedSeriesId,
        selectedFeatureId,
        selectedFeature,
      };
      modeDraft = snapshot;
      modeTransition = {
        sequence: snapshot.sequence,
        status: 'preparing',
        targetLayerId: id,
        targetMode: mode,
      };
      heatmapModes.set(id, mode);
      interactionNotice = '正在切换展示方式…';
      document
        .getElementById('heatmap-controls')
        .setAttribute('aria-busy', 'true');
      showModeTransition(true);
      try {
        layer.setElements(currentElements());
        applyHeatmapPitch();
      } catch {
        snapshot.error = true;
      }
      publish({ reason: 'heatmap-mode-preparing' });
      void completeModeTransition(snapshot, mode);
      return true;
    }
    const preserveFeature =
      selectedFeature?.elementId === id &&
      element.mode !== 'continuous' &&
      mode !== 'continuous'
        ? selectedFeature
        : null;
    clearFeatureSelection();
    heatmapModes.set(id, mode);
    selectedElementId = null;
    selectedFeatureId = null;
    selectedSeriesId = null;
    layer.setElements(currentElements());
    layer.setSeriesSelected(null);
    uiRuntime?.selectElement(null);
    if (preserveFeature) {
      selectedFeature = preserveFeature;
      selectedElementId = preserveFeature.elementId;
      selectedFeatureId = preserveFeature.featureId;
      layer.setFeatureSelected(selectedElementId, selectedFeatureId);
      showFeatureDetails();
    }
    applyHeatmapPitch();
    updateHeatmapControls();
    revision += 1;
    publish({ reason: 'heatmap-mode' });
  }

  function publish(extra = {}) {
    if (disposed) return;
    scheduleReservations();
    scheduleEdgeNavigation();
    const view = currentView();
    window.mapCreateState = {
      layoutSnapshot: layoutSnapshot && {
        revision: layoutSnapshot.revision,
        mapRect: layoutSnapshot.mapRect,
        reservations: layoutSnapshot.reservations,
        status: layoutSnapshot.status,
        degradations: [...layoutDegradations],
        legendCollapsed,
        detailCollapsed,
      },
      status: runtimeErrors.size ? 'error' : 'ready',
      errors: [...runtimeErrors.values()],
      message: [...runtimeErrors.values()]
        .map(error => error.message)
        .join('; '),
      activeViewId,
      selectedElementId,
      selectedSeriesId,
      selectedFeatureId,
      selectedFeatureValue: selectedFeature?.value ?? null,
      selectedFeatureCount: selectedFeature?.count ?? null,
      selectedFeatureMemberIds: selectedFeature
        ? [...selectedFeature.memberIds]
        : [],
      visibleElementIds: view.elementIds.filter(isVisible),
      revision,
      fitCount,
      fitState,
      initialCamera,
      viewportEntries,
      cameraEventRevision,
      pendingCameraFit,
      modeTransition: { ...modeTransition },
      cameraContext: cameraContexts.get(activeViewId)
        ? {
            dimension: cameraContexts.get(activeViewId).dimension,
            follow: cameraContexts.get(activeViewId).follow,
            userChanged: cameraContexts.get(activeViewId).userChanged,
          }
        : null,
      interactionNotice,
      cameraNotice,
      hiddenElementIds: [...hiddenElementIds],
      filterRevision: filterSnapshot().revision,
      analysisFilters: filterSnapshot().groups.map(group => ({
        sourceId: group.definition.sourceId,
        selected: group.selected.map(value => value?.slice() ?? null),
        pointIds: [...group.pointIds],
        effectiveCount: group.pointIds.length,
        sourceCount: group.definition.rows.length,
      })),
      heatmapModes: Object.fromEntries(
        currentElements()
          .filter(element => element.type === 'heatmap')
          .map(element => [
            element.id,
            modeDraft
              ? modeDraft.modes.get(element.id) ||
                elementById.get(element.id).props.mode
              : element.mode,
          ]),
      ),
      visualTheme: graph.visualTheme,
      ...extra,
    };
    mapContainer.dataset.activeView = activeViewId;
    status.textContent = runtimeErrors.size
      ? `地图存在错误 · ${window.mapCreateState.message}`
      : interactionNotice || cameraNotice || `地图已加载 · ${view.title}`;
    mapContainer.dispatchEvent(
      new CustomEvent('mapcreatechange', {
        detail: window.mapCreateState,
        bubbles: true,
      }),
    );
  }

  function recordError(code, message, exception) {
    if (disposed) return;
    window.mapCreateTelemetry?.error(
      code,
      false,
      exception,
      /CAMERA/.test(code) ? 'camera' : /LAYOUT/.test(code) ? 'layout' : 'render',
    );
    if (modeDraft) {
      modeDraft.error = code;
      return;
    }
    // A persistent observer failure must not schedule the same failing frame forever.
    if (runtimeErrors.get(code)?.message === message) return;
    runtimeErrors.set(code, { code, message });
    publish({ reason: 'runtime-error' });
  }

  function clearFeatureSelection() {
    if (selectedFeatureId && selectedElementId)
      layer.setFeatureSelected(selectedElementId, null);
    selectedFeatureId = null;
    selectedFeature = null;
  }

  function showFeatureDetails() {
    if (!selectedFeature || !uiRuntime) return;
    const element = currentElements().find(
      item => item.id === selectedFeature.elementId,
    );
    const capable =
      window.ContentMapKit.getRuntimeContract?.()?.capabilities?.includes(
        'ui.feature-details@1',
      );
    if (!element || !capable) {
      uiRuntime.selectElement(selectedFeature.elementId);
      return;
    }
    const continuous = element.mode === 'continuous';
    const method = element.hexbin?.aggregation?.method || 'count';
    const labels = {
      count: '格内样本数',
      sum: '格内数值合计',
      average: '格内平均值',
      max: '格内最大值',
    };
    uiRuntime.selectFeature({
      elementId: selectedFeature.elementId,
      featureId: selectedFeature.featureId,
      title: continuous ? '热力样本' : '选中蜂窝',
      context: continuous
        ? '样本查询 · 非范围统计'
        : `蜂窝 ${element.mode === 'hexbin-3d' ? '3D' : '2D'}`,
      description: continuous
        ? '此处命中的是查询范围内的一个样本，不代表附近事件总数或热力颜色对应的绝对值。'
        : element.mode === 'hexbin-3d'
          ? '虚线圈定选中格子的地面范围；柱高为视觉编码，不是真实海拔。'
          : '描边圈定当前格子，统计范围仅包含该格内样本。',
      fields: [
        {
          label: continuous ? '样本数值' : labels[method],
          value: selectedFeature.value,
        },
        ...(!continuous && method !== 'count'
          ? [{ label: '格内样本数', value: selectedFeature.count }]
          : []),
      ],
    });
  }

  function hideHover() {
    if (!hoverContainer) return;
    hoverContainer.hidden = true;
    hoverContainer.replaceChildren();
    delete hoverContainer.dataset.hoveredElementId;
    delete hoverContainer.dataset.hoveredFeatureId;
  }

  function showHover(event) {
    if (!event || !hoverContainer || !isVisible(event.id)) {
      hideHover();
      return;
    }
    const definition = elementById.get(event.id);
    if (!definition || definition.props.interaction?.hoverable === false) {
      hideHover();
      return;
    }
    const rendered = currentElements().find(element => element.id === event.id);
    const props = rendered || definition.props;
    const label =
      typeof props.label === 'string' ? props.label : props.label?.text;
    const mode = props.type === 'heatmap' ? props.mode : null;
    const method = props.hexbin?.aggregation?.method || 'count';
    const aggregateLabels = {
      count: '格内样本数',
      sum: '格内数值合计',
      average: '格内平均值',
      max: '格内最大值',
    };
    const title = event.featureId
      ? mode === 'continuous'
        ? '热力样本'
        : mode === 'hexbin-3d'
          ? '三维蜂窝'
          : '二维蜂窝'
      : label || props.title || props.text;
    const facts = event.featureId
      ? [
          {
            label: mode === 'continuous' ? '样本值' : aggregateLabels[method],
            value: event.value,
          },
          ...(mode !== 'continuous' && method !== 'count'
            ? [{ label: '格内样本数', value: event.count }]
            : []),
        ]
      : currentView()
          .ui.sections.filter(
            section => section.source === 'selected.properties',
          )
          .flatMap(section => section.items || [])
          .filter(
            item => item.ownerElementId === event.id && item.label !== '名称',
          )
          .slice(0, 2)
          .map(item => ({
            label: item.label,
            value: String(item.value).slice(0, 120),
          }));
    if (!title) {
      hideHover();
      return;
    }
    hoverContainer.replaceChildren(
      window.ContentMapKit.createMapHover({
        title,
        fields: facts.filter(fact => fact.value !== undefined),
        theme: shellTheme,
      }),
    );
    hoverContainer.dataset.hoveredElementId = event.id;
    if (event.featureId)
      hoverContainer.dataset.hoveredFeatureId = event.featureId;
    else delete hoverContainer.dataset.hoveredFeatureId;
    hoverContainer.hidden = false;
    const mapBox = mapContainer.getBoundingClientRect();
    const original = event.originalEvent || {};
    const rawX = Number.isFinite(original.clientX)
      ? original.clientX - mapBox.left
      : Number.isFinite(original.pixel?.x)
        ? original.pixel.x
        : mapBox.width / 2;
    const rawY = Number.isFinite(original.clientY)
      ? original.clientY - mapBox.top
      : Number.isFinite(original.pixel?.y)
        ? original.pixel.y
        : mapBox.height / 2;
    const box = hoverContainer.getBoundingClientRect();
    const obstacles = [
      uiContainer,
      controlsContainer,
      document.getElementById('map-panels'),
      sourceContainer,
    ]
      .filter(Boolean)
      .map(node => node.getBoundingClientRect())
      .filter(rect => rect.width > 0 && rect.height > 0);
    const candidates = [
      [rawX + 12, rawY + 12],
      [rawX + 12, rawY - box.height - 12],
      [rawX - box.width - 12, rawY - box.height - 12],
      [rawX - box.width - 12, rawY + 12],
    ].map(([left, top]) => ({
      left: Math.min(
        Math.max(12, left),
        Math.max(12, mapBox.width - box.width - 12),
      ),
      top: Math.min(
        Math.max(12, top),
        Math.max(12, mapBox.height - box.height - 12),
      ),
    }));
    const position = candidates.find(
      candidate =>
        !obstacles.some(
          rect =>
            candidate.left + box.width + mapBox.left > rect.left &&
            candidate.left + mapBox.left < rect.right &&
            candidate.top + box.height + mapBox.top > rect.top &&
            candidate.top + mapBox.top < rect.bottom,
        ),
    );
    if (!position) {
      hideHover();
      return;
    }
    hoverContainer.style.left = `${position.left}px`;
    hoverContainer.style.top = `${position.top}px`;
  }

  function createElement(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function renderLegend() {
    legend.replaceChildren();
    legend.dataset.scope = 'view';
    const items = (currentView().legendSeriesIds || [])
      .map(seriesId => graph.seriesStyles?.[seriesId])
      .filter(
        item =>
          item &&
          graph.elements.some(
            element => element.seriesId === item.id && isVisible(element.id),
          ),
      );
    if (!items.length) return;
    const list = createElement('ul', 'legend__list');
    list.id = 'map-legend-items';
    list.dataset.hasSelection = String(Boolean(selectedSeriesId));
    for (const item of items) {
      const row = createElement('li', 'legend__row');
      const button = createElement('button', 'legend__item');
      button.type = 'button';
      button.dataset.seriesId = item.id;
      button.disabled = !graph.elements.some(
        element =>
          isVisible(element.id) &&
          element.seriesId === item.id &&
          element.props?.interaction?.selectable !== false,
      );
      button.setAttribute('aria-pressed', String(selectedSeriesId === item.id));
      button.addEventListener('click', () =>
        selectSeries(selectedSeriesId === item.id ? null : item.id, {
          source: 'legend',
        }),
      );
      const kind = item.kind === 'area' ? 'area' : 'line';
      const swatch = createElement(
        'span',
        `legend__swatch legend__swatch--${kind}`,
      );
      swatch.style.setProperty(
        '--legend-color',
        item.kind === 'area' ? item.fillColor : item.color,
      );
      if (kind === 'line') {
        const representative = currentElements().find(
          element =>
            element.seriesId === item.id && element.visible && element.path,
        );
        const supportsSymbol =
          window.ContentMapKit.getRuntimeContract?.().capabilities?.includes(
            'route.legend-symbol@1',
          );
        if (supportsSymbol && representative) {
          const symbol =
            window.ContentMapKit.getRouteLegendSymbol(representative);
          const namespace = 'http://www.w3.org/2000/svg';
          const svg = document.createElementNS(namespace, 'svg');
          svg.setAttribute('viewBox', symbol.viewBox.join(' '));
          svg.setAttribute('width', String(symbol.width));
          svg.setAttribute('height', String(symbol.height));
          svg.setAttribute('aria-hidden', 'true');
          for (const part of symbol.nodes) {
            if (part.tag === 'texture')
              throw new Error('路线图例不支持未解析纹理');
            const node = document.createElementNS(namespace, part.tag);
            for (const [key, value] of Object.entries(part.attrs))
              node.setAttribute(key, String(value));
            node.setAttribute('data-part', part.part);
            if (part.text !== undefined) node.textContent = part.text;
            svg.append(node);
          }
          Object.assign(swatch.style, {
            width: `${symbol.width}px`,
            height: `${symbol.height}px`,
            border: '0',
            background: 'transparent',
          });
          swatch.dataset.symbolElementId = representative.id;
          swatch.dataset.symbolScale = String(symbol.scale);
          swatch.dataset.componentType = symbol.componentType;
          swatch.append(svg);
        } else {
          swatch.dataset.symbolEvidence = 'legacy-css';
          swatch.style.setProperty('--legend-width', `${item.width || 4}px`);
          swatch.style.setProperty('--legend-line-style', 'solid');
        }
      }
      button.append(swatch, createElement('span', '', item.label));
      row.append(button);
      list.append(row);
    }
    legend.append(
      window.ContentMapKit.createMapDisclosure({
        title: '图例',
        content: list,
        theme: shellTheme,
        collapsed: legendCollapsed,
        onToggle: collapsed => {
          if (legendCollapsed === collapsed || disposed) return;
          legendCollapsed = collapsed;
          scheduleReservations();
          publish({ reason: 'legend-disclosure' });
        },
      }),
    );
  }

  const { selectElement, selectSeries } = window.mapCreateSelectionController({
    read: () => ({ elementId: selectedElementId, seriesId: selectedSeriesId }),
    element: id => elementById.get(id),
    elements: () => graph.elements,
    view: currentView,
    visible: isVisible,
    commit: selection => {
      const changed =
        selectedElementId !== selection.elementId ||
        selectedSeriesId !== selection.seriesId;
      selectionRevision += 1;
      cancelModeTransition();
      clearFeatureSelection();
      selectedElementId = selection.elementId;
      selectedSeriesId = selection.seriesId;
      selectedFeatureId = null;
      layer.setSelected(
        elementById.get(selection.elementId)?.businessRef?.type === 'route'
          ? null
          : selection.elementId,
      );
      layer.setSeriesSelected(selection.seriesId);
      if (uiRuntime) {
        syncingUi = true;
        uiRuntime.selectElement(selection.elementId);
        syncingUi = false;
      }
      revision += 1;
      renderLegend();
      applyHeatmapPitch();
      updateFilterUi();
      updateHeatmapControls();
      publish({ reason: selection.reason });
      if (changed)
        window.mapCreateTelemetry?.interaction(
          selection.elementId || selection.seriesId ? 'select_object' : 'clear_selection',
        );
    },
  });

  function visibleFitBounds(viewport) {
    // The compiler may restrict fit-elements to an explicitly requested region.
    // Visibility/filtering may narrow that scope, never replace it with the whole View.
    const scope = new Set(viewport.elementIds || currentView().elementIds);
    const footprint = { top: 0, right: 0, bottom: 0, left: 0 };
    const extentEnabled = graph.runtimeRequirements?.capabilities?.includes(
      'heatmap.render-extent@1',
    );
    let coverage = 'geometry';
    let west = Infinity,
      south = Infinity,
      east = -Infinity,
      north = -Infinity;
    function include(coordinate) {
      if (
        !Array.isArray(coordinate) ||
        coordinate.length !== 2 ||
        !coordinate.every(Number.isFinite) ||
        Math.abs(coordinate[0]) > 180 ||
        Math.abs(coordinate[1]) > 85
      )
        return;
      west = Math.min(west, coordinate[0]);
      east = Math.max(east, coordinate[0]);
      south = Math.min(south, coordinate[1]);
      north = Math.max(north, coordinate[1]);
    }
    function includeGeometry(value) {
      if (!Array.isArray(value)) return;
      if (typeof value[0] === 'number') include(value);
      else for (const child of value) includeGeometry(child);
    }
    for (const element of currentElements()) {
      if (!element.visible || !scope.has(element.id)) continue;
      if (element.type === 'heatmap') {
        if (extentEnabled) {
          const extent = window.ContentMapKit.getHeatmapRenderExtent(element);
          if (extent.bounds) {
            include(extent.bounds.southwest);
            include(extent.bounds.northeast);
            for (const edge of Object.keys(footprint))
              footprint[edge] = Math.max(
                footprint[edge],
                extent.footprint[edge],
              );
          }
          if (extent.extrusions.length) coverage = 'ground-only';
          continue;
        }
        coverage = 'legacy-sample-bounds';
        const included =
          element.filter?.pointIds == null
            ? null
            : new Set(element.filter.pointIds);
        for (const point of element.points || []) {
          if (!included || included.has(point.id)) include(point.position);
        }
      } else if (element.type === 'circle') {
        const bounds = window.ContentMapKit.getCircleBounds(element.center, element.radiusMeters);
        include(bounds.southwest);
        include(bounds.northeast);
      } else if (element.position) include(element.position);
      else if (element.path) includeGeometry(element.path);
      else if (element.polygons) includeGeometry(element.polygons);
      else for (const point of element.points || []) include(point.position);
    }
    return {
      bounds: Number.isFinite(west)
        ? { southwest: [west, south], northeast: [east, north] }
        : null,
      footprint,
      coverage,
    };
  }

  function cancelCameraFit() {
    cameraFitRequest += 1;
    if (!pendingCameraFit) return;
    pendingCameraFit = false;
    if (fitState?.outcome === 'validating')
      fitState = { ...fitState, outcome: 'cancelled' };
    publish({ reason: 'fit-cancelled' });
  }

  function elevatedSafeRect(padding) {
    const snapshot = syncReservations();
    if (snapshot) {
      const inset = reservationInsets(snapshot, padding);
      let candidates = [
        {
          left: inset.left,
          top: inset.top,
          right: snapshot.mapRect.width - inset.right,
          bottom: snapshot.mapRect.height - inset.bottom,
        },
      ];
      // Floating panels are local blockers, not an arbitrary full-edge inset.
      // Post-fit validation can choose an actual free sub-rectangle if needed.
      for (const { rect, placement } of snapshot.reservations) {
        if (placement.kind !== 'floating') continue;
        const obstacle = {
          left: rect.x - 8,
          top: rect.y - 8,
          right: rect.x + rect.width + 8,
          bottom: rect.y + rect.height + 8,
        };
        candidates = candidates.flatMap(candidate => {
          if (
            obstacle.left >= candidate.right ||
            obstacle.right <= candidate.left ||
            obstacle.top >= candidate.bottom ||
            obstacle.bottom <= candidate.top
          )
            return [candidate];
          return [
            { ...candidate, right: Math.min(candidate.right, obstacle.left) },
            { ...candidate, left: Math.max(candidate.left, obstacle.right) },
            { ...candidate, bottom: Math.min(candidate.bottom, obstacle.top) },
            { ...candidate, top: Math.max(candidate.top, obstacle.bottom) },
          ].filter(
            rect =>
              rect.right - rect.left >= 160 && rect.bottom - rect.top >= 120,
          );
        });
      }
      return (
        candidates.sort(
          (a, b) =>
            (b.right - b.left) * (b.bottom - b.top) -
            (a.right - a.left) * (a.bottom - a.top),
        )[0] || { left: 0, top: 0, right: 0, bottom: 0 }
      );
    }
    const shell = mapContainer.getBoundingClientRect();
    const inset = { ...padding };
    // UI lives outside the renderer. Reserve the smallest normalized edge strip
    // containing each measured overlay, not the width of a bottom-docked legend.
    for (const node of [
      controlsContainer,
      legend,
      uiContainer,
      sourceContainer,
      document.getElementById('heatmap-controls'),
      ...mapContainer.querySelectorAll('.amap-logo,.amap-copyright'),
    ]) {
      if (!node || node.hidden || getComputedStyle(node).display === 'none')
        continue;
      const rect = node.getBoundingClientRect();
      if (
        !rect.width ||
        !rect.height ||
        rect.right <= shell.left ||
        rect.left >= shell.right ||
        rect.bottom <= shell.top ||
        rect.top >= shell.bottom
      )
        continue;
      const edges = [
        [
          'left',
          (rect.right - shell.left) / shell.width,
          rect.right - shell.left,
        ],
        [
          'right',
          (shell.right - rect.left) / shell.width,
          shell.right - rect.left,
        ],
        [
          'top',
          (rect.bottom - shell.top) / shell.height,
          rect.bottom - shell.top,
        ],
        [
          'bottom',
          (shell.bottom - rect.top) / shell.height,
          shell.bottom - rect.top,
        ],
      ];
      const [edge, , amount] = edges.sort((a, b) => a[1] - b[1])[0];
      inset[edge] = Math.max(inset[edge] || 0, amount + 8);
    }
    return {
      left: inset.left,
      top: inset.top,
      right: shell.width - inset.right,
      bottom: shell.height - inset.bottom,
    };
  }

  function viewportPadding(viewport) {
    const box = mapContainer.getBoundingClientRect();
    const maximumHorizontal = Math.max(0, (box.width - 160) / 2);
    const maximumVertical = Math.max(0, (box.height - 120) / 2);
    let padding = viewport.padding || {};
    if (viewport.selectedBy === 'compiler-default' && box.width < 600)
      padding = { top: 24, right: 24, bottom: 24, left: 24 };
    return {
      top: Math.min(padding.top || 0, maximumVertical),
      bottom: Math.min(padding.bottom || 0, maximumVertical),
      left: Math.min(padding.left || 0, maximumHorizontal),
      right: Math.min(padding.right || 0, maximumHorizontal),
    };
  }

  function readViewportEntries() {
    const box = mapContainer.getBoundingClientRect();
    const geometry = layer.getScreenGeometry();
    const titles = new Map();
    for (const text of mapContainer.querySelectorAll(
      'text[data-part="label"], [data-part="label"] text',
    )) {
      const id = text
        .closest('[data-element-id]')
        ?.getAttribute('data-element-id');
      const rect = text.getBoundingClientRect();
      if (!id || !rect.width || !rect.height) continue;
      const previous = titles.get(id);
      titles.set(id, {
        left: Math.min(previous?.left ?? Infinity, rect.left - box.left),
        right: Math.max(previous?.right ?? -Infinity, rect.right - box.left),
        top: Math.min(previous?.top ?? Infinity, rect.top - box.top),
        bottom: Math.max(previous?.bottom ?? -Infinity, rect.bottom - box.top),
      });
    }
    geometry.items = geometry.items.map(item =>
      item.part === 'label' && titles.has(item.elementId)
        ? { ...item, bounds: titles.get(item.elementId) }
        : item,
    );
    return window.mapCreateViewportEntries(
      currentElements(),
      geometry,
      {
        left: 0,
        top: 0,
        right: box.width,
        bottom: box.height,
      },
      syncReservations()?.reservations || [],
    );
  }

  function updateEdgeNavigation() {
    if (!edgeNavigation || disposed || !layer) return;
    viewportEntries = readViewportEntries();
    const snapshot = syncReservations();
    const box = mapContainer.getBoundingClientRect();
    const safeRect = {
      left: 12,
      top: 12,
      right: box.width - 12,
      bottom: box.height - 12,
    };
    edgeNavigation.update({
      viewId: activeViewId,
      groups: viewportEntries.groups,
      safeRect,
      obstacles: (snapshot?.reservations || [])
        .filter(item => item.blocksPointer)
        .map(({ rect }) => ({
          left: rect.x,
          top: rect.y,
          right: rect.x + rect.width,
          bottom: rect.y + rect.height,
        })),
    });
    if (window.mapCreateState)
      window.mapCreateState.viewportEntries = viewportEntries;
  }

  function scheduleEdgeNavigation() {
    if (!edgeNavigation || edgeFrame !== undefined || disposed) return;
    edgeFrame = scheduleFrame(() => {
      edgeFrame = undefined;
      if (layer.getLayoutState?.().status === 'pending') {
        scheduleEdgeNavigation();
        return;
      }
      updateEdgeNavigation();
    });
  }

  function locateEdgeElements(ids) {
    const elementIds = ids.filter(
      id => currentView().elementIds.includes(id) && isVisible(id),
    );
    if (!elementIds.length) return;
    hideHover();
    setCamera({
      strategy: 'fit-elements',
      purpose: 'edge-locate',
      elementIds,
      padding: currentView().viewport.padding || {
        top: 80,
        right: 80,
        bottom: 80,
        left: 80,
      },
      selectedBy: currentView().viewport.selectedBy,
      maxZoom:
        elementIds.length === 1 ? Math.max(map.getZoom(), 15) : undefined,
    });
    const context = cameraContexts.get(activeViewId);
    if (context) context.follow = false;
    publish({ reason: 'edge-locate' });
    window.mapCreateTelemetry?.interaction('locate_object', 'map');
  }

  function pointHasVisibleHit(id) {
    const node = mapContainer.querySelector(
      '[data-element-id="' + CSS.escape(id) + '"]',
    );
    const canvas = mapContainer.getBoundingClientRect();
    const labels = node?.querySelectorAll(
      'text[data-part="label"], [data-part="label"] text',
    );
    const parts = labels?.length
      ? labels
      : node?.querySelectorAll('text,circle,rect,path,image') || [];
    for (const part of parts) {
      const box = part.getBoundingClientRect();
      const left = Math.max(box.left, canvas.left),
        right = Math.min(box.right, canvas.right);
      const top = Math.max(box.top, canvas.top),
        bottom = Math.min(box.bottom, canvas.bottom);
      if (right <= left || bottom <= top) continue;
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
            return true;
    }
    return false;
  }

  async function verifyProjectedFit(
    viewport,
    request,
    { countCorrection = false } = {},
  ) {
    const viewId = activeViewId;
    const current = () =>
      request === cameraFitRequest && viewId === activeViewId;
    const unified = graph.runtimeRequirements?.capabilities?.includes(
      'layout.screen-geometry@1',
    );
    const elevated =
      fitState?.coverage === 'ground-only' ||
      currentElements().some(
        element => element.visible && element.mode === 'hexbin-3d',
      );
    const errorKey = 'MAP_SCREEN_FIT_ERROR';
    const readProjection = () => {
      const ids = viewport.elementIds || currentView().elementIds;
      if (!unified) return layer.getElevatedGeometry(ids);
      const result = layer.getScreenGeometry(ids);
      return {
        ...result,
        cells: result.items.map(item => ({
          ...item,
          featureId: `${item.elementId}:${item.part}`,
        })),
      };
    };
    try {
      for (let corrections = 0; corrections <= 2; corrections++) {
        await nextFrame();
        await nextFrame();
        if (!current()) return;
        await waitForLayout();
        if (!current()) return;
        const safe = elevatedSafeRect(viewportPadding(viewport));
        const projection = readProjection();
        const availableWidth = safe.right - safe.left,
          availableHeight = safe.bottom - safe.top;
        if (
          projection.status === 'unsupported' ||
          projection.status === 'invalid'
        )
          throw Object.assign(new Error('当前地图无法可靠计算绘制范围'), {
            code: projection.code,
          });
        const outside = projection.cells.filter(
          cell =>
            cell.bounds.left < safe.left ||
            cell.bounds.right > safe.right ||
            cell.bounds.top < safe.top ||
            cell.bounds.bottom > safe.bottom,
        );
        const mapBox = mapContainer.getBoundingClientRect();
        const actual = window.mapCreateClassifyFit(
          projection.cells,
          {
            left: 0,
            top: 0,
            right: mapBox.width,
            bottom: mapBox.height,
          },
          layoutSnapshot?.reservations || [],
          safe,
        );
        if (!elevated && edgeNavigation) {
          const entries = readViewportEntries().entries;
          actual.failures = actual.failures.filter(failure => {
            const cell = projection.cells.find(
              item => item.featureId === failure.featureId,
            );
            const entry = entries.find(item => item.id === cell?.elementId);
            const accessible =
              entry &&
              (entry.visible
                ? pointHasVisibleHit(entry.id)
                : viewport.purpose !== 'edge-locate' &&
                  corrections === 2 &&
                  entry.direction);
            if (accessible)
              actual.warnings.push({
                ...failure,
                reason: entry.visible
                  ? 'partial-visible'
                  : 'offscreen-navigation',
              });
            return !accessible;
          });
        }
        fitState = {
          ...fitState,
          corrections,
          projectionStatus: projection.status,
          safeRect: safe,
          outsideFeatureIds: outside.map(cell => cell.featureId),
          failures: actual.failures,
          warnings: actual.warnings,
        };
        if (projection.status === 'ready' && actual.failures.length === 0) {
          fitState = {
            ...fitState,
            outcome: 'applied',
            coverage: elevated ? 'elevated-screen' : 'screen-geometry',
            layoutRevision,
          };
          runtimeErrors.delete(errorKey);
          return;
        }
        if (availableWidth < 160 || availableHeight < 120)
          throw Object.assign(
            new Error('浮层占满了可用地图区域，请收起面板后全览'),
            { code: 'NO_SAFE_VIEWPORT' },
          );
        if (corrections === 2 || projection.status === 'empty')
          throw Object.assign(
            new Error('无法完整展示地图内容，请收起浮层或调整视图范围'),
            { code: elevated ? 'INCOMPLETE_SCREEN_FIT' : 'INCOMPLETE_SCREEN_FIT' },
          );
        if (countCorrection && corrections === 0) {
          fitCount += 1;
          fitState.fitCount = fitCount;
        }
        // The ratio is only a camera proposal; perspective changes are checked
        // again against all roof/base vertices. Never alter data or pillar height.
        const axisRatio = (low, high, axis, available) => {
          const minimum = projection.cells.reduce((current, cell) =>
            cell.bounds[low] < current.bounds[low] ? cell : current,
          );
          const maximum = projection.cells.reduce((current, cell) =>
            cell.bounds[high] > current.bounds[high] ? cell : current,
          );
          const span = maximum.bounds[high] - minimum.bounds[low];
          const fallback = span / (available - 2);
          if (elevated) return fallback;
          const start = elementById.get(minimum.elementId)?.props.position;
          const end = elementById.get(maximum.elementId)?.props.position;
          if (!start || !end) return fallback;
          const startPixel = map.lngLatToContainer(start);
          const endPixel = map.lngLatToContainer(end);
          const anchorSpan =
            axis === 'x'
              ? endPixel.getX() - startPixel.getX()
              : endPixel.getY() - startPixel.getY();
          const fixedSpan = span - anchorSpan;
          const availableAnchors = available - 2 - fixedSpan;
          return anchorSpan > 0 && availableAnchors > 0
            ? Math.max(fallback, anchorSpan / availableAnchors)
            : fallback;
        };
        const ratio =
          projection.status === 'clipped'
            ? 2
            : Math.max(
                axisRatio('left', 'right', 'x', availableWidth),
                axisRatio('top', 'bottom', 'y', availableHeight),
                1,
              );
        if (ratio > 1) {
          const zoom = Math.max(
            map.getZooms?.()[0] ?? 2,
            map.getZoom() - Math.max(0.25, Math.log2(ratio)),
          );
          map.setZoom(zoom, true);
        }
        await nextFrame();
        if (!current()) return;
        await waitForLayout();
        if (!current()) return;
        const adjusted = readProjection();
        if (adjusted.status === 'ready') {
          const b = adjusted.cells.reduce(
            (result, cell) => ({
              left: Math.min(result.left, cell.bounds.left),
              top: Math.min(result.top, cell.bounds.top),
              right: Math.max(result.right, cell.bounds.right),
              bottom: Math.max(result.bottom, cell.bounds.bottom),
            }),
            {
              left: Infinity,
              top: Infinity,
              right: -Infinity,
              bottom: -Infinity,
            },
          );
          // If size already fits, move only the violated edge. Centering on
          // every correction would needlessly move an otherwise valid camera.
          const shift = (low, high, min, max) =>
            high - low > max - min
              ? (min + max - low - high) / 2
              : low < min
                ? min - low
                : high > max
                  ? max - high
                  : 0;
          // Aim one CSS pixel inside, because SDK center quantization can put
          // an edge a few thousandths outside when targeting exact equality.
          // The verification boundary itself stays strict (no overlap tolerance).
          const x = shift(b.left, b.right, safe.left + 1, safe.right - 1);
          const y = shift(b.top, b.bottom, safe.top + 1, safe.bottom - 1);
          if (x || y) map.panBy(x, y, 0);
        }
      }
    } catch (error) {
      if (current()) {
        fitState = {
          ...fitState,
          outcome: 'failed',
          code: error.code || 'INVALID_SCREEN_PROJECTION',
        };
        cameraNotice = error.message;
        recordError(errorKey, error.message, error);
      }
    } finally {
      if (current()) {
        pendingCameraFit = false;
        publish({ reason: unified ? 'screen-fit' : 'elevated-fit' });
      }
    }
  }

  function setCamera(viewport, layoutAttempt = 0, inheritedRequest) {
    // Explicit overview follows the requested mode's geometry. Unlike a user
    // pan/zoom it does not cancel that mode; commit waits for this fit as well.
    if (!viewport || viewport.strategy === 'preserve-camera') return false;
    if (inheritedRequest !== undefined && inheritedRequest !== cameraFitRequest)
      return false;
    gestureCamera = null;
    const context = cameraContexts.get(activeViewId);
    if (context) context.follow = viewport.strategy === 'fit-elements';
    cameraNotice = null;
    if (inheritedRequest === undefined) {
      cancelCameraFit();
      layoutDegradations = [];
    }
    const request = cameraFitRequest;
    const fitExtent =
      viewport.strategy === 'fit-elements' ? visibleFitBounds(viewport) : null;
    const fitBounds = fitExtent ? fitExtent.bounds : viewport.bounds;
    let padding;
    const mapSize = mapContainer.getBoundingClientRect();
    if (!mapSize.width || !mapSize.height) {
      fitState = {
        viewId: activeViewId,
        strategy: viewport.strategy,
        fitCount,
        outcome: 'failed',
        code: 'NO_MAP_SIZE',
      };
      cameraNotice = '地图区域暂不可见，展开窗口后可重新全览。';
      pendingCameraFit = false;
      return false;
    }
    if (viewport.strategy === 'fixed-camera') {
      map.setZoomAndCenter(viewport.zoom, viewport.center, true);
    } else if (viewport.strategy === 'focus-element') {
      map.setZoomAndCenter(viewport.zoom || 15, viewport.center, true);
    } else if (viewport.strategy === 'focus-radius') {
      const zoom = Math.max(
        3,
        Math.min(20, Math.round(16 - Math.log2(viewport.radiusMeters / 500))),
      );
      map.setZoomAndCenter(zoom, viewport.center, true);
    } else if (fitBounds) {
      const bounds = new window.AMap.Bounds(
        fitBounds.southwest,
        fitBounds.northeast,
      );
      try {
        padding = effectivePadding(
          viewportPadding(viewport),
          fitExtent?.footprint,
          viewport.elementIds,
        );
      } catch (error) {
        if (error.code !== 'NO_SAFE_VIEWPORT') throw error;
        // At most two explicit UI reductions. Never change source data or
        // repeatedly fit from ResizeObserver notifications.
        let reduction;
        if (
          layoutAttempt < 2 &&
          !legendCollapsed &&
          legend.querySelector('.legend__item')
        ) {
          legendCollapsed = true;
          renderLegend();
          reduction = 'legend-collapsed';
        }
        if (reduction) {
          layoutDegradations.push(reduction);
          pendingCameraFit = true;
          fitState = {
            viewId: activeViewId,
            strategy: viewport.strategy,
            fitCount,
            outcome: 'waiting-layout',
            layoutAttempt: layoutAttempt + 1,
          };
          void (async () => {
            try {
              await nextFrame();
              await nextFrame();
              if (request !== cameraFitRequest || disposed) return;
              setCamera(viewport, layoutAttempt + 1, request);
            } catch (failure) {
              if (!disposed && request === cameraFitRequest)
                recordError('MAP_CAMERA_ERROR', failure.message, failure);
            } finally {
              if (!disposed && request === cameraFitRequest) {
                if (
                  !['waiting-layout', 'validating'].includes(fitState?.outcome)
                )
                  pendingCameraFit = false;
                publish({ reason: 'layout-fit' });
              }
            }
          })();
          return false;
        }
        fitState = {
          viewId: activeViewId,
          strategy: viewport.strategy,
          fitCount,
          outcome: 'failed',
          code: error.code,
          layoutAttempt,
        };
        cameraNotice = error.message;
        pendingCameraFit = false;
        return false;
      }
      map.setBounds(bounds, true, [
        padding.top || 0,
        padding.bottom || 0,
        padding.left || 0,
        padding.right || 0,
      ]);
      if (viewport.maxZoom && map.getZoom() > viewport.maxZoom)
        map.setZoom(viewport.maxZoom, true);
    } else {
      fitState = {
        viewId: activeViewId,
        strategy: viewport.strategy,
        fitCount,
        outcome: 'no-visible-data',
        bounds: null,
      };
      return false;
    }
    fitCount += 1;
    fitState = {
      viewId: activeViewId,
      strategy: viewport.strategy,
      fitCount,
      outcome: 'applied',
      ...(fitExtent ? { coverage: fitExtent.coverage } : {}),
      ...(fitBounds ? { bounds: fitBounds } : {}),
      appliedAt: new Date().toISOString(),
      elementIds: [...(viewport.elementIds || currentView().elementIds)],
    };
    if (
      fitExtent &&
      (graph.runtimeRequirements?.capabilities?.includes(
        'layout.screen-geometry@1',
      ) ||
        (fitExtent.coverage === 'ground-only' &&
          graph.runtimeRequirements?.capabilities?.includes(
            'heatmap.elevated-projection@1',
          )))
    ) {
      pendingCameraFit = true;
      fitState.outcome = 'validating';
      void verifyProjectedFit(viewport, request);
    }
    return true;
  }

  function effectivePadding(padding, analysisFootprint = {}, elementIds) {
    const shell = document.querySelector('#map-shell').getBoundingClientRect();
    const legendRect = legend.getBoundingClientRect();
    const controlsRect = controlsContainer.getBoundingClientRect();
    const heatmapRect = document
      .getElementById('heatmap-controls')
      .getBoundingClientRect();
    const footprint = {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
      ...analysisFootprint,
    };
    for (const element of currentElements()) {
      if (elementIds && !elementIds.includes(element.id)) continue;
      if (!element.visible || !element.position) continue;
      const measurement =
        layer?.getMeasurements?.().get(element.id) ??
        window.ContentMapKit.measureElement?.(element);
      if (!measurement?.size || !measurement.anchor) continue;
      const offset = element.offset || { x: 0, y: 0 };
      footprint.left = Math.max(
        footprint.left,
        measurement.anchor.x - (offset.x || 0),
      );
      footprint.right = Math.max(
        footprint.right,
        measurement.size.width - measurement.anchor.x + (offset.x || 0),
      );
      footprint.top = Math.max(
        footprint.top,
        measurement.anchor.y - (offset.y || 0),
      );
      footprint.bottom = Math.max(
        footprint.bottom,
        measurement.size.height - measurement.anchor.y + (offset.y || 0),
      );
    }
    const snapshot = syncReservations();
    if (snapshot) {
      const safe = elevatedSafeRect(padding);
      const insets = {
        left: safe.left,
        top: safe.top,
        right: snapshot.mapRect.width - safe.right,
        bottom: snapshot.mapRect.height - safe.bottom,
      };
      const result = Object.fromEntries(
        Object.keys(footprint).map(edge => [
          edge,
          Math.max(padding[edge] || 0, insets[edge] + footprint[edge] + 16),
        ]),
      );
      if (safe.right - safe.left < 160 || safe.bottom - safe.top < 120) {
        layoutSnapshot.status = 'insufficient-space';
        throw Object.assign(
          new Error('浮层占满了可用地图区域，请收起面板或扩大窗口后全览。'),
          { code: 'NO_SAFE_VIEWPORT' },
        );
      }
      const minimumInsets = insets;
      for (const [start, end, dimension, minimum] of [
        ['left', 'right', snapshot.mapRect.width, 160],
        ['top', 'bottom', snapshot.mapRect.height, 120],
      ]) {
        const available = Math.max(
          0,
          dimension - minimum - minimumInsets[start] - minimumInsets[end],
        );
        const extraStart = Math.max(0, result[start] - minimumInsets[start]);
        const extraEnd = Math.max(0, result[end] - minimumInsets[end]);
        const scale = Math.min(
          1,
          available / Math.max(1, extraStart + extraEnd),
        );
        result[start] = minimumInsets[start] + extraStart * scale;
        result[end] = minimumInsets[end] + extraEnd * scale;
      }
      layoutSnapshot.status = 'ready';
      return result;
    }
    const result = {
      top: Math.max(
        footprint.top + 16,
        padding.top || 0,
        heatmapRect.height
          ? heatmapRect.bottom - shell.top + footprint.top + 16
          : 0,
      ),
      right: Math.max(
        padding.right || 0,
        (controlsRect.width ? shell.right - controlsRect.left : 0) +
          footprint.right +
          16,
      ),
      bottom: Math.max(
        padding.bottom || 0,
        (legendRect.height ? shell.bottom - legendRect.top : 0) +
          footprint.bottom +
          16,
      ),
      // The legend is bottom-docked; its width must never reserve the left edge.
      left: Math.max(footprint.left + 16, padding.left || 0),
    };
    for (const [start, end, dimension] of [
      ['left', 'right', shell.width],
      ['top', 'bottom', shell.height],
    ]) {
      const sum = result[start] + result[end];
      const available = Math.max(0, dimension * 0.5);
      if (sum > available && sum > 0) {
        result[start] *= available / sum;
        result[end] *= available / sum;
      }
    }
    return result;
  }

  const rounded = value =>
    Number.isFinite(value) ? Math.round(value * 100) / 100 : null;

  function stabilitySnapshot() {
    const center = map.getCenter?.();
    const centerPosition = center
      ? [center.getLng?.() ?? center.lng, center.getLat?.() ?? center.lat]
      : null;
    const elements = [...mapContainer.querySelectorAll('[data-element-id]')]
      .filter(node => getComputedStyle(node).display !== 'none')
      .map(node => {
        const rect = node.getBoundingClientRect();
        return [
          node.getAttribute('data-element-id'),
          rounded(rect.left),
          rounded(rect.top),
          rounded(rect.width),
          rounded(rect.height),
        ];
      })
      .sort((left, right) => String(left[0]).localeCompare(String(right[0])));
    return JSON.stringify({
      activeViewId,
      cameraEventRevision,
      layoutRevision,
      contentLayout: layer.getLayoutState?.(),
      zoom: rounded(map.getZoom?.()),
      pitch: map.getPitch?.(),
      rotation: map.getRotation?.(),
      size: [mapContainer.clientWidth, mapContainer.clientHeight],
      revision,
      center: centerPosition,
      elements,
    });
  }

  function assertLayoutBudget() {
    const state = layer.getLayoutState?.();
    if (state?.status === 'budget-exceeded')
      throw Object.assign(
        new Error(
          'LAYOUT_BUDGET_EXCEEDED: ' +
            JSON.stringify({
              viewId: activeViewId,
              ...state,
              diagnostics: layer.getLayoutDiagnostics?.(),
              budget: currentView().layoutPolicy?.budget,
            }),
        ),
        { code: 'LAYOUT_BUDGET_EXCEEDED', detail: state },
      );
    return state;
  }

  async function waitForLayout(timeoutMs = 5000) {
    const started = performance.now();
    while (assertLayoutBudget()?.status === 'pending') {
      if (performance.now() - started >= timeoutMs)
        throw Object.assign(new Error('等待地图标签布局超时'), {
          code: 'LAYOUT_TIMEOUT',
        });
      await nextFrame();
    }
  }

  async function waitForStable(options = {}) {
    const viewId = options.viewId || activeViewId;
    const timeoutMs = options.timeoutMs || 5000;
    const requiredStableFrames = options.stableFrames || 2;
    const startedAt = performance.now();
    await waitForResource(
      (resolve, reject) => {
        Promise.resolve(document.fonts?.ready).then(resolve, reject);
      },
      timeoutMs,
      '等待地图字体超时',
    );
    let previousSnapshot,
      stableFrames = 0;
    while (!disposed) {
      const remaining = timeoutMs - (performance.now() - startedAt);
      if (remaining <= 0) throw new Error(`等待 View ${viewId} 地图稳定超时`);
      await nextFrame(remaining);
      const contentLayout = assertLayoutBudget();
      if (!pendingCameraFit && runtimeErrors.size)
        throw Object.assign(
          new Error(
            'MAP_RUNTIME_ERROR: ' +
              JSON.stringify({
                viewId,
                errors: [...runtimeErrors.values()],
                fitState,
              }),
          ),
          {
            code: 'MAP_RUNTIME_ERROR',
          },
        );
      if (
        activeViewId !== viewId ||
        pendingCameraFit ||
        modeDraft ||
        contentLayout?.status === 'pending'
      ) {
        previousSnapshot = undefined;
        stableFrames = 0;
      } else {
        const snapshot = stabilitySnapshot();
        stableFrames = snapshot === previousSnapshot ? stableFrames + 1 : 0;
        previousSnapshot = snapshot;
        if (stableFrames >= requiredStableFrames) {
          updateEdgeNavigation();
          return {
            viewId,
            cameraEventRevision,
            stableFrames,
            elapsedMs: Math.round(performance.now() - startedAt),
            evidence: 'camera-and-layout-stable',
            basemapCompleteness: 'unverified',
          };
        }
      }
    }
    throw disposedError();
  }

  function renderActiveView({ fit = true, reason = 'view-activate' } = {}) {
    cancelCameraFit();
    const request = cameraFitRequest;
    const view = currentView();
    if (!compatibleAnalysisModes(currentElements()))
      throw Object.assign(new Error('连续热力与三维蜂窝不能同时显示'), {
        code: 'HEATMAP_CAMERA_CONFLICT',
      });
    const controls = view.mapUi?.controls || {};
    controlsContainer.dataset.position = controls.position || 'top-right';
    controlsContainer.hidden =
      controls.overview === false && controls.zoom === false;
    controlsRuntime?.update({
      showOverview: controls.overview !== false,
      showZoom: controls.zoom !== false,
      zoomInDisabled: controls.zoom === false || map.getZoom() >= 20,
      zoomOutDisabled: controls.zoom === false || map.getZoom() <= 3,
    });
    clearFeatureSelection();
    layer.setLayoutPolicy(view.layoutPolicy);
    layer.setElements(currentElements());
    layer.setSelected(null);
    layer.setSeriesSelected(null);
    selectedSeriesId = null;
    selectedFeatureId = null;
    renderLegend();
    applyHeatmapPitch({
      restoreView: !fit || view.viewport.strategy === 'preserve-camera',
    });
    updateFilterUi();
    updateVisibilityUi();
    updateHeatmapControls();
    revision += 1;
    if (
      fit &&
      view.viewport.fitOnActivate !== false &&
      view.viewport.strategy !== 'preserve-camera'
    ) {
      pendingCameraFit = true;
      // Measure the committed React controls and sidebar before reserving space.
      scheduleFrame(() =>
        scheduleFrame(() => {
          if (request !== cameraFitRequest || activeViewId !== view.id) return;
          try {
            const canVerifyInitial = graph.runtimeRequirements?.capabilities?.includes(
              'layout.screen-geometry@1',
            );
            if (
              reason === 'initial' && initialCamera &&
              (view.viewport.strategy !== 'fit-elements' || canVerifyInitial)
            ) {
              const extent = visibleFitBounds(view.viewport);
              fitState = {
                viewId: activeViewId,
                strategy: view.viewport.strategy,
                fitCount,
                outcome:
                  view.viewport.strategy === 'fit-elements' && !extent.bounds
                    ? 'no-visible-data'
                    : 'applied',
                bounds: extent.bounds,
                coverage: extent.coverage,
                elementIds: [...(view.viewport.elementIds || view.elementIds)],
              };
              if (view.viewport.strategy === 'fit-elements' && extent.bounds) {
                fitState.outcome = 'validating';
                void verifyProjectedFit(view.viewport, request, {
                  countCorrection: true,
                });
              }
            } else setCamera(view.viewport);
          } catch (error) {
            recordError('MAP_CAMERA_ERROR', error.message, error);
          } finally {
            if (!['validating', 'waiting-layout'].includes(fitState?.outcome))
              pendingCameraFit = false;
            publish({ reason: 'view-fit' });
          }
        }),
      );
    }
    publish({ reason });
  }

  function activateView(viewId, options = {}) {
    window.mapCreateTelemetry?.operation('switch_view');
    selectionRevision += 1;
    if (!viewById.has(viewId)) throw new Error(`View ${viewId} 不存在`);
    cancelModeTransition();
    const entry =
      options.entryElementId &&
      currentView().entryActions?.[options.entryElementId];
    if (
      options.entryElementId &&
      (!isVisible(options.entryElementId) || entry?.viewId !== viewId)
    )
      return false;
    if (entry) {
      const center = map.getCenter?.();
      entryContexts.set(activeViewId, {
        elementId: options.entryElementId,
        center: center ? [center.getLng(), center.getLat()] : null,
        zoom: map.getZoom(),
        pitch: map.getPitch?.() || 0,
        rotation: map.getRotation?.() || 0,
        scrollTop: uiContainer.scrollTop || 0,
      });
    }
    const oldCamera = cameraContexts.get(activeViewId);
    if (oldCamera) oldCamera.last = readCamera();
    const restore = entryContexts.get(viewId);
    clearFeatureSelection();
    activeViewId = viewId;
    interactionNotice = null;
    cameraNotice = null;
    selectedElementId = null;
    renderActiveView({
      fit: !restore && options.fit !== false,
      reason: 'view-activate',
    });
    if (uiRuntime) {
      syncingUi = true;
      uiRuntime.activateView(viewId);
      if (restore && isVisible(restore.elementId)) {
        selectedElementId = restore.elementId;
        layer.setSelected(selectedElementId);
        uiRuntime.selectElement(selectedElementId);
      }
      syncingUi = false;
    }
    if (restore?.center) {
      map.setZoomAndCenter(restore.zoom, restore.center, true);
      map.setPitch?.(restore.pitch, true);
      map.setRotation?.(restore.rotation, true);
    }
    scheduleFrame(() =>
      scheduleFrame(() => {
        if (activeViewId === viewId)
          uiContainer.scrollTop = restore?.scrollTop || 0;
      }),
    );
    publish({ reason: restore ? 'entry-return' : 'view-activate' });
    window.mapCreateTelemetry?.interaction('switch_view');
    return window.mapCreateState;
  }

  function loadAMap() {
    window.forceWebGL = true;
    if (window.AMap) return Promise.resolve(window.AMap);
    window._AMapSecurityConfig = config.serviceHost
      ? { serviceHost: config.serviceHost }
      : { securityJsCode: config.securityJsCode };
    const report = window.mapCreateTelemetry?.resource('amap-sdk');
    return waitForResource(
      (resolve, reject) => {
        const callback = `__mapCreateAMapLoaded_${Date.now()}`;
        const script = document.createElement('script');
        window[callback] = () => resolve(window.AMap);
        script.onerror = () => reject(new Error('AMAP_SDK_LOAD_FAILED'));
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(config.key)}&callback=${callback}`;
        document.head.append(script);
        return () => {
          delete window[callback];
          script.onerror = null;
          script.remove();
        };
      },
      30000,
      'AMAP_SDK_TIMEOUT',
    ).then(value => { report?.(); return value; }).catch(error => { report?.(error); throw error; });
  }

  async function start() {
    window.mapCreateState = { status: 'loading', activeViewId };
    status.textContent = '地图加载中';
    {
      const compatibility = window.mapCreateCheckCompatibility?.(
        graph.runtimeRequirements,
        window.ContentMapKit?.getRuntimeContract?.(),
      );
      if (!compatibility || compatibility.status !== 'compatible') {
        const error = new Error(
          compatibility?.message || '组件协议校验器缺失，无法加载地图',
        );
        error.code = compatibility?.code || 'RUNTIME_CONTRACT_CHECK_MISSING';
        throw error;
      }
    }
    if (
      !['ui.reading-panel@1', 'ui.map-overlays@1'].every(capability =>
        window.ContentMapKit?.getRuntimeContract?.().capabilities?.includes(
          capability,
        ),
      )
    ) {
      const error = new Error(
        '组件资源缺少统一面板能力，请更新资源锁后重新构建',
      );
      error.code = 'UI_RUNTIME_CAPABILITY_MISSING';
      throw error;
    }
    document.documentElement.dataset.bootstrapPhase = 'amap-sdk';
    const AMap = await loadAMap();
    await window.mapCreateWaitForSize?.();
    if (disposed) throw disposedError();
    document.documentElement.dataset.bootstrapPhase = 'amap-map';
    uiRuntime = window.ContentMapKit.mountContentMapRuntime({
      panel: { layout: 'floating' },
      onAnalysisFilterChange: event => layer && setAnalysisFilter(event),
      container: uiContainer,
      graph,
      activeViewId,
      onAction: event => {
        if (syncingUi || !layer) return;
        if (event.type === 'activate-view' && event.viewId !== activeViewId)
          activateView(event.viewId, {
            source: 'ui',
            entryElementId: event.elementId,
          });
        if (event.type === 'select-element' && event.elementId)
          selectElement(event.elementId, { source: 'ui' });
        if (event.type === 'clear-selection')
          selectElement(null, { source: 'detail-close' });
        if (event.type === 'toggle-visibility' && event.elementId) {
          return setElementVisibility(event.elementId, event.visible);
        }
        return false;
      },
      onDiagnostic: diagnostic => {
        recordError(diagnostic.code, diagnostic.message);
        window.mapCreateState = {
          ...window.mapCreateState,
          lastRuntimeDiagnostic: diagnostic,
        };
      },
    });
    sourceContainer.replaceChildren(
      window.ContentMapKit.createMapDisclosure({
        title: '来源',
        content: document.getElementById('sources'),
        theme: shellTheme,
        collapsed: true,
        onToggle: scheduleReservations,
      }),
    );
    const analysisControls = document.getElementById('heatmap-controls');
    const heatmapHost = document.createElement('div');
    const choroplethHost = document.createElement('div');
    analysisControls.append(heatmapHost, choroplethHost);
    if (graph.elements.some(element => element.componentId === 'choropleth')) {
      if (typeof window.ContentMapKit.mountChoroplethLegend !== 'function') {
        throw new Error(
          '组件资源缺少区域分级图图例接口，请更新 ContentMapKit 资源',
        );
      }
      choroplethLegend = window.ContentMapKit.mountChoroplethLegend({
        container: choroplethHost,
        theme: graph.visualTheme.shell,
        collapsed: true,
      });
    }
    heatmapControls = window.ContentMapKit.mountHeatmapControls({
      container: heatmapHost,
      theme: graph.visualTheme.shell,
      elements: [],
      onChange: (id, mode) => layer && setHeatmapMode(id, mode),
    });
    const initialControlPolicy = currentView().mapUi?.controls || {
      overview: true,
      zoom: true,
    };
    controlsRuntime = window.ContentMapKit.mountMapControls({
      container: controlsContainer,
      onOverview: () => {
        if (!layer) return;
        setCamera(currentView().viewport);
        window.mapCreateTelemetry?.interaction('locate_object', 'toolbar');
        publish({ reason: 'explicit-fit' });
      },
      onZoomBy: step => {
        if (!layer) return;
        markUserCamera();
        map.setZoom(map.getZoom() + step, true);
        window.mapCreateTelemetry?.interaction('zoom_map', 'toolbar');
      },
      showOverview: initialControlPolicy.overview !== false,
      showZoom: initialControlPolicy.zoom !== false,
      zoomInDisabled:
        initialControlPolicy.zoom === false || (map?.getZoom() ?? 12) >= 20,
      zoomOutDisabled:
        initialControlPolicy.zoom === false || (map?.getZoom() ?? 12) <= 3,
    });
    renderLegend();
    updateHeatmapControls();
    await nextFrame();
    await nextFrame();
    await window.mapCreateWaitForSize?.();
    if (disposed) throw disposedError();
    const viewport = currentView().viewport;
    const extent = visibleFitBounds(viewport);
    initialCamera = window.mapCreateInitialCamera(
      viewport,
      extent.bounds,
      mapContainer.getBoundingClientRect(),
      viewport.strategy === 'fit-elements'
        ? effectivePadding(
            viewportPadding(viewport), extent.footprint, viewport.elementIds,
          )
        : viewportPadding(viewport),
    );
    map = new AMap.Map(mapContainer, {
      viewMode: '2D',
      pitch: 0,
      rotation: 0,
      rotateEnable: false,
      pitchEnable: false,
      resizeEnable: true,
      mapStyle: graph.visualTheme.mapStyle,
      zoom: initialCamera.zoom,
      center: initialCamera.center,
      ...(graph.visualTheme?.features?.length
        ? { features: graph.visualTheme.features }
        : {}),
    });
    document.documentElement.dataset.bootstrapPhase = 'content-layer';
    layoutSnapshot = null;
    layer = window.ContentMapKit.createContentLayer({
      map,
      layoutPolicy: currentView().layoutPolicy,
      viewportBoundary: graph.runtimeRequirements.capabilities.includes(
        'ui.edge-navigation@1',
      )
        ? 'clip'
        : 'contain',
      basemapLabels: {
        createLayer(options) {
          const labels = new window.AMap.LabelsLayer(options);
          map.add(labels);
          return {
            add: marker => labels.add(marker),
            remove: marker => labels.remove(marker),
            destroy: () => {
              labels.clear();
              map.remove(labels);
            },
          };
        },
        createMarker: options => new window.AMap.LabelMarker(options),
      },
      onError: error => recordError('MAP_RENDER_ERROR', error.message, error),
    });
    if (
      graph.runtimeRequirements.capabilities.includes('ui.edge-navigation@1')
    ) {
      edgeNavigation = window.ContentMapKit.mountMapEdgeNavigation({
        container: document.getElementById('map-edge-navigation'),
        theme: shellTheme,
        onLocate: locateEdgeElements,
      });
    }
    cleanups.add(
      layer.on('click', event => {
        if (disposed) return;
        if (!isVisible(event.id)) return;
        if (
          elementById.get(event.id)?.props.interaction?.selectable === false
        ) {
          selectElement(null);
          return;
        }
        const entry = currentView().entryActions?.[event.id];
        if (entry) {
          activateView(entry.viewId, {
            source: 'map',
            entryElementId: event.id,
          });
          return;
        }
        if (event.featureId) {
          clearFeatureSelection();
          layer.setSelected(null);
          layer.setSeriesSelected(null);
          selectedSeriesId = null;
          layer.setFeatureSelected(event.id, event.featureId);
          selectedElementId = event.id;
          selectedFeatureId = event.featureId;
          selectedFeature = Object.freeze({
            elementId: event.id,
            featureId: event.featureId,
            value: event.value,
            count: event.count,
            memberIds: Object.freeze([...(event.memberIds || [])]),
          });
          if (uiRuntime) {
            syncingUi = true;
            showFeatureDetails();
            syncingUi = false;
          }
          renderLegend();
          revision += 1;
          selectionRevision += 1;
          publish({ reason: 'feature-select' });
          window.mapCreateTelemetry?.interaction('select_object', 'map');
        } else if (
          event.seriesId &&
          elementById.get(event.id)?.businessRef?.type === 'route'
        )
          selectSeries(event.seriesId, { source: 'map' });
        else selectElement(event.id, { source: 'map' });
      }),
    );
    cleanups.add(layer.on('hover', showHover));
    let pointerStart = null;
    const rememberPointerStart = event => {
      pointerStart = { x: event.clientX, y: event.clientY };
    };
    const clearBlankSelection = event => {
      const original = event.originEvent || event;
      const target = original.target;
      if (
        pointerStart &&
        Number.isFinite(original.clientX) &&
        Math.hypot(
          original.clientX - pointerStart.x,
          original.clientY - pointerStart.y,
        ) > 6
      )
        return;
      if (
        target instanceof Element &&
        target.closest(
          '[data-element-id], #content-map-ui, #map-sources, #map-controls, #heatmap-controls, #map-legend, button, a, input, [role="button"]',
        )
      )
        return;
      const clickRevision = selectionRevision;
      // Element handlers may run after the basemap handler for the same click.
      window.setTimeout(() => {
        if (
          !disposed &&
          selectionRevision === clickRevision &&
          (selectedElementId !== null || selectedSeriesId !== null)
        )
          selectElement(null);
      }, 0);
    };
    onMap('click', clearBlankSelection);
    mapContainer.addEventListener('pointerdown', rememberPointerStart, true);
    mapContainer.addEventListener('click', clearBlankSelection, true);
    cleanups.add(() => {
      mapContainer.removeEventListener(
        'pointerdown',
        rememberPointerStart,
        true,
      );
      mapContainer.removeEventListener('click', clearBlankSelection, true);
    });
    onMap('zoomend', () => {
      observeCameraIntent();
      cameraEventRevision += 1;
        const zoomEnabled = currentView().mapUi?.controls?.zoom !== false;
      controlsRuntime?.update({
        zoomInDisabled: !zoomEnabled || map.getZoom() >= 20,
        zoomOutDisabled: !zoomEnabled || map.getZoom() <= 3,
      });
      publish({ reason: 'zoom' });
    });
    onMap('moveend', () => {
      observeCameraIntent();
      cameraEventRevision += 1;
        publish({ reason: 'move' });
    });
    onMap('pitchchange', () => {
      observeCameraIntent();
      });
    onMap('rotatechange', () => {
      observeCameraIntent();
      });
    // Real user camera intent cancels in-flight corrections, not SDK events
    // generated by our own bounded fit. UI overlays are siblings of #map.
    const beginCameraInput = () => {
      cancelModeTransition({ preserveCamera: true });
      cancelCameraFit();
      gestureCamera = readCamera();
    };
    mapContainer.addEventListener('pointerdown', beginCameraInput, {
      passive: true,
    });
    mapContainer.addEventListener('wheel', beginCameraInput, { passive: true });
    cleanups.add(() => {
      mapContainer.removeEventListener('pointerdown', beginCameraInput);
      mapContainer.removeEventListener('wheel', beginCameraInput);
    });
    if (
      graph.runtimeRequirements?.capabilities?.includes(
        'layout.reservations@1',
      ) &&
      typeof ResizeObserver !== 'undefined'
    ) {
      const observer = new ResizeObserver(scheduleReservations);
      for (const node of [
        mapContainer,
        controlsContainer,
        legend,
        uiContainer,
        sourceContainer,
        document.getElementById('heatmap-controls'),
      ])
        if (node) observer.observe(node);
      cleanups.add(() => observer.disconnect());
    }
    renderActiveView({ fit: true, reason: 'initial' });
    const updateTheme = () => {
      if (disposed || graph.visualTheme.mode !== 'auto') return;
      const previousTone = shellTheme.tone;
      window.mapCreateApplyAppearance(
        graph,
        window.mapCreateHostTheme,
        systemTheme?.matches === true,
      );
      Object.assign(shellTheme, graph.visualTheme.shell);
      graph.visualTheme.shell = shellTheme;
      if (shellTheme.tone === previousTone) return;
      applyShellTheme();
      map.setMapStyle(graph.visualTheme.mapStyle);
      layer.setElements(currentElements());
      uiRuntime.refreshAppearance();
      renderLegend();
      updateHeatmapControls();
      const variables =
        window.ContentMapKit.createContentMapThemeVariables(shellTheme);
      for (const node of document
        .getElementById('map-app')
        .querySelectorAll('[style]')) {
        if (!node.style.getPropertyValue('--content-map-panel')) continue;
        for (const [name, value] of Object.entries(variables))
          node.style.setProperty(name, value);
      }
      revision += 1;
      publish({ reason: 'theme-change' });
    };
    const setHostTheme = tone => {
      if (tone !== null && tone !== 'light' && tone !== 'dark')
        throw new TypeError('主题必须为 light、dark 或 null');
      window.mapCreateHostTheme = tone;
      updateTheme();
    };
    window.mapCreateSetHostTheme = setHostTheme;
    systemTheme?.addEventListener('change', updateTheme);
    cleanups.add(() => {
      systemTheme?.removeEventListener('change', updateTheme);
      if (window.mapCreateSetHostTheme === setHostTheme)
        delete window.mapCreateSetHostTheme;
    });
    window.mapCreateRuntime = {
      map,
      layer,
      activateView,
      selectElement,
      selectSeries,
      waitForStable,
      getStabilitySnapshot: stabilitySnapshot,
      setHeatmapMode,
      setAnalysisFilter,
      setElementVisibility,
      fitCurrentView: () => {
        setCamera(currentView().viewport);
        publish({ reason: 'explicit-fit' });
      },
      getState: () =>
        structuredClone(
          disposed
            ? terminalState
            : {
                ...window.mapCreateState,
                contentLayout: layer.getLayoutState?.(),
              },
        ),
      dispose,
    };
    for (const name of [
      'activateView',
      'selectElement',
      'selectSeries',
      'setHeatmapMode',
      'setAnalysisFilter',
      'setElementVisibility',
      'fitCurrentView',
      'getStabilitySnapshot',
    ]) {
      const action = window.mapCreateRuntime[name];
      window.mapCreateRuntime[name] = (...args) => {
        if (disposed) throw disposedError();
        return action(...args);
      };
    }
  }

  window.mapCreateStarted = start().catch(error => {
    if (disposed) return;
    dispose();
    status.textContent = error.message;
    window.mapCreateState = {
      status: 'error',
      activeViewId,
      message: error.message,
      code: error.code || 'RUNTIME_START_FAILED',
      stack: error.stack?.replace(
        /https?:\/\/[^\s)]+/g,
        url => url.split('?')[0],
      ),
    };
    throw error;
  });
})();

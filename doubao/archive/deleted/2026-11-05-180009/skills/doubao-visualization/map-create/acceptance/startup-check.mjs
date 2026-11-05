// Startup evidence only: no camera/layout convergence or interaction checks.
export const STARTUP_CHECKS = [
  'resources',
  'runtime',
  'container',
  'initialView',
  'content',
  'initialUi',
  'loadingMask',
  'fatalErrors',
];
export const STARTUP_LIMITATIONS = [
  '仅验证静态协议及初始页面启动；未检查其他视图、布局碰撞、遮挡、视野覆盖、点击或缩放交互。',
  '不保证底图瓦片完整、GPU 像素正确、审美、自然语言理解或来源真实性。',
];

// Executed in the page after bootstrap completes; does not call waitForStable.
export function inspectStartup() {
  const root = document.documentElement;
  const runtime = window.mapCreateRuntime;
  const state = window.mapCreateState;
  const mask = document.getElementById('map-loading');
  const rect = document.getElementById('map')?.getBoundingClientRect();
  const elements = runtime?.layer?.getElements?.();
  return {
    sections: [...document.querySelectorAll('[data-ui-section-id]')].map(node => ({
      id: node.dataset.uiSectionId,
      viewId: node.dataset.uiViewId,
      source: node.dataset.uiSource,
      mounted: node.childElementCount > 0,
      hasContent: Boolean(node.textContent?.trim()),
    })),
    captureState: root.dataset.captureState,
    captureError: root.dataset.captureError || null,
    hasMap: Boolean(
      runtime?.map && typeof runtime.map.getCenter === 'function',
    ),
    hasLayer: Boolean(runtime?.layer && Array.isArray(elements)),
    activeViewId: state?.activeViewId,
    elementCount: elements?.length ?? 0,
    width: rect?.width ?? 0,
    height: rect?.height ?? 0,
    loadingHidden: Boolean(mask?.hidden),
    runtimeErrors: state?.errors || [],
    startError: !runtime && state?.status === 'error' ? state.message : null,
  };
}

export function evaluateStartup(snapshot, graph, pageErrors = []) {
  const initial =
    graph.views.find((view) => view.id === graph.initialViewId) ||
    graph.views[0];
  // Fit/layout defects remain in diagnostics for developers, never request
  // business-input repairs merely to satisfy screen geometry assertions.
  const layoutCodes = new Set([
    'MAP_SCREEN_FIT_ERROR',
    'MAP_CAMERA_ERROR',
    'LAYOUT_RESERVATION_ERROR',
    'LAYOUT_BUDGET_EXCEEDED',
    'LAYOUT_TIMEOUT',
  ]);
  const fatal = snapshot.runtimeErrors.filter(
    (error) => !layoutCodes.has(error.code),
  );
  // Only configured initial content; no selection details, empty optional
  // sections, expanded collapse bodies, layout or visibility assertions.
  const requiredSections = (initial?.ui?.sections || []).filter(section => {
    if (section.source === 'selected.properties' || section.empty) return false;
    const count = section.items?.length || 0;
    if (section.componentId === 'semi.tabs')
      return Math.min(count, section.props?.maxItems ?? count) >= 2;
    return count > 0 || (section.componentId === 'semi.card' &&
      Boolean(section.props?.description?.trim()));
  });
  const missingSections = requiredSections.filter(section =>
    !(snapshot.sections || []).some(record =>
      record.id === section.id && record.viewId === initial.id &&
      record.source === section.source && record.mounted && record.hasContent),
  ).map(section => section.id);
  const checks = {
    resources: snapshot.captureState === 'ready' && !snapshot.captureError,
    runtime: snapshot.hasMap && snapshot.hasLayer && !snapshot.startError,
    container: snapshot.width > 0 && snapshot.height > 0,
    initialView: Boolean(initial && snapshot.activeViewId === initial.id),
    content: !initial?.elementIds?.length || snapshot.elementCount > 0,
    initialUi: missingSections.length === 0,
    loadingMask: snapshot.loadingHidden,
    fatalErrors: !pageErrors.length && !fatal.length,

  };
  return {
    status: Object.values(checks).every(Boolean) ? 'passed' : 'failed',
    initialViewId: snapshot.activeViewId,
    checks: Object.fromEntries(
      Object.entries(checks).map(([key, ok]) => [
        key,
        ok ? 'passed' : 'failed',
      ]),
    ),
    snapshot,
    missingSections,
    errors: [
      ...Object.entries(checks)
        .filter(([, ok]) => !ok)
        .map(([key]) => `STARTUP_CHECK_FAILED: ${key}`),
      ...pageErrors,
      ...fatal.map((error) => `${error.code}: ${error.message}`),
      ...(snapshot.captureError ? [snapshot.captureError] : []),
    ],
  };
}

export function assertStartupCoverage(report, expectedInitialViewId) {
  const evidence = report.protocolEvidence;
  if (
    report.status !== 'passed' ||
    report.policyVersion !== 'startup-v1' ||
    report.mode !== 'startup' ||
    !Array.isArray(report.errors) ||
    report.errors.length ||
    report.startup?.status !== 'passed' ||
    report.startup.initialViewId !== expectedInitialViewId ||
    STARTUP_CHECKS.some((key) => report.startup.checks?.[key] !== 'passed') ||
    evidence?.status !== 'passed' ||
    ['spec-self', 'spec-plan', 'plan-props', 'spec-props'].some(
      (key) => evidence.phases?.[key] !== 'passed',
    ) ||
    !evidence.checks?.length ||
    evidence.checks.some((check) => check.status !== 'passed')
  )
    throw new Error('启动检查或静态协议校验证据不完整');
}

export function assertDeliveryPolicy(report) {
  if (
    report.status !== 'passed' ||
    !(
      (report.mode === 'startup' && report.policyVersion === 'startup-v1') ||
      (report.mode === 'full' && report.policyVersion === 'deterministic-v2')
    )
  )
    throw new Error(
      '需要 startup-v1 startup 启动报告或开发 deterministic-v2 full 验收报告',
    );
}

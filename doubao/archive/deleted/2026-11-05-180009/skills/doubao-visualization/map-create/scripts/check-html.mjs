import { inspectStartup, evaluateStartup, STARTUP_LIMITATIONS } from '../acceptance/startup-check.mjs';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkerIdentity } from '../acceptance/acceptance-identity.mjs';
import { checkNavigation } from '../acceptance/check-navigation.mjs';
import { checkEdgeNavigationJourneys } from '../acceptance/edge-navigation-journeys.mjs';
import {
  CHECK_GROUPS,
  checkScope,
  retryAdvice,
} from '../acceptance/check-policy.mjs';
import { inspectElevatedGeometry } from '../acceptance/elevated-geometry-evidence.mjs';
import { diagnoseFailure } from '../acceptance/failure-diagnosis.mjs';
import { inspectPolygons } from '../acceptance/polygon-evidence.mjs';
import { checkProductJourneys } from '../acceptance/product-journeys.mjs';
import { compareRenderedElements } from '../acceptance/rendered-elements.mjs';
import { createResourceReadinessProbe } from '../acceptance/resource-readiness.mjs';
import { inspectRouteSymbols } from '../acceptance/route-symbols.mjs';
import { inspectScreenGeometry } from '../acceptance/screen-geometry-evidence.mjs';
import { inspectSelectionShapes } from '../acceptance/selection-shapes.mjs';
import { inspectSourceEvidence } from '../acceptance/source-evidence.mjs';
import { compareUiSections } from '../acceptance/ui-sections.mjs';
import {
  launchBrowserAutomation,
  resolveBrowserAutomation,
} from '../lib/browser-automation.mjs';
import { readArtifact } from '../lib/cdn-assets.mjs';
import { args, readJson, safeError, writeReport } from '../lib/cli-utils.mjs';
import {
  compilerIdentity,
  failOnErrors,
  loadComponentCatalog,
  normalizeInputs,
  prepareGraph,
  protocolHash,
  resolveComponentNodes,
  resolveViews,
  validateContract,
  validateOrganization,
  validateProductGraph,
  validateSemantics,
  validateTransform,
  verifyContractArtifacts,
} from '../lib/engine.mjs';
import { serveArtifact } from '../lib/serve-artifact.mjs';

async function waitForMapStable(page, viewId) {
  try {
    await page.waitForFunction(
      id =>
        window.mapCreateState?.activeViewId === id &&
        typeof window.mapCreateRuntime?.waitForStable === 'function',
      viewId,
      { timeout: 5000 },
    );
    return page.evaluate(
      id =>
        window.mapCreateRuntime.waitForStable({ viewId: id, timeoutMs: 5000 }),
      viewId,
    );
  } catch (error) {
    const snapshot = await page.evaluate(() => ({
      state: window.mapCreateState,
      hasRuntime: Boolean(window.mapCreateRuntime),
      runtimeKeys: Object.keys(window.mapCreateRuntime || {}),
    }));
    throw new Error(
      `等待 View ${viewId} 激活或稳定失败：${error.message}；快照 ${JSON.stringify(snapshot)}`,
    );
  }
}

function visibleElementRects(page) {
  return page.locator('[data-element-id]').evaluateAll(nodes =>
    Object.fromEntries(
      nodes
        .filter(node => getComputedStyle(node).display !== 'none')
        .map(node => {
          const rect = node.getBoundingClientRect();
          return [
            node.getAttribute('data-element-id'),
            {
              transform: node.getAttribute('transform') || '',
              left: rect.left,
              top: rect.top,
              width: rect.width,
              height: rect.height,
              markup: node.innerHTML,
            },
          ];
        })
        .filter(([id]) => Boolean(id)),
    ),
  );
}

async function checkUiSections(page) {
  const snapshot = await page.evaluate(() => {
    const sidebar = document.querySelector('#content-map-ui');
    const selection =
      document.querySelector('[data-content-map-details]') ||
      document.querySelector('#selection-details');
    const singlePanel = Boolean(
      document.querySelector('.content-map-kit-reading-panel'),
    );
    const state = window.mapCreateState;
    const identitySupported =
      window.ContentMapKit?.getRuntimeContract?.().capabilities?.includes(
        'ui.section-evidence@1',
      ) === true;
    return {
      identitySupported,
      singlePanel,
      featureSupported:
        window.ContentMapKit?.getRuntimeContract?.()?.capabilities?.includes(
          'ui.feature-details@1',
        ) === true,
      legacySectionCount:
        sidebar?.querySelector('.content-map-kit-root')?.children.length || 0,
      view: window.mapCreateGraph.views.find(
        view => view.id === state.activeViewId,
      ),
      state: {
        selectedElementId: state.selectedElementId,
        selectedFeatureId: state.selectedFeatureId,
      },
      featureIdentity:
        selection?.dataset.selectedFeatureId ||
        selection?.querySelector('[data-selected-feature-id]')?.dataset
          .selectedFeatureId,
      hasSelectionContainer: singlePanel || Boolean(selection),
      actual: [...document.querySelectorAll('[data-ui-section-id]')].map(
        node => ({
          id: node.dataset.uiSectionId,
          source: node.dataset.uiSource,
          viewId: node.dataset.uiViewId,
          hasContent: Boolean(node.textContent?.trim()),
          clearSelectionCount: node.querySelectorAll(
            'button[aria-label="关闭详情"]',
          ).length,
          slot: selection?.contains(node)
            ? 'selection'
            : sidebar?.contains(node)
              ? 'sidebar'
              : 'unknown',
          rendered: [...node.children].some(child => {
            const rect = child.getBoundingClientRect();
            const style = getComputedStyle(child);
            return (
              rect.width > 0 &&
              rect.height > 0 &&
              style.visibility !== 'hidden' &&
              style.display !== 'none'
            );
          }),
        }),
      ),
    };
  });
  // Keep the historical locked chain's existing assertion, explicitly marked
  // limited. Do not pretend an older bundle exposes per-section evidence.
  if (!snapshot.identitySupported) {
    const expectedCount = snapshot.view.ui.sections.length;
    const errors =
      snapshot.legacySectionCount === expectedCount
        ? []
        : [
            '旧版 Semi section 数量不符；当前资源未声明 ui.section-evidence@1，不能执行身份/槽位验收',
          ];
    return {
      status: errors.length ? 'failed' : 'passed',
      method: 'legacy-section-count',
      identityCheck: 'not-run',
      expectedCount,
      actualCount: snapshot.legacySectionCount,
      errors,
    };
  }
  const featureSelected =
    snapshot.featureSupported && Boolean(snapshot.state.selectedFeatureId);
  const featureDetails = snapshot.actual.filter(
    item => item.id === 'runtime-feature-details',
  );
  const result = compareUiSections(
    snapshot.view,
    featureSelected
      ? { ...snapshot.state, selectedElementId: null }
      : snapshot.state,
    featureSelected
      ? snapshot.actual.filter(item => item.id !== 'runtime-feature-details')
      : snapshot.actual,
    snapshot.hasSelectionContainer,
    { singlePanel: snapshot.singlePanel },
  );
  if (featureSelected) {
    const detail = featureDetails[0];
    if (
      featureDetails.length !== 1 ||
      snapshot.featureIdentity !== snapshot.state.selectedFeatureId ||
      detail.viewId !== snapshot.view.id ||
      detail.slot !== 'selection' ||
      !detail.rendered ||
      !detail.hasContent ||
      detail.clearSelectionCount !== 1
    )
      result.errors.push('分析 feature 详情缺失、身份不符或没有关闭操作');
    result.featureDetails = {
      identity: snapshot.featureIdentity,
      actual: featureDetails,
      statisticsCheck: 'not-run',
    };
    result.status = result.errors.length ? 'failed' : 'passed';
  }
  return result;
}

export async function checkHtml(options, shared = {}) {
  const mode = options.mode || 'startup';
  const startedAt = performance.now();
  const timings = {};
  let phase = 'input',
    phaseStartedAt = startedAt;
  const mark = next => {
    timings[phase] =
      (timings[phase] || 0) + Math.round(performance.now() - phaseStartedAt);
    phase = next;
    phaseStartedAt = performance.now();
  };
  let server,
    browser,
    context,
    deadline,
    htmlSha256,
    previous,
    checkerSha256,
    visualReadiness;
  let expired = false;
  const budgetMs = Number(
    options['max-duration-ms'] || (mode === 'startup' ? 45000 : 180000),
  );
  try {
    if (!Number.isFinite(budgetMs) || budgetMs < 1000)
      throw new Error('max-duration-ms 必须是至少 1000 的有限数值');
    checkerSha256 = checkerIdentity();
    if (options.previous) previous = await readJson(options.previous);
    if (!['startup', 'smoke', 'affected', 'full'].includes(mode))
      throw new Error('--mode 必须是 startup、smoke、affected 或 full');
    if (mode === 'startup' && (options.view || options.checks))
      throw new Error('startup 只检查初始页面，不接受 --view/--checks');
    if (mode === 'affected' && !options.view)
      throw new Error('--mode affected 必须同时提供 --view <viewId>');
    if (!options.html)
      throw new Error(
        '用法：node check-html.mjs --html map.html [--report report.json] --spec spec.json --plan plan.json --compiler-report compile.json',
      );
    const html = await readFile(resolve(options.html), 'utf8');
    htmlSha256 = createHash('sha256').update(html).digest('hex');
    const artifact = await readArtifact(html, resolve(options.html));
    const inputGraph = artifact.graph;
    failOnErrors(validateProductGraph(inputGraph));
    const deterministic = inputGraph?.contractRevision === 3;
    if (!deterministic)
      throw new Error(
        'CONTRACT_REVISION_UNSUPPORTED: 仅验收显式 revision 3 产物，不执行旧截图流程',
      );
    let protocolEvidence;
    if (deterministic) {
      if (!options.spec || !options.plan || !options['compiler-report'])
        throw new Error(
          'revision 3 验收需要 --spec、--plan、--compiler-report 与匹配 Catalog',
        );
      if (options.screenshot)
        throw new Error(
          'revision 3 验收不使用截图；组件视觉开发回归请独立运行',
        );
      const [spec, plan, compiled, catalog] = await Promise.all([
        readJson(options.spec),
        readJson(options.plan),
        readJson(options['compiler-report']),
        loadComponentCatalog(options.catalog),
      ]);
      const manifest = verifyContractArtifacts();
      failOnErrors([
        ...validateContract('revision3MapSpec', spec),
        ...validateContract('revision3PresentationPlan', plan),
        ...validateContract('revision3RenderGraph', inputGraph),
      ]);
      // Semantic validation consumes a copied, normalized fact model (optional
      // routeIds are derived there), while transform checks retain raw inputs.
      const normalized = normalizeInputs(spec, plan);
      failOnErrors([
        ...normalized.diagnostics,
        ...validateSemantics(normalized.spec, normalized.plan),
      ]);
      const intent = validateOrganization(normalized.spec, normalized.plan);
      for (const view of resolveViews(normalized.spec, normalized.plan))
        resolveComponentNodes(
          normalized.spec,
          normalized.plan,
          view,
          catalog,
          intent,
        );
      if (
        inputGraph.trace.compilerCodeSha256 !== compilerIdentity() ||
        inputGraph.trace.contractValidatorSha256 !== manifest.validatorSha256 ||
        compiled.trace?.renderGraphHash !== inputGraph.trace.renderGraphHash ||
        inputGraph.trace.renderGraphHash !==
          protocolHash({ ...inputGraph, trace: undefined })
      )
        throw new Error(
          'PROTOCOL_EVIDENCE_STALE: 编译规则、报告或 Graph 身份不匹配',
        );
      protocolEvidence = validateTransform(spec, plan, inputGraph, catalog);
      failOnErrors(protocolEvidence.diagnostics);
      if (
        compiled.transforms?.status !== 'passed' ||
        JSON.stringify(compiled.transforms.identities) !==
          JSON.stringify(protocolEvidence.identities)
      )
        throw new Error(
          'PROTOCOL_EVIDENCE_STALE: Spec、Plan、Graph 或 Catalog 已变化',
        );
      protocolEvidence.phases = {
        'spec-self': 'passed',
        'spec-plan': 'passed',
        'plan-props': 'passed',
        'spec-props': 'passed',
      };
    }
    mark('browser');
    const automation = shared.automation || (await resolveBrowserAutomation());
    browser =
      shared.browser ||
      (await launchBrowserAutomation(automation, {
        headless: true,
        args: ['--enable-unsafe-swiftshader'],
      }));
    context = await browser.newContext({
      viewport: { width: 1440, height: 960 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    await context.addInitScript(() => { window.mapCreateTelemetryDisabled = true; window.mapCreateTelemetryMode = 'acceptance'; });
    if (mode !== 'startup') visualReadiness = createResourceReadinessProbe(page);
    deadline = setTimeout(
      () => {
        expired = true;
        void context.close().catch(() => {});
      },
      Math.max(1, budgetMs - (performance.now() - startedAt)),
    );
    mark('initialize');
    const errors = [];
    const consoleErrors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() !== 'error') return;
      if (mode === 'startup') consoleErrors.push(message.text());
      else errors.push(message.text());
    });
    server = await serveArtifact(resolve(options.html), artifact.manifest);
    await page.goto(server.url, {
      waitUntil: 'domcontentloaded',
      timeout: Math.max(1, budgetMs - (performance.now() - startedAt)),
    });
    await page.waitForFunction(
      () => ['ready', 'error'].includes(document.documentElement.dataset.captureState),
      null,
      { timeout: 60000, polling: 100 },
    );
    const captureError = await page.evaluate(
      () => document.documentElement.dataset.captureError ||
        (document.documentElement.dataset.captureState === 'error' ? 'MAP_CAPTURE_ERROR' : null),
    );
    if (captureError) throw new Error(captureError);
    if (mode === 'startup') {
      const startup = evaluateStartup(
        await page.evaluate(inspectStartup), inputGraph, errors,
      );
      mark('finalize');
      const report = {
        policyVersion: 'startup-v1',
        mode,
        status: startup.status,
        protocolEvidence,
        startup,
        errors: startup.errors,
        consoleErrors,
        html: resolve(options.html),
        htmlSha256,
        checkerSha256,
        manifestSha256: artifact.manifestSha256,
        graphSha256: protocolHash(inputGraph),
        timings: {
          ...timings,
          totalMs: Math.round(performance.now() - startedAt),
        },
        limitations: STARTUP_LIMITATIONS,
        scope: '静态协议及转换校验、必要资源、Runtime 挂载、非零容器、初始内容提交、首屏必要组件挂载及非空内容、加载遮罩和启动异常；不遍历视图或执行布局与交互验收。',
        checkedAt: new Date().toISOString(),
      };
      report.retry = retryAdvice(report, previous);
      if (report.status === 'failed') report.diagnosis = diagnoseFailure(report);
      if (options.report) await writeReport(options.report, report);
      return report;
    }
    // Derive expected component inputs independently of the live Runtime state.
    // This also checks root-table identities before trusting any ready report.
    await page.evaluate(
      `window.mapCreateEvidenceGraph = (${prepareGraph.toString()})(window.mapCreateGraph)`,
    );
    await page.waitForFunction(
      () => ['ready', 'error'].includes(window.mapCreateState?.status),
      null,
      { timeout: 60000 },
    );
    let initial = await page.evaluate(() => window.mapCreateState);
    if (initial.status !== 'ready')
      errors.push(initial.message || '地图没有完成初始化');
    else {
      await waitForMapStable(page, initial.activeViewId);
      await visualReadiness.wait(initial.activeViewId);
    }
    initial = await page.evaluate(() => window.mapCreateState);

    const cases = [];
    mark('shell');
    const allViewIds = await page.evaluate(() =>
      window.mapCreateGraph.views.map(view => view.id),
    );
    const scope = checkScope(allViewIds, options);
    const viewIds = scope.viewIds;
    const checks = new Set(scope.checks);
    let navigation = null;
    const productJourneys = [];
    const activate = async id => {
      await page.evaluate(viewId => {
        if (window.mapCreateState.activeViewId !== viewId)
          window.mapCreateRuntime.activateView(viewId);
        window.mapCreateRuntime.selectElement(null);
      }, id);
    };
    const shellContract = await page.evaluate(() => {
      const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
      const view = graph.views.find(
        candidate => candidate.id === window.mapCreateState.activeViewId,
      );
      const uiRoot = document.querySelector('.content-map-kit-root');
      const legend = document.querySelector('#map-legend');
      const controls = document.querySelector('#map-controls');
      const uiStyle = uiRoot ? getComputedStyle(uiRoot) : null;
      const expectedLegendSeries = (view?.legendSeriesIds || []).map(
        seriesId => graph.seriesStyles[seriesId],
      );
      const actualLegendSeries = [
        ...legend.querySelectorAll('[data-series-id]'),
      ].map(item => ({
        id: item.dataset.seriesId,
        label: item.textContent?.trim(),
        color: item
          .querySelector('.legend__swatch')
          ?.style.getPropertyValue('--legend-color')
          .trim(),
      }));
      const mapOverlayZ = Math.min(
        Number(getComputedStyle(legend).zIndex) || 0,
        Number(getComputedStyle(controls).zIndex) || 0,
      );
      const contentZ = Math.max(
        ...[...document.querySelectorAll('[data-element-id]')].map(
          node => Number(getComputedStyle(node).zIndex) || 0,
        ),
        0,
      );
      const mapStyle = getComputedStyle(document.querySelector('#map'));
      const mapStackZ = Number(mapStyle.zIndex);
      const mapStackIsolated =
        mapStyle.position !== 'static' &&
        mapStyle.isolation === 'isolate' &&
        Number.isFinite(mapStackZ);
      const overlayHitTest = [legend, controls].every(overlay => {
        const rect = overlay.getBoundingClientRect();
        if (
          !rect.width ||
          !rect.height ||
          getComputedStyle(overlay).display === 'none'
        )
          return true;
        return [0.25, 0.5, 0.75].every(fraction => {
          const top = document.elementFromPoint(
            rect.left + rect.width * fraction,
            rect.top + rect.height / 2,
          );
          return top && overlay.contains(top);
        });
      });
      return {
        runtimeMounted: Boolean(uiRoot),
        themeMatches:
          uiStyle
            ?.getPropertyValue('--semi-color-bg-1')
            .trim()
            .toUpperCase() === graph.visualTheme.shell.panel.toUpperCase() &&
          uiStyle
            ?.getPropertyValue('--semi-color-primary')
            .trim()
            .toUpperCase() ===
            graph.visualTheme.shell.neutralAccent.toUpperCase(),
        legendParentId: (legend.closest('#map-panels') || legend).parentElement
          ?.id,
        legendScope: legend.dataset.scope,
        controlsParentId: controls.parentElement?.id,
        mapOverlayZ,
        contentZ,
        mapStackZ,
        mapStackIsolated,
        overlayHitTest,
        expectedLegendSeries,
        actualLegendSeries,
      };
    });
    if (!shellContract.runtimeMounted)
      errors.push('ContentMapKit Semi Runtime 没有挂载');
    shellContract.sections = await checkUiSections(page);
    errors.push(...shellContract.sections.errors);
    if (!shellContract.themeMatches)
      errors.push('Semi 主题变量没有与 visualTheme.shell 对齐');
    if (shellContract.legendParentId !== 'map-shell')
      errors.push('图例没有悬浮在地图容器上');
    if (shellContract.legendScope !== 'view')
      errors.push('图例没有限定到当前 View');
    if (shellContract.controlsParentId !== 'map-shell')
      errors.push('地图控制没有悬浮在地图容器上');
    if (
      !shellContract.mapStackIsolated ||
      shellContract.mapOverlayZ <= shellContract.mapStackZ ||
      !shellContract.overlayHitTest
    )
      errors.push('地图控制或图例没有压盖点线面内容');
    if (
      JSON.stringify(
        shellContract.expectedLegendSeries.map(item => ({
          id: item.id,
          label: item.label,
          color: item.kind === 'area' ? item.fillColor : item.color,
        })),
      ) !== JSON.stringify(shellContract.actualLegendSeries)
    )
      errors.push('图例没有直接消费路线/区域的最终 seriesStyles');
    const inspectView = async viewId => {
      mark('view-checks');
      const viewStartedAt = performance.now();
      const checkErrors = Object.fromEntries(CHECK_GROUPS.map(check => [check, []]));
      let activeCheck = 'geometry';
      const addErrors = (...messages) => {
        errors.push(...messages);
        checkErrors[activeCheck].push(...messages);
      };
      if (mode === 'smoke') await activate(viewId);
      const activationStability = await waitForMapStable(page, viewId);
      const resourceReadiness = deterministic
        ? await visualReadiness.wait(viewId)
        : null;
      const sourceEvidence = await inspectSourceEvidence(page);
      addErrors(
        ...sourceEvidence.errors.map(message => `${viewId}: ${message}`),
      );
      const routeSymbols = await page.evaluate(inspectRouteSymbols);
      addErrors(...routeSymbols.errors);
      const elevatedGeometry = await page.evaluate(inspectElevatedGeometry);
      addErrors(
        ...elevatedGeometry.errors.map(message => `${viewId}: ${message}`),
      );
      const screenGeometry = await page.evaluate(inspectScreenGeometry, { phase: 'initial' });
      addErrors(
        ...screenGeometry.errors.map(message => `${viewId}: ${message}`),
      );
      const sectionChecks = [];
      const verifySections = async sectionPhase => {
        const result = await checkUiSections(page);
        sectionChecks.push({ phase: sectionPhase, ...result });
        checkErrors.sidebar.push(...result.errors);
        errors.push(
          ...result.errors.map(
            message => `${viewId}/${sectionPhase}: ${message}`,
          ),
        );
        return result;
      };
      await verifySections('activated');
      await page.waitForFunction(
        () =>
          [
            ...document.querySelectorAll('[data-heatmap-engine="maplibre"]'),
          ].every(
            host =>
              getComputedStyle(host).display === 'none' ||
              host.dataset.heatmapReady === 'true',
          ),
        null,
        { timeout: 10000 },
      );
      const initialViewState = await page.evaluate(() => window.mapCreateState);
      const renderedElementIds = await page
        .locator('#map [data-element-id]')
        .evaluateAll(nodes =>
          nodes
            .filter(node => getComputedStyle(node).display !== 'none')
            .map(node => node.getAttribute('data-element-id'))
            .filter(Boolean),
        );
      // Analysis surfaces use a shared canvas or native polygons instead of SVG nodes.
      const analysisEvidence = await page.evaluate(() => {
        const active = window.mapCreateRuntime.layer
          .getElements()
          .filter(
            element =>
              element.visible !== false &&
              ['heatmap', 'continuous_heatmap', 'hexbin_heatmap'].includes(
                element.type,
              ),
          );
        const continuous = active.filter(
          element =>
            element.type === 'continuous_heatmap' ||
            (element.type === 'heatmap' && element.mode === 'continuous'),
        );
        const canvas = document.querySelector(
          'canvas[data-content-map-analysis-layer]',
        );
        let paintedPixels = 0;
        if (canvas && continuous.length === 1) {
          const pixels = canvas
            .getContext('2d')
            .getImageData(0, 0, canvas.width, canvas.height).data;
          for (let i = 3; i < pixels.length; i += 4)
            if (pixels[i]) paintedPixels++;
        }
        const ids = paintedPixels > 0 ? [continuous[0].id] : [];
        for (const host of document.querySelectorAll(
          '[data-heatmap-engine="maplibre"]',
        )) {
          if (getComputedStyle(host).display === 'none') continue;
          const nativeCanvas = host.querySelector('canvas');
          const gl =
            nativeCanvas?.getContext('webgl2') ||
            nativeCanvas?.getContext('webgl');
          if (!gl) continue;
          const pixels = new Uint8Array(
            gl.drawingBufferWidth * gl.drawingBufferHeight * 4,
          );
          gl.readPixels(
            0,
            0,
            gl.drawingBufferWidth,
            gl.drawingBufferHeight,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            pixels,
          );
          let nativePainted = 0;
          for (let i = 3; i < pixels.length; i += 4)
            if (pixels[i]) nativePainted++;
          if (nativePainted > 0)
            ids.push(...JSON.parse(host.dataset.heatmapElementIds || '[]'));
          paintedPixels += nativePainted;
        }
        const columns =
          window.mapCreateRuntime.map.getAllOverlays?.('polygon') || [];
        for (const element of active.filter(
          candidate => candidate.mode === 'hexbin-3d',
        ))
          if (
            columns.some(
              column => column.getExtData()?.elementId === element.id,
            )
          )
            ids.push(element.id);
        return { ids, paintedPixels, nativeColumnCount: columns.length };
      });
      renderedElementIds.push(...analysisEvidence.ids);

      const canvasElementIds = await page
        .locator('#map canvas[data-content-map-analysis-layer]')
        .evaluateAll(nodes =>
          nodes
            .filter(
              node =>
                node.width > 0 &&
                node.height > 0 &&
                getComputedStyle(node).display !== 'none',
            )
            .flatMap(node =>
              JSON.parse(
                node.getAttribute('data-rendered-element-ids') || '[]',
              ),
            ),
        );
      const { missing: missingRenderedElementIds, unexpected } =
        compareRenderedElements(
          initialViewState.visibleElementIds,
          renderedElementIds,
          canvasElementIds,
        );
      if (missingRenderedElementIds.length)
        addErrors(
          `${viewId} 完成视野适配后仍未实际绘制：${missingRenderedElementIds.join(', ')}`,
        );
      if (unexpected.length)
        addErrors(
          `${viewId} 存在非当前可见集合的残留绘制：${unexpected.join(', ')}`,
        );
      const arrowEndpointClearance = await page.evaluate(id => {
        const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
        const view = graph.views.find(item => item.id === id);
        const elements = (view?.elementIds || [])
          .map(elementId =>
            graph.elements.find(element => element.id === elementId),
          )
          .filter(Boolean);
        const requiredInsets = new Map([
          ['numbered-marker', 13.5],
          ['common-marker', 6],
        ]);
        const markers = elements.filter(element =>
          requiredInsets.has(element.componentId),
        );
        return elements
          .filter(element => element.rendererType === 'arrow')
          .map(element => {
            const endpoint = element.props.path?.at(-1);
            const marker = markers.find(
              candidate =>
                JSON.stringify(candidate.props.position) ===
                JSON.stringify(endpoint),
            );
            if (!marker) return null;
            const requiredEndInset = requiredInsets.get(marker.componentId);
            const actualEndInset = element.props.endInset ?? 0;
            return {
              arrowId: element.id,
              markerId: marker.id,
              markerComponentId: marker.componentId,
              requiredEndInset,
              actualEndInset,
              passed: actualEndInset >= requiredEndInset,
            };
          })
          .filter(Boolean);
      }, viewId);
      for (const clearance of arrowEndpointClearance) {
        if (!clearance.passed)
          addErrors(
            `${viewId} 箭头 ${clearance.arrowId} 与终点 ${clearance.markerId} 重叠：endInset=${clearance.actualEndInset}，至少需要 ${clearance.requiredEndInset}`,
          );
      }
      const clippedElementIds = screenGeometry.elements
        .filter(element => element.outside)
        .map(element => element.elementId);
      const journeyStartedAt = performance.now();
      if (mode !== 'smoke')
        productJourneys.push(
          ...(await checkEdgeNavigationJourneys(page, inputGraph)),
        );
      if (mode !== 'smoke')
        productJourneys.push(
          ...(await checkProductJourneys(page, inputGraph, {
            viewIds: [viewId],
            navigate: false,
          })),
        );
      const productJourneyMs = Math.round(performance.now() - journeyStartedAt);
      const interactionScreenGeometry = await page.evaluate(
        inspectScreenGeometry,
        { phase: 'interaction' },
      );
      addErrors(...interactionScreenGeometry.errors.map(message => `${viewId}: ${message}`));
      activeCheck = 'selection';
      // Large route geometry can finish its worker-backed preparation after the
      // camera first becomes stable. Recheck after that window so selection is
      // compared with the final base layout rather than an intermediate frame.
      await page.waitForTimeout(100);
      await waitForMapStable(page, viewId);
      const beforeSelection = await visibleElementRects(page);
      const collectionEntries = [];
      const entryActions = await page.evaluate(
        id =>
          window.mapCreateGraph.views.find(view => view.id === id)
            ?.entryActions || {},
        viewId,
      );
      for (const [elementId, action] of Object.entries(entryActions)) {
        const triggers = [];
        if (checks.has('selection'))
          triggers.push(['map', `[data-element-id="${elementId}"]`]);
        if (checks.has('sidebar')) {
          const selector = `[data-linked-element-id="${elementId}"][data-target-view-id]`;
          if (await page.locator(selector).count())
            triggers.push(['sidebar', selector]);
        }
        for (const [source, selector] of triggers) {
          activeCheck = source === 'map' ? 'selection' : 'sidebar';
          await page.locator(selector).first().dispatchEvent('click');
          await page.waitForFunction(
            id =>
              window.mapCreateState?.activeViewId === id &&
              window.mapCreateState.selectedElementId === null,
            action.viewId,
            { timeout: 5000 },
          );
          await waitForMapStable(page, action.viewId);
          await page.evaluate(
            id => window.mapCreateRuntime.activateView(id),
            viewId,
          );
          await waitForMapStable(page, viewId);
          const restored = await page.evaluate(
            id => window.mapCreateState.selectedElementId === id,
            elementId,
          );
          if (!restored)
            addErrors(
              `${viewId} ${source} 集合入口 ${elementId} 返回后没有恢复入口上下文`,
            );
          collectionEntries.push({
            elementId,
            source,
            targetViewId: action.viewId,
            restored,
          });
        }
      }
      if (collectionEntries.length) {
        await page.evaluate(() => window.mapCreateRuntime.selectElement(null));
        await waitForMapStable(page, viewId);
      }
      activeCheck = 'selection';
      const selectableId = await page.evaluate(
        ({ id, visibleIds }) => {
          const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
          const view = graph.views.find(item => item.id === id);
          return view?.elementIds
            .filter(
              elementId =>
                visibleIds.includes(elementId) &&
                !view.entryActions?.[elementId],
            )
            .map(elementId =>
              graph.elements.find(element => element.id === elementId),
            )
            .find(element => element && 'position' in element.props)?.id;
        },
        { id: viewId, visibleIds: Object.keys(beforeSelection) },
      );
      let selectionStability = null;
      if (checks.has('selection') && selectableId) {
        const selectable = page.locator(`[data-element-id="${selectableId}"]`);
        const beforeSelectedMarkup = await selectable.evaluate(
          node => node.innerHTML,
        );
        await selectable.dispatchEvent('click');
        await page.waitForFunction(
          id => window.mapCreateState?.selectedElementId === id,
          selectableId,
          { timeout: 5000 },
        );
        const selectedStability = await waitForMapStable(page, viewId);
        await verifySections('map-selected');
        const afterSelection = await visibleElementRects(page);
        const afterSelectedMarkup = await page
          .locator(`[data-element-id="${selectableId}"]`)
          .evaluate(node => node.innerHTML);
        const visualChanged = beforeSelectedMarkup !== afterSelectedMarkup;
        const movedElements = Object.keys(beforeSelection)
          .filter(id => id !== selectableId && afterSelection[id])
          .map(id => ({
            id,
            before: beforeSelection[id],
            after: afterSelection[id],
          }))
          .filter(({ before, after }) => before.transform !== after.transform);
        const movedElementIds = movedElements.map(element => element.id);
        const degradedElementIds = Object.keys(beforeSelection).filter(
          id =>
            id !== selectableId &&
            (!afterSelection[id] ||
              beforeSelection[id].markup !== afterSelection[id].markup),
        );
        const selectedRendererType = await page.evaluate(
          id =>
            window.mapCreateGraph.elements.find(element => element.id === id)
              ?.rendererType,
          selectableId,
        );
        const requiresSelectedVisual = [
          'common_waypoint',
          'number_waypoint',
          ...(deterministic
            ? ['poi_marker', 'origin', 'destination', 'transfer_point']
            : []),
        ].includes(selectedRendererType);
        const linkedTimelineRow = page.locator(
          `[data-member-id] [data-linked-element-id="${selectableId}"], [data-linked-element-id="${selectableId}"][data-member-id]`,
        );
        const hasTimelineRows =
          (await page.locator('[data-member-id]').count()) > 0;
        const linkedTimelineMemberId = (await linkedTimelineRow.count())
          ? await linkedTimelineRow.evaluate(node =>
              node.closest('[data-member-id]')?.getAttribute('data-member-id'),
            )
          : null;
        const linkedTimelineSelected = linkedTimelineMemberId
          ? await linkedTimelineRow.evaluate(
              node =>
                node.getAttribute('aria-pressed') === 'true' ||
                node.classList.contains('is-selected'),
            )
          : null;
        if (movedElementIds.length)
          addErrors(
            `${viewId} 选中 ${selectableId} 后其它元素发生位移：${movedElementIds.join(', ')}`,
          );
        if (requiresSelectedVisual && !visualChanged)
          addErrors(`${viewId} 选中 ${selectableId} 后没有产生视觉变化`);
        if (
          ['common_waypoint', 'number_waypoint'].includes(
            selectedRendererType,
          ) &&
          hasTimelineRows &&
          !linkedTimelineMemberId
        )
          addErrors(`${viewId} 地图点 ${selectableId} 没有关联侧栏站点`);
        if (linkedTimelineMemberId && !linkedTimelineSelected)
          addErrors(
            `${viewId} 地图点 ${selectableId} 没有同步侧栏站点选中态`,
          );
        await page.evaluate(() => window.mapCreateRuntime.selectElement(null));
        await page.waitForFunction(
          () => window.mapCreateState?.selectedElementId === null,
          null,
          { timeout: 5000 },
        );
        await waitForMapStable(page, viewId);
        const afterDeselection = await visibleElementRects(page);
        const unrestoredElements = Object.keys(beforeSelection)
          .map(id => ({
            id,
            before: beforeSelection[id],
            after: afterDeselection[id] || null,
          }))
          .filter(
            ({ before, after }) =>
              !after ||
              before.transform !== after.transform ||
              Math.abs(before.width - after.width) > 0.75 ||
              Math.abs(before.height - after.height) > 0.75,
          );
        const unrestoredElementIds = unrestoredElements.map(
          element => element.id,
        );
        if (unrestoredElementIds.length)
          addErrors(
            `${viewId} 取消选中 ${selectableId} 后基础布局未恢复：${unrestoredElementIds.join(', ')}`,
          );
        selectionStability = {
          selectedElementId: selectableId,
          selectedRendererType,
          movedElementIds,
          movedElements,
          degradedElementIds,
          unrestoredElementIds,
          unrestoredElements,
          visualChanged,
          linkedTimelineMemberId,
          linkedTimelineSelected,
          elapsedMs: selectedStability.elapsedMs,
        };
      }
      let sidebarSelection = null;
      await verifySections('after-map-selection-cleared');
      const selectionShapes =
        deterministic && checks.has('selection')
          ? await inspectSelectionShapes(page, viewId, waitForMapStable)
          : null;
      if (selectionShapes?.status === 'failed')
        addErrors({
          viewId,
          code: 'SELECTION_SHAPE_MISMATCH',
          checks: selectionShapes.checks,
        });
      activeCheck = 'sidebar';
      const linkedRows = page.locator(
        '[data-linked-element-id]:not([data-target-view-id])',
      );
      if (checks.has('sidebar') && (await linkedRows.count()) > 1) {
        const row = linkedRows.last();
        const elementId = await row.getAttribute('data-linked-element-id');
        const memberId = await row.evaluate(
          node =>
            node.closest('[data-member-id]')?.getAttribute('data-member-id') ||
            null,
        );
        await row.click();
        await page.waitForFunction(
          id => window.mapCreateState?.selectedElementId === id,
          elementId,
          { timeout: 5000 },
        );
        await waitForMapStable(page, viewId);
        const markerSelected = await page
          .locator(`[data-element-id="${elementId}"]`)
          .evaluate(node => Boolean(node.innerHTML));
        const rowSelected = await row.evaluate(
          node =>
            node.getAttribute('aria-pressed') === 'true' ||
            node.classList.contains('is-selected'),
        );
        if (!markerSelected || !rowSelected)
          addErrors(
            `${viewId} UI 条目 ${memberId || elementId} 没有联动地图 marker`,
          );
        const selectedProperties = page.locator(
          '#selection-details [aria-label="选中对象详情"], #content-map-ui [data-ui-source="selected.properties"]',
        );
        const hasSelectedPropertiesSection = await page.evaluate(
          id =>
            window.mapCreateGraph.views
              .find(view => view.id === window.mapCreateState.activeViewId)
              ?.ui?.sections.some(
                section =>
                  section.source === 'selected.properties' &&
                  section.items?.some(item => item.ownerElementId === id),
              ),
          elementId,
        );
        const sectionEvidence = await verifySections('sidebar-selected');
        const selectedPropertiesVisible = hasSelectedPropertiesSection
          ? sectionEvidence.method === 'section-identity-state-slot'
            ? sectionEvidence.status === 'passed'
            : (await selectedProperties.count()) === 1 &&
              (await selectedProperties.textContent()).trim().length > 0 &&
              (await selectedProperties
                .locator('button[aria-label="关闭详情"]')
                .count()) === 1
          : null;
        if (hasSelectedPropertiesSection && !selectedPropertiesVisible)
          addErrors(`${viewId} selected.properties 没有随地图选择更新`);
        sidebarSelection = {
          memberId,
          elementId,
          markerSelected,
          rowSelected,
          selectedPropertiesVisible,
        };
        await page.evaluate(() => window.mapCreateRuntime.selectElement(null));
        await waitForMapStable(page, viewId);
        await verifySections('selection-cleared');
      }
      activeCheck = 'series';
      let seriesSelection = null;
      const legendItems = page.locator(
        '#map-legend [data-series-id^="route:"]',
      );
      if (checks.has('series') && (await legendItems.count()) > 1) {
        const disclosure = page.locator(
          '#map-legend details:not([open]) > summary',
        );
        if (await disclosure.count()) await disclosure.click();
        const selectedLegend = legendItems.first();
        const seriesId = await selectedLegend.getAttribute('data-series-id');
        await selectedLegend.click();
        await page.waitForFunction(
          id => window.mapCreateState?.selectedSeriesId === id,
          seriesId,
          { timeout: 5000 },
        );
        await waitForMapStable(page, viewId);
        const focus = await page.evaluate(id => {
          const graph = window.mapCreateEvidenceGraph || window.mapCreateGraph;
          const view = graph.views.find(
            candidate => candidate.id === window.mapCreateState.activeViewId,
          );
          const routes = (view?.elementIds || [])
            .map(elementId =>
              graph.elements.find(element => element.id === elementId),
            )
            .filter(element => element?.seriesId?.startsWith('route:'))
            .map(element => {
              const node = document.querySelector(
                `[data-element-id="${element.id}"]`,
              );
              const routeBody = node?.querySelector('[data-route-body="true"]');
              return {
                id: element.id,
                seriesId: element.seriesId,
                opacity: Number(
                  routeBody?.getAttribute('opacity') ||
                    node?.getAttribute('opacity') ||
                    (node ? getComputedStyle(node).opacity : 1) ||
                    1,
                ),
              };
            });
          return {
            routes,
            pressed: document
              .querySelector(`[data-series-id="${id}"]`)
              ?.getAttribute('aria-pressed'),
          };
        }, seriesId);
        const selectedRoutes = focus.routes.filter(
          route => route.seriesId === seriesId,
        );
        const otherRoutes = focus.routes.filter(
          route => route.seriesId !== seriesId,
        );
        const selectedVisible = selectedRoutes.every(
          route => route.opacity >= 0.95,
        );
        const othersWeakened = otherRoutes.every(route => route.opacity <= 0.3);
        if (!selectedVisible || !othersWeakened || focus.pressed !== 'true')
          addErrors(`${viewId} 路线聚焦没有同步弱化其它路线和高亮图例`);
        await page.evaluate(() => window.mapCreateRuntime.selectSeries(null));
        await page.waitForFunction(
          () => window.mapCreateState?.selectedSeriesId === null,
          null,
          { timeout: 5000 },
        );
        seriesSelection = {
          seriesId,
          selectedVisible,
          othersWeakened,
          legendPressed: focus.pressed === 'true',
        };
      }
      activeCheck = 'regions';
      const polygonVisibility = checks.has('regions')
        ? await page.evaluate(inspectPolygons, viewId)
        : [];
      for (const polygon of polygonVisibility)
        for (const error of polygon.errors)
          addErrors(`${viewId} 区域 ${polygon.id}：${error}`);
      activeCheck = 'zoom';
      let zoomStability = null;
      // Entry checks deliberately visit other views; only measure fits caused by zoom here.
      const beforeZoom = await page.evaluate(() => window.mapCreateState);
      const cameraBeforeZoom = await page.evaluate(() => {
        const map = window.mapCreateRuntime.map;
        const center = map.getCenter();
        return {
          zoom: map.getZoom(),
          center: [center.getLng(), center.getLat()],
        };
      });
      if (checks.has('zoom')) {
        await page.evaluate(() => {
          const map = window.mapCreateRuntime.map;
          map.setZoom(Math.min(20, map.getZoom() + 1), true);
        });
        zoomStability = await waitForMapStable(page, viewId);
      }
      const afterZoom = await page.evaluate(() => window.mapCreateState);
      if (afterZoom.activeViewId !== viewId)
        addErrors(`${viewId} 缩放后 activeViewId 丢失`);
      if (afterZoom.fitCount !== beforeZoom.fitCount)
        addErrors(`${viewId} 普通缩放触发了额外 fit`);
      if (
        JSON.stringify(afterZoom.visibleElementIds) !==
        JSON.stringify(beforeZoom.visibleElementIds)
      )
        addErrors(`${viewId} 缩放后可见元素集合变化`);
      if (checks.has('zoom')) {
        await page.evaluate(camera => {
          window.mapCreateRuntime.map.setZoomAndCenter(
            camera.zoom,
            camera.center,
            true,
          );
        }, cameraBeforeZoom);
        await waitForMapStable(page, viewId);
      }
      cases.push({
        viewId,
        productJourneyMs,
        resourceReadiness,
        sectionChecks,
        checkErrors,
        sourceEvidence,
        elapsedMs: Math.round(performance.now() - viewStartedAt),
        checks: Object.fromEntries(
          CHECK_GROUPS.map(check => [
            check,
            checks.has(check)
              ? checkErrors[check].length === 0
                ? 'passed'
                : 'failed'
              : 'not-run',
          ]),
        ),
        visibleElementIds: beforeZoom.visibleElementIds,
        renderedElementIds,
        missingRenderedElementIds,
        arrowEndpointClearance,
        clippedElementIds,
        fitCount: beforeZoom.fitCount,
        zoomPreservedView: afterZoom.activeViewId === viewId,
        stability: {
          activationMs: activationStability.elapsedMs,
          zoomMs: zoomStability?.elapsedMs ?? null,
        },
        selectionStability,
        selectionShapes,
        collectionEntries,
        sidebarSelection,
        seriesSelection,
        polygonVisibility,
        analysisEvidence,
        routeSymbols,
        elevatedGeometry,
        screenGeometry,
        interactionScreenGeometry,
      });
    };
    if (mode === 'smoke') {
      for (const viewId of viewIds) await inspectView(viewId);
    } else {
      navigation = await checkNavigation(
        page,
        waitForMapStable,
        viewIds,
        inspectView,
      );
    }
    mark('finalize');
    const report = {
      policyVersion: 'deterministic-v2',
      protocolEvidence,
      productJourneys,
      manifestSha256: artifact.manifestSha256,
      graphSha256: inputGraph ? protocolHash(inputGraph) : null,
      limitations: deterministic
        ? [
            '不评测审美、底图瓦片完整像素或 GPU 像素正确性；自然语言意图提取与来源真实性不能由结构校验证明。',
          ]
        : [],
      checkerSha256,
      timings: {
        ...timings,
        totalMs: Math.round(performance.now() - startedAt),
      },
      requestedScope: scope,
      coverage: {
        revision: 1,
        views: cases.map(({ viewId, checks: viewChecks }) => ({
          viewId,
          checks: viewChecks,
        })),
      },
      status: errors.length ? 'failed' : 'passed',
      mode,
      html: resolve(options.html),
      htmlSha256,
      automation: {
        driver: 'playwright',
        module: automation.module,
        browser: automation.browser,
      },
      shellContract,
      navigation,
      initial,
      views: cases,
      returnedToInitialView: true,
      visualTheme: initial.visualTheme,
      visualReview: {
        status: 'not-applicable',
        reason: '确定性无截图验收策略，不执行截图或模型看图评分',
      },
      errors,
      checkedAt: new Date().toISOString(),
      scope:
        mode === 'smoke'
          ? '快速检查 HTML 启动、Runtime 挂载、主题、当前 View 图例与地图控制覆盖层。'
          : `${mode === 'affected' ? '定向' : '完整'}检查 View 切换、图例—seriesStyles 一致性、UI 与地图双向联动、稳定性、视野适配、箭头避让、缩放、选中和可逆恢复；不评测审美与底图/GPU 像素正确性。`,
    };
    report.retry = retryAdvice(report, previous);
    if (report.status === 'failed') report.diagnosis = diagnoseFailure(report);
    if (options.report) await writeReport(options.report, report);
    return report;
  } catch (error) {
    const report = {
      status: 'failed',
      mode,
      htmlSha256,
      checkerSha256,
      requestedScope: { view: options.view, checks: options.checks },
      error: expired
        ? { message: mode === 'startup' ? '启动检查超过预算' : '验收总时长超过预算', code: mode === 'startup' ? 'STARTUP_TIMEOUT' : 'CHECK_BUDGET_EXHAUSTED' }
        : safeError(error),
      phase,
      timings: {
        ...timings,
        [phase]: Math.round(performance.now() - phaseStartedAt),
        totalMs: Math.round(performance.now() - startedAt),
      },
      checkedAt: new Date().toISOString(),
    };
    report.retry = retryAdvice(report, previous);
    report.diagnosis = diagnoseFailure(report);
    if (options.report) await writeReport(options.report, report);
    return report;
  } finally {
    clearTimeout(deadline);
    visualReadiness?.dispose();
    await context?.close();
    await server?.close();
    if (!shared.browser) await browser?.close();
  }
}

async function main() {
  const options = args();
  let browser;
  try {
    let reports;
    if (options.batch) {
      const jobs = await readJson(options.batch);
      if (!Array.isArray(jobs) || !jobs.length || jobs.length > 20)
        throw new Error('batch 需要 1–20 个验收任务');
      const automation = await resolveBrowserAutomation();
      browser = await launchBrowserAutomation(automation, {
        headless: true,
        args: ['--enable-unsafe-swiftshader'],
      });
      reports = [];
      for (const job of jobs) {
        const report = await checkHtml(job, { browser, automation });
        reports.push(report);
        if (report.status !== 'passed') break;
      }
    } else reports = [await checkHtml(options)];
    for (const report of reports) {
      const summary = options.verbose
        ? report
        : {
            status: report.status,
            mode: report.mode,
            timings: report.timings,
            retry: report.retry,
            errors: report.errors,
            error: report.error,
            views: report.views?.map(view => ({
              viewId: view.viewId,
              elapsedMs: view.elapsedMs,
            })),
            visualReview: report.visualReview,
          };
      process.stdout.write(JSON.stringify(summary, null, 2) + '\n');
    }
    if (reports.some(report => report.status !== 'passed'))
      process.exitCode = 1;
  } catch (error) {
    process.stderr.write(
      JSON.stringify({ status: 'failed', error: safeError(error) }) + '\n',
    );
    process.exitCode = 1;
  } finally {
    await browser?.close();
  }
}
if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)
  await main();

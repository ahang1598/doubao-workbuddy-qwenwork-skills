import { createHash } from 'node:crypto';

export const CHECK_GROUPS = [
  'geometry',
  'selection',
  'sidebar',
  'series',
  'regions',
  'zoom',
];
const hash = value =>
  createHash('sha256').update(JSON.stringify(value)).digest('hex');

export function checkScope(allViewIds, options) {
  const mode = options.mode || 'full';
  if (!['full', 'affected', 'smoke'].includes(mode))
    throw new Error('无效验收 mode');
  const split = value => [
    ...new Set(
      String(value || '')
        .split(',')
        .map(id => id.trim())
        .filter(Boolean),
    ),
  ];
  if (mode !== 'affected' && (options.checks || options.view))
    throw new Error('--checks/--view 仅用于 affected，不能缩小 full 覆盖');
  const viewIds =
    mode === 'smoke' ? [] : mode === 'full' ? allViewIds : split(options.view);
  if (mode === 'affected' && !viewIds.length)
    throw new Error('affected 需要 --view');
  if (
    !allViewIds.length ||
    new Set(allViewIds).size !== allViewIds.length ||
    viewIds.some(id => !allViewIds.includes(id))
  )
    throw new Error('View 范围为空、重复或不存在');
  const checks = options.checks ? split(options.checks) : [...CHECK_GROUPS];
  if (!checks.length || checks.some(check => !CHECK_GROUPS.includes(check)))
    throw new Error('未知检查项');
  if (!checks.includes('geometry')) checks.push('geometry');
  // Selection assertions exercise both sides of the map/sidebar bridge.
  if (checks.includes('selection') && !checks.includes('sidebar'))
    checks.push('sidebar');
  return { viewIds, checks: mode === 'smoke' ? [] : checks };
}

export function screenshotSetHash(screenshots) {
  return hash(screenshots.map(({ viewId, sha256 }) => ({ viewId, sha256 })));
}

export function assertCompleteCoverage(report, expectedViewIds) {
  const coverage = report.coverage;
  if (
    report.mode !== 'full' ||
    coverage?.revision !== 1 ||
    !expectedViewIds.length ||
    new Set(expectedViewIds).size !== expectedViewIds.length ||
    coverage.views?.length !== expectedViewIds.length
  )
    throw new Error('验收覆盖不完整：需要当前产物的完整报告');
  for (const viewId of expectedViewIds) {
    const rows = coverage.views.filter(view => view.viewId === viewId);
    if (
      rows.length !== 1 ||
      CHECK_GROUPS.some(check => rows[0].checks?.[check] !== 'passed')
    )
      throw new Error(`验收覆盖不完整：${viewId}`);
  }
  if (report.policyVersion === 'deterministic-v2') {
    if (
      report.navigation?.status !== 'passed' ||
      report.navigation.method !== 'visible-ui-click' ||
      report.navigation.returnedToInitialView !== true ||
      expectedViewIds.some(
        id => !report.navigation.visitedViewIds?.includes(id),
      )
    )
      throw new Error('确定性验收不完整：缺少实际用户导航及返回证据');
    if (
      report.protocolEvidence?.status !== 'passed' ||
      ['spec-self', 'spec-plan', 'plan-props', 'spec-props'].some(
        phase => report.protocolEvidence.phases?.[phase] !== 'passed',
      ) ||
      !report.protocolEvidence.checks?.length ||
      report.protocolEvidence.checks.some(check => check.status !== 'passed') ||
      expectedViewIds.some(
        id =>
          report.views?.filter(
            view =>
              view.viewId === id && view.resourceReadiness?.status === 'passed',
          ).length !== 1,
      )
    )
      throw new Error('确定性验收不完整：缺少源协议校验或浏览器资源证据');
    return;
  }
  throw new Error('仅接受 deterministic-v2 无截图完整验收报告');
}

export function retryAdvice(report, previous) {
  if (report.status === 'passed')
    return { consecutiveFailures: 0, action: 'continue' };
  // Same artifact AND scope AND checker: different work must not inherit a retry count.
  const fingerprint = hash([
    report.htmlSha256,
    report.checkerSha256,
    report.mode,
    report.requestedScope,
    [...(report.errors || [report.error])]
      .map(value => JSON.stringify(value))
      .sort(),
  ]);
  const consecutiveFailures =
    previous?.status === 'failed' && previous.retry?.fingerprint === fingerprint
      ? previous.retry.consecutiveFailures + 1
      : 1;
  return {
    fingerprint,
    consecutiveFailures,
    action: consecutiveFailures >= 2 ? 'stop-and-diagnose' : 'inspect-failure',
  };
}

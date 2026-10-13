const ENDPOINTS = Object.freeze({
  online: { api: 'https://livesaas.volcengineapi.com', console: 'https://console.volcengine.com' },
});

function invalid() {
  throw Object.assign(new Error('质检环境或任务定位不可用'), { code: 'INVALID_REMOTE_TARGET' });
}

// New requests default to production; saved task environments remain explicitly pinned.
export function resolveInspectionEnvironment({ environment = 'online', env = process.env, resolveRuntime } = {}) {
  if (environment !== undefined && !Object.hasOwn(ENDPOINTS, environment)) invalid();
  const resolve = resolveRuntime || (() => ({ baseUrl: ENDPOINTS.online.api }));
  const runtime = resolve(environment ? { baseUrl: ENDPOINTS[environment].api } : {}, env);
  const api = String(runtime.baseUrl || '').replace(/\/+$/, '');
  const entry = Object.entries(ENDPOINTS).find(([, value]) => value.api === api);
  // Custom API gateways are not evidence of either console environment.
  if (!entry) invalid();
  return { environment: entry[0], baseUrl: entry[1].api };
}

function remoteTaskBase({ environment, projectName, taskId }) {
  if (!Object.hasOwn(ENDPOINTS, environment)) invalid();
  const project = String(projectName ?? '');
  const task = String(taskId ?? '');
  if (!project || project === '.' || project === '..' || /[\x00-\x1f\x7f/\\]/.test(project)
    || !/^\d+$/.test(task) || !Number.isSafeInteger(Number(task)) || Number(task) <= 0) invalid();
  return `${ENDPOINTS[environment].console}/livesaas/liveinspect/projectManagement/${encodeURIComponent(project)}/taskManagement`;
}

export function remoteDashboard(target) {
  return { status: 'remote', environment: target.environment, dashboard_url: `${remoteTaskBase(target)}/dashboard/${Number(target.taskId)}` };
}

// Both kinds use the shared report page; a generated address does not prove readiness or access.
export function remoteReport({ kind, ...target }) {
  if (!['live', 'video'].includes(kind)) invalid();
  const base = remoteTaskBase(target);
  const route = 'report/view';
  return { status: 'link_generated', environment: target.environment, report_kind: kind, report_url: `${base}/${route}/${Number(target.taskId)}` };
}

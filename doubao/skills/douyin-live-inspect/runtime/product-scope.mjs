// The Agent resolves accessible projects/scenarios before invoking the create script.
// Never substitute another customer's deployment defaults for missing selections.
export function resolveLiveScope(input = {}) {
  const environment = input.environment === undefined ? 'online' : input.environment;
  if (!['online'].includes(environment)) throw Object.assign(new Error('质检环境不可用'), { code: 'UNSUPPORTED_ENVIRONMENT' });
  const project = typeof input.project_name === 'string' ? input.project_name.trim() : '';
  const name = typeof input.scenario === 'string' ? input.scenario.trim() : '';
  const id = String(input.scenario_id ?? '').trim();
  const fail = (code) => { throw Object.assign(new Error('质检场景配置不可用'), { code }); };
  if (!project || project === '.' || project === '..' || /[\x00-\x1f\x7f/\\]/.test(project)) fail('PROJECT_REQUIRED');
  if (!/^\d+$/.test(id) || !Number.isSafeInteger(Number(id)) || Number(id) <= 0) fail('SCENARIO_REQUIRED');
  if (!name) fail('SCENARIO_NAME_REQUIRED');
  return { projectName: project, scenarioId: id, scenarioName: name };
}

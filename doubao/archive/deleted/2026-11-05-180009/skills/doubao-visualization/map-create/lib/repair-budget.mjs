import { digest } from './cdn-assets.mjs';

export const repairLimits = Object.freeze({
  input: 20,
  acceptance: 10,
  resource: 10,
});

export function repairCategory(phase) {
  if (['input', 'prepare-input', 'compile'].includes(phase)) return 'input';
  if (['accept', 'trace', 'deliver'].includes(phase)) return 'acceptance';
  return 'resource';
}

export function restoreRepairBudget(previous) {
  if (!['failed', 'pending'].includes(previous?.status))
    return {
      version: 1,
      failures: { input: 0, acceptance: 0, resource: 0 },
      recent: [],
    };
  if (previous.repairBudget?.version === 1)
    return structuredClone(previous.repairBudget);
  const failures = { input: 0, acceptance: 0, resource: 0 };
  if (previous.status === 'failed')
    failures[repairCategory(previous.phase || 'input')] = previous.attempt || 1;
  return { version: 1, failures, recent: [], migrated: true };
}

export function assertRepairAllowed(budget, phase, identity) {
  const category = repairCategory(phase);
  if (budget.failures[category] >= repairLimits[category])
    throw new Error(
      'REPAIR_LIMIT: ' +
        category +
        ' 阶段预算已耗尽；可离线预检，不得换目录或重置记录',
    );
  const repeated = budget.recent
    .filter(item => item.category === category)
    .slice(-2);
  if (
    repeated.length === 2 &&
    repeated.every(item => item.identity === identity) &&
    repeated[0].fingerprint === repeated[1].fingerprint
  )
    throw new Error(
      'REPAIR_REPEAT: 相同输入连续两次同源失败，停止盲目重试；先修正诊断字段',
    );
}

export function recordRepairFailure(budget, phase, identity, error) {
  const category = repairCategory(phase);
  const diagnostics = (error.diagnostics || [])
    .filter(item => item.severity === 'error')
    .map(item => [item.code, item.path, item.keyword])
    .sort((left, right) =>
      JSON.stringify(left).localeCompare(JSON.stringify(right)),
    );
  const fingerprint = digest(
    JSON.stringify(
      diagnostics.length ? diagnostics : [error.code, error.message],
    ),
  );
  budget.failures[category]++;
  budget.recent.push({ category, identity, fingerprint });
  budget.recent = budget.recent.slice(-12);
}

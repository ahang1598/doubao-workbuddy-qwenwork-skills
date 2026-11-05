export function diagnoseFailure(report) {
  const diagnostics = report.error?.diagnostics || report.diagnostics || [];
  const codes = diagnostics
    .filter(item => item.severity !== 'info')
    .map(item => item.code);
  const message = [report.error?.message, ...(report.errors || [])]
    .filter(Boolean)
    .join('\n');
  const code =
    report.error?.code ||
    codes[0] ||
    message.match(/\b[A-Z][A-Z_]{4,}\b/)?.[0] ||
    'UNCLASSIFIED_FAILURE';
  const maintenance =
    /CONTRACT_VALIDATOR_STALE|UI_STOPS_CONTENT_MISMATCH|RUNTIME_.*MISSING|BLANK_CLEAR|STARTUP_CHECK_FAILED|RUNTIME_START_FAILED|VIEWPORT_ACCESS_FAILED|REGION_(NOT_HITTABLE|FILL_NOT_RENDERED|SELECTION_.*|CLEAR_NOT_RESTORED)/.test(
      [code, ...codes].join(' '),
    );
  const environment =
    /TIMEOUT|BUDGET|NETWORK|ASSET_|MODULE_NOT_FOUND|ENOTFOUND|ECONN|SDK_LOAD|RESOURCE_|BOOTSTRAP_LOAD/.test(
      code,
    );
  const input =
    diagnostics.some(item => item.severity === 'error') &&
    !maintenance &&
    !environment;
  const operationalAdvice = /BUDGET/.test(code)
    ? '读取 repairBudget 和失败历史；达到上限后由维护者排查，不能换目录、删记录或重复重试。'
    : /TIMEOUT|NETWORK|ENOTFOUND|ECONN|SDK_LOAD/.test(code)
      ? '核对报告中的失败阶段、资源地址和网络状态；保留现场，不重新搜索地点或改写输入来规避网络故障。'
      : /ASSET_|RESOURCE_|BOOTSTRAP_LOAD|MODULE_NOT_FOUND/.test(code)
        ? '由维护者核对报错资源的可达性、哈希、版本与依赖完整性；普通生成不替换 CDN、安装依赖或关闭检查。'
        : '保留具体错误及产物，由维护者定位；普通生成不修改实现或业务事实来迁就验收。';
  const failures = diagnostics.filter(item => item.severity === 'error');
  if (!failures.length) failures.push({ code, message: message || '未返回具体失败原因，请保留原始执行日志供维护者定位。' });
  return {
    code,
    owner: maintenance
      ? 'maintenance'
      : environment
        ? 'environment'
        : input
          ? 'input'
          : 'needs-triage',
    action: input ? 'repair-input' : 'stop-and-diagnose',
    issues: failures.map(item => ({
      code: item.code,
      path: item.path,
      reason: item.message,
      suggestion: item.suggestion || item.details?.suggestion || (input
        ? '依据该字段的具体原因和协议说明修正输入；不能定位时保留报告交由维护者，不读取实现代码。'
        : operationalAdvice),
    })),
    paths: [...new Set(diagnostics.map(item => item.path).filter(Boolean))],
    nextStep: input
      ? '按 issues 中的路径、原因和建议一次修正已报告的输入问题；仅仍需定位时使用离线预检，不读取或解包实现代码；输入、验收、资源失败分别计数，读取 workflow-report.repairBudget，不重置历史。'
      : operationalAdvice,
  };
}

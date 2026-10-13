export const REPORT_UPLOAD_FIELDS = ['file_path', 'task_id', 'project_name', 'room_name', 'environment', 'profile', 'account_id', 'dry_run'];
// 联调仅这两个复盘接口走 ST，原任务环境和其他质检接口不切换。
export const REPORT_UPLOAD_CONFIG = Object.freeze({
  baseUrls: Object.freeze({
    online: 'https://livesaas.volcengineapi.com/',
  }),
  action: 'UploadReport',
  fetchAction: 'GetReportDataForCLI',
  version: '2026-08-17',
  region: 'cn-north-1',
  services: Object.freeze({ online: 'live_saas_test' }),
});

export function resolveReportEnvironment(input = {}) {
  const { environment } = input;
  if (input.account_id !== undefined && (typeof input.account_id !== 'string' || !/^[0-9]{1,128}$/.test(input.account_id))) throw Object.assign(new Error('account_id must be a numeric account identifier'), { code: 'INVALID_INPUT', stage: 'input', retryable: false });
  const allowed = ['environment', 'profile', 'account_id', 'task_id', 'project_name', 'file_path', 'file_name', 'room_name', 'target', 'dry_run', 'output'];
  if (Object.keys(input).some(key => !allowed.includes(key)) || environment !== 'online') {
    throw Object.assign(new Error('The original task must use --environment online'), {
      code: 'INVALID_INPUT', stage: 'input', retryable: false,
    });
  }
  return 'online';
}

export function reportUploadEndpoint(environment) {
  if (!Object.hasOwn(REPORT_UPLOAD_CONFIG.baseUrls, environment)) {
    throw new Error('Unsupported report upload environment');
  }
  const url = new URL(REPORT_UPLOAD_CONFIG.baseUrls[environment]);
  url.searchParams.set('Action', REPORT_UPLOAD_CONFIG.action);
  url.searchParams.set('Version', REPORT_UPLOAD_CONFIG.version);
  return url.href;
}

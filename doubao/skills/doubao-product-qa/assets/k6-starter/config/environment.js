export function environment() {
  const baseUrl = (__ENV.QA_BASE_URL || '').replace(/\/$/, '')
  if (!baseUrl) throw new Error('必须显式设置 QA_BASE_URL')
  const method = (__ENV.QA_METHOD || 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && __ENV.QA_ALLOW_WRITES !== '1') {
    throw new Error('写请求需要在确认测试环境和清理策略后设置 QA_ALLOW_WRITES=1')
  }
  return {
    baseUrl,
    path: __ENV.QA_PATH || '/health',
    method,
    token: __ENV.QA_API_TOKEN || '',
    payload: __ENV.QA_PAYLOAD || '',
  }
}

function numberEnv(name) {
  const value = Number(__ENV[name])
  if (!Number.isFinite(value)) throw new Error(`缺少或无效阈值 ${name}`)
  return value
}

export function thresholds() {
  if (__ENV.QA_BASELINE_ONLY === '1') return {}
  const p95 = numberEnv('QA_P95_MS')
  const errorRate = numberEnv('QA_ERROR_RATE')
  const businessSuccess = numberEnv('QA_BUSINESS_SUCCESS_RATE')
  return {
    http_req_duration: [`p(95)<${p95}`],
    http_req_failed: [`rate<${errorRate}`],
    business_success: [`rate>${businessSuccess}`],
  }
}

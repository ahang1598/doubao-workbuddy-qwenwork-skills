import http from 'k6/http'
import { check, group, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

import { environment } from '../config/environment.js'

const businessSuccess = new Rate('business_success')
const businessDuration = new Trend('business_duration', true)
const env = environment()

export function apiFlow() {
  group('TC-PERF-API-001 核心接口', () => {
    const headers = { Accept: 'application/json' }
    if (env.token) headers.Authorization = `Bearer ${env.token}`
    if (env.payload) headers['Content-Type'] = 'application/json'
    const response = http.request(env.method, `${env.baseUrl}${env.path}`, env.payload || null, {
      headers,
      tags: { case_id: 'TC-PERF-API-001', business_flow: 'core_api' },
    })
    const ok = check(response, {
      '状态为 2xx': (value) => value.status >= 200 && value.status < 300,
      '响应体非空或为 204': (value) => value.status === 204 || value.body.length > 0,
    })
    businessSuccess.add(ok)
    businessDuration.add(response.timings.duration)
  })
  sleep(Number(__ENV.QA_THINK_TIME_SECONDS || '1'))
}

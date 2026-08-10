import { apiFlow } from './flows/api-flow.js'
import { environment } from './config/environment.js'
import { scenario } from './config/scenarios.js'
import { thresholds } from './config/thresholds.js'
import { markdownSummary } from './utils/summary.js'

const profile = __ENV.QA_PROFILE || 'smoke'
const env = environment()

export const options = {
  scenarios: { [profile]: { ...scenario(profile), exec: 'apiFlow' } },
  thresholds: thresholds(),
  summaryTimeUnit: 'ms',
  discardResponseBodies: false,
}

export { apiFlow }

export function handleSummary(data) {
  return {
    stdout: markdownSummary(data, { profile, baseUrl: env.baseUrl, baselineOnly: __ENV.QA_BASELINE_ONLY === '1' }),
    'artifacts/summary.json': JSON.stringify(data, null, 2),
    'artifacts/summary.md': markdownSummary(data, { profile, baseUrl: env.baseUrl, baselineOnly: __ENV.QA_BASELINE_ONLY === '1' }),
  }
}

const integer = (name, fallback) => Number.parseInt(__ENV[name] || String(fallback), 10)

export function scenario(profile) {
  const vus = integer('QA_VUS', 5)
  const rate = integer('QA_RATE', 5)
  const duration = __ENV.QA_DURATION || '1m'
  const ramp = __ENV.QA_RAMP || '30s'
  const profiles = {
    smoke: { executor: 'constant-vus', vus: integer('QA_VUS', 1), duration: __ENV.QA_DURATION || '30s' },
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [{ duration: ramp, target: vus }, { duration, target: vus }, { duration: ramp, target: 0 }],
      gracefulRampDown: '15s',
    },
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: ramp, target: vus },
        { duration, target: vus },
        { duration: ramp, target: vus * 2 },
        { duration, target: vus * 2 },
        { duration: ramp, target: 0 },
      ],
      gracefulRampDown: '15s',
    },
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [{ duration: '10s', target: vus }, { duration: '10s', target: vus * 5 }, { duration: '30s', target: vus * 5 }, { duration: ramp, target: 0 }],
    },
    soak: {
      executor: 'constant-arrival-rate',
      rate,
      timeUnit: '1s',
      duration: __ENV.QA_DURATION || '30m',
      preAllocatedVUs: vus,
      maxVUs: integer('QA_MAX_VUS', vus * 3),
    },
  }
  if (!profiles[profile]) throw new Error(`QA_PROFILE 只支持 ${Object.keys(profiles).join('/')}`)
  return profiles[profile]
}

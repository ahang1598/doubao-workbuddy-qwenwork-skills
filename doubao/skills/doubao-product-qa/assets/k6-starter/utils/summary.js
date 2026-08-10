function metricValue(metric, key) {
  return metric && metric.values && metric.values[key] !== undefined ? metric.values[key] : null
}

export function markdownSummary(data, context) {
  const metrics = data.metrics || {}
  const thresholdRows = Object.entries(metrics)
    .flatMap(([name, metric]) => Object.entries(metric.thresholds || {}).map(([rule, value]) => `| ${name} | ${rule} | ${value.ok ? '通过' : '失败'} |`))
  const thresholdFailed = Object.values(metrics).some((metric) => Object.values(metric.thresholds || {}).some((value) => !value.ok))
  return [
    '# k6 测试结果摘要',
    '',
    `- Profile：${context.profile}`,
    `- Base URL：${context.baseUrl}`,
    `- 模式：${context.baselineOnly ? '仅基线采样，不作达标结论' : '阈值门禁'}`,
    `- 结论：${context.baselineOnly ? '待建立 SLO' : thresholdFailed ? '未达到阈值' : '达到已配置阈值'}`,
    `- 请求数：${metricValue(metrics.http_reqs, 'count') ?? 'N/A'}`,
    `- 失败率：${metricValue(metrics.http_req_failed, 'rate') ?? 'N/A'}`,
    `- p95：${metricValue(metrics.http_req_duration, 'p(95)') ?? 'N/A'} ms`,
    `- 业务成功率：${metricValue(metrics.business_success, 'rate') ?? 'N/A'}`,
    '',
    '| 指标 | 阈值 | 结果 |',
    '|---|---|---|',
    ...(thresholdRows.length ? thresholdRows : ['| 未配置 | - | 仅采样 |']),
    '',
    '原始数据见 `summary.json`。上线判断还需关联服务端 CPU、内存、数据库、缓存、队列及错误日志。',
    '',
  ].join('\n')
}

const durationNote = '不含接口未提供的候机、等车和换乘等待时间';

function seconds(value) {
  if (value == null) return null;
  if (!Number.isFinite(value) || value < 0) throw new Error('路线分段耗时无效');
  return value;
}

export function formatDuration(value) {
  const duration = seconds(value);
  if (duration === null) return '未知';
  if (duration < 60) return '小于1分钟';
  const totalMinutes = Math.round(duration / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${duration % 60 ? '约' : ''}${hours ? `${hours}小时` : ''}${minutes ? `${minutes}分钟` : ''}`;
}

export function formatDistance(value) {
  if (value == null) return '未知';
  if (!Number.isFinite(value) || value < 0) throw new Error('路线距离无效');
  return value >= 1000
    ? `${Math.round(value / 100) / 10} 公里`
    : `${Math.round(value)} 米`;
}

// segments 与 steps 是同一行程的两种投影，只选一份累加，不能重复计时。
export function routePlanMetrics(route) {
  const segments = route.segments?.length ? route.segments : route.steps;
  const details = (segments || []).map((segment, index) => ({
    index,
    mode: segment.transit_mode || null,
    name: segment.transit?.name || segment.instruction || null,
    origin: segment.transit?.on_station?.name || null,
    destination: segment.transit?.off_station?.name || null,
    durationSeconds: seconds(segment.time),
    duration: formatDuration(segment.time),
    ...(Number.isFinite(segment.transit?.price) && segment.transit.price > 0
      ? { fare: segment.transit.price, currency: 'CNY' }
      : {}),
  }));
  const complete =
    details.length > 0 &&
    details.every(segment => segment.durationSeconds !== null);
  const knownDurationSeconds = details.reduce(
    (sum, segment) => sum + (segment.durationSeconds ?? 0),
    0,
  );
  return {
    segments: details,
    durationComplete: complete,
    durationSeconds: complete ? knownDurationSeconds : null,
    duration: complete ? formatDuration(knownDurationSeconds) : '合计不完整',
    knownDurationSeconds,
    knownDuration: details.some(segment => segment.durationSeconds !== null)
      ? formatDuration(knownDurationSeconds)
      : '未知',
    durationNote: complete
      ? durationNote
      : `分段耗时缺失，合计不完整；${durationNote}`,
    reportedDurationSeconds: seconds(route.time),
  };
}

export function routePlanDescription(entity, metrics) {
  // 保留路线概述，移除原耗时措辞；长步骤明细不再拼成另一份摘要。
  const description = (entity.simple_summary || entity.mode)
    .replace(/(?:总)?耗时[^，,；;。]*(?:[，,；;。]|$)/g, '')
    .trim();
  const duration = metrics.durationComplete
    ? `各段耗时合计${metrics.duration}`
    : `已知分段耗时${metrics.knownDuration}`;
  return `${description}；${duration}；${metrics.durationNote}`;
}

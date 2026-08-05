/*
个人健康管理报告的趋势分析辅助函数。
用于稳定计算百分比变化和基础趋势状态，避免每次手写计算逻辑。
*/

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function percentChange(first, last) {
  const a = finiteNumber(first);
  const b = finiteNumber(last);
  if (a === null || b === null || a === 0) return null;
  return ((b - a) / Math.abs(a)) * 100;
}

function classifyTrend(values, options = {}) {
  const nums = values.map(finiteNumber).filter((v) => v !== null);
  if (nums.length < 2) return '数据不足';
  const first = nums[0];
  const last = nums[nums.length - 1];
  const pct = percentChange(first, last);
  const minPct = options.minPct == null ? 5 : Number(options.minPct);
  if (pct !== null && Math.abs(pct) < minPct) return '基本稳定';
  const increasingSteps = nums.slice(1).filter((v, i) => v > nums[i]).length;
  const decreasingSteps = nums.slice(1).filter((v, i) => v < nums[i]).length;
  if (increasingSteps === nums.length - 1) return '持续上升';
  if (decreasingSteps === nums.length - 1) return '持续下降';
  if (last > first && pct >= minPct) return '总体上升';
  if (last < first && pct <= -minPct) return '总体下降';
  return '波动变化';
}

function abnormalState(value, low, high) {
  const v = finiteNumber(value);
  const lo = finiteNumber(low);
  const hi = finiteNumber(high);
  if (v === null) return '未知';
  if (lo !== null && v < lo) return '偏低';
  if (hi !== null && v > hi) return '偏高';
  return '正常';
}

if (typeof module !== 'undefined') {
  module.exports = {
    percentChange,
    classifyTrend,
    abnormalState
  };
}

#!/usr/bin/env node
/*
从健康证据表自动生成飞书图表助手 block JSON。

用法：
  node scripts/prepare-health-chart-blocks.js evidence.json > chart-blocks.json

输入可以是数组，也可以是 { "evidence": [...] }。
证据字段兼容 data-contract.md：
date, category, item_normalized, item_original, value_normalized,
unit_normalized, reference_range, abnormal_flag, confidence
*/

const fs = require('fs');
const file = process.argv[2];

if (!file) {
  console.error('用法：node prepare-health-chart-blocks.js <evidence.json>');
  process.exit(2);
}

const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
const evidence = Array.isArray(raw) ? raw : Array.isArray(raw.evidence) ? raw.evidence : [];

function toNumber(value) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value !== 'string') return null;
  const match = value.replace(/,/g, '').match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function parseReferenceLimit(range, direction) {
  if (!range || typeof range !== 'string') return null;
  const text = range.replace(/\s/g, '');
  if (direction === 'upper') {
    const match = text.match(/[<≤]\s*(\d+(?:\.\d+)?)/) || text.match(/(\d+(?:\.\d+)?)\s*[-~至]\s*(\d+(?:\.\d+)?)/);
    if (!match) return null;
    return Number(match[2] || match[1]);
  }
  if (direction === 'lower') {
    const match = text.match(/[>≥]\s*(\d+(?:\.\d+)?)/) || text.match(/(\d+(?:\.\d+)?)\s*[-~至]\s*(\d+(?:\.\d+)?)/);
    if (!match) return null;
    return Number(match[1]);
  }
  return null;
}

function parseReferenceBounds(range) {
  if (!range || typeof range !== 'string') return { lower: null, upper: null };
  const text = range.replace(/\s/g, '');
  const between = text.match(/(\d+(?:\.\d+)?)\s*[-~至]\s*(\d+(?:\.\d+)?)/);
  if (between) return { lower: Number(between[1]), upper: Number(between[2]) };
  return {
    lower: parseReferenceLimit(range, 'lower'),
    upper: parseReferenceLimit(range, 'upper')
  };
}

function isAbnormal(item) {
  const flag = String(item.abnormal_flag || item.status || '').toLowerCase();
  if (!flag) return false;
  return !['normal', '正常', '阴性', 'negative', ''].includes(flag);
}

function abnormalDirection(item) {
  const flag = String(item.abnormal_flag || item.status || '').toLowerCase();
  if (/low|↓|低|偏低|降低/.test(flag)) return '偏低';
  if (/high|↑|高|偏高|升高/.test(flag)) return '偏高';
  const bounds = parseReferenceBounds(item.reference_range);
  if (bounds.lower !== null && item.value < bounds.lower) return '偏低';
  if (bounds.upper !== null && item.value > bounds.upper) return '偏高';
  return '异常';
}

function deviationPercent(item) {
  const bounds = parseReferenceBounds(item.reference_range);
  if (bounds.lower !== null && item.value < bounds.lower && bounds.lower !== 0) {
    return Math.round(Math.abs((item.value - bounds.lower) / bounds.lower) * 1000) / 10;
  }
  if (bounds.upper !== null && item.value > bounds.upper && bounds.upper !== 0) {
    return Math.round(Math.abs((item.value - bounds.upper) / bounds.upper) * 1000) / 10;
  }
  return null;
}

function makeChartRecord(chart) {
  return {
    theme: 'fresh-blue-green-health',
    elements: [
      {
        type: 'chart',
        position: { x: 0, y: 0, width: 600, height: 360 },
        options: {
          chartType: chart.chartType,
          data: {
            type: 'standard',
            value: {
              columns: chart.columns,
              data: chart.data
            }
          },
          enableDataEdit: true
        }
      }
    ]
  };
}

function makeBlock(chart) {
  return {
    title: chart.title,
    insight: chart.insight,
    block: {
      block_type: 40,
      add_ons: {
        component_type_id: 'blk_64df3b277a87c002dafdc52b',
        record: JSON.stringify(makeChartRecord(chart))
      }
    }
  };
}

const usable = evidence
  .map((item) => {
    const date = item.date || item.report_date || item.check_date;
    const name = item.item_normalized || item.item_original || item.name;
    const value = toNumber(item.value_normalized ?? item.value_original ?? item.value);
    const unit = item.unit_normalized || item.unit_original || item.unit || '';
  const confidence = item.confidence || 'high';
    if (!date || !name || value === null || confidence === 'low') return null;
    return {
      ...item,
      date: String(date).slice(0, 10),
      name: String(name),
      value,
      unit,
      category: item.category || item.group || item.system || '未分组'
    };
  })
  .filter(Boolean);

const groups = new Map();
for (const item of usable) {
  const key = `${item.name}__${item.unit}`;
  if (!groups.has(key)) groups.set(key, []);
  groups.get(key).push(item);
}

const charts = [];

const abnormalItems = usable.filter(isAbnormal);
if (abnormalItems.length > 0) {
  const categoryCounts = new Map();
  for (const item of abnormalItems) {
    const category = item.category || '未分组';
    categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
  }

  charts.push({
    title: '异常指标分类分布',
    chartType: 'horizontalBar',
    columns: ['类别', '异常项数'],
    data: Array.from(categoryCounts.entries()).map(([category, count]) => ({
      类别: category,
      异常项数: count
    })),
    insight: `图表解读：本次检查共有 ${abnormalItems.length} 个异常数值指标，主要用于定位需要优先阅读的指标类别。该图不构成诊断，需结合症状、病史和医生判断。`
  });

  const deviationRows = abnormalItems
    .map((item) => ({
      指标: item.name,
      偏离程度: deviationPercent(item),
      方向: abnormalDirection(item)
    }))
    .filter((row) => row.偏离程度 !== null)
    .sort((a, b) => b.偏离程度 - a.偏离程度)
    .slice(0, 8);

  if (deviationRows.length > 0) {
    charts.push({
      title: '异常指标偏离程度',
      chartType: 'horizontalBar',
      columns: ['指标', '偏离程度', '方向'],
      data: deviationRows,
      insight: '图表解读：偏离程度用于辅助识别哪些指标与参考边界差距更大，但不同指标的临床意义不能直接横向等同，需结合医生判断。'
    });
  }
}

for (const [, rows] of groups) {
  const uniqueDates = new Set(rows.map((r) => r.date));
  if (uniqueDates.size < 2) continue;

  rows.sort((a, b) => a.date.localeCompare(b.date));
  const first = rows[0];
  const metricName = first.name;
  const valueField = first.unit ? `${metricName}(${first.unit})` : metricName;
  const upper = parseReferenceLimit(first.reference_range, 'upper');
  const lower = parseReferenceLimit(first.reference_range, 'lower');

  const columns = ['日期', valueField];
  if (upper !== null) columns.push('参考上限');
  if (lower !== null) columns.push('参考下限');

  const data = rows.map((r) => {
    const row = { 日期: r.date, [valueField]: r.value };
    if (upper !== null) row['参考上限'] = upper;
    if (lower !== null) row['参考下限'] = lower;
    return row;
  });

  const start = rows[0].value;
  const end = rows[rows.length - 1].value;
  const direction = end > start ? '升高' : end < start ? '下降' : '基本稳定';
  const abnormalHint = rows.some((r) => r.abnormal_flag && r.abnormal_flag !== 'normal') ? '，其中包含异常标记' : '';

  charts.push({
    title: `${metricName} 历年趋势`,
    chartType: 'line',
    columns,
    data,
    insight: `图表解读：${metricName} 从 ${rows[0].date} 到 ${rows[rows.length - 1].date} ${direction}${abnormalHint}。该图用于辅助理解趋势，具体风险需结合参考范围、病史和医生判断。`
  });
}

const blocks = charts.slice(0, 5).map(makeBlock);
process.stdout.write(JSON.stringify({ chart_count: blocks.length, blocks }, null, 2));
process.stdout.write('\n');

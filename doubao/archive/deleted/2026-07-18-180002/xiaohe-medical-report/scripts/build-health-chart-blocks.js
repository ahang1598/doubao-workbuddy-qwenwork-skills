#!/usr/bin/env node
/*
生成飞书图表助手 add-on block JSON。

用法：
  node scripts/build-health-chart-blocks.js charts.json > chart-blocks.json

输入格式：
{
  "charts": [
    {
      "title": "LDL-C 历年趋势",
      "chartType": "line",
      "columns": ["日期", "LDL-C", "参考上限"],
      "data": [
        { "日期": "2024-06-01", "LDL-C": 2.92, "参考上限": 3.4 }
      ],
      "insight": "图表解读：..."
    }
  ]
}
*/

const fs = require('fs');
const file = process.argv[2];

if (!file) {
  console.error('用法：node build-health-chart-blocks.js <charts.json>');
  process.exit(2);
}

const payload = JSON.parse(fs.readFileSync(file, 'utf8'));
const charts = Array.isArray(payload.charts) ? payload.charts : [];

function must(condition, message) {
  if (!condition) throw new Error(message);
}

function makeChartRecord(chart) {
  must(chart && typeof chart === 'object', 'chart 必须是对象');
  must(chart.title && typeof chart.title === 'string', 'chart.title 必填');
  must(chart.chartType && typeof chart.chartType === 'string', `${chart.title} 缺少 chartType`);
  must(Array.isArray(chart.columns) && chart.columns.length >= 2, `${chart.title} columns 至少 2 列`);
  must(Array.isArray(chart.data) && chart.data.length > 0, `${chart.title} data 不能为空`);

  return {
    theme: 'fresh-blue-green-health',
    elements: [
      {
        type: 'chart',
        position: { x: 0, y: 0, width: chart.width || 600, height: chart.height || 360 },
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

function makeChartBlock(chart) {
  return {
    title: chart.title,
    insight: chart.insight || '',
    block: {
      block_type: 40,
      add_ons: {
        component_type_id: 'blk_64df3b277a87c002dafdc52b',
        record: JSON.stringify(makeChartRecord(chart))
      }
    }
  };
}

try {
  const result = { blocks: charts.map(makeChartBlock) };
  process.stdout.write(JSON.stringify(result, null, 2));
  process.stdout.write('\n');
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

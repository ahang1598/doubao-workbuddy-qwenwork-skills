#!/usr/bin/env node
/*
Static validator for generated daily stock analysis HTML.
Current production version disables all K-line/chart modules.
Usage: node scripts/validate-report.js path/to/report.html
*/

const fs = require('fs');
const file = process.argv[2];

if (!file) {
  console.error('Usage: node validate-report.js <report.html>');
  process.exit(2);
}

const html = fs.readFileSync(file, 'utf8');
const styleBlock = (html.match(/<style[^>]*>([\s\S]*?)<\/style>/i) || [null, ''])[1];
const failures = [];
const stockCode = ((html.match(/class=["'][^"']*stock-code[^"']*["'][^>]*>\s*([^<]+?)\s*</i) || [null, ''])[1] || '').trim();
const isAshare = /(?:\.(?:SH|SZ|BJ)\b|^(?:SH|SZ|BJ)?\d{6}$)/i.test(stockCode);

function must(condition, message) {
  if (!condition) failures.push(message);
}

const chartForbidden = [
  /class=["'][^"']*market-chart-module/i,
  /class=["'][^"']*chart-tabs/i,
  /class=["'][^"']*tab-controls/i,
  /class=["'][^"']*kline-panels/i,
  /class=["'][^"']*chart-panel/i,
  /Price Action\s*\/\s*价格走势/i,
  /近期股价\s*K\s*线图/i,
  /window\.RECAP_CHART_DATA/i,
  /LightweightCharts/i,
  /KLineCharts/i,
  /CandlestickSeries/i,
  /HistogramSeries/i,
  /data-range=["'](?:today|oneMonth|threeMonth)["']/i,
  /<input[^>]+name=["']chart-range["']/i,
  /lightweight-charts/i,
  /klinecharts/i
];

must(html.trimStart().startsWith('<!DOCTYPE html>'), 'HTML must start with <!DOCTYPE html>');
must(html.trimEnd().endsWith('</html>'), 'HTML must end with </html>');
must(!/<script\b/i.test(html), 'Current version must not contain any script tag');
must(!/<script\s+src=/i.test(html), 'No external script src allowed');
must(!/<link\s+[^>]*stylesheet/i.test(html), 'No external stylesheet allowed');
must(!/<img\b/i.test(html), 'Images are not allowed in the report layout');
for (const pattern of chartForbidden) {
  must(!pattern.test(html), `Chart/K-line residue found: ${pattern}`);
}
must(!/(cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com)/i.test(html), 'External CDN references are not allowed');
must(!/(REDESIGN\s+OVERRIDES|晨报\s*v?\d|override\s+patch|dashboard_template|历史样式|改版补丁)/i.test(html), 'Historical CSS/template override marker found');
must(!/class=["'][^"']*(?:hero|news-card|timeline|hero-evidence|summary-card|dashboard-card|memo-card)[^"']*["']/i.test(html), 'Unsupported variable visual layout class found');

must(/header[^>]*class=["'][^"']*report-header/.test(html), 'report-header missing');
must(/class=["'][^"']*lead[^"']*["']/.test(html), 'lead paragraph missing');
must(/class=["'][^"']*metric-grid/.test(html), 'metric-grid missing');
const leadIndex = html.indexOf('class="lead"');
const metricIndex = html.indexOf('metric-grid');
const sectionOneIndex = html.indexOf('一、今日行情、量能与资金流向');
must(leadIndex >= 0 && metricIndex > leadIndex && sectionOneIndex > metricIndex, 'First screen order must be report-header -> lead -> metric-grid -> section one');

const reportHeaderStyle = (styleBlock.match(/\.report-header\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/display\s*:\s*block/.test(reportHeaderStyle), 'report-header must be block, not side-by-side grid');
must(!/grid-template-columns\s*:/.test(reportHeaderStyle), 'report-header must not use grid columns');
const metaBoxStyle = (styleBlock.match(/\.meta-box\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/text-align\s*:\s*left/.test(metaBoxStyle), 'meta-box must be left aligned');
must(!/报告类型|观点口径/.test(html), 'Header meta must only contain generated date');

const twoColStyle = (styleBlock.match(/\.two-col\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/grid-template-columns\s*:\s*1fr\s*;/.test(twoColStyle), 'two-col must stack vertically with one column');
must(!/@media[\s\S]*\.two-col[\s\S]*grid-template-columns\s*:\s*(?:1fr\s+1fr|repeat\s*\(\s*2|[0-9.]+fr\s+[0-9.]+fr)/i.test(styleBlock), 'media query must not turn two-col into side-by-side layout');
const technicalDashboardStyle = (styleBlock.match(/\.technical-dashboard\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/grid-template-columns\s*:\s*1fr\s*;/.test(technicalDashboardStyle), 'technical-dashboard must stack vertically with one column');
must(!/(--mono|var\(--mono\)|SFMono|Menlo|Consolas|monospace)/i.test(styleBlock), 'CSS must use one unified sans font family; mono fonts are forbidden');
must(/font-variant-numeric\s*:\s*tabular-nums/.test(styleBlock), 'tabular numeric alignment missing');

const inlineStyleTags = [...html.matchAll(/<([a-z0-9-]+)\b[^>]*\sstyle=["'][^"']+["'][^>]*>/gi)];
for (const match of inlineStyleTags) {
  const tag = match[0];
  const isPriceZoneDynamicStyle = /class=["'][^"']*(?:zone-range|zone-current|zone-edge)[^"']*["']/i.test(tag)
    && /style=["'][^"']*(?:left|width)\s*:/i.test(tag)
    && !/style=["'][^"']*(?:color|font-size|border|background|display|grid|flex|position)\s*:/i.test(tag);
  must(isPriceZoneDynamicStyle, `inline style only allowed for price-zone dynamic left/width: ${tag.slice(0, 120)}`);
}

for (const title of [
  '一、今日行情、量能与资金流向',
  '二、板块联动与个股地位',
  '三、技术面分析',
  '四、消息面与隔夜观察',
  '五、投行一致预期',
  '六、综合评级',
  '七、短期风险提示'
]) {
  must(html.includes(title), `${title} missing`);
}
must(!/六、综合评级与短期操作建议/.test(html), 'Old section 6 title must not be used');
must(!/空仓者|持仓者|短线参与者|仓位\s*\/\s*风控|止损|止盈/.test(html), 'Specific operation advice table/content must not be rendered');
must(/class=["'][^"']*metric-note[^"']*["'][^>]*>\s*注：以上行情摘要/.test(html), 'metric data as-of note missing below metric grid');
const metricNoteStyle = (styleBlock.match(/\.metric-note\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/font-size\s*:\s*11px/.test(metricNoteStyle) && /line-height\s*:\s*1\.55/.test(metricNoteStyle), 'metric-note must use fixed 11px / 1.55 style');
const changeMetric = html.match(/<div class=["'][^"']*metric[^"']*["'][\s\S]*?<div class=["']label["']>\s*涨跌幅\s*<\/div>[\s\S]*?<\/div>\s*<\/div>/);
must(!!changeMetric && /class=["']value\s+(positive|negative|neutral)["']/.test(changeMetric[0]), 'change metric value must use positive/negative/neutral class');
const metricGridBlock = (html.match(/<div[^>]*class=["'][^"']*metric-grid[^"']*["'][\s\S]*?(?=<p[^>]*class=["'][^"']*metric-note|<section)/i) || [''])[0];
const metricCitationCount = (metricGridBlock.match(/class=["'][^"']*cite-ref[^"']*["']/g) || []).length;
must(metricCitationCount >= 8, `each of the 8 summary metrics must carry a source citation, got ${metricCitationCount}`);

const fundFlowBlock = (html.match(/<table[^>]*class=["'][^"']*fund-flow-table[^"']*["'][\s\S]*?<\/table>/i) || [''])[0];
if (isAshare) {
  must(/资金类别[\s\S]{0,260}流向趋势[\s\S]{0,260}复盘含义/.test(html), 'A-share fund flow table header must use 流向趋势');
  must(!/>读数<\/th>|>读数<\/td>/.test(html), 'old fund flow header 读数 must not be used');
  must(/<table[^>]*class=["'][^"']*fund-flow-table[^"']*["']/.test(html), 'A-share fund flow table must use fund-flow-table class');
  must(/<table[^>]*class=["'][^"']*fund-flow-table[^"']*["'][\s\S]*?<colgroup>[\s\S]*?fund-col-category[\s\S]*?fund-col-trend[\s\S]*?fund-col-meaning[\s\S]*?<\/colgroup>/i.test(html), 'A-share fund flow table must include fixed colgroup');
  must((fundFlowBlock.match(/class=["'][^"']*cite-ref[^"']*["']/g) || []).length >= 3, 'A-share fund flow table must cite data sources in table cells');
} else {
  must(!/<table[^>]*class=["'][^"']*fund-flow-table[^"']*["']/i.test(html), 'Non-A-share reports must not render A-share fund-flow table');
  must(!/<h3>\s*资金流向\s*<\/h3>/i.test(html), 'Non-A-share reports must not render standalone 资金流向 subsection');
}
const consensusSection = (html.match(/五、投行一致预期[\s\S]*?(?=六、综合评级|<section[^>]*class=["'][^"']*section[^"']*["'][^>]*>\s*<h2>\s*六、|$)/i) || [''])[0];
const consensusBlock = (consensusSection.match(/<table[^>]*class=["'][^"']*consensus-table[^"']*["'][\s\S]*?<\/table>/i) || [''])[0];
const hasConsensusEmpty = /class=["'][^"']*consensus-empty[^"']*["']/i.test(consensusSection)
  || /暂未检索到可核验的(?:投行|券商).*?(?:覆盖|评级|目标价)记录/i.test(consensusSection);
must(!!consensusBlock || hasConsensusEmpty, 'section five must use either consensus-table or consensus-empty no-coverage explanation');
if (consensusBlock) {
  must(!hasConsensusEmpty, 'consensus section must not mix table and no-coverage explanation');
  must((consensusBlock.match(/class=["'][^"']*cite-ref[^"']*["']/g) || []).length >= 3, 'consensus table must cite forecast/estimate sources in table cells');
  const hasFinancialForecastHeader = /年份[\s\S]{0,220}归母净利润[\s\S]{0,220}营业总收入[\s\S]{0,220}每股收益[\s\S]{0,220}市盈率/.test(consensusBlock);
  const hasRatingTargetHeader = /机构名称[\s\S]{0,220}最新评级[\s\S]{0,220}目标价[\s\S]{0,220}日期/.test(consensusBlock);
  must(hasFinancialForecastHeader || hasRatingTargetHeader, 'consensus table must use either financial forecast header or broker rating/target-price header');
  must(!(hasFinancialForecastHeader && hasRatingTargetHeader), 'consensus table must not mix financial forecast and broker rating headers');
  must(!/未披露/.test(consensusBlock), 'consensus table must not use 未披露; use 暂无 for partial missing fields or consensus-empty when no coverage exists');
  const dataCells = [...consensusBlock.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map(m => m[1].replace(/<[^>]+>/g, '').replace(/\s+/g, ''));
  const missingCells = dataCells.filter(text => /^(暂无|未披露|-|—|NA|N\/A)$/i.test(text)).length;
  must(dataCells.length === 0 || missingCells / dataCells.length < 0.6, 'consensus table appears mostly empty; use consensus-empty no-coverage explanation instead');
} else {
  must(/class=["'][^"']*consensus-empty[^"']*["']/i.test(consensusSection), 'no-coverage consensus section must use consensus-empty class');
  must(!/<table\b/i.test(consensusSection), 'no-coverage consensus section must not render a table');
  must(/机会|预期发现|估值重估|关注度|定价效率/.test(consensusSection), 'no-coverage consensus explanation must discuss opportunity');
  must(/风险|外部验证|估值锚|流动性|信息透明度|波动/.test(consensusSection), 'no-coverage consensus explanation must discuss risk');
}
const thStyle = (styleBlock.match(/(?:^|\n)th\s*\{([\s\S]*?)\}/) || [null, ''])[1];
const tableStyle = (styleBlock.match(/(?:^|\n)table\s*\{([\s\S]*?)\}/) || [null, ''])[1];
const tdStyle = (styleBlock.match(/(?:^|\n)td\s*\{([\s\S]*?)\}/) || [null, ''])[1];
const allTablesBlock = (html.match(/<table[\s\S]*<\/table>/gi) || []).join('\n');
must(!/暂未获取可信(?:信息|来源|数据)?|暂未获取可验证|未取得可信|未能获取可信/i.test(allTablesBlock), 'table cells must use short placeholder 暂无 instead of long missing-data phrases');
const fundFlowColWidthStyle = (styleBlock.match(/\.fund-flow-table\s+\.fund-col-category,\s*\.fund-flow-table\s+\.fund-col-trend\s*\{([\s\S]*?)\}/) || [null, ''])[1];
const fundFlowCol12Style = (styleBlock.match(/\.fund-flow-table\s+td:nth-child\(1\),\s*\.fund-flow-table\s+td:nth-child\(2\),\s*\.fund-flow-table\s+td\.num\s*\{([\s\S]*?)\}/) || [null, ''])[1];
const fundFlowCol3Style = (styleBlock.match(/\.fund-flow-table\s+td:nth-child\(3\)\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/font-size\s*:\s*11px/.test(tableStyle), 'table base font-size must be 11px');
must(/font-size\s*:\s*11px/.test(thStyle) && /text-align\s*:\s*center/.test(thStyle), 'table header must be 11px and centered');
must(/font-size\s*:\s*11px/.test(tdStyle), 'table body td font-size must match header at 11px');
if (isAshare) {
  must(/width\s*:\s*82px/.test(fundFlowColWidthStyle), 'fund flow first two columns must be fixed at 82px');
  must(/text-align\s*:\s*center/.test(fundFlowCol12Style), 'fund flow first and second body columns must be centered');
  must(/text-align\s*:\s*left/.test(fundFlowCol3Style), 'fund flow third body column must be left aligned');
}

must(/class=["'][^"']*tech-indicator-table/.test(html), 'tech indicator table missing');
must(/class=["'][^"']*tech-indicator-head/.test(html), 'tech indicator head missing');
const techBlock = (html.match(/<div[^>]*class=["'][^"']*tech-indicator-table[^"']*["'][\s\S]*?(?=<\/div>\s*<\/div>|<h3|<section)/i) || [''])[0];
must((techBlock.match(/class=["'][^"']*cite-ref[^"']*["']/g) || []).length >= 3, 'MA/MACD/RSI rows must cite technical indicator sources');
const techHeadStyle = (styleBlock.match(/\.tech-indicator-head\s*\{([\s\S]*?)\}/) || [null, ''])[1];
const techCenterColsStyle = (styleBlock.match(/\.tech-indicator-row\s*>\s*div:nth-child\(1\),\s*\.tech-indicator-row\s*>\s*div:nth-child\(2\),\s*\.tech-indicator-row\s*>\s*div:nth-child\(4\)\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/font-size\s*:\s*11px/.test(techHeadStyle) && /text-align\s*:\s*center/.test(techHeadStyle) && /color\s*:\s*#2d2d2d/.test(techHeadStyle), 'tech indicator header must be black, 11px and centered');
must(/text-align\s*:\s*center/.test(techCenterColsStyle), 'tech indicator columns 1, 2 and 4 must be centered');
must(!/tech-signal-grid|tech-signal|tech-copy|tech-read|tech-desc|tech-badge/.test(html), 'old tech indicator structure must not appear');

must(/class=["'][^"']*risk-list[^"']*["']/.test(html), 'risk-list missing');
const riskItemCount = (html.match(/class=["'][^"']*risk-item/g) || []).length;
must(riskItemCount >= 3 && riskItemCount <= 5, `risk item count must be 3-5, got ${riskItemCount}`);
const riskSection = (html.match(/七、短期风险提示[\s\S]*?(?:<section|<footer|<\/main>)/) || [''])[0];
must(!/<ul\b|<ol\b|<li\b/.test(riskSection), 'risk section must not use bullet/numbered list markup');
const riskItemStyle = (styleBlock.match(/\.risk-item\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/font-size\s*:\s*14px/.test(riskItemStyle) && /line-height\s*:\s*1\.72/.test(riskItemStyle) && /margin\s*:\s*0\s+0\s+9px/.test(riskItemStyle), 'risk-item paragraph rhythm must match section body');

const priceZoneStyle = (styleBlock.match(/\.zone-range\s*\{([\s\S]*?)\}/) || [null, ''])[1]
  + (styleBlock.match(/\.zone-oscillation\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(/#d1d3d1/.test(priceZoneStyle) && /#9aa0a6/.test(priceZoneStyle), 'price-zone oscillation band must use fixed gray colors');
must(!/linear-gradient|radial-gradient/.test(styleBlock), 'price-zone gradients are forbidden');
must(!/zone-support|zone-pressure|zone-bound|zone-level/.test(html), 'support/pressure markers must not appear on price-zone chart');

must(/<section[^>]*class=["'][^"']*section[^"']*source-note[^"']*["'][^>]*id=["']sources["'][\s\S]*<h2>\s*信息来源\s*<\/h2>/.test(html), 'information sources section missing');
must(!/<h2>\s*数据与口径说明\s*<\/h2>/.test(html), 'old 数据与口径说明 title must not be used');
must(/class=["'][^"']*cite-ref[^"']*["']/.test(html), 'body citation superscripts missing');
must(/class=["'][^"']*source-list[^"']*["']/.test(html), 'source-list missing');
const sourceListStyle = (styleBlock.match(/\.source-list\s*\{([\s\S]*?)\}/) || [null, ''])[1];
must(!/border-top\s*:/.test(sourceListStyle), 'source-list must not have top border');
must(/\.source-row:last-child\s*\{[^}]*border-bottom\s*:\s*0/.test(styleBlock), 'source-row:last-child border-bottom reset missing');

const sourceIdMatches = [...html.matchAll(/class=["'][^"']*source-row[^"']*["'][^>]*id=["'](source-\d+)["']/g)];
must(sourceIdMatches.length > 0, 'source rows missing');
const sourceIds = new Set(sourceIdMatches.map((row) => row[1]));
for (let i = 0; i < sourceIdMatches.length; i += 1) {
  const id = sourceIdMatches[i][1];
  const start = sourceIdMatches[i].index;
  const nextRow = i + 1 < sourceIdMatches.length ? sourceIdMatches[i + 1].index : -1;
  const nextSection = html.indexOf('<section', start + 1);
  const end = nextRow !== -1 ? nextRow : (nextSection !== -1 ? nextSection : html.length);
  const fullRow = html.slice(start, end === -1 ? html.length : end);
  must(/class=["'][^"']*source-index[^"']*["']/.test(fullRow), `${id} source-index missing`);
  must(/class=["'][^"']*source-name[^"']*["']/.test(fullRow), `${id} source-name missing`);
  must(/class=["'][^"']*source-date[^"']*["']/.test(fullRow), `${id} source-date missing`);
  must(/class=["'][^"']*source-title[^"']*["']/.test(fullRow), `${id} source-title missing`);
  const link = fullRow.match(/<a\b[^>]*class=["'][^"']*source-link[^"']*["'][^>]*href=["']([^"']+)["'][^>]*>\s*打开原文\s*<\/a>/i);
  must(Boolean(link), `${id} source-link 打开原文 missing or not an anchor`);
  if (link) {
    const href = link[1].trim();
    must(/^https?:\/\//i.test(href), `${id} source-link must be a real external http(s) URL`);
    must(!/^(#|javascript:|about:blank$)/i.test(href), `${id} source-link fake href not allowed`);
    must(!/(?:verified-data-pack|核验材料包|本地材料|用户提供材料|\.txt)/i.test(href), `${id} source-link must not point to local verification materials`);
    must(!/(?:search|s\?wd=|query=|q=)[^\/]*$/i.test(href), `${id} source-link must not be a search result placeholder`);
  }
  must(!/(?:本地核验材料包|本地材料|用户提供材料包|verified-data-pack|\.txt)/i.test(fullRow), `${id} must not use local verification materials as information source`);
  must(!/<span\b[^>]*class=["'][^"']*source-link[^"']*["'][^>]*>\s*打开原文\s*<\/span>/i.test(fullRow), `${id} 打开原文 must not be plain text`);
}
const citationRefs = [...html.matchAll(/<a[^>]*class=["'][^"']*cite-ref[^"']*["'][^>]*href=["']#(source-\d+)["'][^>]*>\s*\[\d+\]\s*<\/a>/g)].map((match) => match[1]);
must(citationRefs.length > 0, 'cite-ref href targets missing');
for (const id of new Set(citationRefs)) {
  must(sourceIds.has(id), `citation target ${id} missing in sources`);
}
const sourcesSection = (html.match(/<section[^>]*id=["']sources["'][\s\S]*?(?=<section[^>]*class=["'][^"']*section[^"']*source-note[^"']*disclaimer-note)/) || [''])[0];
must(!/<p>\s*说明[:：]/.test(sourcesSection), 'information sources section must not include explanatory note paragraph');
must(!/href=["']\s*(?:#|javascript:void\(0\)|)\s*["']/i.test(html), 'fake/empty href not allowed');

must(/class=["'][^"']*section[^"']*source-note[^"']*disclaimer-note[^"']*["'][\s\S]*<h2>\s*免责声明\s*<\/h2>/.test(html), 'disclaimer must be a standalone source-note section');
must(!/<footer[^>]*class=["'][^"']*disclaimer/.test(html), 'old footer disclaimer must not be used');
must(!/<strong>\s*免责声明[:：]\s*<\/strong>/.test(html), 'disclaimer title must not be inline strong text');
must(/以上内容为AI自动生成或AI辅助生成，仅用于信息整理、投研辅助、教育交流或一般性分析参考/.test(html), 'disclaimer paragraph 1 missing');
must(/以上内容可能基于公开信息、历史数据或用户提供材料进行总结、归纳、推演与情景分析/.test(html), 'disclaimer paragraph 2 missing');
must(/用户应基于自身风险承受能力、投资目标、财务状况及适用法律法规独立作出判断/.test(html), 'disclaimer paragraph 3 missing');

if (failures.length) {
  console.error(`Validation failed (${failures.length}):`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Validation passed');

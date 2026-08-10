import fs from 'node:fs';
import path from 'node:path';
import { globSync } from '../lib/simple-glob.mjs';
import { prepareQualityScanSurface, locateQualityReference } from '../lib/quality-runtime.mjs';

const DEFAULT_THRESHOLDS = Object.freeze({
  core: { s3RatioMax: 10, s6SemicolonDensityMax: 2, p1MaxIssues: 1, p2MinRatio: 0.1, b0MaxDuplicates: 0, b2MinDensity: 1 },
  ops: { s3RatioMax: 15, s6SemicolonDensityMax: 3, p1MaxIssues: 2, p2MinRatio: 0.05, b0MaxDuplicates: 1, b2MinDensity: 1 },
  ledger: { s3RatioMax: 18, s6SemicolonDensityMax: 4, p1MaxIssues: 4, p2MinRatio: 0, b0MaxDuplicates: 999, b2MinDensity: 0.8 },
  standard: { s3RatioMax: 10, s6SemicolonDensityMax: 2, p1MaxIssues: 2, p2MinRatio: 0.05, b0MaxDuplicates: 0, b2MinDensity: 1 },
});

const ADVERBS = ['甚', '甚为', '格外', '相当', '特别', '尤其', '前所未有', '全面地', '深刻地', '极大地', '广泛', '深度', '高度', '极其', '完全', '彻底', '根本性', '大幅', '显著', '非常', '充分', '深入'];
const PROTECTED = ['高度复杂', '高度专业', '高度不确定', '深度专注', '深度思考', '深度参与', '深度积累', '深度专家', '深度整合', '深度分析', '深度研究', '深度理解', '深度工作', '深度阅读', '深度学习'];
const CONNECTORS = ['在此基础上', '此时', '总而言之', '所以', '因此', '由此可见', '总的来说', '需要指出的是', '值得注意的是', '不难看出', '综上所述', '而且', '再者', '其次', '同时', '另外', '此外'];

function plainObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function loadJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function thresholdsFor(bundleRoot) {
  const candidates = [path.join(bundleRoot, 'references', 'source-policy.json'), path.join(process.cwd(), 'references', 'source-policy.json')];
  for (const file of candidates) {
    const configured = loadJson(file)?.qualityAuditProfiles?.thresholds;
    if (!plainObject(configured)) continue;
    return Object.fromEntries(Object.entries(DEFAULT_THRESHOLDS).map(([profile, defaults]) => [
      profile, { ...defaults, ...(plainObject(configured[profile]) ? configured[profile] : {}) },
    ]));
  }
  return DEFAULT_THRESHOLDS;
}

function buzzwordsFor(bundleRoot) {
  const terms = loadJson(locateQualityReference(bundleRoot, 'cliche-catalog.json'))?.terms;
  return Array.isArray(terms) && terms.length > 0 ? terms : ['中台', '体系化', '赋能', '颗粒度', '组合拳', '全链路', '底层能力'];
}

function profileFor(file) {
  const normalized = file.replace(/\\/g, '/').toLowerCase();
  if (normalized.includes('/.doubao-book-writer/') || normalized.endsWith('/chapter-ledger.md') || normalized.includes('/internal-memo-')) return 'ledger';
  if (normalized.endsWith('/skill.md')) return 'core';
  if (normalized.includes('/references/') && /(volume-tiers|source-policy)\.json$/.test(normalized)) return 'ops';
  if (normalized.includes('/references/')) return 'core';
  return 'standard';
}

function proseFrom(raw) {
  return String(raw)
    .replace(/^---[\s\S]*?---\s*/m, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1');
}

function cv(values) {
  if (values.length === 0) return 0;
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  if (mean === 0) return 0;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance) / mean;
}

function firstLine(lines) {
  for (let index = 0; index < lines.length; index += 1) {
    const text = lines[index].trim();
    if (!text || text === '---' || /^\|.*\|$/.test(text) || text.startsWith('>')) continue;
    const cleaned = text.replace(/^#{1,6}\s+|^[-*+]\s+|^\d+\.\s+/g, '').replace(/`[^`]*`|[*_~]/g, '').trim();
    if (cleaned) return { line: index + 1, text: cleaned };
  }
  return { line: 1, text: '' };
}

function longSentences(content) {
  const prose = content.replace(/^\s*(?:\|.*\||#{1,6}\s+.*|[-*+]\s+.*|\d+\.\s+.*)$/gm, '').replace(/`[^`]*`/g, '');
  const pieces = prose.split(/[。！？；;：:\n]/).flatMap((sentence) => sentence.length > 45 ? sentence.split(/[，,]/) : [sentence]).map((item) => item.trim()).filter(Boolean);
  const longCount = pieces.filter((item) => item.length > 40).length;
  const ratio = pieces.length === 0 ? 0 : longCount * 100 / pieces.length;
  return { passed: ratio < 10, ratio: Number(ratio.toFixed(2)), longCount, total: pieces.length };
}

function occurrences(content, terms) {
  return Object.fromEntries(terms.map((term) => [term, content.split(term).length - 1]).filter(([, count]) => count > 0));
}

function paragraphIssue(paragraph, index) {
  const text = paragraph.trim();
  if (text.length < 80 || /^[-*>#]|^\d+\.|^\|.*\|$|^```/.test(text)) return null;
  const lead = text.split(/[。！？]/)[0] || text;
  const concreteLeadTokens = '\\u65f6\\u95f4\\u5730\\u70b9\\u4eba\\u7269\\u573a\\u666f\\u95ee\\u9898\\u76ee\\u6807\\u7528\\u6237\\u6d41\\u7a0b\\u7b56\\u7565\\u4efb\\u52a1';
  return new RegExp(`[？?：:${concreteLeadTokens}]`).test(lead) ? null : `段落${index + 1}: ${lead.slice(0, 30)}...`;
}

function sectionsAndParagraphs(content) {
  return {
    lines: content.split('\n'),
    paragraphs: content.split(/\n\s*\n+/).map((item) => item.trim()).filter(Boolean),
    sections: content.split(/^##/m).map((item) => item.trim()).filter(Boolean),
  };
}

function inspectContent(content, buzzwords) {
  const { lines, paragraphs, sections } = sectionsAndParagraphs(content);
  let adverbText = content;
  for (const phrase of PROTECTED) adverbText = adverbText.replaceAll(phrase, '');
  const adverbIssues = Object.entries(occurrences(adverbText, ADVERBS)).map(([term, count]) => `${term}(${count})`);
  const connectorHits = occurrences(content, CONNECTORS);
  const compactLength = Math.max(content.replace(/\s+/g, '').length / 1000, 1);
  const connectorTotal = Object.values(connectorHits).reduce((sum, count) => sum + count, 0);
  const punctuation = content.match(/[，。；：！？、“”"'（）【】《》……]/g) ?? [];
  const headings = content.match(/^#+\s+.*$/gm) ?? [];
  const ids = headings.map((heading) => heading.match(/^#+\s+(\d+(?:\.\d+)*\.?)\b/)?.[1]?.replace(/\.$/, '')).filter(Boolean);
  const zhNumerals = '\\u4e00\\u4e8c\\u4e09\\u56db\\u4e94\\u516d\\u4e03\\u516b\\u4e5d\\u5341\\u767e';
  const formulaPatterns = [
    new RegExp(`^#{1,3}\\s+第[${zhNumerals}\\d]+章`),
    new RegExp('^#{1,3}\\s+(\\u5982\\u4f55|\\u600e\\u4e48|\\u600e\\u6837)'),
    new RegExp('^#{1,3}\\s+\\d+\\s*(\\u4e2a|\\u79cd|\\u6761|\\u6b65|\\u5927|\\u9879)'),
    new RegExp('^#{1,3}\\s+(\\u672c\\u7ae0\\u5c0f\\u7ed3|\\u672c\\u8282\\u5c0f\\u7ed3|\\u5c0f\\u8282\\u603b\\u7ed3|\\u603b\\u7ed3|\\u5c0f\\u7ed3)\\s*$'),
  ];
  const formulaic = headings.filter((heading) => formulaPatterns.some((pattern) => pattern.test(heading))).map((heading) => heading.replace(/^#+\s+/, ''));
  const paragraphLengths = paragraphs.map((item) => item.length);
  const sectionLengths = sections.map((item) => item.length);
  const leads = sections.map((section) => section.split('\n').find((line) => line.trim() && !line.trim().startsWith('#'))?.trim().slice(0, 5)).filter(Boolean);
  const duplicateLeads = leads.length - new Set(leads).size;
  const p1Issues = paragraphs.map(paragraphIssue).filter(Boolean);
  const quoteCount = (content.match(/[“”"「」『』]/g) ?? []).length + (content.match(/`[^`]+`/g) ?? []).length;
  const tail = content.split(/[。！？\n]/).map((item) => item.trim()).filter(Boolean).slice(-3).join('');
  const imageCount = (content.match(/!\[[^\]]*\]\([^\)]+\)|<img\b[^>]*>/g) ?? []).length;
  const mermaidCount = (content.match(/```mermaid[\s\S]*?```/g) ?? []).length;
  const tableBlocks = lines.reduce((count, line, index) => count + (/^\s*\|.*\|\s*$/.test(line) && !/^\s*\|.*\|\s*$/.test(lines[index - 1] ?? '') ? 1 : 0), 0);
  const visualCount = imageCount + mermaidCount + tableBlocks;
  const sentenceStarts = content.split(/[。！？]/).map((item) => item.trim()).filter((item) => item.length > 28 && !/^[-*#>|`]/.test(item)).map((item) => item.slice(0, 6));
  const bridgeStart = new RegExp('^(?:\\u6b64\\u5916|\\u53e6\\u5916|\\u540c\\u65f6|\\u603b\\u7684\\u6765\\u8bf4|\\u6362\\u8a00\\u4e4b|\\u4e5f\\u5c31\\u662f)', 'u');
  const repeatedStart = sentenceStarts.some((start, index) => start === sentenceStarts[index + 1] && start === sentenceStarts[index + 2]);
  const numbers = content.match(/\d+/g) ?? [];
  const percentages = content.match(/\d+%/g) ?? [];
  const longStats = longSentences(content);
  return {
    S: {
      S1: { passed: new RegExp(`[${'\\u4eba\\u7269\\u573a\\u666f\\u6570\\u636e\\u95ee\\u9898\\u76ee\\u6807\\u7528\\u6237\\u6d41\\u7a0b\\u7b56\\u7565\\u4efb\\u52a1\\u7ae0\\u8282\\u7248\\u672c\\u8bf4\\u660e'}]`).test(firstLine(lines).text) || firstLine(lines).text.length >= 10, line: firstLine(lines).line },
      S2: { passed: adverbIssues.length === 0, issues: adverbIssues },
      S3: longStats,
      S4: { passed: connectorTotal / compactLength < 2, found: connectorHits, total: connectorTotal, density: Number((connectorTotal / compactLength).toFixed(2)) },
      S5: { passed: !buzzwords.some((term) => content.includes(term)), issues: buzzwords.filter((term) => content.includes(term)) },
      S6: { passed: (content.match(/——/g) ?? []).length / compactLength <= 1 && (content.match(/；/g) ?? []).length / compactLength <= 2 && (content.match(/！/g) ?? []).length <= 2, dashCount: (content.match(/——/g) ?? []).length, semicolonCount: (content.match(/；/g) ?? []).length, exclamationCount: (content.match(/！/g) ?? []).length, dashDensity: Number(((content.match(/——/g) ?? []).length / compactLength).toFixed(2)), semicolonDensity: Number(((content.match(/；/g) ?? []).length / compactLength).toFixed(2)) },
    },
    P: {
      P1: { passed: p1Issues.length <= 2, issues: p1Issues },
      P2: { passed: quoteCount / compactLength >= 0.6, ratio: Number((quoteCount / compactLength).toFixed(2)) },
      P3: { passed: !repeatedStart },
      P4: { passed: !paragraphs.some((item) => bridgeStart.test(item) && item.length < 60), issues: paragraphs.map((item, index) => bridgeStart.test(item) && item.length < 60 ? `段落${index + 1}: 疑似过渡注水` : null).filter(Boolean) },
    },
    C: {
      C1: (() => { const passed = content.trim().length < 100 || ['前提是', '目前', '可能', '尚未', '有待', '不足', '局限', '不过', '然而', '但是'].some((term) => content.includes(term)); return { passed, note: passed ? 'limitation or qualification found' : 'no limitation/qualification detected' }; })(),
      C2: (() => { const passed = ['完成', '实施', '执行', '接下来', '下一步', '需要', '建议', '应该', '可以'].some((term) => tail.includes(term)); return { passed, note: passed ? 'action-oriented ending found' : 'ending lacks actionable direction' }; })(),
      C3: { passed: sections.length <= 1 || cv(sectionLengths) >= 0.3, cv: Number(cv(sectionLengths).toFixed(2)) },
      C4: { passed: percentages.length / Math.max(numbers.length, 1) * 100 <= 20, ratio: Number((percentages.length / Math.max(numbers.length, 1) * 100).toFixed(2)) },
    },
    B: {
      B0: { passed: ids.length === new Set(ids).size, duplicates: ids.length - new Set(ids).size },
      B1: { passed: headings.length <= 2 || formulaic.length <= 1, formulaic, count: formulaic.length },
      B2: { passed: paragraphs.length <= 1 || cv(paragraphLengths) >= 0.3, cv: Number(cv(paragraphLengths).toFixed(2)) },
      B4: { passed: new Set(punctuation).size / compactLength >= 1, density: Number((new Set(punctuation).size / compactLength).toFixed(2)), uniqueCount: new Set(punctuation).size },
      B5: { passed: leads.length <= 2 || duplicateLeads / leads.length <= 0.3, similarity: Number((leads.length ? duplicateLeads / leads.length : 0).toFixed(2)), duplicateLeads },
      B3: { passed: paragraphs.length <= 2 || cv(paragraphLengths) >= 0.4, cv: Number(cv(paragraphLengths).toFixed(2)) },
      V1: { passed: visualCount / Math.max(content.replace(/\s+/g, '').length / 5000, 1) >= 1, imageCount, mermaidCount, tableBlocks, visualCount, densityPer5k: Number((visualCount / Math.max(content.replace(/\s+/g, '').length / 5000, 1)).toFixed(2)) },
    },
  };
}

function applyThresholds(details, profile, thresholds) {
  const rule = thresholds[profile] ?? thresholds.standard;
  details.S.S3.passed = details.S.S3.ratio <= rule.s3RatioMax;
  details.S.S6.passed = details.S.S6.dashDensity <= 1 && details.S.S6.semicolonDensity <= rule.s6SemicolonDensityMax && details.S.S6.exclamationCount <= 2;
  details.P.P1.passed = details.P.P1.issues.length <= rule.p1MaxIssues;
  details.P.P2.passed = details.P.P2.ratio >= rule.p2MinRatio;
  details.B.B0.passed = details.B.B0.duplicates <= rule.b0MaxDuplicates;
  details.B.B4.passed = details.B.B4.density >= rule.b2MinDensity;
  return details;
}

function layerScore(layer, keys = Object.keys(layer)) {
  return Number((keys.filter((key) => layer[key]?.passed).length * 10 / Math.max(keys.length, 1)).toFixed(1));
}

export function auditQualityFile(filePath, options = {}) {
  const bundleRoot = options.bundleRoot;
  const profile = profileFor(filePath);
  const content = proseFrom(fs.readFileSync(filePath, 'utf8'));
  const details = applyThresholds(inspectContent(content, options.buzzwords ?? buzzwordsFor(bundleRoot)), profile, options.thresholds ?? thresholdsFor(bundleRoot));
  const scores = { S: layerScore(details.S), P: layerScore(details.P), C: layerScore(details.C), B: layerScore(details.B, ['B0', 'B1', 'B2', 'B4', 'B5', 'B3']), V1: details.B.V1.passed ? 10 : 0 };
  scores.total = scores.converted = scores.overall = Number(((scores.S + scores.P + scores.C + scores.B) / 4).toFixed(1));
  const min = Number(options.minScore || 7.5);
  return { filePath, profile, scoringVersion: 'equal-weight-4layer-10', scores, threshold: { min, passed: scores.overall >= min }, gGate: { status: 'needs_human_review' }, details };
}

export function summarizeQualityResults(results, minScore) {
  const passed = results.filter((item) => item.threshold?.passed).length;
  const scored = results.filter((item) => item.scores);
  return { timestamp: new Date().toISOString(), scoringVersion: 'equal-weight-4layer-10', minScore, total: results.length, passed, failed: results.length - passed, avgScore: Number((scored.reduce((sum, item) => sum + item.scores.overall, 0) / Math.max(scored.length, 1)).toFixed(2)), results };
}

function parseCli(argv, defaultBundleRoot) {
  const args = { bundleRoot: defaultBundleRoot, workspace: process.cwd(), files: [], glob: null, minScore: 7.5, json: false, quiet: false, failFast: false, standalone: false, jsonOut: null };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--inputs') args.files.push(...String(argv[++index] || '').split(',').map((item) => item.trim()).filter(Boolean));
    else if (token === '--input') args.files.push(argv[++index]);
    else if (token === '--glob') args.glob = argv[++index];
    else if (token === '--min-score') args.minScore = Number(argv[++index] || args.minScore);
    else if (token === '--json') args.json = true;
    else if (token === '--quiet') args.quiet = true;
    else if (token === '--fail-fast') args.failFast = true;
    else if (token === '--standalone') args.standalone = true;
    else if (token === '--bundle-root') args.bundleRoot = argv[++index] || args.bundleRoot;
    else if (token === '--workspace') args.workspace = argv[++index] || args.workspace;
    else if (token === '--json-out') args.jsonOut = argv[++index] || null;
    else if (token === '--inputs-file') args.inputsFile = argv[++index] || null;
    else if (!token.startsWith('--')) args.files.push(token);
  }
  args.bundleRoot = path.resolve(args.bundleRoot);
  args.workspace = path.resolve(args.workspace);
  return args;
}

function inputFiles(args) {
  const files = new Set(args.files.map((file) => path.resolve(args.workspace, file)));
  if (args.inputsFile && fs.existsSync(path.resolve(args.inputsFile))) {
    fs.readFileSync(path.resolve(args.inputsFile), 'utf8').split(/\r?\n/).map((line) => line.trim()).filter(Boolean).forEach((file) => files.add(path.resolve(file)));
  }
  if (args.glob) globSync(args.glob, { cwd: args.workspace, absolute: true }).forEach((file) => files.add(file));
  return [...files].filter((file) => fs.existsSync(file));
}

function writeMemorySummary(args, summary) {
  const reports = path.join(args.workspace, '.doubao-book-writer', 'reports');
  try {
    fs.mkdirSync(reports, { recursive: true });
    const taskId = `bk-score-${Date.now()}`;
    const p0Count = summary.results.filter((item) => !item.threshold?.passed && (item.scores?.overall || 0) < 5).length;
    const meta = { taskId, conclusion: summary.failed === 0 ? 'passed' : `failed(${summary.failed}/${summary.total})`, p0Count, p1Count: summary.failed - p0Count, total: summary.total, avgScore: summary.avgScore, reportPath: summary.reportPath || '' };
    fs.writeFileSync(path.join(reports, `score-summary-${taskId}.md`), `<!-- BK_SCORE_META ${JSON.stringify(meta)} -->\n# score-engine summary\n\n- taskId: ${taskId}\n- conclusion: ${meta.conclusion}\n- p0BelowFive: ${meta.p0Count}\n- p1Failed: ${meta.p1Count}\n- files: ${meta.total}\n- avgScore: ${meta.avgScore}\n- reportPath: ${meta.reportPath || '(none)'}\n- generatedAt: ${summary.timestamp}\n`, 'utf8');
  } catch {
    // Memory persistence is supplementary and must not replace the primary report.
  }
}

export function runQualityScoreCli(argv, defaultBundleRoot) {
  const args = parseCli(argv, defaultBundleRoot);
  const files = inputFiles(args);
  if (files.length === 0) {
    console.error('Usage: node scripts/quality/quality-score-engine.mjs <file.md> [--inputs a.md,b.md] [--glob "**/*.md"] [--workspace .] [--bundle-root .] [--standalone] [--min-score 7.5] [--json]');
    return 2;
  }
  const bootstrap = args.standalone || !fs.existsSync(path.join(args.workspace, '.doubao-book-writer'));
  const runtime = bootstrap ? prepareQualityScanSurface(args.workspace, { files }) : null;
  const shared = { minScore: args.minScore, bundleRoot: args.bundleRoot, thresholds: thresholdsFor(args.bundleRoot), buzzwords: buzzwordsFor(args.bundleRoot) };
  const results = [];
  for (const file of [...new Set(files.map((item) => path.resolve(item)))]) {
    const result = auditQualityFile(file, shared);
    results.push(result);
    if (!args.quiet) console.log(`\n[quality] ${result.filePath}\n  综合: ${result.scores.overall}/10 ${result.threshold.passed ? '✅' : '❌'} | S ${result.scores.S} / P ${result.scores.P} / C ${result.scores.C} / B ${result.scores.B}`);
    if (args.failFast && !result.threshold.passed) break;
  }
  const summary = summarizeQualityResults(results, args.minScore);
  if (runtime || args.jsonOut) {
    const report = path.resolve(args.jsonOut || path.join(args.workspace, 'qc-output', 'score-summary.json'));
    fs.mkdirSync(path.dirname(report), { recursive: true });
    fs.writeFileSync(report, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
    summary.reportPath = report;
  }
  writeMemorySummary(args, summary);
  if (args.json) console.log(JSON.stringify(summary, null, 2));
  else console.log(`\n[quality] 汇总: total=${summary.total}, passed=${summary.passed}, failed=${summary.failed}, avg=${summary.avgScore}/10`);
  return summary.failed > 0 ? 1 : 0;
}

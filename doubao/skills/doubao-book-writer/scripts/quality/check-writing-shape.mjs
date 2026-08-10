#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { globSync } from '../lib/simple-glob.mjs';

const ARABIC_HEADING_PATTERNS = [
  /^第\s*\d+\s*[章节篇卷部]/,
  /^\d+(?:\.\d+)+(?:[、.．]\s*|\s+)/,
  /^\d+[、.．]\s*\S/,
  /^[（(]\d+[）)]\s*\S/,
];
const CHINESE_NUMERAL = '\u96f6\u3007\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07\u4e24\u5eff\u5345';
const BASIC_NUMERAL = '\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e';
const CONNECTOR_TERMS = Object.freeze([
  '\u9700\u8981\u6307\u51fa\u7684\u662f',
  '\u503c\u5f97\u6ce8\u610f\u7684\u662f',
  '\u603b\u7684\u6765\u8bf4',
  '\u7efc\u4e0a\u6240\u8ff0',
  '\u7efc\u4e0a',
  '\u540c\u65f6',
  '\u53e6\u5916',
  '\u6b64\u5916',
  '\u6700\u540e',
  '\u518d\u6b21',
  '\u5176\u6b21',
  '\u9996\u5148',
]);
const CONNECTOR_GROUP = CONNECTOR_TERMS.join('|');
const FORBIDDEN_SECTION_HEADING_RE = new RegExp(`^第[${CHINESE_NUMERAL}]+节(?:\\s|$)`, 'u');
const DECORATIVE_CALLOUT_RE = /^>\s*\[![A-Z][A-Z0-9_-]*\]/iu;
const COLLAPSIBLE_BLOCK_RE = /^\s*<\/?details(?:\s|>)/iu;
const NUMBERED_ITEM_RE = new RegExp(`^\\s*(?:\\d+[.)、．]|[（(]\\d+[）)]|[①②③④⑤⑥⑦⑧⑨⑩]|[${BASIC_NUMERAL}]+[、.．]|[（(][${BASIC_NUMERAL}]+[）)])\\s*`);
const BULLET_ITEM_RE = /^\s*[-*+]\s+/;
const LABEL_LINE_RE = /^\s*[^，。！？；：:\n]{2,24}[：:]\s*\S+/;
const EMPTY_OPENING_RE = /^(?:近年来|随着[^，。]{0,24}(?:发展|推进|普及)|在当今[^，。]{0,24}(?:时代|社会|背景下)|众所周知|毋庸置疑|不言而喻)[，,]/;
const CONNECTOR_OPENING_RE = new RegExp(`^(?:${CONNECTOR_GROUP})[，,、]|^(?:第[${BASIC_NUMERAL.replace('百', '')}]+|一|二|三|四|五)[，,、]|^(?:一|二|三|四|五)是(?:[，,、]|(?=\\S))`, 'u');
const REPORT_TONE_RE = /^(?:下面从[^，。.]{0,30}(?:展开|介绍|分析)|本节主要介绍|本节将|本章主要|综上所述|总的来说)[，,、]/;
const INTRA_PARAGRAPH_CONNECTOR_RE = new RegExp(`(?:${CONNECTOR_GROUP})[，,、]`, 'gu');
const FUNCTIONAL_LIST_CONTEXT_RE = /清单|步骤|操作|规范|流程|参数|资源|核对|检查项|要点回顾|安全红线|法律条款|目录/;
const PAPER_HEADING_RE = /^(?:摘要|绪论|研究方法|实验方法|实验结果|讨论)$/;
const CHAPTER_HEADING_RE = new RegExp(`^第[${CHINESE_NUMERAL}]+章(?:\\s+(.+))?$`, 'u');
const TOPIC_HEADING_RE = new RegExp(`^[${CHINESE_NUMERAL}]+、\\s*(.*)$`, 'u');
const SUBTOPIC_HEADING_RE = new RegExp(`^（[${CHINESE_NUMERAL}]+）\\s*(.*)$`, 'u');
const PARENTHESIZED_BODY_HEADING_RE = new RegExp(`^（[${CHINESE_NUMERAL}]+）\\s*[^，。！？；：:]{2,30}$`, 'u');
const BOLD_ONLY_RE = /^\*\*([^*\n]{2,30})\*\*[。．]?$/u;
const BOLD_SPAN_RE = /\*\*([^*\n]+)\*\*/gu;
const TABLE_LINE_RE = /^\s*\|.*\|\s*$/u;
const UNNUMBERED_HEADING_RE = /^(?:书名|目录|前言|序言|摘要|结语|后记|附录|参考文献)$/u;
const CHECKER_POLICY_VERSION = 'writing-shape-v3';

function normalizeText(text) {
  return String(text).replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
}

function visibleLines(text) {
  const lines = normalizeText(text).split('\n');
  const visible = [];
  let fenced = false;
  const frontmatterClose = lines[0]?.trim() === '---'
    ? lines.slice(1, 51).findIndex(line => line.trim() === '---')
    : -1;
  let frontmatter = frontmatterClose >= 0;
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    if (index === 0 && frontmatter) continue;
    if (frontmatter) {
      if (trimmed === '---') frontmatter = false;
      continue;
    }
    if (/^```|^~~~/.test(trimmed)) {
      fenced = !fenced;
      continue;
    }
    if (!fenced) visible.push({ number: index + 1, text: line });
  }
  return visible;
}

function headingInfo(line) {
  const match = line.match(/^\s*(#{1,6})\s+(.+?)\s*#*\s*$/);
  return match ? { level: match[1].length, content: match[2].trim() } : null;
}

function contextAllowsList(heading, prelude) {
  return FUNCTIONAL_LIST_CONTEXT_RE.test(`${heading || ''} ${prelude || ''}`);
}

function pushFailure(failures, rule, line, message, sample) {
  failures.push({ rule, line, message, sample: String(sample || '').trim().slice(0, 160) });
}

export function validateWritingText(text, { file = '<memory>' } = {}) {
  const failures = [];
  const warnings = [];
  const lines = visibleLines(text);
  let currentHeading = '';
  let currentHeadingLevel = 0;
  let numberedRun = [];
  let bulletRun = [];
  let labelRun = [];
  let connectorParagraphRun = [];
  let tableRun = [];
  let tableBlockCount = 0;
  let boldSpanCount = 0;
  let boldSubheadingCount = 0;
  let previousBoldOnly = false;

  function validateHeading(entry, level, content) {
    if (level >= 4) {
      pushFailure(failures, 'heading-depth-exceeded', entry.number, '正式标题只允许三层；更细导航使用无编号加粗小标题', entry.text);
    }
    if (/\*\*/.test(content)) {
      pushFailure(failures, 'bold-inside-heading', entry.number, 'Markdown 标题本身已有层级样式，不再重复加粗', entry.text);
    }
    const chapter = content.match(CHAPTER_HEADING_RE);
    const topic = content.match(TOPIC_HEADING_RE);
    const subtopic = content.match(SUBTOPIC_HEADING_RE);
    if (level === 2 && !topic && !UNNUMBERED_HEADING_RE.test(content)) {
      pushFailure(failures, 'heading-level-format', entry.number, '二级标题应使用“一、具体标题”', entry.text);
    }
    if (level === 3 && !subtopic) {
      pushFailure(failures, 'heading-level-format', entry.number, '三级标题应使用“（一）具体标题”', entry.text);
    }
    if ((chapter && level !== 1) || (topic && level !== 2) || (subtopic && level !== 3)) {
      pushFailure(failures, 'heading-level-mismatch', entry.number, '标题编号与 Markdown 层级不匹配，应为“第一章 → 一、 → （一）”', entry.text);
    }
    const semanticTitle = topic?.[1] ?? subtopic?.[1];
    if (semanticTitle !== undefined && semanticTitle.trim().length < 2) {
      pushFailure(failures, 'heading-title-missing', entry.number, '二、三级编号后必须有具体语义标题', entry.text);
    }
  }

  function flushTable() {
    if (tableRun.length === 0) return;
    tableBlockCount += 1;
    const cells = line => line.trim().slice(1, -1).split('|').map(cell => cell.trim());
    const header = cells(tableRun[0].text);
    const separator = tableRun[1] ? cells(tableRun[1].text) : [];
    const validSeparator = separator.length === header.length && separator.every(cell => /^:?-{3,}:?$/.test(cell));
    if (header.length < 2 || tableRun.length < 3 || !validSeparator) {
      pushFailure(failures, 'malformed-table', tableRun[0].number, '表格至少需要两列、表头分隔行和一行数据', tableRun.map(item => item.text.trim()).join(' | '));
    }
    tableRun = [];
  }

  function flushNumbered() {
    if (numberedRun.length >= 3 && !contextAllowsList(currentHeading, numberedRun[0]?.prelude)) {
      pushFailure(
        failures,
        'numbered-list-mashup',
        numberedRun[0].number,
        `连续 ${numberedRun.length} 个编号条目替代正文论述`,
        numberedRun.map(item => item.text.trim()).join(' | '),
      );
    }
    numberedRun = [];
  }

  function flushBullets() {
    if (bulletRun.length >= 3) {
      const first = bulletRun[0];
      const prelude = first.prelude || '';
      if (!contextAllowsList(currentHeading, prelude)) {
        pushFailure(
          failures,
          'list-then-sublist',
          first.number,
          `短导语后连续 ${bulletRun.length} 个无序列表项替代正文论述`,
          `${prelude} ${bulletRun.map(item => item.text.trim()).join(' | ')}`,
        );
      }
    }
    bulletRun = [];
  }

  function flushLabels() {
    if (labelRun.length >= 3) {
      pushFailure(
        failures,
        'label-colon-mashup',
        labelRun[0].number,
        `连续 ${labelRun.length} 个标签冒号句，正文仍是提纲形态`,
        labelRun.map(item => item.text.trim()).join(' | '),
      );
    }
    labelRun = [];
  }

  function flushConnectors() {
    if (connectorParagraphRun.length >= 2 && !contextAllowsList(currentHeading, connectorParagraphRun[0]?.prelude)) {
      pushFailure(
        failures,
        'mechanical-connectors',
        connectorParagraphRun[0].number,
        `连续 ${connectorParagraphRun.length} 个段落依靠模板连接词推进`,
        connectorParagraphRun.map(item => item.text.trim()).join(' | '),
      );
    }
    connectorParagraphRun = [];
  }

  let previousNonEmpty = '';
  for (let index = 0; index < lines.length; index += 1) {
    const entry = lines[index];
    const trimmed = entry.text.trim();
    const heading = headingInfo(entry.text);
    const nextLine = lines[index + 1]?.text?.trim() || '';
    const tableLine = TABLE_LINE_RE.test(trimmed);

    if (tableLine) tableRun.push(entry);
    else flushTable();

    if (heading === null && trimmed && /^(?:=+|-{3,})$/.test(nextLine)) {
      flushNumbered();
      flushBullets();
      flushLabels();
      flushConnectors();
      currentHeading = trimmed;
      currentHeadingLevel = nextLine.startsWith('=') ? 1 : 2;
      previousBoldOnly = false;
      validateHeading(entry, currentHeadingLevel, trimmed);
      if (ARABIC_HEADING_PATTERNS.some(pattern => pattern.test(trimmed))) {
        pushFailure(failures, 'arabic-numbered-heading', entry.number, '标题层级编号必须使用汉字', entry.text);
      }
      if (FORBIDDEN_SECTION_HEADING_RE.test(trimmed)) {
        pushFailure(failures, 'forbidden-section-heading', entry.number, '子级标题使用“一、”与“（一）”，不使用“第几节”', entry.text);
      }
      if (PAPER_HEADING_RE.test(trimmed)) {
        warnings.push({
          rule: 'paper-structure-heading',
          line: entry.number,
          message: '检测到论文式结构标题，请确认与当前书稿体裁一致',
          sample: trimmed,
        });
      }
      previousNonEmpty = trimmed;
      continue;
    }

    if (heading !== null) {
      flushNumbered();
      flushBullets();
      flushLabels();
      flushConnectors();
      currentHeading = heading.content;
      currentHeadingLevel = heading.level;
      previousBoldOnly = false;
      validateHeading(entry, heading.level, heading.content);
      if (ARABIC_HEADING_PATTERNS.some(pattern => pattern.test(heading.content))) {
        pushFailure(failures, 'arabic-numbered-heading', entry.number, '标题层级编号必须使用汉字', entry.text);
      }
      if (FORBIDDEN_SECTION_HEADING_RE.test(heading.content)) {
        pushFailure(failures, 'forbidden-section-heading', entry.number, '子级标题使用“一、”与“（一）”，不使用“第几节”', entry.text);
      }
      if (PAPER_HEADING_RE.test(heading.content)) {
        warnings.push({
          rule: 'paper-structure-heading',
          line: entry.number,
          message: '检测到论文式结构标题，请确认与当前书稿体裁一致',
          sample: heading.content,
        });
      }
      previousNonEmpty = trimmed;
      continue;
    }

    if (!trimmed) continue;
    if (DECORATIVE_CALLOUT_RE.test(trimmed) || COLLAPSIBLE_BLOCK_RE.test(trimmed)) {
      pushFailure(failures, 'decorative-callout', entry.number, '正文不得使用装饰性高亮块或折叠块', entry.text);
      flushNumbered();
      flushBullets();
      flushLabels();
      flushConnectors();
      previousNonEmpty = trimmed;
      continue;
    }
    if (tableLine || /^<!--/.test(trimmed) || /^---+$/.test(trimmed)) {
      flushNumbered();
      flushBullets();
      flushLabels();
      flushConnectors();
      continue;
    }

    if (PARENTHESIZED_BODY_HEADING_RE.test(trimmed)) {
      pushFailure(
        failures,
        currentHeadingLevel >= 3 ? 'pseudo-fourth-level-heading' : 'unmarked-subheading',
        entry.number,
        currentHeadingLevel >= 3
          ? '三级标题下不得再次使用“（一）”编号；改用无编号加粗小标题或自然段'
          : '疑似三级标题缺少 Markdown 标题标记，应写为“### （一）具体标题”',
        entry.text,
      );
    }

    const boldMatches = [...trimmed.matchAll(BOLD_SPAN_RE)];
    boldSpanCount += boldMatches.length;
    const boldOnly = BOLD_ONLY_RE.test(trimmed);
    if (boldOnly) {
      boldSubheadingCount += 1;
      if (previousBoldOnly) {
        pushFailure(failures, 'bold-heading-stack', entry.number, '加粗小标题之间必须有正文，不得连续堆叠', entry.text);
      }
    } else if (/^\*\*.*\*\*$/.test(trimmed) && trimmed.length > 34) {
      pushFailure(failures, 'whole-paragraph-bold', entry.number, '不得整段加粗', entry.text);
    }
    previousBoldOnly = boldOnly;

    if (NUMBERED_ITEM_RE.test(trimmed)) {
      flushBullets();
      flushLabels();
      numberedRun.push({ ...entry, prelude: previousNonEmpty });
    } else {
      flushNumbered();
    }

    if (BULLET_ITEM_RE.test(trimmed)) {
      flushNumbered();
      flushLabels();
      bulletRun.push({ ...entry, prelude: previousNonEmpty });
    } else {
      flushBullets();
    }

    if (!NUMBERED_ITEM_RE.test(trimmed) && !BULLET_ITEM_RE.test(trimmed) && LABEL_LINE_RE.test(trimmed) && trimmed.length <= 100) {
      labelRun.push(entry);
    } else {
      flushLabels();
    }

    if (EMPTY_OPENING_RE.test(trimmed)) {
      pushFailure(failures, 'empty-opening', entry.number, '段落以空泛趋势套话开头', entry.text);
    }

    if (REPORT_TONE_RE.test(trimmed) && !contextAllowsList(currentHeading, previousNonEmpty)) {
      pushFailure(failures, 'report-tone', entry.number, '段落用汇报口吻开头，应直接进入具体对象', entry.text);
    }

    // 检测段落内多个机械连接词（一段内出现 2+ 个"首先/其次/最后"等），功能清单章节豁免
    const intraMatches = trimmed.match(INTRA_PARAGRAPH_CONNECTOR_RE);
    if (intraMatches && intraMatches.length >= 2 && !contextAllowsList(currentHeading, previousNonEmpty)) {
      pushFailure(
        failures,
        'intra-paragraph-connectors',
        entry.number,
        `单段落内出现 ${intraMatches.length} 个机械连接词，仍是提纲形态`,
        trimmed.slice(0, 160),
      );
    }

    if (CONNECTOR_OPENING_RE.test(trimmed)) connectorParagraphRun.push(entry);
    else flushConnectors();

    previousNonEmpty = trimmed;
  }

  flushNumbered();
  flushBullets();
  flushLabels();
  flushConnectors();
  flushTable();

  const contentCharacters = normalizeText(text).replace(/\s+/g, '').length;
  const maximumBoldSpans = Math.max(4, Math.ceil(contentCharacters / 500));
  const maximumBoldSubheadings = Math.max(3, Math.ceil(contentCharacters / 1000));
  const maximumTables = Math.max(1, Math.ceil(contentCharacters / 2000));
  if (boldSpanCount > maximumBoldSpans) {
    pushFailure(failures, 'excessive-bold', 0, `加粗共 ${boldSpanCount} 处，超过当前篇幅允许的 ${maximumBoldSpans} 处`, `${boldSpanCount}/${maximumBoldSpans}`);
  }
  if (boldSubheadingCount > maximumBoldSubheadings) {
    pushFailure(failures, 'excessive-bold-subheadings', 0, `无编号加粗小标题共 ${boldSubheadingCount} 处，超过当前篇幅允许的 ${maximumBoldSubheadings} 处`, `${boldSubheadingCount}/${maximumBoldSubheadings}`);
  }
  if (tableBlockCount > maximumTables) {
    pushFailure(failures, 'excessive-tables', 0, `表格共 ${tableBlockCount} 个，超过当前篇幅允许的 ${maximumTables} 个`, `${tableBlockCount}/${maximumTables}`);
  }

  return {
    file,
    status: failures.length === 0 ? 'pass' : 'fail',
    failures,
    warnings,
  };
}

function defaultTargets(workspace) {
  const targets = new Set();
  const shortManuscript = path.join(workspace, 'manuscript.md');
  if (fs.existsSync(shortManuscript) && fs.statSync(shortManuscript).isFile()) targets.add(shortManuscript);
  for (const pattern of ['manuscript/**/*.md', 'deliverables/**/*.md', 'releases/**/*.md']) {
    for (const target of globSync(pattern, { cwd: workspace, absolute: true, nodir: true })) targets.add(target);
  }
  return [...targets].sort((left, right) => left.localeCompare(right, 'zh-CN'));
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, filePath);
}

export function checkWritingShape({ workspace = process.cwd(), inputs = [], reportPath, writeReport = true } = {}) {
  const root = path.resolve(workspace);
  const finalReportPath = reportPath
    ? path.resolve(root, reportPath)
    : path.join(root, '.doubao-book-writer', 'reports', 'writing-shape-check.json');
  let previousFiles = new Map();
  try {
    const previous = JSON.parse(fs.readFileSync(finalReportPath, 'utf8').replace(/^\uFEFF/, ''));
    if (previous.policyVersion === CHECKER_POLICY_VERSION && Array.isArray(previous.files)) {
      previousFiles = new Map(previous.files.map(file => [`${file.file}\u0000${file.sha256}`, file]));
    }
  } catch {
    previousFiles = new Map();
  }
  const targets = inputs.length > 0
    ? inputs.map(input => path.resolve(root, input))
    : defaultTargets(root);
  const files = [];
  const missing = [];
  let reusedFiles = 0;
  let scannedFiles = 0;
  for (const target of targets) {
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
      missing.push(path.relative(root, target).split(path.sep).join('/'));
      continue;
    }
    const relative = path.relative(root, target).split(path.sep).join('/');
    const content = fs.readFileSync(target, 'utf8');
    const sha256 = createHash('sha256').update(content).digest('hex');
    const previous = previousFiles.get(`${relative}\u0000${sha256}`);
    if (previous) {
      files.push({ ...previous, reused: true });
      reusedFiles += 1;
    } else {
      files.push({ ...validateWritingText(content, { file: relative }), sha256, reused: false });
      scannedFiles += 1;
    }
  }
  const failures = files.flatMap(result => result.failures.map(failure => ({ file: result.file, ...failure })));
  for (const file of missing) failures.push({ file, rule: 'missing-input', line: 0, message: '输入文件不存在', sample: '' });
  if (targets.length === 0) failures.push({ file: '', rule: 'no-targets', line: 0, message: '未找到可检查的正文 Markdown', sample: '' });
  const warnings = files.flatMap(result => result.warnings.map(warning => ({ file: result.file, ...warning })));
  const payload = {
    policyVersion: CHECKER_POLICY_VERSION,
    generatedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'pass' : 'fail',
    checkedFiles: files.length,
    failureCount: failures.length,
    warningCount: warnings.length,
    scannedFiles,
    reusedFiles,
    failures,
    warnings,
    files,
  };
  if (writeReport) writeJsonAtomic(finalReportPath, payload);
  return { ...payload, reportPath: finalReportPath };
}

function parseArgs(argv) {
  const options = { inputs: [], workspace: process.cwd(), json: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--input') options.inputs.push(argv[++index]);
    else if (token === '--report') options.reportPath = argv[++index];
    else if (token === '--json') options.json = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function help() {
  return `Doubao writing shape checker\n\nUsage:\n  node scripts/quality/check-writing-shape.mjs --workspace <path> [--input <relative.md>] [--report <relative.json>] [--json]\n\nWithout --input, scans manuscript.md, manuscript/**/*.md, deliverables/**/*.md, and releases/**/*.md.\n`;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write(help());
    return;
  }
  const result = checkWritingShape(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exitCode = result.status === 'pass' ? 0 : 1;
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invokedPath === fileURLToPath(import.meta.url)) main();

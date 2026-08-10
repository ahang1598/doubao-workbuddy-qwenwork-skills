#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ruleBounds } from './manuscript-word-count-gate.mjs';

const REQUIRED_OUTLINE_ARTIFACTS = ['outline.md', 'chapter-ledger.md'];
const EMPTY_DEPENDENCY_VALUES = new Set(['', '-', '—', '无', 'none', 'n/a']);
const COLUMN_ALIASES = {
  id: ['章节', '章节编号', '编号'],
  title: ['标题', '章节标题', '章名'],
  question: ['核心问题', '本章问题', '要回答的问题'],
  takeaway: ['用户收获', '读者收获', '收获点'],
  target: ['目标字数', '预估字数', '预计字数'],
  dependency: ['前置章节', '依赖章节', '前置依赖'],
};

function normalizeText(text) {
  return String(text).replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
}

function normalizeLabel(value) {
  return String(value || '').replace(/\s+/g, '').replace(/[：:]/g, '').trim();
}

function readText(filePath) {
  return normalizeText(fs.readFileSync(filePath, 'utf8'));
}

function readJson(filePath) {
  return JSON.parse(readText(filePath));
}

function writeJsonAtomic(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, filePath);
}

function splitTableRow(line) {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  return trimmed.split('|').map(cell => cell.trim());
}

function isSeparatorRow(cells) {
  return cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, '')));
}

function parseMarkdownTable(lines) {
  for (let index = 0; index < lines.length - 1; index += 1) {
    if (!lines[index].trim().startsWith('|') || !lines[index + 1].trim().startsWith('|')) continue;
    const headers = splitTableRow(lines[index]);
    const separator = splitTableRow(lines[index + 1]);
    if (headers.length !== separator.length || !isSeparatorRow(separator)) continue;
    const rows = [];
    for (let rowIndex = index + 2; rowIndex < lines.length; rowIndex += 1) {
      if (!lines[rowIndex].trim().startsWith('|')) break;
      const cells = splitTableRow(lines[rowIndex]);
      if (cells.length !== headers.length) break;
      const row = {};
      headers.forEach((header, columnIndex) => {
        row[normalizeLabel(header)] = cells[columnIndex];
      });
      rows.push({ line: rowIndex + 1, values: row });
    }
    return { headers: headers.map(normalizeLabel), rows };
  }
  return null;
}

function parseSections(markdown) {
  const lines = normalizeText(markdown).split('\n');
  const sections = [];
  let current = { heading: '', line: 1, lines: [] };
  for (let index = 0; index < lines.length; index += 1) {
    const match = lines[index].match(/^##\s+(.+?)\s*#*\s*$/);
    if (match) {
      sections.push(current);
      current = { heading: match[1].trim(), line: index + 1, lines: [] };
    } else {
      current.lines.push(lines[index]);
    }
  }
  sections.push(current);
  return sections;
}

function findSection(sections, patterns) {
  return sections.find(section => patterns.some(pattern => pattern.test(normalizeLabel(section.heading))));
}

function sectionVisibleText(section) {
  return section
    ? section.lines.filter(line => line.trim() && !line.trim().startsWith('|')).join('\n').trim()
    : '';
}

function columnName(headers, aliases) {
  return aliases.map(normalizeLabel).find(alias => headers.includes(alias)) || null;
}

function valueFor(row, column) {
  return column ? String(row.values[column] || '').trim() : '';
}

function parsePositiveInteger(value) {
  const match = String(value || '').replace(/[,，]/g, '').match(/\d+/);
  if (!match) return null;
  const number = Number(match[0]);
  return Number.isInteger(number) && number > 0 ? number : null;
}

function parseChapterId(value) {
  const match = String(value || '').trim().match(/^ch0*(\d+)$/i);
  if (!match) return null;
  const number = Number(match[1]);
  return Number.isInteger(number) && number > 0 ? number : null;
}

function parseDependencies(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (EMPTY_DEPENDENCY_VALUES.has(normalized)) return [];
  return String(value)
    .split(/[、,，;；/\s]+/)
    .map(item => item.trim())
    .filter(Boolean);
}

function addFailure(failures, rule, message, details = {}) {
  failures.push({ rule, message, ...details });
}

function validateRequiredSections(sections, failures) {
  const required = [
    ['core-claim', 'outline.md 缺少“核心主张”章节', [/^核心主张$/]],
    ['target-reader', 'outline.md 缺少“目标读者”章节', [/^目标读者/]],
    ['voice-tone', 'outline.md 缺少“语气”或“作者声音”章节', [/语气/, /作者声音/]],
    ['chapter-plan', 'outline.md 缺少“章节规划”章节', [/^章节规划$/, /^章节列表$/]],
    ['dependencies', 'outline.md 缺少“章节依赖关系”章节', [/章节依赖/]],
    ['total-words', 'outline.md 缺少“总字数目标”章节', [/总字数/]],
  ];
  const found = {};
  for (const [key, message, patterns] of required) {
    found[key] = findSection(sections, patterns);
    if (!found[key]) addFailure(failures, `missing-${key}`, message, { file: 'outline.md' });
  }
  for (const key of ['core-claim', 'target-reader', 'voice-tone']) {
    if (found[key] && !sectionVisibleText(found[key])) {
      addFailure(failures, `empty-${key}`, `${found[key].heading} 内容不能为空`, {
        file: 'outline.md',
        line: found[key].line,
      });
    }
  }
  return found;
}

function validateChapterPlan(section, failures) {
  if (!section) return [];
  const table = parseMarkdownTable(section.lines);
  if (!table) {
    addFailure(failures, 'missing-chapter-table', '章节规划必须包含 Markdown 表格', {
      file: 'outline.md',
      line: section.line,
    });
    return [];
  }
  const columns = {
    id: columnName(table.headers, COLUMN_ALIASES.id),
    title: columnName(table.headers, COLUMN_ALIASES.title),
    question: columnName(table.headers, COLUMN_ALIASES.question),
    takeaway: columnName(table.headers, COLUMN_ALIASES.takeaway),
    target: columnName(table.headers, COLUMN_ALIASES.target),
  };
  for (const [key, column] of Object.entries(columns)) {
    if (!column) {
      addFailure(failures, `missing-chapter-column-${key}`, `章节规划表缺少必需列：${COLUMN_ALIASES[key][0]}`, {
        file: 'outline.md',
        line: section.line,
      });
    }
  }
  if (Object.values(columns).some(column => !column)) return [];
  if (table.rows.length === 0) {
    addFailure(failures, 'empty-chapter-table', '章节规划表至少需要一章', { file: 'outline.md' });
    return [];
  }

  const chapters = [];
  const ids = new Set();
  const titles = new Set();
  for (const row of table.rows) {
    const id = valueFor(row, columns.id);
    const number = parseChapterId(id);
    const title = valueFor(row, columns.title);
    const question = valueFor(row, columns.question);
    const takeaway = valueFor(row, columns.takeaway);
    const targetWords = parsePositiveInteger(valueFor(row, columns.target));
    const line = section.line + row.line;
    if (number == null) addFailure(failures, 'invalid-chapter-id', `章节 ID 必须使用 chNN：${id || '(空)'}`, { file: 'outline.md', line });
    if (ids.has(id.toLowerCase())) addFailure(failures, 'duplicate-chapter-id', `章节 ID 重复：${id}`, { file: 'outline.md', line });
    if (!title) addFailure(failures, 'empty-chapter-title', `章节 ${id || '(未知)'} 标题不能为空`, { file: 'outline.md', line });
    else if (titles.has(title)) addFailure(failures, 'duplicate-chapter-title', `章节标题重复：${title}`, { file: 'outline.md', line });
    if (!question) addFailure(failures, 'empty-core-question', `章节 ${id || '(未知)'} 核心问题不能为空`, { file: 'outline.md', line });
    if (!takeaway) addFailure(failures, 'empty-user-takeaway', `章节 ${id || '(未知)'} 用户收获不能为空`, { file: 'outline.md', line });
    if (targetWords == null) addFailure(failures, 'invalid-target-words', `章节 ${id || '(未知)'} 目标字数必须为正整数`, { file: 'outline.md', line });
    ids.add(id.toLowerCase());
    if (title) titles.add(title);
    chapters.push({ id: id.toLowerCase(), number, title, question, takeaway, targetWords, line });
  }
  const validNumbers = chapters.map(chapter => chapter.number).filter(number => number != null);
  validNumbers.forEach((number, index) => {
    if (number !== index + 1) {
      addFailure(failures, 'non-contiguous-chapter-id', `章节 ID 必须从 ch01 连续排列，位置 ${index + 1} 实际为 ch${String(number).padStart(2, '0')}`, {
        file: 'outline.md',
        line: chapters[index]?.line,
      });
    }
  });
  return chapters;
}

function validateTotalWords(section, chapters, failures, checklist) {
  if (!section) return null;
  const totalTarget = parsePositiveInteger(section.lines.join(' '));
  if (totalTarget == null) {
    addFailure(failures, 'invalid-total-words', '总字数目标必须包含正整数', { file: 'outline.md', line: section.line });
    return null;
  }
  if (chapters.some(chapter => chapter.targetWords == null)) return totalTarget;
  const plannedTotal = chapters.reduce((sum, chapter) => sum + chapter.targetWords, 0);
  if (plannedTotal !== totalTarget) {
    addFailure(
      failures,
      'chapter-budget-not-allocated',
      `章节目标字数合计 ${plannedTotal} 必须完整分配全书目标 ${totalTarget}，不能把偏差留到成稿阶段处理`,
      { file: 'outline.md', line: section.line },
    );
  }
  const totalRule = Array.isArray(checklist?.wordCountRules)
    ? checklist.wordCountRules.find(rule => !rule?.path && ['target', 'minimum', 'maximum'].some(field => Number.isFinite(Number(rule?.[field]))))
    : null;
  if (totalRule) {
    const bounds = ruleBounds(totalRule);
    if (bounds.minimum != null && totalTarget < bounds.minimum) {
      addFailure(failures, 'outline-total-below-contract', `大纲总字数目标 ${totalTarget} 低于需求清单下限 ${bounds.minimum}`, { file: 'outline.md', line: section.line });
    }
    if (bounds.maximum != null && totalTarget > bounds.maximum) {
      addFailure(failures, 'outline-total-above-contract', `大纲总字数目标 ${totalTarget} 高于需求清单上限 ${bounds.maximum}`, { file: 'outline.md', line: section.line });
    }
  }
  return totalTarget;
}

function validateDependencies(section, chapters, failures) {
  if (!section || chapters.length === 0) return [];
  const table = parseMarkdownTable(section.lines);
  if (!table) {
    addFailure(failures, 'missing-dependency-table', '章节依赖关系必须包含 Markdown 表格', {
      file: 'outline.md',
      line: section.line,
    });
    return [];
  }
  const idColumn = columnName(table.headers, COLUMN_ALIASES.id);
  const dependencyColumn = columnName(table.headers, COLUMN_ALIASES.dependency);
  if (!idColumn) addFailure(failures, 'missing-dependency-id-column', '章节依赖表缺少“章节”列', { file: 'outline.md', line: section.line });
  if (!dependencyColumn) addFailure(failures, 'missing-dependency-column', '章节依赖表缺少“前置章节”列', { file: 'outline.md', line: section.line });
  if (!idColumn || !dependencyColumn) return [];

  const chapterIndex = new Map(chapters.map((chapter, index) => [chapter.id, index]));
  const seen = new Set();
  const edges = [];
  for (const row of table.rows) {
    const id = valueFor(row, idColumn).toLowerCase();
    const line = section.line + row.line;
    if (!chapterIndex.has(id)) {
      addFailure(failures, 'unknown-dependency-row', `依赖表包含未知章节：${id || '(空)'}`, { file: 'outline.md', line });
      continue;
    }
    if (seen.has(id)) addFailure(failures, 'duplicate-dependency-row', `依赖表章节重复：${id}`, { file: 'outline.md', line });
    seen.add(id);
    const dependencies = parseDependencies(valueFor(row, dependencyColumn)).map(item => item.toLowerCase());
    for (const dependency of dependencies) {
      if (dependency === id) addFailure(failures, 'self-dependency', `${id} 不能依赖自身`, { file: 'outline.md', line });
      else if (!chapterIndex.has(dependency)) addFailure(failures, 'unknown-dependency', `${id} 的前置章节不存在：${dependency}`, { file: 'outline.md', line });
      else if (chapterIndex.get(dependency) >= chapterIndex.get(id)) {
        addFailure(failures, 'forward-dependency', `${id} 的前置章节必须位于其之前：${dependency}`, { file: 'outline.md', line });
      }
      edges.push({ chapter: id, dependency });
    }
  }
  for (const chapter of chapters) {
    if (!seen.has(chapter.id)) addFailure(failures, 'missing-dependency-row', `依赖表缺少章节：${chapter.id}`, { file: 'outline.md' });
  }
  return edges;
}

function validateLedger(markdown, chapters, failures) {
  const table = parseMarkdownTable(normalizeText(markdown).split('\n'));
  if (!table) {
    addFailure(failures, 'missing-ledger-table', 'chapter-ledger.md 必须包含章节台账表格', { file: 'chapter-ledger.md' });
    return;
  }
  const idColumn = columnName(table.headers, COLUMN_ALIASES.id);
  const titleColumn = columnName(table.headers, COLUMN_ALIASES.title);
  const targetColumn = columnName(table.headers, COLUMN_ALIASES.target);
  if (!idColumn) addFailure(failures, 'missing-ledger-id-column', '章节台账缺少“章节”列', { file: 'chapter-ledger.md' });
  if (!titleColumn) addFailure(failures, 'missing-ledger-title-column', '章节台账缺少“标题”列', { file: 'chapter-ledger.md' });
  if (!targetColumn) addFailure(failures, 'missing-ledger-target-column', '章节台账缺少“目标字数”列', { file: 'chapter-ledger.md' });
  if (!idColumn || !titleColumn || !targetColumn) return;

  const outlineById = new Map(chapters.map(chapter => [chapter.id, chapter]));
  const ledgerIds = new Set();
  for (const row of table.rows) {
    const id = valueFor(row, idColumn).toLowerCase();
    const title = valueFor(row, titleColumn);
    const targetWords = parsePositiveInteger(valueFor(row, targetColumn));
    if (ledgerIds.has(id)) addFailure(failures, 'duplicate-ledger-id', `章节台账 ID 重复：${id}`, { file: 'chapter-ledger.md', line: row.line });
    ledgerIds.add(id);
    const outlineChapter = outlineById.get(id);
    if (!outlineChapter) {
      addFailure(failures, 'ledger-extra-chapter', `章节台账包含大纲中不存在的章节：${id}`, { file: 'chapter-ledger.md', line: row.line });
      continue;
    }
    if (title !== outlineChapter.title) {
      addFailure(failures, 'ledger-title-mismatch', `${id} 标题与大纲不一致：${title} != ${outlineChapter.title}`, { file: 'chapter-ledger.md', line: row.line });
    }
    if (targetWords !== outlineChapter.targetWords) {
      addFailure(failures, 'ledger-target-mismatch', `${id} 目标字数与大纲不一致：${targetWords} != ${outlineChapter.targetWords}`, { file: 'chapter-ledger.md', line: row.line });
    }
  }
  for (const chapter of chapters) {
    if (!ledgerIds.has(chapter.id)) addFailure(failures, 'ledger-missing-chapter', `章节台账缺少大纲章节：${chapter.id}`, { file: 'chapter-ledger.md' });
  }
}

export function runOutlineStructureGate({ workspace, writeReport = true, checklist = null } = {}) {
  const root = path.resolve(workspace || process.cwd());
  const failures = [];
  const warnings = [];
  const paths = Object.fromEntries(REQUIRED_OUTLINE_ARTIFACTS.map(relative => [relative, path.join(root, ...relative.split('/'))]));
  for (const [relative, filePath] of Object.entries(paths)) {
    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile() || fs.readFileSync(filePath, 'utf8').trim().length === 0) {
      addFailure(failures, 'missing-artifact', `缺少或为空：${relative}`, { file: relative });
    }
  }

  let chapters = [];
  let totalTarget = null;
  let dependencies = [];
  if (failures.length === 0) {
    try {
      const outline = readText(paths['outline.md']);
      const sections = parseSections(outline);
      const required = validateRequiredSections(sections, failures);
      chapters = validateChapterPlan(required['chapter-plan'], failures);
      let resolvedChecklist = checklist;
      const checklistPath = path.join(root, '.doubao-book-writer', 'requirement-checklist.json');
      if (resolvedChecklist == null && fs.existsSync(checklistPath)) resolvedChecklist = readJson(checklistPath);
      totalTarget = validateTotalWords(required['total-words'], chapters, failures, resolvedChecklist);
      dependencies = validateDependencies(required.dependencies, chapters, failures);
      validateLedger(readText(paths['chapter-ledger.md']), chapters, failures);
    } catch (error) {
      addFailure(failures, 'parse-error', `大纲结构解析失败：${error.message}`);
    }
  }

  const payload = {
    generatedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'pass' : 'fail',
    failureCount: failures.length,
    warningCount: warnings.length,
    failures,
    warnings,
    summary: {
      chapterCount: chapters.length,
      totalTargetWords: totalTarget,
      plannedChapterWords: chapters.reduce((sum, chapter) => sum + (chapter.targetWords || 0), 0),
      dependencyEdges: dependencies.length,
    },
  };
  const reportPath = path.join(root, '.doubao-book-writer', 'reports', 'outline-structure-check.json');
  if (writeReport) writeJsonAtomic(reportPath, payload);
  return { ...payload, reportPath };
}

function parseArgs(argv) {
  const options = { json: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--json') options.json = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function help() {
  return `Doubao outline structure gate\n\nUsage:\n  node scripts/gates/outline-structure-gate.mjs --workspace <path> [--json]\n`;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write(help());
    return;
  }
  if (!options.workspace) {
    process.stderr.write('missing --workspace\n');
    process.exitCode = 2;
    return;
  }
  const result = runOutlineStructureGate(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exitCode = result.status === 'pass' ? 0 : 1;
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invokedPath === fileURLToPath(import.meta.url)) main();

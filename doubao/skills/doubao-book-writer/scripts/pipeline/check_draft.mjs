#!/usr/bin/env node
// 写作阶段门卫：对正文做确定性形态与字数检查，不判断书稿内容对错。
//
// 职责：
//   - 对正文跑 quality/check-writing-shape.mjs（标题层级/列表滥用/机械连接词/加粗表格滥用）。
//   - 跑 gates/manuscript-word-count-gate.mjs（字数区间硬门禁）。
//   - long 稿额外：core/refresh-chapter-ledger.mjs 刷新台账字数，
//     gates/verify-chapter-ledger-truth.mjs 防止把空壳章节标为已完成。
//   - short 稿查根 manuscript.md；long 稿查 manuscript/*.md 全部章节（全量，不做增量）。
//
// fail-closed：一次报全所有 failures。exit code：0 通过 / 1 阻断 / 2 环境或参数错误。
// 只调用既有检查器的导出函数，不重写其逻辑。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

import { globSync } from '../lib/simple-glob.mjs';
import { checkWritingShape } from '../quality/check-writing-shape.mjs';
import { runManuscriptWordCountGate } from '../gates/manuscript-word-count-gate.mjs';
import { refreshChapterCharCounts } from '../core/refresh-chapter-ledger.mjs';
import { verifyChapterLedgerTruth } from '../gates/verify-chapter-ledger-truth.mjs';
import { detectLayout } from './check_prepare.mjs';

const REPORT_RELATIVE = ['.doubao-book-writer', 'reports', 'draft_check.json'];

// 终稿清洁规则：正文不得残留占位符/半成品标记（搬自 final-manuscript-clean-gate，
// 去掉其交付回执耦合，只保留纯正则扫描）。命中即阻断。
const PLACEHOLDER_RULES = Object.freeze([
  ['pending-mat-bracket', /\[待核实-MAT-[^\]\r\n]+\]/giu],
  ['mat-todo-suffix', /MAT-[A-Za-z0-9-]+（待补充）/giu],
  ['discarded-tag', /\[DISCARDED-[^\]\r\n]{1,300}\]/giu],
  ['todo-tbd', /\bTODO\b|\bTBD\b/giu],
  ['template-braces', /\{\{[^}\r\n]+\}\}/gu],
  ['cn-placeholder-pending', /（待续写|待补充|待完善|待核实）/gu],
  ['cn-placeholder-expect', /敬请期待|稍后补充|此处省略/gu],
  ['cn-placeholder-omit', /（略）/gu],
]);

function emit(payload, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(exitCode);
}

function readJsonOptional(filePath) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

/**
 * 列出待检查正文文件（相对 workspace）。
 * short 稿取根 manuscript.md（存在才纳入）；long 稿取 manuscript 目录下全部 .md 章节。
 */
function manuscriptTargets(root, layout) {
  if (layout === 'long') {
    return globSync('manuscript/**/*.md', { cwd: root, nodir: true })
      .sort((left, right) => left.localeCompare(right, 'zh-Hans-CN', { numeric: true }));
  }
  return fs.existsSync(path.join(root, 'manuscript.md')) ? ['manuscript.md'] : [];
}

function inventoryFor(root, targets) {
  return targets.map(relative => {
    const absolute = path.join(root, relative);
    let content = null;
    try {
      content = fs.readFileSync(absolute, 'utf8');
    } catch {
      content = null;
    }
    return {
      relative,
      absolute,
      content,
      public: {
        file: relative,
        chars: content == null ? null : content.replace(/\s+/g, '').length,
        bytes: content == null ? null : Buffer.byteLength(content, 'utf8'),
        sha256: content == null ? null : createHash('sha256').update(content).digest('hex'),
      },
    };
  });
}

/**
 * 把 minimumAdded 增量规则转成全量下限（minimum）。
 *
 * 三阶段模型移除了旧的 admission 基线（写作前的字数快照），字数门禁的
 * evaluateManuscriptWordCount 对 minimumAdded 规则强依赖该基线，缺失会报
 * WORD_COUNT_BASELINE_MISSING。这里在调用处把「新增至少 N 字」改写为
 * 「当前正文至少 N 字」这一全量下限，与「write 阶段一次性全量检查」一致；
 * 不修改检查器本身。仅在规则未显式给出 minimum 时转换，避免覆盖显式区间。
 */
function normalizeWordCountRules(checklist) {
  const rules = Array.isArray(checklist.wordCountRules) ? checklist.wordCountRules : [];
  const notes = [];
  const normalized = rules.map(rule => {
    if (rule && Number.isFinite(Number(rule.minimumAdded)) && !Number.isFinite(Number(rule.minimum))) {
      const { minimumAdded, ...rest } = rule;
      notes.push(`${rule.id || 'word-count'}: minimumAdded ${minimumAdded} 已按全量下限（minimum）校验，三阶段模型不再使用增量基线`);
      return { ...rest, minimum: Number(minimumAdded) };
    }
    return rule;
  });
  return { checklist: { ...checklist, wordCountRules: normalized }, notes };
}

/**
 * 执行写作阶段检查。
 * @param {{ workspace?: string, writeReport?: boolean }} options
 */
export function checkDraft({ workspace = process.cwd(), writeReport = false } = {}) {
  const root = path.resolve(workspace);
  const checklist = readJsonOptional(path.join(root, '.doubao-book-writer', 'requirement-checklist.json'));
  const { layout, source: layoutSource } = detectLayout(root, checklist);

  const failures = [];
  const warnings = [];

  // 1. 正文存在性：正文不存在直接阻断（write 阶段未产出）。
  const targets = manuscriptTargets(root, layout);
  if (targets.length === 0) {
    const missing = layout === 'long' ? 'manuscript/ 下的章节文件' : 'manuscript.md';
    return {
      status: 'fail',
      stage: 'write',
      code: 1,
      workspace: root,
      layout,
      layoutSource,
      failures: [`正文不存在：未找到 ${missing}`],
      fix: layout === 'long'
        ? '分章写入 manuscript/chNN-*.md 后重跑 make write。'
        : '把正文写入 manuscript.md 后重跑 make write。',
    };
  }
  const inventory = inventoryFor(root, targets);

  // 2. 形态检查（反 AI 提纲腔）。writeReport=true 时同步写入 shape 缓存报告，
  // 供下一轮按 policyVersion+sha256 复用未变章节结果。
  const shape = checkWritingShape({ workspace: root, inputs: targets, writeReport });
  for (const failure of shape.failures) {
    const location = failure.line ? `:${failure.line}` : '';
    failures.push(`[shape] ${failure.rule} (${failure.file || ''}${location})：${failure.message}`);
  }
  for (const warning of shape.warnings || []) {
    warnings.push(`[shape] ${warning.rule} (${warning.file || ''})：${warning.message}`);
  }

  // 3. 字数门禁（区间硬门）。用规范化后的 checklist 避免增量基线依赖。
  const { checklist: wordCountChecklist, notes: wordCountNotes } = normalizeWordCountRules(checklist);
  warnings.push(...wordCountNotes.map(note => `[word-count] ${note}`));
  const wordCount = runManuscriptWordCountGate({ workspace: root, checklist: wordCountChecklist, fileInventory: inventory.map(entry => entry.public) });
  for (const failure of wordCount.failures) {
    failures.push(`[word-count] ${failure.code}${failure.id ? ` (${failure.id})` : ''}：${failure.message}`);
  }

  // 4. 终稿清洁：正文不得残留占位符/半成品标记（TODO/待补充/{{}}/DISCARDED 等）。
  for (const entry of inventory) {
    if (entry.content == null) continue;
    for (const [rule, pattern] of PLACEHOLDER_RULES) {
      const matches = String(entry.content).match(pattern);
      if (matches && matches.length > 0) {
        failures.push(`[clean] ${rule} (${entry.relative})：残留占位符/半成品标记 ${matches.slice(0, 3).join('、')}`);
      }
    }
  }

  // 5. long 稿专属：刷新台账字数 + 防空壳真值校验。
  let ledger = null;
  let statusTruth = null;
  if (layout === 'long') {
    try {
      // dryRun 与 writeReport 联动：只有 write 模式（--write-report）才真正回写 chapter-ledger.md，
      // 否则只报告将更新多少行，保证只读诊断不改动磁盘文件。
      ledger = refreshChapterCharCounts(root, { dryRun: !writeReport });
    } catch (error) {
      // 台账缺失/表头不合规时记为 failure，而不是让脚本崩溃（fail-closed）。
      failures.push(`[ledger] 台账字数同步失败：${error instanceof Error ? error.message : String(error)}`);
    }

    const truth = verifyChapterLedgerTruth({ workspace: root, strict: true });
    statusTruth = { failureCount: truth.failures.length, warningCount: truth.warnings.length };
    for (const failure of truth.failures) failures.push(`[status-truth] ${failure}`);
    for (const warning of truth.warnings) warnings.push(`[status-truth] ${warning}`);
  }

  const status = failures.length === 0 ? 'pass' : 'fail';
  const payload = {
    status,
    stage: 'write',
    code: status === 'pass' ? 0 : 1,
    workspace: root,
    layout,
    layoutSource,
    checkedFiles: targets,
    result: {
      writingShape: { status: shape.status, failureCount: shape.failureCount, warningCount: shape.warningCount },
      wordCount: { status: wordCount.status, results: wordCount.results },
      ledger,
      statusTruth,
      inventory: inventory.map(entry => entry.public),
    },
    failures,
    warnings,
  };
  if (failures.length > 0) {
    payload.fix = '按 failures 修正正文（形态/字数/台账），再重跑 make write。';
  }

  if (writeReport) {
    const reportPath = path.join(root, ...REPORT_RELATIVE);
    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
    payload.reportPath = reportPath;
  }

  return payload;
}

function parseArgs(argv) {
  const options = { workspace: process.cwd(), writeReport: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--write-report') options.writeReport = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write('用法: node scripts/pipeline/check_draft.mjs --workspace <path> [--write-report]\n');
    return;
  }
  try {
    const result = checkDraft(options);
    emit(result, result.code ?? (result.status === 'pass' ? 0 : 1));
  } catch (error) {
    emit({ status: 'error', stage: 'write', code: 2, failures: [error instanceof Error ? error.message : String(error)] }, 2);
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

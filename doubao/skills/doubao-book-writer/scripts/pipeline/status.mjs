#!/usr/bin/env node
// 三态判定层：只读 .doubao-book-writer/reports/ 下的检查报告与磁盘产物，
// 给出最终交付状态。模型不得自行总结完成度，最终回答以本脚本结论为准。
//
// 只看真实文件，不读任何模型自称字段。三态：
//   - PASS：prepare 与 draft 检查都过，且飞书读回过（或 --allow-lark-skip）。
//   - BLOCKED：最早未满足的阶段（prepare 未过 / 正文不存在）及其修复指令；流程卡住。
//   - DRAFT_ONLY：正文存在但 draft 检查未过，或写作已过但尚未完成交付；未验收草稿，禁止称完成。
//
// 逻辑对齐 paper-write-zh 的 status.py，按 short/long 布局判定正文存在性与终稿。
// exit code：0=PASS / 1=BLOCKED 或 DRAFT_ONLY（未完成）/ 2=环境错误。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { detectLayout } from './check_prepare.mjs';

function emit(payload, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(exitCode);
}

/** 读检查报告 JSON；不存在或非法返回 null。 */
function loadReport(filePath) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function nonEmptyFile(filePath) {
  try {
    return fs.statSync(filePath).isFile() && fs.readFileSync(filePath, 'utf8').trim().length > 0;
  } catch {
    return false;
  }
}

function readJsonOptional(filePath) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

/** 判定正文是否存在（非空）。short 看根 manuscript.md；long 看 manuscript/ 下是否有非空 .md。 */
function manuscriptExists(root, layout) {
  if (layout === 'long') {
    const directory = path.join(root, 'manuscript');
    if (!fs.existsSync(directory) || !fs.statSync(directory).isDirectory()) return false;
    const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).some(entry => {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) return walk(full);
      return entry.isFile() && entry.name.toLowerCase().endsWith('.md') && nonEmptyFile(full);
    });
    return walk(directory);
  }
  return nonEmptyFile(path.join(root, 'manuscript.md'));
}

/**
 * 判定交付状态。
 * @param {{ workspace?: string, allowLarkSkip?: boolean }} options
 */
export function computeStatus({ workspace = process.cwd(), allowLarkSkip = false } = {}) {
  const root = path.resolve(workspace);
  const reports = path.join(root, '.doubao-book-writer', 'reports');
  const checklist = readJsonOptional(path.join(root, '.doubao-book-writer', 'requirement-checklist.json'));
  const { layout } = detectLayout(root, checklist);

  const prepareReport = loadReport(path.join(reports, 'prepare_check.json'));
  const draftReport = loadReport(path.join(reports, 'draft_check.json'));
  const larkReport = loadReport(path.join(reports, 'lark_check.json'));

  const draftExists = manuscriptExists(root, layout);
  const finalExists = nonEmptyFile(path.join(root, 'deliverables', 'final.md'));

  // 1. prepare 未过或未跑：卡在准备。
  if (prepareReport === null) {
    return { status: 'BLOCKED', stage: 'prepare', code: 1, layout, reason: '尚未通过准备阶段检查（缺 prepare_check.json）。', next: '运行 make prepare，按其提示补齐需求清单与大纲。' };
  }
  if (prepareReport.status !== 'pass') {
    return { status: 'BLOCKED', stage: 'prepare', code: 1, layout, reason: '准备阶段检查未通过。', failures: prepareReport.failures || [], next: '按 failures 修正后重跑 make prepare。' };
  }

  // 2. 正文不存在：卡在写作。
  if (!draftExists) {
    const target = layout === 'long' ? 'manuscript/ 下的章节文件' : 'manuscript.md';
    return { status: 'BLOCKED', stage: 'write', code: 1, layout, reason: `正文不存在或为空（${target}）。`, next: layout === 'long' ? '分章写入 manuscript/chNN-*.md 后运行 make write。' : '把正文写入 manuscript.md 后运行 make write。' };
  }

  // 3. 正文存在但检查未过：DRAFT_ONLY，禁止称完成。
  if (draftReport === null || draftReport.status !== 'pass') {
    return { status: 'DRAFT_ONLY', stage: 'write', code: 1, layout, reason: '正文存在但未通过写作检查，只是未验收草稿，不能称完成。', failures: (draftReport || {}).failures || ['未运行 make write 检查'], next: '按 failures 修正正文，重跑 make write。' };
  }

  // 4. 写作已过。用户显式跳过飞书：终稿存在即 PASS。
  if (allowLarkSkip) {
    if (!finalExists) {
      return { status: 'DRAFT_ONLY', stage: 'deliver', code: 1, layout, reason: '写作已过但缺终稿 deliverables/final.md。', next: '运行 make deliver 生成终稿（已跳过飞书）。' };
    }
    return { status: 'PASS', stage: 'deliver', code: 0, layout, reason: '写作检查通过，终稿已生成，用户已跳过飞书交付。', lark: 'skipped_by_user' };
  }

  // 5. 需要飞书交付：终稿与读回校验都要过。
  if (!finalExists || larkReport === null) {
    return { status: 'DRAFT_ONLY', stage: 'deliver', code: 1, layout, reason: '写作已过但尚未完成飞书交付与读回校验。', next: '运行 make deliver 创建飞书文档并读回校验（或用 --allow-lark-skip 显式跳过）。' };
  }
  if (larkReport.status !== 'pass') {
    return { status: 'BLOCKED', stage: 'deliver', code: 1, layout, reason: '飞书读回校验未通过。', failures: larkReport.failures || [], next: '按 failures 修复飞书文档后重跑 make deliver。' };
  }

  return { status: 'PASS', stage: 'deliver', code: 0, layout, reason: '写作检查通过，飞书文档已创建并读回校验通过。' };
}

function parseArgs(argv) {
  const options = { workspace: process.cwd(), allowLarkSkip: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--allow-lark-skip') options.allowLarkSkip = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write('用法: node scripts/pipeline/status.mjs --workspace <path> [--allow-lark-skip]\n');
    return;
  }
  try {
    const result = computeStatus(options);
    emit(result, result.code ?? (result.status === 'PASS' ? 0 : 1));
  } catch (error) {
    emit({ status: 'error', code: 2, failures: [error instanceof Error ? error.message : String(error)] }, 2);
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

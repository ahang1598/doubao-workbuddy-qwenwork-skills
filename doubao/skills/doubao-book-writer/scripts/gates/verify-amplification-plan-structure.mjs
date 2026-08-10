#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { readPlanRows } from './chapter-length-verify.mjs';

const REQUIRED_SECTIONS = [
  { pattern: /##\s+全书目标/u, message: '扩写计划应有「## 全书目标」小节，用来说明整体加厚后的目标。' },
  { pattern: new RegExp('##\\s*(?:\\u7ae0\\u8282\\u6269\\u5199\\u76ee\\u6807\\u8868|\\u673a\\u8bfb)', 'iu'), message: '扩写计划应提供可解析的章节目标表，供 chapter-length-verify 读取。' },
  { pattern: /##\s*(?:执行策略|并行)/iu, message: '扩写计划应说明执行策略，并把并行度控制在 3 以内（建议不超过 2）。' },
];

function cliOptions(argv) {
  const options = { workspace: null, strict: false, json: false, relaxed: undefined };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = path.resolve(argv[++index] || '');
    else if (token === '--strict') options.strict = true;
    else if (token === '--relaxed') options.relaxed = true;
    else if (token === '--json') options.json = true;
  }
  return options;
}

function confirmationState(markdown) {
  const section = markdown.match(new RegExp('##\\s*(?:\\u7528\\u6237\\u786e\\u8ba4|\\u6388\\u6743\\u8bb0\\u5f55)[\\s\\S]*?(?=\\n## |\\n---\\n|$)', 'iu'))?.[0];
  if (!section || !new RegExp('\\u7528\\u6237\\u5df2\\u786e\\u8ba4|\\u786e\\u8ba4\\u672c\\u8ba1\\u5212|\\u7528\\u6237\\u5df2\\u540c\\u610f\\u672c\\u8f6e\\u6269\\u5199\\u8ba1\\u5212', 'u').test(section)) return null;
  if (/\[x\]/iu.test(section)) return true;
  return /\[\s*\]/u.test(section) ? false : null;
}

function addRelaxable(message, relaxed, errors, warnings) {
  if (relaxed) warnings.push(`${message}（relaxed：仅警告）`);
  else errors.push(message);
}

export function auditExpansionPlanShape(workspace, options = {}) {
  const strict = Boolean(options.strict);
  const relaxed = options.relaxed == null ? !strict : Boolean(options.relaxed);
  const planPath = path.join(path.resolve(workspace), '.doubao-book-writer', 'amplification-plan.md');
  const errors = [];
  const warnings = [];
  if (!fs.existsSync(planPath)) return { ok: false, code: 2, errors: ['missing .doubao-book-writer/amplification-plan.md'], warnings, planPath };

  const markdown = fs.readFileSync(planPath, 'utf8').replace(/^\uFEFF/, '');
  for (const section of REQUIRED_SECTIONS) if (!section.pattern.test(markdown)) warnings.push(section.message);
  if (!new RegExp('##\\s*(?:\\u7528\\u6237\\u786e\\u8ba4|\\u6388\\u6743\\u8bb0\\u5f55)', 'iu').test(markdown)) {
    addRelaxable('缺少扩写授权小节；开始加厚前必须能记录用户是否同意。', relaxed, errors, warnings);
  }
  const rows = readPlanRows(planPath, workspace, { filterMeta: false });
  if (rows.length === 0) {
    addRelaxable('扩写目标表没有可解析记录；表头需覆盖章节、文件路径和目标字符数。', relaxed, errors, warnings);
  }
  const confirmation = confirmationState(markdown);
  if (strict && confirmation !== true) {
    errors.push(confirmation === false
      ? 'strict: 扩写授权仍是空框，请把确认项勾为 [x]。'
      : 'strict: 找不到可解析的扩写授权勾选项。');
  } else if (!strict && confirmation === false) warnings.push('扩写授权仍未勾选，开工前需在对话中完成确认。');
  return {
    ok: errors.length === 0,
    code: errors.length > 0 ? 2 : warnings.length > 0 ? 1 : 0,
    errors,
    warnings,
    planPath,
    rowCount: rows.length,
  };
}

function main() {
  const options = cliOptions(process.argv);
  if (!options.workspace) {
    process.stderr.write('用法: node scripts/gates/verify-amplification-plan-structure.mjs --workspace <工作目录> [--strict] [--relaxed] [--json]\n');
    process.exitCode = 2;
    return;
  }
  const result = auditExpansionPlanShape(options.workspace, options);
  if (options.json) process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  else {
    for (const error of result.errors) process.stderr.write(`[verify-amplification-plan-structure] ERROR: ${error}\n`);
    for (const warning of result.warnings) process.stderr.write(`[verify-amplification-plan-structure] WARN: ${warning}\n`);
    if (result.ok) process.stdout.write(`[verify-amplification-plan-structure] OK rows=${result.rowCount} ${result.planPath}\n`);
  }
  process.exitCode = result.code;
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

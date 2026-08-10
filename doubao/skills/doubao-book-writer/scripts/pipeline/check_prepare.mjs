#!/usr/bin/env node
// 准备阶段门卫：只做确定性检查，不判断书稿质量。
//
// 职责：
//   1. 校验 .doubao-book-writer/requirement-checklist.json 存在且字段合规
//      （参考 references/checklist-schema.md）。
//   2. 判定 short/long 布局（short=根 manuscript.md；long=outline.md + manuscript/ 目录）。
//   3. long 稿额外调 gates/outline-structure-gate.mjs 校验大纲结构（章节表/依赖/预算/台账）。
//
// fail-closed：任何缺失或非法字段都阻断；一次报全所有 failures，不在首个错误处返回。
// 只调用既有检查器的导出函数，不重写其逻辑。
//
// exit code：0 通过 / 1 阻断（可修复）/ 2 环境或参数错误。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { ruleBounds } from '../gates/manuscript-word-count-gate.mjs';
import { runOutlineStructureGate } from '../gates/outline-structure-gate.mjs';

const CHECKLIST_RELATIVE = ['.doubao-book-writer', 'requirement-checklist.json'];
const REPORT_RELATIVE = ['.doubao-book-writer', 'reports', 'prepare_check.json'];

/** 打印 JSON 结果到 stdout 并以指定退出码结束进程。仅在 CLI 入口使用。 */
function emit(payload, exitCode = 0) {
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  process.exit(exitCode);
}

/** 统一为小写去空白字符串，布尔转 yes/no，便于与枚举比较。 */
function norm(value) {
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  return String(value ?? '').trim().toLowerCase();
}

/** 读 JSON，兼容 Windows BOM；抛出的错误由调用方按 fail-closed 处理。 */
function readJsonStrict(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
}

function isNonEmptyFile(filePath) {
  return fs.existsSync(filePath) && fs.statSync(filePath).isFile();
}

function isDirectory(filePath) {
  return fs.existsSync(filePath) && fs.statSync(filePath).isDirectory();
}

/**
 * 布局判定优先级：checklist 显式 layout 字段 > 文件系统推断。
 * 三阶段模型不再有 state.json（旧状态机产物），布局要么由需求清单显式声明，
 * 要么按物理产物推断：有 outline.md 或 manuscript/ 目录即 long，否则 short。
 */
export function detectLayout(root, checklist) {
  const explicit = norm(checklist?.layout);
  if (explicit === 'short' || explicit === 'long') return { layout: explicit, source: 'checklist' };

  const hasOutline = isNonEmptyFile(path.join(root, 'outline.md'));
  const hasManuscriptDir = isDirectory(path.join(root, 'manuscript'));
  const hasRootManuscript = isNonEmptyFile(path.join(root, 'manuscript.md'));
  if (hasOutline || hasManuscriptDir) return { layout: 'long', source: 'filesystem' };
  if (hasRootManuscript) return { layout: 'short', source: 'filesystem' };
  return { layout: 'short', source: 'default' };
}

/**
 * 校验需求清单字段。只强制 prepare 阶段必需项：topic 与 requirements。
 * resolution 是交付阶段才要求的（yes 项交付前必须回填），此处不检查，与 fixtures 一致。
 * 可选块（contentProfile/delivery/wordCountRules 等）仅在出现时做取值校验，缺失不阻断。
 */
export function checkChecklistShape(checklist) {
  const failures = [];

  if (typeof checklist.topic !== 'string' || !checklist.topic.trim()) {
    failures.push('requirement-checklist.json 缺少非空 topic');
  }

  const requirements = checklist.requirements;
  if (!Array.isArray(requirements) || requirements.length === 0) {
    failures.push('requirement-checklist.json 的 requirements 至少需要一项');
  } else {
    let mainCount = 0;
    requirements.forEach((requirement, index) => {
      if (!requirement || typeof requirement !== 'object' || Array.isArray(requirement)) {
        failures.push(`requirements[${index}] 必须是对象`);
        return;
      }
      if (typeof requirement.requirement !== 'string' || !requirement.requirement.trim()) {
        failures.push(`requirements[${index}] 缺少非空 requirement 文本`);
      }
      const inScope = norm(requirement.in_scope);
      if (inScope !== 'yes' && inScope !== 'no') {
        failures.push(`requirements[${index}].in_scope 必须为 yes 或 no（实际：${JSON.stringify(requirement.in_scope)}）`);
      }
      if (norm(requirement.priority) === 'main') mainCount += 1;
    });
    if (mainCount === 0) failures.push('requirements 至少需要一项 priority: main');
  }

  if (checklist.wordCountRules !== undefined) {
    if (!Array.isArray(checklist.wordCountRules)) {
      failures.push('wordCountRules 必须是数组');
    } else {
      checklist.wordCountRules.forEach((rule, index) => {
        if (!rule || typeof rule !== 'object' || Array.isArray(rule)) {
          failures.push(`wordCountRules[${index}] 必须是对象`);
          return;
        }
        // 复用字数门禁的 ruleBounds 校验容差合法性（0-20），保持与写作阶段口径一致。
        const bounds = ruleBounds(rule);
        if (!bounds.toleranceValid) {
          failures.push(`wordCountRules[${index}].tolerancePercent 必须在 0-20 之间（实际：${rule.tolerancePercent}）`);
        }
        const hasAnyBound = ['target', 'minimum', 'maximum', 'minimumAdded']
          .some(key => Number.isFinite(Number(rule[key])));
        if (!hasAnyBound) {
          failures.push(`wordCountRules[${index}] 必须至少含 target/minimum/maximum/minimumAdded 之一`);
        }
      });
    }
  }

  return failures;
}

/**
 * 执行准备阶段检查。返回结构化结果供 CLI 或其它脚本使用。
 * @param {{ workspace?: string, writeReport?: boolean }} options
 * @returns {{ status: 'pass'|'fail'|'error', ... }}
 */
export function checkPrepare({ workspace = process.cwd(), writeReport = false } = {}) {
  const root = path.resolve(workspace);
  const checklistPath = path.join(root, ...CHECKLIST_RELATIVE);

  if (!isNonEmptyFile(checklistPath)) {
    return {
      status: 'fail',
      stage: 'prepare',
      code: 1,
      failures: [`缺少需求清单 ${CHECKLIST_RELATIVE.join('/')}`],
      fix: `创建 ${CHECKLIST_RELATIVE.join('/')}，填写 topic 与 requirements（见 references/checklist-schema.md）。`,
    };
  }

  let checklist;
  try {
    checklist = readJsonStrict(checklistPath);
  } catch (error) {
    return {
      status: 'error',
      stage: 'prepare',
      code: 2,
      failures: [`requirement-checklist.json 不是合法 JSON：${error.message}`],
    };
  }
  if (!checklist || typeof checklist !== 'object' || Array.isArray(checklist)) {
    return {
      status: 'error',
      stage: 'prepare',
      code: 2,
      failures: ['requirement-checklist.json 顶层必须是对象'],
    };
  }

  const failures = checkChecklistShape(checklist);
  const { layout, source: layoutSource } = detectLayout(root, checklist);

  let outline = null;
  if (layout === 'long') {
    // long 稿必须先冻结大纲：调既有 outline-structure-gate 校验章节表/依赖/预算/台账一致。
    const gate = runOutlineStructureGate({ workspace: root, writeReport });
    outline = {
      status: gate.status,
      failureCount: gate.failureCount,
      summary: gate.summary,
      reportPath: gate.reportPath,
    };
    for (const failure of gate.failures) {
      const location = failure.line ? `:${failure.line}` : '';
      failures.push(`[outline] ${failure.rule} (${failure.file || 'outline.md'}${location})：${failure.message}`);
    }
  }

  const status = failures.length === 0 ? 'pass' : 'fail';
  const payload = {
    status,
    stage: 'prepare',
    code: status === 'pass' ? 0 : 1,
    workspace: root,
    layout,
    layoutSource,
    checklistPath: path.relative(root, checklistPath).split(path.sep).join('/'),
    outline,
    failures,
  };
  if (failures.length > 0) {
    payload.fix = '按 failures 逐条补齐需求清单与大纲结构，再重跑 make prepare。';
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
    process.stdout.write('用法: node scripts/pipeline/check_prepare.mjs --workspace <path> [--write-report]\n');
    return;
  }
  try {
    const result = checkPrepare(options);
    emit(result, result.code ?? (result.status === 'pass' ? 0 : 1));
  } catch (error) {
    emit({ status: 'error', stage: 'prepare', code: 2, failures: [error instanceof Error ? error.message : String(error)] }, 2);
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

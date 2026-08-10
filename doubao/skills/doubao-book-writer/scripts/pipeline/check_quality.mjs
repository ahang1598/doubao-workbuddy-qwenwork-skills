#!/usr/bin/env node
// 可选深度质检：包装 quality-score-engine（S/P/C/B 四层评分）与
// machine-quality-engine（破折号/长句/绝对化/无来源数字/命令词密度）。
//
// 这是决策十确认的「可选目标」（make quality / DEEP_QUALITY=1），不进 write 强制门，
// 避免多维评分误伤正常写作。write 阶段只跑形态+字数（check_draft）。
//
// 只调用既有引擎的导出函数，不重写评分逻辑：
//   - 评分引擎用纯函数 auditQualityFile（逐文件打分，无隐式落盘）。
//   - 机器质检引擎只暴露 CLI 版 runMachineQualityCli（会 console.log 并写 qc-output），
//     故在调用期间静默 console 并通过 --json-out 读回它写出的报告，保持本脚本 stdout 只输出聚合 JSON。
//
// 参数 --workspace [--min-score 7.5]。产物 .doubao-book-writer/reports/quality_check.json。
// exit code：0 通过 / 1 质量未达标 / 2 环境或参数错误。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { bundleRootFromUrl } from '../lib/quality-runtime.mjs';
import { globSync } from '../lib/simple-glob.mjs';
import { auditQualityFile, summarizeQualityResults } from '../quality/quality-score-engine.mjs';
import { runMachineQualityCli } from '../quality/machine-quality-engine.mjs';
import { detectLayout } from './check_prepare.mjs';

const REPORT_RELATIVE = ['.doubao-book-writer', 'reports', 'quality_check.json'];
const MACHINE_REPORT_RELATIVE = ['.doubao-book-writer', 'reports', 'quality-machine.json'];
// 本包根目录：references/ 与 sub-skills/ 词表所在目录。scripts/pipeline -> ../..。
const BUNDLE_ROOT = bundleRootFromUrl(import.meta.url);

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

/** short 稿取根 manuscript.md；long 稿取 manuscript 目录下全部章节（相对 workspace）。 */
function manuscriptTargets(root, layout) {
  if (layout === 'long') {
    return globSync('manuscript/**/*.md', { cwd: root, nodir: true })
      .sort((left, right) => left.localeCompare(right, 'zh-Hans-CN', { numeric: true }));
  }
  return fs.existsSync(path.join(root, 'manuscript.md')) ? ['manuscript.md'] : [];
}

/**
 * 静默 console 运行 machine 引擎并读回其 JSON 报告。
 * machine 引擎大量 console.log 且没有纯函数导出，直接调用会污染本脚本 stdout；
 * 这里临时替换 console，调用后恢复，再读它写出的报告文件。
 */
function runMachineQualitySilently(root, targets) {
  const machineReportPath = path.join(root, ...MACHINE_REPORT_RELATIVE);
  fs.mkdirSync(path.dirname(machineReportPath), { recursive: true });
  const argv = ['node', 'machine-quality-engine', '--workspace', root, '--json-out', machineReportPath];
  for (const target of targets) argv.push('--inputs', target);

  const originalLog = console.log;
  const originalError = console.error;
  console.log = () => {};
  console.error = () => {};
  let code;
  try {
    code = runMachineQualityCli(argv, BUNDLE_ROOT);
  } finally {
    console.log = originalLog;
    console.error = originalError;
  }
  const report = readJsonOptional(machineReportPath);
  return { code, machineReportPath, report };
}

/**
 * 执行深度质检。
 * @param {{ workspace?: string, minScore?: number }} options
 */
export function checkQuality({ workspace = process.cwd(), minScore = 7.5 } = {}) {
  const root = path.resolve(workspace);
  const checklist = readJsonOptional(path.join(root, '.doubao-book-writer', 'requirement-checklist.json'));
  const { layout, source: layoutSource } = detectLayout(root, checklist);
  const targets = manuscriptTargets(root, layout);

  if (targets.length === 0) {
    return {
      status: 'error',
      stage: 'quality',
      code: 2,
      workspace: root,
      layout,
      failures: ['未找到可质检的正文文件；先完成 write 阶段。'],
    };
  }

  // 1. S/P/C/B 四层评分（纯函数，逐文件）。
  const scoreResults = targets.map(target =>
    auditQualityFile(path.resolve(root, target), { bundleRoot: BUNDLE_ROOT, minScore }));
  const scoreSummary = summarizeQualityResults(scoreResults, minScore);

  // 2. 机器可检项（破折号/长句/绝对化/无来源数字等）。
  const machine = runMachineQualitySilently(root, targets);

  const failures = [];
  for (const result of scoreResults) {
    if (!result.threshold?.passed) {
      failures.push(`[score] ${path.relative(root, result.filePath).split(path.sep).join('/')} 综合 ${result.scores.overall}/10 低于门槛 ${minScore}`);
    }
  }
  for (const issue of machine.report?.issues || []) failures.push(`[machine] ${issue}`);

  const status = failures.length === 0 ? 'pass' : 'fail';
  const payload = {
    status,
    stage: 'quality',
    code: status === 'pass' ? 0 : 1,
    workspace: root,
    layout,
    layoutSource,
    minScore,
    checkedFiles: targets,
    result: {
      score: {
        total: scoreSummary.total,
        passed: scoreSummary.passed,
        failed: scoreSummary.failed,
        avgScore: scoreSummary.avgScore,
        files: scoreResults.map(item => ({
          file: path.relative(root, item.filePath).split(path.sep).join('/'),
          overall: item.scores.overall,
          layers: { S: item.scores.S, P: item.scores.P, C: item.scores.C, B: item.scores.B },
          passed: item.threshold?.passed ?? false,
        })),
      },
      machine: {
        issueCount: machine.report?.issueCount ?? null,
        warningCount: machine.report?.warningCount ?? null,
        reportPath: machine.machineReportPath,
      },
    },
    failures,
    warnings: machine.report?.warnings || [],
  };
  if (failures.length > 0) payload.fix = '按 failures 修正正文质量（评分/机器项），再重跑 make quality。';

  const reportPath = path.join(root, ...REPORT_RELATIVE);
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  payload.reportPath = reportPath;

  return payload;
}

function parseArgs(argv) {
  const options = { workspace: process.cwd(), minScore: 7.5 };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--min-score') options.minScore = Number(argv[++index]) || options.minScore;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write('用法: node scripts/pipeline/check_quality.mjs --workspace <path> [--min-score 7.5]\n');
    return;
  }
  try {
    const result = checkQuality(options);
    emit(result, result.code ?? (result.status === 'pass' ? 0 : 1));
  } catch (error) {
    emit({ status: 'error', stage: 'quality', code: 2, failures: [error instanceof Error ? error.message : String(error)] }, 2);
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

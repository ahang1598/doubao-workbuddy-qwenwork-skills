#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { loadScaleTiers, pickWritingStrategyTier } from '../lib/volume-tiers.mjs';

const DEFAULT_BUNDLE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

function cliOptions(argv) {
  const options = { workspace: null, bundleRoot: DEFAULT_BUNDLE_ROOT, strict: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') options.workspace = argv[++index];
    else if (token === '--bundle-root') options.bundleRoot = path.resolve(argv[++index] || '');
    else if (token === '--strict') options.strict = true;
  }
  return options;
}

function jsonObject(filePath) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function draftRange(config, target, chapterCount) {
  const average = target != null && chapterCount > 0 ? Math.round(target / chapterCount) : null;
  const minimum = finite(config.chapterDraftWordMin)
    ?? (average == null ? null : Math.max(500, Math.round(average * 0.7)));
  const maximum = finite(config.chapterDraftWordMax)
    ?? (average == null ? null : Math.max(minimum || 0, Math.round(average * 1.3)));
  return { minimum, maximum };
}

export function assessWritingContract(config = {}, tiers) {
  const warnings = [];
  const blockers = [];
  const target = finite(config.targetWordCount);
  const chapterCount = finite(config.plannedChapterTotal);
  const plannedMinimum = finite(config.plannedChapterMin);
  const plannedMaximum = finite(config.plannedChapterMax);
  const range = draftRange(config, target, chapterCount);

  if (chapterCount != null && plannedMinimum != null && chapterCount < plannedMinimum) {
    blockers.push(`plannedChapterTotal(${chapterCount}) < plannedChapterMin(${plannedMinimum})`);
  }
  if (chapterCount != null && plannedMaximum != null && chapterCount > plannedMaximum) {
    blockers.push(`plannedChapterTotal(${chapterCount}) > plannedChapterMax(${plannedMaximum})`);
  }
  if (target != null && chapterCount > 0 && range.minimum != null && range.maximum != null) {
    const lowerWarning = chapterCount * range.minimum * 0.5;
    const upperWarning = chapterCount * range.maximum * 2;
    if (target < lowerWarning) warnings.push(`targetWordCount(${target}) 低于章节下限折算值的一半（约 ${Math.round(lowerWarning)}），请复核全书目标是否偏低。`);
    if (target > upperWarning) warnings.push(`targetWordCount(${target}) 超过章节上限折算值两倍（约 ${Math.round(upperWarning)}），请复核章数规划和单章字数区间。`);
  }

  const strategy = pickWritingStrategyTier(target, chapterCount, tiers);
  if (strategy && strategy.byWords !== strategy.byChapters) {
    warnings.push(`字数推导档位 ${strategy.byWords}、章数推导档位 ${strategy.byChapters} 不一致，当前采用较高档 ${strategy.tier}（${strategy.policy}）。请复核 targetWordCount 与 plannedChapterTotal。`);
  }
  return { warnings, blockers, strategy };
}

function materialBudgetWarning(workspace, config) {
  const limit = finite(config.materialGatherNotesMaxChars);
  const inventory = path.join(workspace, '.doubao-book-writer', 'material-inventory.md');
  if (!(limit > 0) || !fs.existsSync(inventory)) return null;
  const actual = fs.readFileSync(inventory, 'utf8').length;
  return actual > limit
    ? `material-inventory.md length=${actual}, limit=${limit}；素材摘记超出预算，扩大范围前需拿到用户确认。`
    : null;
}

export function runWritingContractCheck(workspace, bundleRoot, options = {}) {
  const config = jsonObject(path.join(workspace, '.doubao-book-writer', 'project-config.json'));
  if (!config) {
    return options.strict
      ? { code: 2, warnings: [], blockers: ['缺少 .doubao-book-writer/project-config.json'], strategy: null }
      : { code: 0, warnings: [], blockers: [], strategy: null };
  }
  const result = assessWritingContract(config, loadScaleTiers(bundleRoot));
  const budgetWarning = materialBudgetWarning(workspace, config);
  const warnings = budgetWarning ? [...result.warnings, budgetWarning] : result.warnings;
  const code = result.blockers.length > 0 ? 2 : options.strict && warnings.length > 0 ? 1 : 0;
  return { code, warnings, blockers: result.blockers, strategy: result.strategy };
}

function main() {
  const options = cliOptions(process.argv);
  if (!options.workspace) {
    process.stderr.write('用法: node scripts/gates/style-contract-gate.mjs --workspace <工作目录> [--bundle-root <本包根>] [--strict]\n');
    process.exitCode = 2;
    return;
  }
  const result = runWritingContractCheck(path.resolve(options.workspace), options.bundleRoot, options);
  for (const warning of result.warnings) process.stderr.write(`[writing-contract] WARN: ${warning}\n`);
  for (const blocker of result.blockers) process.stderr.write(`[writing-contract] BLOCK: ${blocker}\n`);
  if (result.strategy) process.stdout.write(`[writing-contract] 策略档位: ${result.strategy.tier}（${result.strategy.policy}） 字=${result.strategy.byWords} 章=${result.strategy.byChapters}\n`);
  process.exitCode = result.code;
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

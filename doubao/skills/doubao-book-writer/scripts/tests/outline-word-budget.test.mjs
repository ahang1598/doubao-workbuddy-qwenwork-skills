import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { runOutlineStructureGate } from '../gates/outline-structure-gate.mjs';

function workspace() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dbw-outline-budget-'));
  fs.mkdirSync(path.join(root, '.doubao-book-writer'), { recursive: true });
  return root;
}

function write(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, 'utf8');
}

function writeOutline(root, firstTarget, secondTarget, totalTarget) {
  write(path.join(root, 'outline.md'), `# 白皮书\n\n## 核心主张\n\n形成可执行判断。\n\n## 目标读者\n\n面向项目负责人。\n\n## 作者声音\n\n专业、克制、具体。\n\n## 章节规划\n\n| 章节 | 标题 | 核心问题 | 用户收获 | 目标字数 |\n|---|---|---|---|---|\n| ch01 | 现状 | 当前问题是什么 | 理解问题边界 | ${firstTarget} |\n| ch02 | 路径 | 如何实施 | 获得行动路径 | ${secondTarget} |\n\n## 章节依赖关系\n\n| 章节 | 前置章节 |\n|---|---|\n| ch01 | — |\n| ch02 | ch01 |\n\n## 总字数目标\n\n${totalTarget} 字\n`);
  write(path.join(root, 'chapter-ledger.md'), `| 章节 | 标题 | 状态 | 目标字数 | 当前字数 |\n|---|---|---|---|---|\n| ch01 | 现状 | 待写 | ${firstTarget} | 0 |\n| ch02 | 路径 | 待写 | ${secondTarget} | 0 |\n`);
}

test('outline gate requires chapter budgets to allocate the declared total exactly', () => {
  const root = workspace();
  writeOutline(root, 4000, 5000, 10000);
  const result = runOutlineStructureGate({ workspace: root, writeReport: false });
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some(failure => failure.rule === 'chapter-budget-not-allocated'));

  writeOutline(root, 4000, 6000, 10000);
  assert.equal(runOutlineStructureGate({ workspace: root, writeReport: false }).status, 'pass');
});

test('outline total must stay inside the checklist word-count contract', () => {
  const root = workspace();
  write(path.join(root, '.doubao-book-writer', 'requirement-checklist.json'), `${JSON.stringify({
    wordCountRules: [{ id: 'total', target: 10000, tolerancePercent: 10 }],
  })}\n`);
  writeOutline(root, 6000, 6000, 12000);
  const result = runOutlineStructureGate({ workspace: root, writeReport: false });
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some(failure => failure.rule === 'outline-total-above-contract'));
});

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { auditSimilarity } from '../quality/origin-similarity-audit.mjs';

test('similarity audit detects a copied text file moved to another path', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'dbw-similarity-audit-'));
  const targetRoot = path.join(root, 'target');
  const referenceRoot = path.join(root, 'reference');
  fs.mkdirSync(path.join(targetRoot, 'new'), { recursive: true });
  fs.mkdirSync(path.join(referenceRoot, 'old'), { recursive: true });
  const content = '# 第一章\n\n这是一段足够长的独立实现审计文本，用于识别改名后仍然相同的文件。\n';
  fs.writeFileSync(path.join(targetRoot, 'new', 'contract.md'), content, 'utf8');
  fs.writeFileSync(path.join(referenceRoot, 'old', 'contract.md'), content, 'utf8');
  const result = auditSimilarity({ targetRoot, referenceRoot, threshold: 0.85 });
  assert.equal(result.exactCount, 0);
  assert.equal(result.crossPathNearCount, 1);
  assert.equal(result.crossPathNear[0].targetPath, 'new/contract.md');
  assert.equal(result.crossPathNear[0].referencePath, 'old/contract.md');
  assert.equal(result.crossPathNear[0].score, 1);
});

test('similarity audit excludes a nested target from its parent reference tree', () => {
  const referenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'dbw-similarity-parent-'));
  const targetRoot = path.join(referenceRoot, 'nested-target');
  fs.mkdirSync(targetRoot, { recursive: true });
  fs.writeFileSync(path.join(targetRoot, 'only-here.md'), '# 唯一文件\n\n只存在于目标子树。\n', 'utf8');
  const result = auditSimilarity({ targetRoot, referenceRoot, threshold: 0.85 });
  assert.equal(result.sharedPathCount, 0);
  assert.equal(result.crossPathNearCount, 0);
});

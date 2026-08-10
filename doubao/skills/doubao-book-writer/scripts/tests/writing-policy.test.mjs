import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { checkWritingShape, validateWritingText } from '../quality/check-writing-shape.mjs';

test('Chinese publication headings reject numbered section labels', () => {
  const result = validateWritingText('# 第一章 行业背景\n\n## 第一节 智能制造的边界\n\n正文。\n');
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some((failure) => failure.rule === 'forbidden-section-heading'));
});

test('Chinese publication headings allow chapter, topic, and subtopic hierarchy', () => {
  const result = validateWritingText('# 第一章 行业背景\n\n## 一、智能制造的边界\n\n### （一）概念演进\n\n正文。\n');
  assert.equal(result.status, 'pass', JSON.stringify(result));
});

test('third-level sections allow restrained unnumbered bold subheadings and functional tables', () => {
  const result = validateWritingText(`# 第一章 电脑基础

## 一、设备操作

### （一）关机与重启

**正常关机**

关机前需保存所有工作文件并关闭程序，避免尚未写入磁盘的数据丢失。不同系统的入口不同，但都应优先使用系统菜单完成关机。

| 系统 | 操作入口 |
| --- | --- |
| Windows | 开始菜单中的电源选项 |
| macOS | 苹果菜单中的关机选项 |

表格用于快速定位入口，真正执行时仍应先确认文件已经保存。

**重启与睡眠**

系统卡顿或完成更新后可以重启；短时间离开时使用睡眠，以保留当前工作状态。
`);
  assert.equal(result.status, 'pass', JSON.stringify(result));
});

test('parenthesized numbering below a third-level heading is rejected as a pseudo fourth level', () => {
  const result = validateWritingText(`# 第一章 电脑基础

## 一、设备操作

### （一）关机与重启

（一）正常关机

关机前需保存所有工作文件并关闭程序。

（二）重启与睡眠

系统卡顿后可以选择重启。
`);
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some((failure) => failure.rule === 'pseudo-fourth-level-heading'));
});

test('visible heading depth stops at three and numbered headings require semantic titles', () => {
  const result = validateWritingText('# 第一章 电脑基础\n\n## 一、设备操作\n\n### （一）\n\n#### 应急处理\n');
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some((failure) => failure.rule === 'heading-title-missing'));
  assert.ok(result.failures.some((failure) => failure.rule === 'heading-depth-exceeded'));
});

test('excessive bold and malformed tables fail writing-shape validation', () => {
  const result = validateWritingText(`# 第一章 电脑基础

**重点一** **重点二** **重点三** **重点四** **重点五**

| 单列 |
| --- |
| 内容 |
`);
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some((failure) => failure.rule === 'excessive-bold'));
  assert.ok(result.failures.some((failure) => failure.rule === 'malformed-table'));
});

test('decorative Markdown callouts fail writing-shape validation', () => {
  const result = validateWritingText('# 第一章 行业背景\n\n> [!NOTE]\n> 这是装饰性高亮块。\n');
  assert.equal(result.status, 'fail');
  assert.ok(result.failures.some((failure) => failure.rule === 'decorative-callout'));
});

test('ordinary sourced blockquotes remain available', () => {
  const result = validateWritingText('# 第一章 行业背景\n\n> 这是需要保留的原始引语。\n');
  assert.equal(result.status, 'pass', JSON.stringify(result));
});

test('writing shape report reuses unchanged file results by policy version and sha256', () => {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'dbw-writing-cache-'));
  const manuscriptPath = path.join(workspace, 'manuscript.md');
  fs.writeFileSync(manuscriptPath, '# 第一章 行业背景\n\n正文。\n', 'utf8');
  const first = checkWritingShape({ workspace });
  assert.equal(first.scannedFiles, 1);
  assert.equal(first.reusedFiles, 0);
  const second = checkWritingShape({ workspace });
  assert.equal(second.scannedFiles, 0);
  assert.equal(second.reusedFiles, 1);
  assert.equal(second.files[0].reused, true);

  fs.appendFileSync(manuscriptPath, '\n新增内容。\n', 'utf8');
  const third = checkWritingShape({ workspace });
  assert.equal(third.scannedFiles, 1);
  assert.equal(third.reusedFiles, 0);
  assert.equal(third.files[0].reused, false);
});

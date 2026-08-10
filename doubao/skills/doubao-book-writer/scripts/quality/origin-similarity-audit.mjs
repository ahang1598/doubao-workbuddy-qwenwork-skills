#!/usr/bin/env node
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const EXCLUDED_DIRECTORIES = new Set(['.git', 'node_modules']);
const TEXT_EXTENSIONS = new Set(['.md', '.mjs', '.js', '.json', '.txt', '.yaml', '.yml']);

function filesUnder(root, directory = root, result = []) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && EXCLUDED_DIRECTORIES.has(entry.name)) continue;
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) filesUnder(root, absolute, result);
    else if (entry.isFile()) result.push(path.relative(root, absolute).split(path.sep).join('/'));
  }
  return result;
}

function digest(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

function shingles(text, width = 7) {
  const normalized = text
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s\p{P}\p{S}]+/gu, '');
  const values = new Set();
  for (let index = 0; index <= normalized.length - width; index += 1) {
    values.add(normalized.slice(index, index + width));
  }
  return values;
}

function similaritySets(leftSet, rightSet) {
  if (leftSet.size === 0 && rightSet.size === 0) return 1;
  if (leftSet.size === 0 || rightSet.size === 0) return 0;
  let intersection = 0;
  for (const value of leftSet) if (rightSet.has(value)) intersection += 1;
  return intersection / (leftSet.size + rightSet.size - intersection);
}

function similarity(left, right) {
  return similaritySets(shingles(left), shingles(right));
}

function parseArgs(argv) {
  const options = { threshold: 0.85, reportOnly: false };
  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--target-root') options.targetRoot = path.resolve(argv[++index] || '');
    else if (token === '--reference-root') options.referenceRoot = path.resolve(argv[++index] || '');
    else if (token === '--json-out') options.jsonOut = path.resolve(argv[++index] || '');
    else if (token === '--threshold') options.threshold = Number(argv[++index]);
    else if (token === '--report-only') options.reportOnly = true;
  }
  return options;
}

export function auditSimilarity({ targetRoot, referenceRoot, threshold = 0.85 } = {}) {
  if (!targetRoot || !referenceRoot) throw new Error('targetRoot and referenceRoot are required');
  const targetFiles = filesUnder(targetRoot);
  const nestedTarget = path.relative(referenceRoot, targetRoot).split(path.sep).join('/');
  const nestedPrefix = nestedTarget && !nestedTarget.startsWith('..') ? `${nestedTarget}/` : null;
  const referenceFiles = filesUnder(referenceRoot).filter(relativePath => !nestedPrefix || !relativePath.startsWith(nestedPrefix));
  const referenceSet = new Set(referenceFiles);
  const sharedPaths = targetFiles.filter(relativePath => referenceSet.has(relativePath));
  const exact = [];
  const near = [];
  for (const relativePath of sharedPaths) {
    const targetBuffer = fs.readFileSync(path.join(targetRoot, relativePath));
    const referenceBuffer = fs.readFileSync(path.join(referenceRoot, relativePath));
    if (digest(targetBuffer) === digest(referenceBuffer)) {
      exact.push(relativePath);
      continue;
    }
    if (!TEXT_EXTENSIONS.has(path.extname(relativePath).toLowerCase())) continue;
    const score = similarity(targetBuffer.toString('utf8'), referenceBuffer.toString('utf8'));
    if (score >= threshold) near.push({ path: relativePath, score: Number(score.toFixed(4)) });
  }
  near.sort((left, right) => right.score - left.score);
  const crossPathNear = [];
  const textTargets = targetFiles.filter(relativePath => TEXT_EXTENSIONS.has(path.extname(relativePath).toLowerCase()));
  const textReferences = referenceFiles.filter(relativePath => TEXT_EXTENSIONS.has(path.extname(relativePath).toLowerCase()));
  const referenceByExtension = new Map();
  for (const relativePath of textReferences) {
    const extension = path.extname(relativePath).toLowerCase();
    if (!referenceByExtension.has(extension)) referenceByExtension.set(extension, []);
    referenceByExtension.get(extension).push(relativePath);
  }
  const textCache = new Map();
  const shingleCache = new Map();
  const textFor = (root, relativePath) => {
    const key = `${root}\u0000${relativePath}`;
    if (!textCache.has(key)) textCache.set(key, fs.readFileSync(path.join(root, relativePath), 'utf8'));
    return textCache.get(key);
  };
  const shinglesFor = (root, relativePath) => {
    const key = `${root}\u0000${relativePath}`;
    if (!shingleCache.has(key)) shingleCache.set(key, shingles(textFor(root, relativePath)));
    return shingleCache.get(key);
  };
  for (const targetPath of textTargets) {
    const targetText = textFor(targetRoot, targetPath);
    let best = null;
    for (const referencePath of referenceByExtension.get(path.extname(targetPath).toLowerCase()) || []) {
      if (referencePath === targetPath) continue;
      const referenceText = textFor(referenceRoot, referencePath);
      const larger = Math.max(targetText.length, referenceText.length, 1);
      if (Math.min(targetText.length, referenceText.length) / larger < 0.6) continue;
      const score = similaritySets(shinglesFor(targetRoot, targetPath), shinglesFor(referenceRoot, referencePath));
      if (score >= threshold && (!best || score > best.score)) best = { targetPath, referencePath, score };
    }
    if (best) crossPathNear.push({ ...best, score: Number(best.score.toFixed(4)) });
  }
  crossPathNear.sort((left, right) => right.score - left.score);
  return {
    targetRoot,
    referenceRoot,
    threshold,
    targetFileCount: targetFiles.length,
    sharedPathCount: sharedPaths.length,
    exactCount: exact.length,
    nearCount: near.length,
    crossPathNearCount: crossPathNear.length,
    exact,
    near,
    crossPathNear,
  };
}

function main() {
  const options = parseArgs(process.argv);
  try {
    const targetRoot = options.targetRoot
      || path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
    const result = auditSimilarity({
      targetRoot,
      referenceRoot: options.referenceRoot,
      threshold: options.threshold,
    });
    const output = `${JSON.stringify(result, null, 2)}\n`;
    if (options.jsonOut) {
      fs.mkdirSync(path.dirname(options.jsonOut), { recursive: true });
      fs.writeFileSync(options.jsonOut, output, 'utf8');
    }
    process.stdout.write(output);
    process.exitCode = options.reportOnly || (result.exactCount === 0 && result.nearCount === 0 && result.crossPathNearCount === 0) ? 0 : 2;
  } catch (error) {
    process.stderr.write(`[origin-similarity-audit] ${error.message}\n`);
    process.exitCode = 1;
  }
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invokedPath === fileURLToPath(import.meta.url)) main();

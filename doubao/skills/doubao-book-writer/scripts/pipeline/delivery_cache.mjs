#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const RECEIPT_RELATIVE = ['.doubao-book-writer', 'delivery-receipt.json'];

function readJson(filePath) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, ''));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function sha256(filePath) {
  const hash = createHash('sha256');
  hash.update(fs.readFileSync(filePath));
  return hash.digest('hex');
}

function receiptPath(workspace) {
  return path.join(path.resolve(workspace), ...RECEIPT_RELATIVE);
}

function docUrlFrom(result) {
  return result?.data?.document?.url
    || result?.data?.url
    || result?.url
    || '';
}

function docIdFrom(result) {
  return result?.data?.document?.document_id
    || result?.data?.document?.documentId
    || result?.data?.document_id
    || result?.document_id
    || '';
}

export function checkDeliveryCache({ workspace, finalPath } = {}) {
  if (!workspace || !finalPath) return { reusable: false, reason: 'missing workspace or final' };
  const root = path.resolve(workspace);
  const final = path.resolve(finalPath);
  if (!fs.existsSync(final) || !fs.statSync(final).isFile()) return { reusable: false, reason: 'missing final' };
  const receipt = readJson(receiptPath(root));
  if (!receipt) return { reusable: false, reason: 'missing receipt' };
  const lark = readJson(path.join(root, '.doubao-book-writer', 'reports', 'lark_check.json'));
  if (lark?.status !== 'pass') return { reusable: false, reason: 'lark report not pass' };
  const currentHash = sha256(final);
  if (receipt.finalSha256 !== currentHash) return { reusable: false, reason: 'final changed', currentHash };
  if (!receipt.url) return { reusable: false, reason: 'receipt missing url', currentHash };
  return { reusable: true, url: receipt.url, documentId: receipt.documentId || '', finalSha256: currentHash };
}

export function recordDelivery({ workspace, finalPath, docResultPath, larkReportPath } = {}) {
  if (!workspace || !finalPath || !docResultPath || !larkReportPath) {
    throw new Error('missing workspace/final/doc-result/lark-report');
  }
  const root = path.resolve(workspace);
  const final = path.resolve(finalPath);
  const docResult = readJson(docResultPath);
  const lark = readJson(larkReportPath);
  if (lark?.status !== 'pass') throw new Error('lark report is not pass');
  const url = docUrlFrom(docResult);
  if (!url) throw new Error('doc-result does not contain document url');
  const receipt = {
    schemaVersion: 'delivery-cache-v1',
    generatedAt: new Date().toISOString(),
    finalPath: path.relative(root, final).split(path.sep).join('/'),
    finalSha256: sha256(final),
    url,
    documentId: docIdFrom(docResult),
    larkReportPath: path.relative(root, path.resolve(larkReportPath)).split(path.sep).join('/'),
  };
  const target = receiptPath(root);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return { recorded: true, receiptPath: target, url, finalSha256: receipt.finalSha256 };
}

function parseArgs(argv) {
  const args = { command: argv[2] || '', workspace: process.cwd(), finalPath: null, docResultPath: null, larkReportPath: null };
  for (let index = 3; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--workspace') args.workspace = argv[++index];
    else if (token === '--final') args.finalPath = argv[++index];
    else if (token === '--doc-result') args.docResultPath = argv[++index];
    else if (token === '--lark-report') args.larkReportPath = argv[++index];
    else if (token === '--help' || token === '-h') args.help = true;
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help || !['check', 'record'].includes(args.command)) {
    process.stdout.write('用法: node scripts/pipeline/delivery_cache.mjs <check|record> --workspace <path> --final <final.md> [--doc-result <json> --lark-report <json>]\n');
    return;
  }
  try {
    if (args.command === 'check') {
      const result = checkDeliveryCache(args);
      process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
      process.exitCode = result.reusable ? 0 : 1;
      return;
    }
    const result = recordDelivery(args);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 2;
  }
}

const invoked = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invoked === fileURLToPath(import.meta.url)) main();

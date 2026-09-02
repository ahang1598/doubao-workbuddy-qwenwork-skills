import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { inspectReviewFile, resolveUploadArguments, uploadReviewFile } from './upload-review-file-lib.mjs';

test('resolves explicit file selector and presigned URL', () => {
  const parsed = resolveUploadArguments([
    '--file-path', '/tmp/合同.docx',
    '--upload-url', 'https://cos.example/upload?signature=secret',
  ]);
  assert.deepEqual(parsed.fileArgs, ['--file-path', '/tmp/合同.docx']);
  assert.equal(parsed.uploadUrl, 'https://cos.example/upload?signature=secret');
});

test('uploads file with PUT and returns local metadata', async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'review-upload-'));
  const filePath = path.join(tempDir, '合同.docx');
  fs.writeFileSync(filePath, 'contract');
  let request;

  const result = await uploadReviewFile(filePath, 'https://cos.example/upload', async (url, options) => {
    request = { url, options };
    return new Response('', { status: 200 });
  });

  assert.equal(request.url, 'https://cos.example/upload');
  assert.equal(request.options.method, 'PUT');
  assert.equal(result.fileName, '合同.docx');
  assert.equal(result.fileSize, 8);
  fs.rmSync(tempDir, { recursive: true, force: true });
});

test('inspects local metadata before requesting an upload URL', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'review-upload-'));
  const filePath = path.join(tempDir, '合同.doc');
  fs.writeFileSync(filePath, 'legacy-doc');
  assert.deepEqual(inspectReviewFile(filePath), {
    fileName: '合同.doc',
    fileSize: 10,
    fileType: 'doc',
  });
  fs.rmSync(tempDir, { recursive: true, force: true });
});

test('marks 403 as an expired presigned URL without exposing URL', async () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'review-upload-'));
  const filePath = path.join(tempDir, '清单.xlsx');
  fs.writeFileSync(filePath, 'checklist');

  await assert.rejects(
    () => uploadReviewFile(filePath, 'https://cos.example/upload?signature=secret',
      async () => new Response('', { status: 403 })),
    error => error.code === 'PRESIGNED_URL_EXPIRED'
      && !error.message.includes('signature=secret'),
  );
  fs.rmSync(tempDir, { recursive: true, force: true });
});

test('does not read authentication environment variables', () => {
  const source = fs.readFileSync(new URL('./upload-review-file.mjs', import.meta.url), 'utf8')
    + fs.readFileSync(new URL('./upload-review-file-lib.mjs', import.meta.url), 'utf8');
  assert.equal(source.includes('RICHEEAI_TOKEN'), false);
  assert.equal(source.includes('RICHEEAI_API_BASE'), false);
});

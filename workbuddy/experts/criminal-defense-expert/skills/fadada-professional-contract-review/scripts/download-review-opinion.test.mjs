import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  downloadReviewOpinion,
  resolveResponseFileName,
} from './download-review-opinion-lib.mjs';

test('downloads a DOCX from the presigned URL without authentication headers', async () => {
  const cwd = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'review-opinion-'));
  let requestOptions;
  try {
    const result = await downloadReviewOpinion({
      downloadUrl: 'https://cos.example/review-opinion.docx?sign=one',
      fileName: '采购合同-审查意见书.docx',
      cwd,
      fetchImpl: async (_url, options) => {
        requestOptions = options;
        return new Response(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
          status: 200,
          headers: {
            'content-type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'content-length': '4',
          },
        });
      },
    });

    assert.equal(requestOptions.headers, undefined);
    assert.equal(result.fileName, '采购合同-审查意见书.docx');
    assert.deepEqual(await fs.promises.readFile(result.localPath), Buffer.from([0x50, 0x4b, 0x03, 0x04]));
  } finally {
    await fs.promises.rm(cwd, { recursive: true, force: true });
  }
});

test('reports an expired presigned URL with a stable error code', async () => {
  const cwd = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'review-opinion-'));
  try {
    await assert.rejects(
      downloadReviewOpinion({
        downloadUrl: 'https://cos.example/review-opinion.docx?expired=1',
        fileName: '审查意见书.docx',
        cwd,
        fetchImpl: async () => new Response('', { status: 403 }),
      }),
      error => error.code === 'PRESIGNED_URL_EXPIRED',
    );
  } finally {
    await fs.promises.rm(cwd, { recursive: true, force: true });
  }
});

test('sanitizes the MCP-provided file name', () => {
  assert.equal(resolveResponseFileName(null, '../采购:合同'), '采购 合同.docx');
});

test('download implementation does not read Richee client authentication variables', async () => {
  const source = await fs.promises.readFile(
    new URL('./download-review-opinion.mjs', import.meta.url),
    'utf8',
  );
  assert.equal(source.includes('RICHEEAI_TOKEN'), false);
  assert.equal(source.includes('RICHEEAI_API_BASE'), false);
  assert.equal(source.includes('richee-token'), false);
});

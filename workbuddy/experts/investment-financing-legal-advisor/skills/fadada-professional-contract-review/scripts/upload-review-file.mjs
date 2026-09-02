#!/usr/bin/env node
/**
 * 使用 MCP 返回的 PUT 预签名地址上传合同审查文件。
 *
 * 用法：
 *   node upload-review-file.mjs --attachment-id <附件ID> --upload-url <预签名URL>
 *   node upload-review-file.mjs --file-path <本地路径> --upload-url <预签名URL>
 */
import { resolveUploadFilePath } from './resolve-upload-input.mjs';
import { inspectReviewFile, resolveUploadArguments, uploadReviewFile } from './upload-review-file-lib.mjs';

function fail(message, code) {
  console.error(JSON.stringify({ success: false, code, message }));
  process.exit(1);
}

let uploadUrl;
let filePath;
try {
  const args = process.argv.slice(2);
  if (args.includes('--inspect')) {
    const fileArgs = args.filter(arg => arg !== '--inspect');
    filePath = resolveUploadFilePath(fileArgs);
    console.log(JSON.stringify({ success: true, ...inspectReviewFile(filePath) }));
    process.exit(0);
  }
  const parsed = resolveUploadArguments(args);
  uploadUrl = parsed.uploadUrl;
  filePath = resolveUploadFilePath(parsed.fileArgs);
} catch (error) {
  fail(error.message);
}

try {
  console.log(JSON.stringify(await uploadReviewFile(filePath, uploadUrl)));
} catch (error) {
  fail(error.message, error.code);
}

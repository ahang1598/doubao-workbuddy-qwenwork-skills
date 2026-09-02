#!/usr/bin/env node
/**
 * 使用 MCP 返回的预签名 URL 下载审查意见书到当前会话工作目录。
 *
 * 用法：node download-review-opinion.mjs --url <fileUrl> --file-name <fileName>
 */
import { downloadReviewOpinion } from './download-review-opinion-lib.mjs';

function fail(message, code) {
  console.error(JSON.stringify({ success: false, ...(code ? { code } : {}), message }));
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length !== 4
    || args[0] !== '--url'
    || !args[1]?.trim()
    || args[2] !== '--file-name'
    || !args[3]?.trim()) {
  fail('用法: node download-review-opinion.mjs --url <fileUrl> --file-name <fileName>');
}

try {
  const result = await downloadReviewOpinion({
    downloadUrl: args[1],
    fileName: args[3],
    cwd: process.cwd(),
  });
  console.log(JSON.stringify(result));
} catch (error) {
  const timedOut = error && (error.name === 'TimeoutError' || error.name === 'AbortError');
  fail(timedOut
    ? '审查意见书下载超时（120s 无响应），请稍后重试'
    : error.message, error?.code);
}

import fs from 'node:fs';
import path from 'node:path';

const MAX_SIZE = 50 * 1024 * 1024;

export function resolveUploadArguments(args) {
  const uploadUrlIndex = args.indexOf('--upload-url');
  if (uploadUrlIndex < 0 || !args[uploadUrlIndex + 1]) {
    throw new Error('缺少 --upload-url <预签名上传地址>');
  }
  const uploadUrl = args[uploadUrlIndex + 1];
  let parsedUrl;
  try {
    parsedUrl = new URL(uploadUrl);
  } catch {
    throw new Error('预签名上传地址格式无效');
  }
  if (parsedUrl.protocol !== 'https:') {
    throw new Error('预签名上传地址仅支持 HTTPS');
  }
  const fileArgs = args.filter((_, index) => index !== uploadUrlIndex && index !== uploadUrlIndex + 1);
  return { uploadUrl, fileArgs };
}

export async function uploadReviewFile(filePath, uploadUrl, fetchImpl = fetch) {
  const file = inspectReviewFile(filePath);

  let response;
  try {
    response = await fetchImpl(uploadUrl, {
      method: 'PUT',
      body: new Blob([fs.readFileSync(filePath)]),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (error) {
    const timedOut = error && (error.name === 'TimeoutError' || error.name === 'AbortError');
    throw new Error(timedOut
      ? '上传请求超时（120s 无响应）'
      : `上传请求失败: ${sanitizeError(error?.message)}`);
  }

  if (!response.ok) {
    const error = new Error(response.status === 403
      ? '预签名上传地址已失效或无权使用'
      : `对象存储上传失败（HTTP ${response.status}）`);
    error.code = response.status === 403 ? 'PRESIGNED_URL_EXPIRED' : 'UPLOAD_FAILED';
    throw error;
  }

  return { success: true, ...file };
}

export function inspectReviewFile(filePath) {
  if (!fs.existsSync(filePath)) throw new Error(`文件不存在: ${filePath}`);
  if (fs.statSync(filePath).isDirectory()) throw new Error(`路径为目录，请传入文件: ${filePath}`);
  const stat = fs.statSync(filePath);
  if (stat.size === 0) throw new Error('文件为空，无法上传');
  if (stat.size > MAX_SIZE) {
    throw new Error(`文件大小超过上限 50MB（当前 ${(stat.size / 1024 / 1024).toFixed(1)}MB）`);
  }

  return {
    fileName: path.basename(filePath),
    fileSize: stat.size,
    fileType: path.extname(filePath).slice(1).toLowerCase(),
  };
}

function sanitizeError(message) {
  return String(message || '未知网络错误').replace(/https?:\/\/\S+/g, '[redacted-url]');
}

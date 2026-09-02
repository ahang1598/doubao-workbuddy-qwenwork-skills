import fs from 'node:fs';
import path from 'node:path';

export const MAX_REVIEW_OPINION_BYTES = 50 * 1024 * 1024;

const OUTPUT_RELATIVE_DIR = path.join(
  '.cowork-temp',
  'attachments',
  'generated',
  'contract-review',
);

const DOCX_CONTENT_TYPES = new Set([
  'application/octet-stream',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]);

function decodeFileName(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function resolveResponseFileName(headerValue, requestedFileName) {
  let candidate = String(requestedFileName ?? '').trim();
  if (headerValue) {
    const extended = headerValue.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
    const plain = headerValue.match(/filename\s*=\s*"?([^";]+)"?/i);
    candidate = decodeFileName((extended?.[1] ?? plain?.[1] ?? candidate).trim());
  }
  const basename = path.posix.basename(candidate.replace(/\\/g, '/'))
    .replace(/[\u0000-\u001f<>:"/\\|?*]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  const safeName = basename || '审查意见书.docx';
  return safeName.toLowerCase().endsWith('.docx') ? safeName : `${safeName}.docx`;
}

async function resolveAvailablePath(directory, fileName) {
  const extension = path.extname(fileName);
  const baseName = fileName.slice(0, -extension.length);
  for (let index = 0; ; index += 1) {
    const suffix = index === 0 ? '' : ` (${index})`;
    const candidate = path.join(directory, `${baseName}${suffix}${extension}`);
    try {
      await fs.promises.access(candidate);
    } catch {
      return candidate;
    }
  }
}

function validateResponse(response, maxBytes) {
  if (!response.ok) {
    const error = new Error(`下载审查意见书失败: HTTP ${response.status}`);
    error.code = response.status === 403 ? 'PRESIGNED_URL_EXPIRED' : 'DOWNLOAD_FAILED';
    throw error;
  }
  const contentType = (response.headers.get('content-type') ?? '').split(';')[0].trim().toLowerCase();
  if (!DOCX_CONTENT_TYPES.has(contentType)) {
    throw new Error(`下载审查意见书失败: 非Word响应(${contentType || 'unknown'})`);
  }
  const contentLength = Number(response.headers.get('content-length'));
  if (Number.isFinite(contentLength) && contentLength > maxBytes) {
    throw new Error(`审查意见书超过大小限制(${Math.floor(maxBytes / 1024 / 1024)}MB)`);
  }
  if (!response.body) {
    throw new Error('下载审查意见书失败: 响应内容为空');
  }
}

async function streamToFile(response, outputPath, maxBytes) {
  const partPath = `${outputPath}.part-${process.pid}-${Date.now()}`;
  let handle = null;
  let totalBytes = 0;
  const signature = [];
  try {
    handle = await fs.promises.open(partPath, 'wx');
    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      totalBytes += value.byteLength;
      if (totalBytes > maxBytes) {
        await reader.cancel();
        throw new Error(`审查意见书超过大小限制(${Math.floor(maxBytes / 1024 / 1024)}MB)`);
      }
      for (const byte of value.subarray(0, Math.max(0, 2 - signature.length))) {
        signature.push(byte);
      }
      await handle.write(value);
    }
    if (signature[0] !== 0x50 || signature[1] !== 0x4b) {
      throw new Error('下载审查意见书失败: 文件不是有效的DOCX');
    }
    await handle.close();
    handle = null;
    await fs.promises.rename(partPath, outputPath);
    return totalBytes;
  } catch (error) {
    await handle?.close().catch(() => undefined);
    await fs.promises.rm(partPath, { force: true }).catch(() => undefined);
    throw error;
  }
}

export async function downloadReviewOpinion({
  downloadUrl,
  fileName: requestedFileName,
  cwd = process.cwd(),
  fetchImpl = fetch,
  maxBytes = MAX_REVIEW_OPINION_BYTES,
}) {
  const normalizedUrl = String(downloadUrl ?? '').trim();
  if (!normalizedUrl) throw new Error('缺少预签名下载地址');
  let parsedUrl;
  try {
    parsedUrl = new URL(normalizedUrl);
  } catch {
    throw new Error('预签名下载地址格式无效');
  }
  if (parsedUrl.protocol !== 'https:') {
    throw new Error('预签名下载地址必须使用HTTPS');
  }

  const workspace = path.resolve(cwd);
  const stat = await fs.promises.stat(workspace).catch(() => null);
  if (!stat?.isDirectory()) throw new Error(`会话工作目录不可用: ${cwd}`);

  const response = await fetchImpl(normalizedUrl, {
    signal: AbortSignal.timeout(120_000),
  });
  validateResponse(response, maxBytes);

  const directory = path.join(workspace, OUTPUT_RELATIVE_DIR);
  await fs.promises.mkdir(directory, { recursive: true });
  const resolvedFileName = resolveResponseFileName(
    response.headers.get('content-disposition'),
    requestedFileName,
  );
  const outputPath = await resolveAvailablePath(directory, resolvedFileName);
  const size = await streamToFile(response, outputPath, maxBytes);
  return {
    success: true,
    fileName: path.basename(outputPath),
    localPath: outputPath,
    size,
  };
}

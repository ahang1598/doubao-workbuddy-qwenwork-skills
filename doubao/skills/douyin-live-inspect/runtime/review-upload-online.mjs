// 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
import * as config from './review-upload-config-online.mjs';
import { resolveUploadCredentials } from './upload-auth-online.mjs';
import { uploadReviewJson } from './review-service.mjs';

export function uploadReviewReport(input, dependencies = {}) {
  return uploadReviewJson(input, { ...config, resolveUploadCredentials }, dependencies);
}

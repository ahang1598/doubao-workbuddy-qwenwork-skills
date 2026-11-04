// 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
import * as config from './review-upload-config-online.mjs';
import { resolveUploadCredentials } from './upload-auth-online.mjs';
import { fetchReviewJson, saveReviewJson } from './review-service.mjs';
export { validateTaskId } from './review-document.mjs';

export function fetchReviewReport(input, dependencies = {}) {
  return fetchReviewJson(input, { ...config, resolveUploadCredentials }, dependencies);
}
export function saveReviewReport(input, dependencies = {}) {
  return saveReviewJson(input, { ...config, resolveUploadCredentials }, dependencies);
}

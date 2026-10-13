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

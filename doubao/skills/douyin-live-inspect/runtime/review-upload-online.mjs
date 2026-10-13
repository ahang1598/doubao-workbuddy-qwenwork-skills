import * as config from './review-upload-config-online.mjs';
import { resolveUploadCredentials } from './upload-auth-online.mjs';
import { uploadReviewJson } from './review-service.mjs';

export function uploadReviewReport(input, dependencies = {}) {
  return uploadReviewJson(input, { ...config, resolveUploadCredentials }, dependencies);
}

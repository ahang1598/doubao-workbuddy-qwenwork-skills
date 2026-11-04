#!/usr/bin/env node
import { readStdin } from '../runtime/script-input.mjs';
import telemetry, { EVENTS, isPreview } from '../telemetry/main.mjs';
// 将已校验的复盘报告上传到原任务，保留失败恢复信息。
import { parseArgs } from 'node:util';
import { uploadReviewReport } from '../runtime/review-upload-online.mjs';
import { reportErrorDetails } from '../runtime/review-service.mjs';

async function main() {
  const { values } = parseArgs({
    options: {
      file: { type: 'string' },
      'task-id': { type: 'string' },
      'project-name': { type: 'string' },
      'room-name': { type: 'string' },
      environment: { type: 'string' },
      profile: { type: 'string' },
      'account-id': { type: 'string' },
      'dry-run': { type: 'boolean' },
      help: { type: 'boolean' },
    },
  });
  if (values.help) {
    process.stdout.write(
      'Save complete v1 report JSON in the original task environment; analysis-only JSON must be assembled with the original task context first.\nUsage: node scripts/ecommerce-review-upload.mjs --file report.json --task-id ID --project-name PROJECT [--room-name NAME] --environment online --profile NAME --account-id ACCOUNT_ID [--dry-run]\nOr provide one JSON object on stdin (file_path, task_id, project_name, room_name, dry_run, environment, profile, account_id).\n',
    );
    return;
  }
  let input;
  if (Object.keys(values).length) {
    input = Object.fromEntries(
      Object.entries(values).map(([key, value]) => [
        key === 'file' ? 'file_path' : key.replaceAll('-', '_'),
        value,
      ]),
    );
  } else {
    if (process.stdin.isTTY)
      throw Object.assign(new Error('Provide --file or stdin JSON'), {
        code: 'INVALID_INPUT',
      });
    const bytes = await readStdin(
      65536,
      Object.assign(new Error('Upload input exceeds 64 KiB'), { code: 'INVALID_INPUT' }),
    );
    try {
      input = JSON.parse(bytes.toString('utf8'));
    } catch {
      throw Object.assign(new Error('stdin must contain one JSON object'), {
        code: 'INVALID_INPUT',
      });
    }
  }
  return telemetry.runCommand(
    { command: EVENTS.formal.ECOMMERCE_REVIEW_UPLOAD, skip: isPreview(input) },
    async () => {
      const data = await uploadReviewReport(input);
      const result = { ok: true, command: 'ecommerce-review-upload', data };
      process.stdout.write(`${JSON.stringify(result)}\n`);
      return result;
    },
  );
}
await main().catch((error) => {
  const known = Boolean(error.stage || error.code === 'INVALID_INPUT');
  process.stdout.write(
    `${JSON.stringify({
      ok: false,
      command: 'ecommerce-review-upload',
      data: null,
      error: {
        code: known ? error.code : 'UPLOAD_FAILED',
        message: known ? error.message : 'Upload failed; source JSON is preserved',
        stage: error.stage || 'input',
        retryable: false,
        write_occurred:
          error.write_occurred ?? (error.code === 'UPLOAD_RESULT_UNKNOWN' ? null : false),
        mutation_state: error.mutation_state,
        next_action: error.next_action,
        verification_result: error.verification_result,
        ...(Number.isInteger(error.http_status) ? { http_status: error.http_status } : {}),
        ...(error.request_id ? { request_id: error.request_id } : {}),
        ...(error.api_code ? { api_code: error.api_code } : {}),
        ...(error.report_hash ? { report_hash: error.report_hash } : {}),
        ...reportErrorDetails(error),
      },
    })}\n`,
  );
  process.exitCode = [
    'INVALID_INPUT',
    'UNSUPPORTED_REPORT_VERSION',
    'TASK_BINDING_MISMATCH',
  ].includes(error.code)
    ? 2
    : 1;
});

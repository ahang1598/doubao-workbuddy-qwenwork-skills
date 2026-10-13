#!/usr/bin/env node
import { EVENTS, runCommand } from '../runtime/telemetry.mjs';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { renderReviewReport, startReviewReportServer } from '../runtime/ecommerce-review-report.mjs';
import { readReviewRenderContext } from '../runtime/ecommerce-review-input.mjs';

import { readAnalysis, parseAnalysisJson, analysisErrorDetails } from '../runtime/review-analysis.mjs';

const SCRIPT_PATH = fileURLToPath(import.meta.url);

function emit(data, error = null) {
  process.stdout.write(`${JSON.stringify({ ok: !error, command: 'ecommerce-review-render', data: error ? null : data, error })}\n`);
}

function safeMessage(value) {
  return String(value || 'Render failed').replace(/https?:\/\/\S+/gi, '[redacted-url]').slice(0, 500);
}

async function readInput() {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > 2 * 1024 * 1024) throw Object.assign(new Error('review result exceeds the 2 MiB input limit'), { code: 'INPUT_TOO_LARGE' });
    chunks.push(chunk);
  }
  try {
    const parsed = parseAnalysisJson(Buffer.concat(chunks));
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
    return parsed;
  } catch (error) {
    if (error?.code) throw error;
    throw Object.assign(new Error('stdin must contain one JSON object'), { code: 'INVALID_INPUT' });
  }
}

async function launchReportServer(path, taskId) {
  const token = randomUUID();
  const args = [SCRIPT_PATH, '--serve', '--path', path, '--token', token];
  if (taskId !== null) args.push('--task-id', String(taskId));
  const child = spawn(process.execPath, args, {
    detached: true, shell: false, stdio: ['ignore', 'pipe', 'pipe'],
  });
  try {
    const startup = await new Promise((resolve, reject) => {
      let stdout = '';
      const timer = setTimeout(() => { child.kill('SIGTERM'); reject(new Error('Report service did not become ready in time')); }, 5000);
      child.stdout.on('data', (chunk) => {
        stdout += chunk.toString('utf8');
        const newline = stdout.indexOf('\n');
        if (newline < 0) return;
        clearTimeout(timer);
        try {
          const parsed = JSON.parse(stdout.slice(0, newline));
          if (!parsed.review_report_url) throw Object.assign(new Error(parsed?.error?.message || 'Report service did not return a URL'), { code: parsed?.error?.code || 'REPORT_SERVER_ERROR' });
          resolve(parsed);
        } catch (error) { reject(error?.code ? error : new Error('Report service returned invalid startup data')); }
      });
      child.once('error', (error) => { clearTimeout(timer); reject(error); });
      child.once('exit', () => { clearTimeout(timer); reject(new Error('Report service exited before becoming ready')); });
    });
    const response = await fetch(startup.review_report_url, { signal: AbortSignal.timeout(3000), redirect: 'error' });
    if (!response.ok) throw new Error('Report service failed its HTTP readiness check');
    await response.arrayBuffer();
    return { review_report_url: startup.review_report_url, review_report_download_url: startup.review_report_download_url, report_pid: child.pid };
  } catch (error) {
    child.kill('SIGTERM');
    throw error;
  } finally {
    child.stdout.destroy();
    child.stderr.destroy();
    child.unref();
  }
}

async function serve(argv) {
  const value = (name) => {
    const index = argv.indexOf(name);
    return index < 0 ? undefined : argv[index + 1];
  };
  const token = value('--token');
  const path = value('--path');
  const rawTaskId = value('--task-id');
  const taskId = rawTaskId === undefined ? null : Number(rawTaskId);
  const rawPort = value('--port');
  const port = rawPort === undefined ? 0 : Number(rawPort);
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw Object.assign(new Error('port must be an integer between 0 and 65535'), { code: 'INVALID_INPUT' });
  const running = await startReviewReportServer({ path, token, taskId, port });
  process.stdout.write(`${JSON.stringify({ review_report_url: running.url, review_report_download_url: running.downloadUrl })}\n`);
  const close = () => running.stop();
  process.on('SIGINT', close);
  process.on('SIGTERM', close);
  await new Promise((resolveClose) => running.server.once('close', resolveClose));
}

async function main(argv = process.argv.slice(2)) {
  if (argv.includes('--serve')) return serve(argv);
  if (argv.includes('--open')) {
    const index = argv.indexOf('--path');
    const path = index < 0 ? '' : argv[index + 1];
    if (!path) throw Object.assign(new Error('--open requires --path'), { code: 'INVALID_INPUT' });
    const taskIndex = argv.indexOf('--task-id');
    const taskId = taskIndex < 0 ? null : Number(argv[taskIndex + 1]);
    if (taskId !== null && (!Number.isSafeInteger(taskId) || taskId <= 0)) {
      throw Object.assign(new Error('task id must be a positive integer'), { code: 'INVALID_INPUT' });
    }
    const served = await launchReportServer(path, taskId);
    emit({ status: 'served', review_report_file: path, ...served });
    return;
  }
  const input = await readInput();
  const skillRoot = dirname(dirname(fileURLToPath(import.meta.url)));
  const review = await readAnalysis(input);
  const format = input.format ?? 'json';
  let renderContext = null;
  try { renderContext = input.render_context_id ? await readReviewRenderContext(input.render_context_id) : null; }
  catch (error) {
    if (error.code !== 'ENOENT') throw Object.assign(new Error('Invalid private context; rerun ecommerce-review-prepare for the original task'), { code: 'INVALID_RENDER_CONTEXT' });
  }
  if (format === 'json' && !renderContext) {
    throw Object.assign(new Error('Run ecommerce-review-prepare for the original task and retry with its render_context_id; preserve the analysis source'), { code: 'REVIEW_CONTEXT_REQUIRED' });
  }
  const metadata = { ...(input.metadata || {}), playback: renderContext };
  // Prepared task identity is authoritative; an analysis result cannot rebind the report.
  for (const key of ['task_id', 'project_name']) {
    if (renderContext?.[key] !== undefined && renderContext[key] !== '') {
      if (metadata[key] !== undefined && String(metadata[key]) !== String(renderContext[key])) {
        throw Object.assign(new Error('Report metadata does not match the prepared task'), { code: 'TASK_BINDING_MISMATCH' });
      }
      metadata[key] = renderContext[key];
    }
  }
  const artifact = await renderReviewReport({
    review,
    metadata,
    format,
    templatePath: join(skillRoot, 'references', 'review_report.html'),
  });
  if (input.delivery_mode === 'chat' || format === 'json') {
    emit({
      status: 'rendered_file_only',
      review_report_file: artifact.path,
      report_format: format,
      review_report_url: null,
      review_report_download_url: null,
      report_pid: null,
      local_service_error: null,
      segment_count: artifact.segmentCount,
      scope: artifact.scope,
      contains_raw_asr: Boolean(renderContext?.asr_timeline?.length),
      asr_timeline_segment_count: Array.isArray(renderContext?.asr_timeline) ? renderContext.asr_timeline.length : 0,
    });
    return;
  }
  let served = null;
  let serverError = null;
  try { served = await launchReportServer(artifact.path, Number.isSafeInteger(Number(input.metadata?.task_id)) ? Number(input.metadata.task_id) : null); }
  catch (error) { serverError = { code: error?.code || 'REPORT_SERVER_ERROR', message: safeMessage(error?.message) }; }
  emit({
    status: served ? 'served' : 'rendered_file_only',
    review_report_file: artifact.path,
    review_report_url: served?.review_report_url ?? null,
    review_report_download_url: served?.review_report_download_url ?? null,
    report_pid: served?.report_pid ?? null,
    local_service_error: serverError,
    segment_count: artifact.segmentCount,
    scope: artifact.scope,
    contains_raw_asr: Boolean(renderContext?.asr_timeline?.length),
    asr_timeline_segment_count: Array.isArray(renderContext?.asr_timeline) ? renderContext.asr_timeline.length : 0,
  });
}

await runCommand(EVENTS.formal.ECOMMERCE_REVIEW_RENDER, () => main()).catch((error) => {
  emit(null, { code: error?.code || 'UNEXPECTED_ERROR', message: safeMessage(error?.message), ...analysisErrorDetails(error), retryable: false });
  process.exitCode = 1;
});

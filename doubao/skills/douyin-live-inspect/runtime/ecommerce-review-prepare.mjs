import { onlineEnvironment } from "./online-environment.mjs";
import { runService } from "./service-call.mjs";
import {
  buildEcommerceReviewInput,
  buildReviewRenderContext,
  writeReviewInput,
  cleanupReviewInput,
} from "./ecommerce-review-input.mjs";
import { resolveTaskBinding } from "./task-binding.mjs";
import { resolveInspectionEnvironment } from "./remote-dashboard.mjs";
import { setTimeout as sleep } from "node:timers/promises";

const MAX_OUTPUT_BYTES = 16 * 1024 * 1024;

function safeMessage(value) {
  return String(value || "Command failed")
    .replace(/https?:\/\/\S+/gi, "[redacted-url]")
    .slice(0, 500);
}

function positiveInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0)
    throw Object.assign(new Error(`${name} must be a positive integer`), {
      code: "INVALID_INPUT",
    });
  return parsed;
}

function nonNegativeInteger(value, name) {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 0)
    throw Object.assign(new Error(`${name} must be a non-negative integer`), {
      code: "INVALID_INPUT",
    });
  return parsed;
}

function reportPending(error) {
  if (error?.recoveryCode) return false;
  return /ReportNotFound|not.?found|generat|生成|尚未|未生成|not.?ready/i.test(
    `${error?.code || ""} ${error?.message || ""}`
  );
}

function transientRead(error) {
  if (error?.recoveryCode) return false;
  return error?.httpStatus === 429 || (error?.httpStatus >= 500 && error?.httpStatus <= 599)
    || /^(NETWORK_ERROR|REQUEST_TIMEOUT|ECONNRESET|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|UND_ERR_CONNECT_TIMEOUT|UND_ERR_SOCKET)$/.test(error?.code || error?.cause?.code || '');
}

export function runPreparationCli(args, options = {}) {
  return runService(args, options);
}

function parseCliResult(result) {
  if (result.overflow)
    throw Object.assign(
      new Error("GetReport output exceeded the 16 MiB safety limit"),
      { code: "OUTPUT_TOO_LARGE" }
    );
  let payload;
  try {
    payload = JSON.parse(
      result.code === 0 ? result.stdout : result.stderr.trim() || result.stdout
    );
  } catch {
    throw Object.assign(new Error("Service returned an unreadable response"), {
      code: "SERVICE_ERROR",
    });
  }
  if (result.code !== 0 || !payload?.ok) {
    const error = payload?.error || {};
    const response = error.details?.response;
    const status = Number(
      error.http_status ??
        error.httpStatus ??
        error.statusCode ??
        error.details?.http_status ??
        response?.status
    );
    const remoteCode =
      response?.data?.ResponseMetadata?.Error?.Code ??
      response?.ResponseMetadata?.Error?.Code;
    const marker = `${error.type || ""} ${error.subtype || ""} ${
      error.code || ""
    } ${remoteCode || ""}`;
    // Keep the standalone error code while giving the watcher a safe recovery route.
    const recoveryCode =
      status === 403 ||
      /authorization|forbidden|permission|access.?denied/i.test(marker)
        ? "PERMISSION_DENIED"
        : status === 401 ||
          /authentication|unauthorized|credential|token|session|login|auth_required/i.test(
            marker
          )
        ? "AUTH_REQUIRED"
        : undefined;
    throw Object.assign(new Error(safeMessage(error.message)), {
      code: error.subtype || error.code || "GET_REPORT_FAILED",
      recoveryCode,
      httpStatus: status,
    });
  }
  return payload;
}

function resultObject(payload) {
  return (
    payload?.data?.response?.data?.Result ??
    payload?.data?.response?.Result ??
    payload?.data?.Result ??
    payload?.Result ??
    {}
  );
}

export async function prepareEcommerceReview(
  input,
  {
    signal,
    runCli = runPreparationCli,
    now = () => Date.now(),
    wait = (ms, abortSignal) => sleep(ms, undefined, { signal: abortSignal }),
    setTimer = setTimeout,
    clearTimer = clearTimeout,
    writeInput = writeReviewInput,
  } = {}
) {
  if (!input || typeof input !== "object" || Array.isArray(input))
    throw Object.assign(new Error("Input must be an object"), {
      code: "INVALID_INPUT",
    });
  const projectName = String(input.project_name || "").trim();
  const taskId = positiveInteger(input.task_id, "task_id");
  const segmentDurationMs =
    input.segment_duration_ms === undefined
      ? 120_000
      : positiveInteger(input.segment_duration_ms, "segment_duration_ms");
  const waitForReportMs =
    input.wait_for_report_ms === undefined
      ? 10 * 60_000
      : nonNegativeInteger(input.wait_for_report_ms, "wait_for_report_ms");
  const pollIntervalMs =
    input.poll_interval_ms === undefined
      ? 30_000
      : positiveInteger(input.poll_interval_ms, "poll_interval_ms");
  if (!projectName)
    throw Object.assign(new Error("project_name is required"), {
      code: "INVALID_INPUT",
    });
  if (segmentDurationMs < 60_000 || segmentDurationMs > 180_000)
    throw Object.assign(
      new Error("segment_duration_ms must be between 60000 and 180000"),
      { code: "INVALID_INPUT" }
    );
  if (waitForReportMs > 10 * 60_000)
    throw Object.assign(
      new Error("wait_for_report_ms must not exceed 600000"),
      { code: "INVALID_INPUT" }
    );
  if (pollIntervalMs < 5_000 || pollIntervalMs > 60_000)
    throw Object.assign(
      new Error("poll_interval_ms must be between 5000 and 60000"),
      { code: "INVALID_INPUT" }
    );

  const timeout = new AbortController();
  const combined = signal
    ? AbortSignal.any([signal, timeout.signal])
    : timeout.signal;
  let timer = null;
  let lastReadError;
  try {
    combined.throwIfAborted();
    const binding = await resolveTaskBinding(input, async (args) =>
      parseCliResult(
        await runCli(args, {
          signal: combined,
          env: { ...process.env, DOUYIN_INSPECT_AUTO_LOGIN: "0" },
        })
      )
    );
    const environment = binding[binding.indexOf("--env") + 1];
    const profile = binding[binding.indexOf("--profile") + 1];
    const account_id = binding.includes("--account-id")
      ? binding[binding.indexOf("--account-id") + 1]
      : undefined;
    if (!account_id || !/^[0-9]{1,128}$/.test(account_id))
      throw Object.assign(
        new Error("Original task account identity is required"),
        { code: "ORIGINAL_TASK_CONTEXT_REQUIRED" }
      );
    const taskIdentity = { environment, profile, account_id };
    const routing = resolveInspectionEnvironment({ environment });
    const childEnv = {
      ...process.env,
      DOUYIN_INSPECT_ENV: environment,
      DOUYIN_INSPECT_BASE_URL: routing.baseUrl,
      DOUYIN_INSPECT_AUTO_LOGIN: "0",
    };
    const run = (args) => {
      combined.throwIfAborted();
      return runCli([...binding, ...args], { env: childEnv, signal: combined });
    };
    const task = parseCliResult(
      await run([
        "quality",
        "+task-get",
        "--project-name",
        projectName,
        "--task-id",
        String(taskId),
      ])
    );
    if (binding.length) {
      const detail = resultObject(task);
      if (
        detail.ProjectName !== projectName ||
        String(detail.TaskId) !== String(taskId) ||
        Number(detail.TaskType) !== 2
      ) {
        throw Object.assign(
          new Error("Task does not match the original live inspection"),
          { code: "TASK_BINDING_MISMATCH" }
        );
      }
    }
    const taskStatus = Number(resultObject(task).Status);
    if ([1, 2].includes(taskStatus))
      throw Object.assign(
        new Error(
          `quality task ${taskId} is still running; GetReport is not ready`
        ),
        { code: "REPORT_NOT_READY" }
      );
    if (taskStatus === 5)
      throw Object.assign(new Error(`quality task ${taskId} failed`), {
        code: "TASK_FAILED",
      });
    if (binding.length && ![3, 4].includes(taskStatus))
      throw Object.assign(new Error("Task status is not confirmed"), {
        code: "REPORT_NOT_READY",
      });
    const deadline = now() + waitForReportMs;
    // Zero means one bounded attempt, retaining the standalone prepare contract.
    if (waitForReportMs > 0)
      timer = setTimer(() => timeout.abort(), waitForReportMs);
    let report;
    let transientRetries = 0;
    while (!report) {
      try {
        combined.throwIfAborted();
        report = parseCliResult(
          await run([
            "quality",
            "report",
            "get",
            "--project-name",
            projectName,
            "--task-id",
            String(taskId),
          ])
        );
      } catch (error) {
        combined.throwIfAborted();
        const transient = transientRead(error);
        lastReadError = transient ? error : undefined;
        if ((!transient && !reportPending(error)) || now() >= deadline || (transient && transientRetries >= 2)) {
          if (transient) throw error;
          if (reportPending(error))
            throw Object.assign(
              new Error(
                `quality report for task ${taskId} is still generating`
              ),
              { code: "REPORT_NOT_READY" }
            );
          throw error;
        }
        if (transient) transientRetries++;
        await wait(
          Math.min(pollIntervalMs, Math.max(0, deadline - now())),
          combined
        );
        if (now() >= deadline) {
          if (lastReadError) throw lastReadError;
          throw Object.assign(new Error("Quality report is still generating"), {
            code: "REPORT_NOT_READY",
          });
        }
      }
    }
    combined.throwIfAborted();
    if (waitForReportMs > 0 && now() >= deadline)
      throw Object.assign(new Error("Quality report is still generating"), {
        code: "REPORT_NOT_READY",
      });
    const scenarioName = resultObject(task).ScenarioName ?? input.scenario_name;
    const reviewInput = buildEcommerceReviewInput(report, {
      projectName,
      taskId,
      scenarioName,
      segmentDurationMs,
    });
    const renderContext = {
      ...buildReviewRenderContext(report, {
        segments: reviewInput.fd.sg,
        scenarioName,
        projectName,
        taskId,
      }),
      ...taskIdentity,
    };
    const artifact = await writeInput(reviewInput, undefined, renderContext);
    if (combined.aborted) {
      await cleanupReviewInput(artifact.path);
      combined.throwIfAborted();
    }
    const segments = reviewInput.fd.sg;
    return {
      status: "ready",
      ...taskIdentity,
      project_name: projectName,
      input_contract: reviewInput.input_contract,
      review_input_file: artifact.path,
      cleanup_id: artifact.id,
      render_context_id: artifact.renderContextId,
      playback_available: Boolean(
        renderContext?.play_url || renderContext?.vid
      ),
      task_id: taskId,
      scenario_id: reviewInput.fd.ev.quality_report.scenario_id,
      scenario_name: reviewInput.fd.ev.quality_report.scenario_name,
      segment_count: segments.length,
      start_time: segments[0].st,
      end_time: segments.at(-1).et,
      target_skill: "douyin-live-inspect/SKILL.md",
      review_reference: "references/ecommerce-review.md",
      render_script: "scripts/ecommerce-review-render.mjs",
      report_format: "json",
      scope: reviewInput.fd.ev.scope,
    };
  } catch (error) {
    if (signal?.aborted)
      throw Object.assign(new Error("Review preparation cancelled"), {
        code: "CANCELLED",
      });
    if (timeout.signal.aborted) {
      if (lastReadError) throw lastReadError;
      throw Object.assign(new Error("Quality report is still generating"), {
        code: "REPORT_NOT_READY",
      });
    }
    throw error;
  } finally {
    if (timer !== null) clearTimer(timer);
    timeout.abort();
  }
}

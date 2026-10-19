import flow from './workflow-telemetry.cjs';
import { requireOriginalTaskContext } from './task-binding.mjs';
import {
  mkdir,
  readFile,
  writeFile,
  rename,
  rm,
  open,
  access,
} from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { readAnalysis, analysisErrorDetails } from "./review-analysis.mjs";
import { renderReviewReport } from "./ecommerce-review-report.mjs";
import {
  readReviewRenderContext,
  cleanupReviewInput,
  REVIEW_INPUT_ROOT,
} from "./ecommerce-review-input.mjs";
import {
  readReviewFile,
  reportDigest,
  validateTaskId,
  validateProjectName,
} from "./review-document.mjs";
import { uploadReviewJson, verifyReviewJson, reportErrorDetails } from "./review-service.mjs";
import * as config from "./review-upload-config-online.mjs";
import { resolveUploadCredentials } from "./upload-auth-online.mjs";

const ROOT = join(tmpdir(), "byted-live-inspect", "review-finalizations");
const runtime = { ...config, resolveUploadCredentials };
function fail(code) {
  return Object.assign(new Error(code), { code });
}
function matchesIdentity(actual, expected) {
  return (
    actual &&
    Object.entries(expected).every(
      ([key, value]) => String(actual[key]) === String(value)
    )
  );
}
// The console review URL is deterministic for a saved report. The upload /
// readback service may omit Result.URL, so backfill it here to keep the
// fetch_report_link → ack_delivered state machine idempotent.
function reviewConsoleUrl(identity) {
  return `https://console.volcengine.com/livesaas/liveinspect/projectManagement/${encodeURIComponent(identity.project_name)}/taskManagement/report/view/${identity.task_id}?reportType=review`;
}
function uuid(id) {
  if (!/^[0-9a-f-]{36}$/i.test(id || "")) throw fail("INVALID_RENDER_CONTEXT");
  return id;
}
async function lock(file) {
  try {
    const handle = await open(file, "wx", 0o600);
    await handle.writeFile(String(process.pid));
    await handle.close();
    return;
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  // Serialize stale-lock recovery so two rescuers cannot remove each
  // other's newly acquired lock. A live owner is never interrupted.
  let recovery;
  try {
    recovery = await open(`${file}.recovery`, "wx", 0o600);
  } catch {
    throw fail("FINALIZATION_BUSY");
  }
  try {
    const pid = Number(await readFile(file, "utf8"));
    if (!Number.isSafeInteger(pid) || pid <= 0) throw fail("FINALIZATION_BUSY");
    try {
      process.kill(pid, 0);
    } catch (error) {
      if (error.code === "ESRCH") {
        await rm(file, { force: true });
        const handle = await open(file, "wx", 0o600);
        await handle.writeFile(String(process.pid));
        await handle.close();
        return;
      }
    }
    throw fail("FINALIZATION_BUSY");
  } finally {
    await recovery.close();
    await rm(`${file}.recovery`, { force: true });
  }
}

export async function finalizeReview(input, dependencies = {}) {
  requireOriginalTaskContext(input);
  const environment = config.resolveReportEnvironment({
    environment: input.environment,
  });
  if (typeof input.profile !== "string" || !input.profile.trim())
    throw fail("INVALID_INPUT");
  if (input.account_id === undefined)
    throw fail("ORIGINAL_TASK_CONTEXT_REQUIRED");
  if (
    input.account_id !== undefined &&
    (typeof input.account_id !== "string" ||
      !/^[0-9]{1,128}$/.test(input.account_id))
  )
    throw fail("INVALID_INPUT");
  const identity = {
    environment,
    profile: input.profile,
    ...(input.account_id ? { account_id: input.account_id } : {}),
    project_name: validateProjectName(input.project_name),
    task_id: validateTaskId(input.task_id),
  };
  const originalContext = input.original_task_context;
  if (
    originalContext !== undefined &&
    !matchesIdentity(originalContext, identity)
  )
    throw fail("TASK_BINDING_MISMATCH");
  let id = createHash("sha256").update(JSON.stringify(identity)).digest("hex");
  const { account_id: _account, ...legacyIdentity } = identity;
  const legacyId = createHash("sha256")
    .update(JSON.stringify(legacyIdentity))
    .digest("hex");
  const root = dependencies.root || ROOT;
  let legacyExists = false;
  try {
    await access(join(root, `${legacyId}.json`));
    legacyExists = true;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  if (legacyExists) {
    let legacyState;
    try {
      legacyState = JSON.parse(
        await readFile(join(root, `${legacyId}.json`), "utf8")
      );
    } catch {
      throw fail("INVALID_FINALIZATION_STATE");
    }
    if (!legacyState.identity?.account_id && !originalContext)
      throw fail("ORIGINAL_TASK_CONTEXT_REQUIRED");
    if (
      legacyState.identity?.account_id &&
      !matchesIdentity(legacyState.identity, identity)
    )
      throw fail("TASK_BINDING_MISMATCH");
    id = legacyId;
  }
  if (input.finalization_id && input.finalization_id !== id)
    throw fail("TASK_BINDING_MISMATCH");
  await mkdir(root, { recursive: true, mode: 0o700 });
  const file = join(root, `${id}.json`);
  const lockFile = join(root, `${id}.lock`);
  await lock(lockFile);
  let state;
  const save = async () => {
    const temporary = `${file}.${randomUUID()}.tmp`;
    try {
      await writeFile(temporary, JSON.stringify(state), {
        mode: 0o600,
        flag: "wx",
      });
      await rename(temporary, file);
    } finally {
      await rm(temporary, { force: true });
    }
  };
  const cleanup = async () => {
    if (!state.cleanup_id || state.cleanup_status === "complete") return;
    try {
      await (dependencies.cleanup || cleanupReviewInput)(
        join(REVIEW_INPUT_ROOT, `${uuid(state.cleanup_id)}.json`)
      );
      state.cleanup_status = "complete";
    } catch {
      state.cleanup_status = "pending";
    }
  };
  try {
    try {
      state = JSON.parse(await readFile(file, "utf8"));
    } catch (error) {
      if (error.code !== "ENOENT") throw fail("INVALID_FINALIZATION_STATE");
    }
    if (state && !state.identity?.account_id) {
      if (!originalContext) throw fail("ORIGINAL_TASK_CONTEXT_REQUIRED");
      if (!matchesIdentity(state.identity, legacyIdentity))
        throw fail("TASK_BINDING_MISMATCH");
      state.identity = identity;
      await save();
    }
    if (state && !matchesIdentity(state.identity, identity))
      throw fail("TASK_BINDING_MISMATCH");
    if (!state) {
      if (input.ack_delivered) throw fail("REPORT_NOT_SAVED");
      state = { identity, phase: "preparing", cleanup_status: "pending" };
      await save();
    }
    if (input.ack_delivered) {
      if (state.phase !== "saved") throw fail("REPORT_NOT_SAVED");
      if (!state.report_url) throw fail("REPORT_LINK_PENDING");
      delete state.error;
      state.delivered = true;
      await save();
      await cleanup();
      try {
        if (state.report_file) await rm(state.report_file, { force: true });
        state.artifact_cleanup_status = "complete";
      } catch {
        state.artifact_cleanup_status = "pending";
      }
      await save();
    } else {
      if (state.phase === "preparing") {
        const review = await readAnalysis(input);
        const contextId = uuid(input.render_context_id);
        if (input.cleanup_id && input.cleanup_id !== contextId)
          throw fail("TASK_BINDING_MISMATCH");
        let context;
        try {
          context = await (dependencies.readContext || readReviewRenderContext)(
            contextId
          );
        } catch {
          throw fail("REVIEW_CONTEXT_REQUIRED");
        }
        const contextIdentity = {
          environment: context.environment,
          profile: context.profile,
          account_id: context.account_id,
        };
        if (
          Object.values(contextIdentity).some((value) => value === undefined)
        ) {
          if (!originalContext) throw fail("ORIGINAL_TASK_CONTEXT_REQUIRED");
          for (const [key, value] of Object.entries(contextIdentity))
            if (value !== undefined && value !== identity[key])
              throw fail("TASK_BINDING_MISMATCH");
        } else if (
          !matchesIdentity(contextIdentity, {
            environment: identity.environment,
            profile: identity.profile,
            account_id: identity.account_id,
          })
        )
          throw fail("TASK_BINDING_MISMATCH");
        if (
          String(context.task_id) !== identity.task_id ||
          context.project_name !== identity.project_name
        )
          throw fail("TASK_BINDING_MISMATCH");
        const artifact = await (dependencies.render || renderReviewReport)({
          review,
          metadata: { ...identity, playback: context },
          format: "json",
        });
        state.report_file = artifact.path;
        state.report_quality = review.status === 'degraded' ? 'insufficient' : 'ready';
        const { report } = await readReviewFile(artifact.path, identity);
        state.report_hash = reportDigest(report);
        state.cleanup_id = contextId;
        state.phase = "rendered";
        await save();
        // Generation is observed before optional online persistence; no delivery is implied.
        try {
          await flow.formal(identity,{recap:state.report_quality,...(state.report_quality==='insufficient'?{failure_stage:'recap',failure_reason:'CONTENT_INSUFFICIENT'}:{})},{env:dependencies.env||process.env});
        } catch { /* An optional observer must not interrupt report persistence. */ }
      }
      const uploadInput = { ...identity, file_path: state.report_file };
      const attemptingUpload = state.phase === "rendered";
      try {
        let saved;
        if (state.phase === "rendered") {
          // Persist ambiguity BEFORE the write. A killed process must never
          // cause a second upload on resume, even if the response was lost.
          const { report } = await readReviewFile(state.report_file, identity);
          if (reportDigest(report) !== state.report_hash)
            throw fail("REPORT_FILE_CHANGED");
          state.phase = "unknown";
          await save();
          saved = await (dependencies.upload || uploadReviewJson)(
            uploadInput,
            runtime,
            dependencies
          );
        } else if (
          state.phase === "unknown" ||
          (state.phase === "saved" && !state.report_url)
        ) {
          saved = await (dependencies.verify || verifyReviewJson)(
            identity,
            state.report_hash,
            runtime,
            dependencies
          );
        }
        if (saved) {
          state.phase = "saved";
          state.report_url = saved.report_url || reviewConsoleUrl(identity);
          state.verification = saved.verification;
          delete state.error;
        }
      } catch (error) {
        // A later verification updates its own result, but retains the original
        // upload request identifiers for diagnosis.
        const { http_status, api_code, request_id } = !attemptingUpload ? state.error || {} : {};
        const previousDetails = reportErrorDetails({ http_status, api_code, request_id });
        state.error = {
          code: ['ENOMEM', 'ERR_WORKER_OUT_OF_MEMORY', 'OUT_OF_MEMORY'].includes(error.code) ? 'OUT_OF_MEMORY' : error.stage ? error.code : "FINALIZATION_FAILED",
          ...previousDetails,
          ...reportErrorDetails(error),
        };
        // Only a known pre-write failure permits a subsequent upload attempt.
        if (
          attemptingUpload && (error.write_occurred === false || [
            "INVALID_INPUT",
            "SETUP_PENDING",
            "UNSUPPORTED_REPORT_VERSION",
            "TASK_BINDING_MISMATCH",
          ].includes(error.code))
        )
          state.phase = "rendered";
      } finally {
        await cleanup();
        await save();
      }
    }
    // Only verified saved content and the existing explicit host acknowledgement count.
    try {
      if(state.phase==='saved') {
        const quality=state.report_quality || 'none'; // Legacy state has no quality evidence.
        await flow.formal(identity,{recap:quality,report_saved:true,...(quality==='insufficient'?{failure_stage:'recap',failure_reason:'CONTENT_INSUFFICIENT'}:{})},{env:dependencies.env||process.env});
        if(state.delivered && quality==='ready')await flow.ack(identity,'recap','delivered',{env:dependencies.env||process.env});
      } else if(state.error)await flow.problem(state.report_quality==='ready'?'delivery':'recap',state.error.code,false,{env:dependencies.env||process.env});
    }catch{/* delivery business state remains authoritative */}
    // Online persistence must not hide an already generated, validated report.
    // Keep unknown writes on the verification route; a local copy is not an ack.
    let localReportFile = null;
    if (['rendered', 'unknown'].includes(state.phase) && state.report_file) {
      try {
        const { report } = await readReviewFile(state.report_file, identity);
        if (reportDigest(report) === state.report_hash) localReportFile = state.report_file;
      } catch { /* Missing or changed files cannot be offered as valid reports. */ }
    }
    return {
      finalization_id: id,
      status: state.phase,
      report_saved: state.phase === "saved",
      report_url: state.report_url || null,
      verification: state.verification,
      cleanup_status: state.cleanup_status,
      artifact_cleanup_status: state.artifact_cleanup_status || "retained",
      delivered: state.delivered === true,
      local_report_file: localReportFile,
      delivery_fallback: localReportFile ? {
        next_action: 'deliver_local_report',
        reason: state.error?.code || 'REPORT_SAVE_PENDING',
        message: '复盘正文已生成；先交付本地报告或完整 Chat 正文，并说明线上保存尚未确认。保留原任务继续核验，不重复上传，不确认线上交付成功。',
      } : null,
      error: state.error,
      next_action:
        state.phase !== "saved"
          ? state.phase === "rendered"
            ? state.error?.next_action || "resume_finalization"
            : "verify_report"
          : state.delivered
          ? state.cleanup_status === "pending" ||
            state.artifact_cleanup_status === "pending"
            ? "ack_delivered"
            : "none"
          : state.report_url
          ? "deliver_report"
          : "fetch_report_link",
    };
  } catch (error) {
    if (error.code === "INVALID_INPUT")
      Object.assign(error, analysisErrorDetails(error));
    throw error;
  } finally {
    await rm(lockFile, { force: true });
  }
}

#!/usr/bin/env node
import { EVENTS, runCommand, isPreview } from '../runtime/telemetry.mjs';
import { parseArgs } from "node:util";
import { saveReviewReport } from "../runtime/review-upload-tos-online.mjs";
import { reportErrorDetails } from "../runtime/review-service.mjs";
async function main() {
  const { values } = parseArgs({
    options: {
      "task-id": { type: "string" },
      "project-name": { type: "string" },
      output: { type: "string" },
      profile: { type: "string" },
      "account-id": { type: "string" },
      environment: { type: "string" },
      "dry-run": { type: "boolean" },
      help: { type: "boolean" },
    },
  });
  if (values.help) {
    process.stdout.write(
      "Download uploaded review JSON by task ID.\nUsage: node scripts/ecommerce-review-fetch.mjs --task-id ID --project-name PROJECT --output report.json --environment online --profile NAME --account-id ACCOUNT_ID [--dry-run]\n"
    );
    return;
  }
  let input;
  if (Object.keys(values).length) {
    input = Object.fromEntries(
      Object.entries(values).map(([key, value]) => [
        key.replaceAll("-", "_"),
        value,
      ])
    );
  } else {
    if (process.stdin.isTTY)
      throw Object.assign(new Error("Provide arguments or stdin JSON"), {
        code: "INVALID_INPUT",
        stage: "input",
      });
    const chunks = [];
    let size = 0;
    for await (const chunk of process.stdin) {
      size += chunk.length;
      if (size > 65536)
        throw Object.assign(new Error("Input exceeds 64 KiB"), {
          code: "INVALID_INPUT",
          stage: "input",
        });
      chunks.push(chunk);
    }
    try {
      input = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch {
      throw Object.assign(new Error("stdin must contain one JSON object"), {
        code: "INVALID_INPUT",
        stage: "input",
      });
    }
    if (!input || typeof input !== "object" || Array.isArray(input))
      throw Object.assign(new Error("stdin must contain one JSON object"), {
        code: "INVALID_INPUT",
        stage: "input",
      });
  }
  return runCommand(EVENTS.formal.ECOMMERCE_REVIEW_FETCH, async()=>{
  const data = await saveReviewReport(input);
  process.stdout.write(
    `${JSON.stringify({ ok: true, command: "ecommerce-review-fetch", data })}\n`
  );
  }, {skip:isPreview(input)});
}
await main().catch((error) => {
  process.stdout.write(
    `${JSON.stringify({
      ok: false,
      command: "ecommerce-review-fetch",
      error: {
        code: error.stage ? error.code : "REPORT_FETCH_FAILED",
        message: error.stage
          ? error.message
          : "Unable to retrieve report; no report delivered",
        retryable: false,
        ...reportErrorDetails(error),
        ...(Number.isInteger(error.http_status)
          ? { http_status: error.http_status }
          : {}),
      },
    })}\n`
  );
  process.exitCode = error.code === "INVALID_INPUT" ? 2 : 1;
});

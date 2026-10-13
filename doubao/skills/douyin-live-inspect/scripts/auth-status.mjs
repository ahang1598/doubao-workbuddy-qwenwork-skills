#!/usr/bin/env node
import { parseArgs } from "node:util";
import { getAuthStatus } from "../runtime/auth.mjs";
import { EVENTS, runCommand } from '../runtime/telemetry.mjs';
await runCommand(EVENTS.formal.AUTH_STATUS, async () => {
try {
  const { values } = parseArgs({
    options: {
      profile: { type: "string" },
      environment: { type: "string", default: "online" },
      help: { type: "boolean" },
      json: { type: "boolean" },
    },
  });
  if (values.help)
    console.log(
      "Usage: node scripts/auth-status.mjs [--profile NAME] [--environment online]"
    );
  else
    console.log(
      JSON.stringify({
        ok: true,
        command: "auth-status",
        data: await getAuthStatus({
          ...values,
          authorizationResponseStdin: values["authorization-response-stdin"],
        }),
      })
    );
} catch {
  console.log(
    JSON.stringify({
      ok: false,
      command: "auth-status",
      error: {
        code: "AUTH_FAILED",
        message:
          "Authentication operation failed; check login status and retry. Authorization input is never echoed.",
      },
    })
  );
  process.exitCode = 1;
}
}, {skip:process.argv.includes('--help')});

#!/usr/bin/env node
import { parseArgs } from "node:util";
import { logout } from "../runtime/auth.mjs";
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
      "Usage: node scripts/logout.mjs [--profile NAME] [--environment online]"
    );
  else
    console.log(
      JSON.stringify({
        ok: true,
        command: "logout",
        data: await logout({
          ...values,
          authorizationResponseStdin: values["authorization-response-stdin"],
        }),
      })
    );
} catch {
  console.log(
    JSON.stringify({
      ok: false,
      command: "logout",
      error: {
        code: "AUTH_FAILED",
        message:
          "Authentication operation failed; check login status and retry. Authorization input is never echoed.",
      },
    })
  );
  process.exitCode = 1;
}

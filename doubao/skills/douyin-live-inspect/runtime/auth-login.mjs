import { randomBytes, createHash, timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";
import {
  SIGNIN,
  SCOPE,
  CLIENT_LOCAL,
  CLIENT_REMOTE,
  requireOnline,
  exchangeToken,
  tokenSession,
} from "./auth.mjs";
import {
  profileName,
  readStore,
  writeStore,
  removeStore,
  withProfileLock,
} from "./auth-store.mjs";
function authorizationParams(raw) {
  try {
    return new URL(raw).searchParams;
  } catch {
    return new URLSearchParams(String(raw).replace(/^\?/, ""));
  }
}
export function decodeAuthorizationResponse(raw, state) {
  let p = authorizationParams(raw);
  if (!p.has("code") && !p.has("error"))
    p = authorizationParams(Buffer.from(String(raw), "base64url").toString());
  if (
    ["state", "code", "error"].some((key) => p.getAll(key).length > 1) ||
    (p.has("code") && p.has("error"))
  )
    throw new Error("Ambiguous authorization response");
  const actual = Buffer.from(p.get("state") || "");
  const expected = Buffer.from(state);
  if (
    !expected.length ||
    actual.length !== expected.length ||
    !timingSafeEqual(actual, expected)
  )
    throw new Error("Authorization state mismatch");
  if (p.has("error"))
    throw Object.assign(new Error("Authorization denied"), {
      code: "AUTH_DENIED",
    });
  if (!p.get("code")) throw new Error("Authorization failed");
  return p.get("code");
}
export async function readAuthorizationResponse(input) {
  if (!input || input.isTTY || input.readable !== true)
    throw new Error("Resume requires controlled non-echoing stdin");
  let size = 0;
  const chunks = [];
  for await (const chunk of input) {
    const b = Buffer.from(chunk);
    size += b.length;
    if (size > 65536) throw new Error("Authorization input too large");
    chunks.push(b);
  }
  const value = Buffer.concat(chunks).toString().trim();
  if (!value || value.includes("\0"))
    throw new Error("Invalid authorization input");
  return value;
}
export async function runLogin(
  input = {},
  {
    env = process.env,
    fetchImpl = globalThis.fetch,
    now = Date.now,
    stdin = process.stdin,
    output = process.stderr,
    timeoutMs = 300000,
  } = {}
) {
  requireOnline(input);
  const profile = profileName(input);
  const clock = typeof now === "function" ? now : () => now;
  if (input.authorizationResponseStdin && !input.remote)
    throw new Error("Resume requires --remote");
  return withProfileLock(profile, env, async () => {
    let pending;
    let server;
    let result;
    try {
      if (input.authorizationResponseStdin) {
        pending = await readStore(profile, "pending", env);
        if (
          !pending ||
          clock() - pending.createdAt > 600000 ||
          clock() < pending.createdAt ||
          pending.clientId !== CLIENT_REMOTE ||
          pending.redirectUri !== `${SIGNIN}/authorize/oauth/authorize`
        )
          throw new Error("Pending login missing or expired");
        result = await readAuthorizationResponse(stdin);
      } else {
        pending = {
          state: randomBytes(32).toString("base64url"),
          verifier: randomBytes(32).toString("base64url"),
          createdAt: clock(),
          clientId: input.remote ? CLIENT_REMOTE : CLIENT_LOCAL,
        };
        let callback;
        if (input.remote)
          pending.redirectUri = `${SIGNIN}/authorize/oauth/authorize`;
        else {
          callback = new Promise((resolve, reject) => {
            server = createServer((req, res) => {
              if (
                req.method !== "GET" ||
                !req.url.startsWith("/oauth/callback?")
              ) {
                res.writeHead(404).end();
                return;
              }
              try {
                decodeAuthorizationResponse(
                  req.url.slice(req.url.indexOf("?")),
                  pending.state
                );
                res
                  .writeHead(200, {
                    "Content-Type": "text/plain; charset=utf-8",
                    "Cache-Control": "no-store",
                  })
                  .end("已收到授权回调。请回到当前对话回复“已授权”或“继续”，核验登录状态后继续质检。此页面不会自动让对话继续。");
                resolve(req.url.slice(req.url.indexOf("?")));
              } catch (error) {
                res.writeHead(400).end("Invalid authorization response");
                if (error.code === "AUTH_DENIED") reject(error);
              }
            });
            server.on("error", () =>
              reject(new Error("Local callback unavailable"))
            );
          });
          callback.catch(() => {});
          await new Promise((resolve, reject) => {
            server.once("error", reject);
            server.listen(0, "127.0.0.1", resolve);
          });
          pending.redirectUri = `http://127.0.0.1:${
            server.address().port
          }/oauth/callback`;
        }
        const url = new URL(`${SIGNIN}/authorize/oauth/authorize`);
        url.search = new URLSearchParams({
          response_type: "code",
          client_id: pending.clientId,
          redirect_uri: pending.redirectUri,
          scope: SCOPE,
          state: pending.state,
          code_challenge: createHash("sha256")
            .update(pending.verifier)
            .digest("base64url"),
          code_challenge_method: "S256",
        }).toString();
        if (input.remote) await writeStore(profile, "pending", pending, env);
        output.write(
          `Open this URL manually in your chosen browser:\n${url}\n${input.remote ? "请通过受控授权输入渠道提交授权结果，再回到当前对话回复“已授权”或“继续”。" : "授权完成后，请回到当前对话回复“已授权”或“继续”，核验登录状态后继续质检。"}授权页面不会自动让对话继续。\n`
        );
        if (input.remote)
          return {
            profile,
            environment: "online",
            status: "pending",
            resume:
              "Run login.mjs --remote --authorization-response-stdin with either the code provided by the Volcengine authorization page (Base64 result) or the complete callback URL on controlled stdin; the decoded result must include state",
          };
        let timer;
        try {
          result = await Promise.race([
            callback,
            new Promise((_, reject) => {
              timer = setTimeout(
                () => reject(new Error("Login timed out")),
                timeoutMs
              );
            }),
          ]);
        } finally {
          clearTimeout(timer);
        }
      }
      const code = decodeAuthorizationResponse(result, pending.state);
      const token = await exchangeToken(
        {
          grant_type: "authorization_code",
          client_id: pending.clientId,
          scope: SCOPE,
          code,
          code_verifier: pending.verifier,
          redirect_uri: pending.redirectUri,
        },
        { fetchImpl }
      );
      const session = tokenSession(
        token,
        { clientId: pending.clientId },
        clock()
      );
      await writeStore(profile, "session", session, env);
      await removeStore(profile, "pending", env);
      return {
        profile,
        environment: "online",
        account_id: session.account_id,
        status: "authenticated",
      };
    } finally {
      if (server) {
        server.closeAllConnections();
        await new Promise((resolve) => server.close(resolve));
      }
    }
  });
}

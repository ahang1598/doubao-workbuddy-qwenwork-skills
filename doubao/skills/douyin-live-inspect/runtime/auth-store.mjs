import {
  mkdir,
  chmod,
  readFile,
  writeFile,
  rename,
  rm,
  readdir,
  stat,
} from "node:fs/promises";
import { homedir } from "node:os";
import { resolve, join } from "node:path";
import { createHash, randomUUID } from "node:crypto";
export function configDir(env = process.env) {
  return env.DOUYIN_LIVE_INSPECT_CONFIG_DIR
    ? resolve(env.DOUYIN_LIVE_INSPECT_CONFIG_DIR)
    : join(homedir(), ".douyin-live-inspect");
}
export function profileName(input = {}) {
  const p = input.profile ?? "default";
  if (typeof p !== "string" || !p.trim() || p.length > 128)
    throw new Error("Invalid profile");
  return p.trim();
}
export function storePath(profile, kind = "session", env) {
  return join(
    configDir(env),
    `${createHash("sha256").update(profile).digest("hex")}.${kind}.json`
  );
}
export async function readStore(profile, kind, env, signal) {
  try {
    return JSON.parse(await readFile(storePath(profile, kind, env), { encoding: "utf8", signal }));
  } catch (e) {
    if (e.code === "ABORT_ERR") throw e;
    if (e.code === "ENOENT") return null;
    throw new Error("Authentication cache is invalid");
  }
}
export async function writeStore(profile, kind, value, env) {
  const root = configDir(env);
  await mkdir(root, { recursive: true, mode: 0o700 });
  await chmod(root, 0o700);
  const path = storePath(profile, kind, env);
  const temp = `${path}.${randomUUID()}.tmp`;
  try {
    await writeFile(temp, JSON.stringify(value), { mode: 0o600, flag: "wx" });
    await rename(temp, path);
  } finally {
    await rm(temp, { force: true });
  }
}
export async function removeStore(profile, kind, env) {
  await rm(storePath(profile, kind, env), { force: true });
}
// Each acquisition has an immutable unique filename. Dead-owner recovery therefore
// cannot unlink a new owner's lock, even when several processes recover together.
// Ticket ordering is Lamport's bakery algorithm; zero means choosing a ticket.
export async function withProfileLock(
  profile,
  env,
  fn,
  { waitMs = 35000, pollMs = 50, missingPidAgeMs = 600000, signal } = {}
) {
  const root = configDir(env);
  await mkdir(root, { recursive: true, mode: 0o700 });
  await chmod(root, 0o700);
  const directory = `${storePath(profile, "lock", env)}.d`;
  await mkdir(directory, { recursive: true, mode: 0o700 });
  await chmod(directory, 0o700);
  const id = `${process.pid}.${randomUUID()}.json`;
  const path = join(directory, id);
  const deadline = Date.now() + waitMs;
  const pause = () => new Promise((resolve) => setTimeout(resolve, pollMs));
  async function contenders() {
    const result = [];
    for (const name of await readdir(directory)) {
      if (!name.endsWith(".json")) continue;
      const entry = join(directory, name);
      try {
        const pid = Number(/^(\d+)\./.exec(name)?.[1]);
        if (Number.isSafeInteger(pid) && pid > 0) {
          let dead = false;
          try {
            process.kill(pid, 0);
          } catch (error) {
            dead = error.code === "ESRCH";
          }
          if (dead) {
            await rm(entry, { force: true });
            continue;
          }
        } else if (Date.now() - (await stat(entry)).mtimeMs > missingPidAgeMs) {
          await rm(entry, { force: true });
          continue;
        }
        let ticket = 0;
        try {
          ticket = JSON.parse(await readFile(entry, "utf8")).ticket;
        } catch (error) {
          if (error.code === "ENOENT") continue;
        }
        result.push({
          id: name,
          ticket: Number.isSafeInteger(ticket) && ticket > 0 ? ticket : 0,
        });
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
      }
    }
    return result;
  }
  await writeFile(path, JSON.stringify({ ticket: 0 }), {
    mode: 0o600,
    flag: "wx",
  });
  try {
    const ticket =
      Math.max(0, ...(await contenders()).map((entry) => entry.ticket)) + 1;
    // Readers seeing a partially written ticket treat it as 'choosing' and wait.
    await writeFile(path, JSON.stringify({ ticket }), { mode: 0o600 });
    while (
      (await contenders()).some(
        (entry) =>
          entry.id !== id &&
          (entry.ticket === 0 ||
            entry.ticket < ticket ||
            (entry.ticket === ticket && entry.id < id))
      )
    ) {
      if (signal?.aborted)
        throw Object.assign(new Error("Authentication cancelled"), {
          code: "ABORT_ERR",
        });
      if (Date.now() >= deadline)
        throw new Error(
          "Authentication is busy; retry after the active operation finishes"
        );
      await pause();
    }
    return await fn();
  } finally {
    await rm(path, { force: true });
  }
}

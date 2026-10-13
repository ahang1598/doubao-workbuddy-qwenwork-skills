import { requireOriginalTaskContext, assertTaskAccount } from './task-binding.mjs';
import { resolveCredentials, requireOnline, authRequired } from "./auth.mjs";
export async function resolveUploadCredentials(input, deps = {}) {
  requireOnline(input);
  requireOriginalTaskContext(input);
  if (deps.resolveCredentials) {
    const result = await deps.resolveCredentials(input);
    const cred = result?.cred || result;
    assertTaskAccount(input, result);
    if (
      !cred?.accessKeyId ||
      !cred?.secretAccessKey ||
      (result.profile && input.profile && result.profile !== input.profile) ||
      (input.account_id && result.account_id !== input.account_id)
    )
      throw authRequired();
    return cred;
  }
  return resolveCredentials(input, {
    env: deps.env,
    fetchImpl: deps.fetchImpl,
    now: deps.now,
    signal: deps.signal,
  });
}

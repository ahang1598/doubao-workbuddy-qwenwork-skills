// 本文件负责正式版命令与 OpenAPI 操作的遥测包装：
// 在不改业务返回值的前提下，统一补充上下文、处理取消信号、避免嵌套重复记事件。
import { AsyncLocalStorage } from 'node:async_hooks';
import contract from './formal-telemetry-contract.cjs';
import {fitExtra} from '../lite/scripts/telemetry-contract.cjs';
import {reportRequest} from './request-telemetry.cjs';
import identity from '../lite/scripts/telemetry-identity.cjs';

import {EVENTS, disabled, createTelemetry, runEvent} from './telemetry-reporter.cjs';
export {EVENTS} from './telemetry-reporter.cjs';
// 用异步上下文在一次命令调用链内透传 telemetry 状态，避免到处手工传参。
const storage = new AsyncLocalStorage();
const operations = EVENTS.operations;
const scripts = new Set(Object.values(EVENTS.formal));
// 这些公共探测命令发生在“尚未明确选择正式版”之前，因此以 unselected 归类。
const publicSetup = new Set([EVENTS.formal.DETECT_ACCOUNT_ENTRY, EVENTS.formal.DETECT_RUNTIME_MODE,
  EVENTS.formal.CHECK_LOGIN_CAPABILITY, EVENTS.formal.AUTH_STATUS]);

export function addCommandContext(value) {
  const state = storage.getStore();
  if (state) Object.assign(state.extra, contract.safeFields(value));
}
export function addScenarioContext(value) { addCommandContext({scenario_category:contract.scenarioCategory(value)}); }

// Called only with a credential resolution the business already required.
export function observeAccount(account) {
  const state = storage.getStore();
  if (!state) return;
  // ponytail: 只拦截已知样例账号；其他人工测试用 BYTEDLIVE_TELEMETRY_DISABLED=1。
  if (account === '123' || account === '123456') state.testAccount = true;
  if (typeof account !== 'string' || !/^\d{1,128}$/.test(account) || (state.account && state.account !== account)) state.accountConflict = true;
  else state.account = account;
}
export function commandSignal() { return storage.getStore()?.controller?.signal; }
export function commandUserAgent() {
  try { return storage.getStore()?.telemetry?.getUserAgent(); } catch { return undefined; }
}
function observeError(error) {
  const state = storage.getStore();
  if (!state) return;
  const metadata = contract.errorMetadata(error);
  state.failed = true;
  state.cancelled ||= metadata.outcome === 'cancelled';
  // A later business guard must not hide a previously observed runtime fault.
  if (state.outcome !== 'failure') {
    state.outcome = metadata.outcome;
    addCommandContext({error_code:metadata.error_code});
  }
}
export function observeResult(value) {
  if (value?.ok === false) observeError(value.error || value.data?.error || {});
  return value;
}

export function isPreview(input, confirmationRequired = false) {
  // 统一兼容 dry_run / dry-run / dryRun 这类控制字段写法。
  const controls = Object.fromEntries(Object.entries(input || {}).map(([key,value])=>[key.replace(/[_-]/g,'').toLowerCase(),value]));
  return controls.dryrun === true || controls.plan === true || (confirmationRequired && !controls.confirmtoken);
}

// 运行命令核心逻辑
export async function runCommand(name, handler, {skip = false, env = process.env} = {}) {
  const parent = storage.getStore();
  // 内层调用直接复用外层上下文，避免同一条调用链被重复记成多次入口事件。
  if ((parent && (parent.name === name || !operations[name])) || skip || process.argv.includes('--help') || process.argv.includes('-h') || disabled() || (!operations[name] && !scripts.has(name))) return handler();
  if (!parent && env.INSPECT_ENTRY_PROBE !== '1') {
    const selection = [EVENTS.formal.DOUYIN_TASK_CREATE, 'quality/+task-create', 'content/+video-task-create'].includes(name) ? 'formal' : undefined;
    try { await reportRequest({mode:'formal', select:!!selection, env}); } catch { /* Optional request metadata. */ }
  }
  // workflow 包装器本身不抢占上报权，真正的 operation 才是最终事件所有者。
  if (parent && operations[name]) parent.serviceEvents = true;
  let telemetry;
  try {
    telemetry = createTelemetry({toolName:'douyin-live-inspect', isolated:Boolean(operations[name])});
  // telemetry 初始化失败时直接退化为纯业务执行，不影响命令本身。
  } catch { return handler(); }
  const canonicalCommand = operations[name] || name;
  // 正式版脚本命令与底层 operation 共用同一套 extra 合同，但来源不同。
  const extra = operations[name] ? contract.inspectionMetadata(canonicalCommand, {...env,VE_SKILL_ID:process.env.VE_SKILL_ID,BYTEDLIVE_INSPECT_FEATURE:env.BYTEDLIVE_INSPECT_FEATURE || (parent?.extra.feature==='live_recap'?'live_recap':undefined)}) : contract.commandMetadata(name, publicSetup.has(name) ? 'unselected':'formal', {workflow_kind:env.BYTEDLIVE_INSPECT_WORKFLOW_KIND || env.INSPECT_TELEMETRY_WORKFLOW, scenario_category:env.BYTEDLIVE_INSPECT_SCENARIO_CATEGORY || 'unknown'});
  try { Object.assign(extra, await identity.resolveIdentity(process.env), {deviceId:identity.resolveDeviceId(process.env)}); } catch { /* optional attribution */ }
  Object.assign(extra, contract.safeFields(parent?.extra || {}));
  // state 是整次命令期间的共享态：既给业务读，也给 telemetry 收口时用。
  const state = {name, telemetry, extra, account:parent?.account, accountConflict:parent?.accountConflict, controller:new AbortController()};
  // workflow 包装层让出 reporter；底层 service 已上报时，这里不再重复发送。
  // 即便 SDK reporter 不可用，也不能因此重放业务逻辑。
  try {
    const reporter = telemetry.getReporter();
    telemetry.reporter = {report:event => {
      if (state.serviceEvents || state.testAccount) return;
      // Classify the emitted event, never clear process.exitCode or change the
      // handler result. SDK exit-code checks must not turn a business guard
      // back into a runtime failure.
      if (state.outcome === 'failure') {
        event = {...event, result:'failure', error_message:'Inspection command failed'};
      } else if (!state.cancelled && state.outcome === 'business_rejected') {
        event = {...event, result:'business_rejected', error_message:undefined};
      }
      return reporter.report(event);
    }};
  } catch { /* Older SDK fixture without a reporter. */ }
  let signalReceived;
  const signals = process.platform === 'win32' ? ['SIGINT','SIGTERM'] : ['SIGINT','SIGTERM','SIGHUP'];
  const listeners = new Map(signals.map(signal=>[signal, ()=>{
    signalReceived = signal;
    state.cancelled = true;
    // 把进程级中断翻译成可传递给业务代码的 AbortSignal。
    state.controller.abort(Object.assign(new Error('Command cancelled'), {name:'AbortError',code:'CANCELLED'}));
  }]));
  for (const [signal,listener] of listeners) process.on(signal,listener);
  let business, originalError;
  // 业务函数只允许真正执行一次；后续无论 SDK 成败还是补偿路径都复用同一个 Promise。
  const execute = () => business ??= Promise.resolve().then(handler).then(observeResult);
  // 收到取消后先给业务一小段时间自我收敛，避免已经被服务端接受的写操作被过早打断。
  // 若业务不响应 AbortSignal，再由本地兜底超时结束等待。
  let cancelTimer;
  const cancelled = new Promise((_,reject)=>state.controller.signal.addEventListener('abort',()=>{
    cancelTimer = setTimeout(()=>reject(state.controller.signal.reason), 250);
  },{once:true}));
  // 将共享状态挂到异步上下文后执行，确保 handler 内部任意层级都能读到统一 telemetry 状态。
  await storage.run(state, async () => {
    try {
      await runEvent(telemetry, canonicalCommand, async () => {
        try { await Promise.race([execute(),cancelled]); } catch (error) { originalError = error; observeError(error); }
        if (!state.failed && Number(process.exitCode) > 0) observeError({});
        try {
          const fitted = fitExtra(state.extra);
          if (fitted) telemetry.addExtra(fitted);
          // 仅在账号来源单一且可信时写入 accountId，避免多账号冲突导致错误归因。
          if (state.account && !state.accountConflict) telemetry.setAccountId(state.account);
        } catch { /* metadata must not alter execution */ }
        if (state.failed || state.cancelled) { const safe = new Error('Inspection command failed'); if (state.cancelled && state.outcome !== 'failure') safe.name = 'AbortError'; throw safe; }
      });
    } catch { /* SDK and sanitized business failures are handled independently. */ }
    // SDK 可能在调用前或调用后失败；这里只负责兜底拿回真实业务结果，绝不重复执行 handler。
    if (!signalReceived) { try { await execute(); } catch (error) { originalError = error; } }
  });
  clearTimeout(cancelTimer);
  for (const [signal,listener] of listeners) process.removeListener(signal,listener);
  if (signalReceived) {
    // telemetry 尽力收尾后，恢复进程收到信号时原本应有的退出语义。
    if (process.platform === 'win32') process.exit(signalReceived === 'SIGINT' ? 130 : 143);
    else { process.removeAllListeners(signalReceived); process.kill(process.pid,signalReceived); await new Promise(()=>{}); }
  }
  if (originalError) throw originalError;
  return business;
}

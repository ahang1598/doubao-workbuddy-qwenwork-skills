#!/usr/bin/env node
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';

const usage = 'node scripts/inspect-entry.mjs --kind live|video --task-state not_created|existing [--profile NAME] [--environment online] [--no-lite] [--mode lite|formal] [--new-request] [--expected-tasks 1..100] [--task-dir PATH | --batch-dir PATH]';
const sourceGuidance = '入口不接收 URL 或位置参数。来源链接保留在对话中，选择版本后交给对应创建流程；每个参数须单独传入。新建直播入口：node scripts/inspect-entry.mjs --kind live --task-state not_created';

// 新请求的第一站只负责分流和预留任务目录：这里不能登录、创建远端任务或启动采集。
// 这样版本选择前不会产生副作用，后续流程也能复用同一个 task_dir。

// Dynamic import lets an incomplete installation produce one safe decision,
// rather than an unstructured MODULE_NOT_FOUND that could trigger a wrong route.
try {
  const { values } = parseArgs({
    options: {
      mode: { type: 'string' },
      kind: { type: 'string' },
      profile: { type: 'string' },
      environment: { type: 'string', default: 'online' },
      'task-dir': { type: 'string' },
      'batch-dir': { type: 'string' },
      'task-state': { type: 'string' },
      'expected-tasks': { type: 'string' },
      'new-request': { type: 'boolean', default: false },
      'no-lite': { type: 'boolean', default: false },
      help: { type: 'boolean', default: false },
    },
  });
  if (values.help) {
    process.stdout.write(
      `Usage: ${usage}\n${sourceGuidance}\nNew requests may clarify their source; existing requests reuse their directory. Does not log in or create tasks.\n`,
    );
  } else {
    // 单任务和批次目录互斥，避免同一次请求出现两个无法判断归属的持久化位置。
    if (values['task-dir'] && values['batch-dir']) throw Error('choose one task directory');
    if (values.mode !== undefined && !['lite', 'formal'].includes(values.mode))
      throw Error('unsupported entry mode');
    const existing = values['task-state'] === 'existing';
    if (
      values['expected-tasks'] !== undefined &&
      (values.kind !== 'video' ||
        !/^\d+$/.test(values['expected-tasks']) ||
        Number(values['expected-tasks']) < 1 ||
        Number(values['expected-tasks']) > 100)
    )
      throw Error('invalid expected task count');
    const directory = values['task-dir'] || values['batch-dir'];
    if (
      !['not_created', 'existing'].includes(values['task-state']) ||
      values.environment !== 'online' ||
      (values.kind !== undefined && !['live', 'video'].includes(values.kind)) ||
      (existing && (!values.mode || !directory)) ||
      (values.mode === 'lite' && values['no-lite'])
    )
      throw Error('invalid business entry');
    const { reserveTask, readContext } = await import('../runtime/lite-task-context.cjs');
    let context;
    // existing 只读取并续办已有身份；not_created 才会预留新的本地身份。
    if (existing) {
      const task_dir = fs.realpathSync(directory);
      const value = readContext(task_dir);
      if (
        !(values.mode === 'formal' && value) &&
        !['inspection.db', 'batch.json'].some((name) =>
          fs.statSync(path.join(task_dir, name), { throwIfNoEntry: false })?.isFile(),
        )
      )
        throw Error('existing task is required');
      context = { task_dir, ...(value ? { task_id: value.task_id } : {}) };
    } else {
      context = reserveTask(directory);
      if (!context) throw Error('existing task requires continuation');
    }
    const { default: telemetry } = await import('../telemetry/main.mjs');
    process.env.INSPECT_USAGE_CONTEXT_DIR = context.task_dir;
    await telemetry.withContext({}, (current) =>
      current.skillStart({
        mode: values.mode,
        context,
        existing,
        kind: values.kind,
        batch: !!values['batch-dir'],
        expected:
          values['expected-tasks'] === undefined ? undefined : Number(values['expected-tasks']),
        newRequest: values['new-request'],
      }),
    );
    const { inspectEntry } = await import('../runtime/inspect-entry.mjs');
    // 显式选择 Lite 可以直接返回；正式版必须经过能力探测，防止把未配置账号误判为可用。
    const result =
      values.mode && (existing || values.mode === 'lite')
        ? {
            ok: true,
            command: 'inspect-entry',
            data: {
              route: values.mode,
              reason: 'explicit_version_selection',
              next_action: existing
                ? 'continue_existing_task'
                : values.mode === 'lite'
                  ? 'start_lite'
                  : 'continue_formal',
            },
          }
        : values.kind === undefined
          ? {
              ok: true,
              command: 'inspect-entry',
              data: {
                route: 'clarify',
                reason: 'source_required',
                next_action: 'clarify_source',
              },
            }
          : await inspectEntry(
              {
                mode: values.mode,
                kind: values.kind,
                profile: values.profile,
                environment: values.environment,
                task_state: values['task-state'],
                allow_lite: !values['no-lite'],
              },
              { env: { ...process.env, INSPECT_ENTRY_PROBE: '1' } },
            );
    if (
      !existing &&
      values.mode !== result.data.route &&
      ['lite', 'formal'].includes(result.data.route)
    )
      await telemetry.withContext({}, (current) =>
        current.versionSelected({ mode: result.data.route, context }),
      );
    await telemetry.withContext({}, (current) =>
      current.operationCompleted({
        operation: 'entry',
        kind: values.kind,
        existing,
        result,
      }),
    );
    Object.assign(result.data, {
      ...(context.task_id && result.data.route !== 'formal' ? { task_id: context.task_id } : {}),
      [values['batch-dir'] ? 'batch_dir' : 'task_dir']: context.task_dir,
      ...(!existing && result.data.route === 'lite' && values.kind
        ? {
            start_command_argv: values['batch-dir']
              ? ['batch-create', '--batch-dir', context.task_dir]
              : [values.kind === 'video' ? 'start-video' : 'start', '--task-dir', context.task_dir],
          }
        : {}),
      execution_env: { INSPECT_USAGE_CONTEXT_DIR: context.task_dir },
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
    process.exitCode = result.ok ? 0 : 2;
  }
} catch (error) {
  const missing = ['MODULE_NOT_FOUND', 'ERR_MODULE_NOT_FOUND'].includes(error.code);
  // 固定文案避免 parseArgs 的原始错误回显来源链接、签名或其他敏感参数。
  const argumentMessage = {
    ERR_PARSE_ARGS_UNEXPECTED_POSITIONAL: '存在不支持的位置参数。',
    ERR_PARSE_ARGS_UNKNOWN_OPTION: '存在不支持的选项，请按 usage 检查参数名。',
    ERR_PARSE_ARGS_INVALID_OPTION_VALUE: '选项缺少值或值类型错误，请按 usage 检查。',
    ERR_PARSE_ARGS_INVALID_OPTION_VALUE_AMBIGUOUS: '选项值与选项名有歧义，请按 usage 检查。',
  }[error.code];
  process.stdout.write(
    `${JSON.stringify({
      ok: false,
      command: 'inspect-entry',
      data: {
        route: 'blocked',
        reason: missing ? 'skill_installation_incomplete' : 'invalid_input_or_execution_failed',
        next_action: 'resolve_blocker',
        ...(argumentMessage ? { message: `${argumentMessage}${sourceGuidance}`, usage } : {}),
        activation_guidance_required: false,
        diagnostics: {
          stage: missing ? 'installation' : 'validation',
          category: missing ? 'script_missing' : 'invalid_input',
          attempts: 0,
        },
      },
    })}\n`,
  );
  process.exitCode = 2;
}

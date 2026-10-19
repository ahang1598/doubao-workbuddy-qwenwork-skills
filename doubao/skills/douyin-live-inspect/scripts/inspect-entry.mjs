#!/usr/bin/env node
import { parseArgs } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';

// Dynamic import lets an incomplete installation produce one safe decision,
// rather than an unstructured MODULE_NOT_FOUND that could trigger a wrong route.
try {
  const { values } = parseArgs({ options: {
    mode: { type: 'string' }, kind: { type: 'string' }, profile: { type: 'string' },
    environment: { type: 'string', default: 'online' },
    'task-dir': { type: 'string' }, 'batch-dir': { type: 'string' },
    'task-state': { type: 'string' }, 'expected-tasks': {type:'string'}, 'new-request': {type:'boolean', default:false},
    'no-lite': { type: 'boolean', default: false }, help: { type: 'boolean', default: false },
  } });
  if (values.help) {
    process.stdout.write('Usage: node scripts/inspect-entry.mjs --kind live|video --task-state not_created|existing [--profile NAME] [--environment online] [--no-lite] [--mode lite|formal] [--new-request] [--expected-tasks 1..100] [--task-dir PATH | --batch-dir PATH]\nNew requests may clarify their source; existing requests reuse their directory. Does not log in or create tasks.\n');
  } else {
    if (values['task-dir'] && values['batch-dir']) throw Error('choose one task directory');
    if (values.mode !== undefined && !['lite','formal'].includes(values.mode)) throw Error('unsupported entry mode');
    const existing = values['task-state'] === 'existing';
    if(values['expected-tasks']!==undefined && (values.kind!=='video'||!/^\d+$/.test(values['expected-tasks'])||Number(values['expected-tasks'])<1||Number(values['expected-tasks'])>100))throw Error('invalid expected task count');
    const directory = values['task-dir'] || values['batch-dir'];
    if (!['not_created','existing'].includes(values['task-state']) || values.environment !== 'online' ||
        (values.kind !== undefined && !['live','video'].includes(values.kind)) ||
        (existing && (!values.mode || !directory)) || (values.mode==='lite' && values['no-lite'])) throw Error('invalid business entry');
    const {reserveTask, readContext} = await import('../runtime/lite-task-context.cjs');
    let context;
    if (existing) {
      const task_dir = fs.realpathSync(directory);
      const value = readContext(task_dir);
      if (!(values.mode === 'formal' && value) && !['inspection.db','batch.json'].some(name=>fs.statSync(path.join(task_dir,name),{throwIfNoEntry:false})?.isFile())) throw Error('existing task is required');
      context = {task_dir, ...(value ? {task_id:value.task_id} : {})};
    } else {
      context = reserveTask(directory);
      if (!context) throw Error('existing task requires continuation');
    }
    const {reportRequest} = await import('../runtime/request-telemetry.cjs');
    process.env.INSPECT_USAGE_CONTEXT_DIR=context.task_dir;
    const flow = (await import('../runtime/workflow-telemetry.cjs')).default;
    if (!existing) await flow.begin({kind:values.kind,mode:values.mode,expected:values['expected-tasks']===undefined?undefined:Number(values['expected-tasks'])});
    await reportRequest({mode:values.mode, context, newRequest:values['new-request'], select:!existing});
    const { inspectEntry } = await import('../runtime/inspect-entry.mjs');
    const result = values.mode ? {ok:true,command:'inspect-entry',data:{route:values.mode,reason:'explicit_version_selection',
      next_action:existing ? 'continue_existing_task' : values.mode==='lite' ? 'start_lite' : 'continue_formal'}} :
      values.kind === undefined ? {ok:true,command:'inspect-entry',data:{route:'clarify',reason:'source_required',next_action:'clarify_source'}} :
      await inspectEntry({ kind: values.kind, profile: values.profile, environment: values.environment,
        task_state: values['task-state'], allow_lite: !values['no-lite'] }, {env:{...process.env,INSPECT_ENTRY_PROBE:'1'}});
    if (!values.mode && ['lite','formal'].includes(result.data.route)) await reportRequest({mode:result.data.route, context});
    if (!existing) {
      await flow.begin({kind:values.kind,mode:result.data.route});
      if (!result.ok || result.data.route==='blocked') await flow.problem('entry','SETUP_PENDING');
    }
    Object.assign(result.data, { ...(context.task_id && result.data.route!=='formal' ? {task_id:context.task_id} : {}),
      [values['batch-dir'] ? 'batch_dir' : 'task_dir']:context.task_dir,
      execution_env:{INSPECT_USAGE_CONTEXT_DIR:context.task_dir}});
    process.stdout.write(`${JSON.stringify(result)}\n`);
    process.exitCode = result.ok ? 0 : 2;
  }
} catch (error) {
  const missing = ['MODULE_NOT_FOUND', 'ERR_MODULE_NOT_FOUND'].includes(error.code);
  process.stdout.write(`${JSON.stringify({ ok: false, command: 'inspect-entry', data: {
    route: 'blocked', reason: missing ? 'skill_installation_incomplete' : 'invalid_input_or_execution_failed',
    next_action: 'resolve_blocker', activation_guidance_required: false,
    diagnostics: { stage: missing ? 'installation' : 'validation', category: missing ? 'script_missing' : 'invalid_input', attempts: 0 },
  } })}\n`);
  process.exitCode = 2;
}

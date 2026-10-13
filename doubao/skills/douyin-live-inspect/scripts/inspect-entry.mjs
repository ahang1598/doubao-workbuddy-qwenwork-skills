#!/usr/bin/env node
import { parseArgs } from 'node:util';

// Dynamic import lets an incomplete installation produce one safe decision,
// rather than an unstructured MODULE_NOT_FOUND that could trigger a wrong route.
try {
  const { values } = parseArgs({ options: {
    kind: { type: 'string' }, profile: { type: 'string' },
    environment: { type: 'string', default: 'online' },
    'task-state': { type: 'string' },
    'no-lite': { type: 'boolean', default: false }, help: { type: 'boolean', default: false },
  } });
  if (values.help) {
    process.stdout.write('Usage: node scripts/inspect-entry.mjs --kind live|video --task-state not_created [--profile NAME] [--environment online] [--no-lite]\nOnly new requests with a known source. Does not log in or create tasks.\n');
  } else {
    const { inspectEntry } = await import('../runtime/inspect-entry.mjs');
    const result = await inspectEntry({ kind: values.kind, profile: values.profile, environment: values.environment,
      task_state: values['task-state'], allow_lite: !values['no-lite'] });
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

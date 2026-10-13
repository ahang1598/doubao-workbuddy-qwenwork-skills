#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { checkInspectionService } from '../runtime/inspection-service.mjs';

try {
  const { values } = parseArgs({ options: {
    kind: { type: 'string' }, profile: { type: 'string' },
    environment: { type: 'string', default: 'online' },
    'task-state': { type: 'string' }, 'no-lite': { type: 'boolean', default: false },
    help: { type: 'boolean', default: false },
  } });
  if (values.help) {
    process.stdout.write('Usage: node scripts/check-inspection-service.mjs --kind live|video [--profile NAME] --environment online --task-state not_created [--no-lite]\nOnly for new requests with no created or uncertain task. No login or task creation is performed.\n');
  } else {
    const result = await checkInspectionService({
      kind: values.kind, profile: values.profile, environment: values.environment,
      task_state: values['task-state'], allow_lite: !values['no-lite'],
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
    process.exitCode = result.ok ? 0 : 2;
  }
} catch {
  process.stdout.write(`${JSON.stringify({ ok: false, command: 'check-inspection-service', data: {
    route: 'blocked', reason: 'invalid_input_or_execution_failed', next_action: 'resolve_blocker',
  } })}\n`);
  process.exitCode = 2;
}

#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { executeOperation, getOperationSchema } from '../runtime/operations.mjs';
import { runCommand, observeResult, isPreview } from '../runtime/telemetry.mjs';
const MAX_INPUT_BYTES = 2 * 1024 * 1024;
try {
  const { values } = parseArgs({ options: { operation: { type: 'string' }, schema: { type: 'boolean' }, help: { type: 'boolean' } }, strict: true, allowPositionals: false });
  if (values.help) {
    console.log('Usage: node scripts/api.mjs --operation NAME < input.json\n       node scripts/api.mjs --schema [--operation NAME]\nInput: one JSON object on stdin.');
  } else {
    if (values.operation !== undefined && !getOperationSchema(values.operation)) throw new Error('Unknown operation');
    if (values.schema) console.log(JSON.stringify(getOperationSchema(values.operation)));
    else {
      if (!values.operation) throw new Error('An operation is required');
      const chunks = [];
      let bytes = 0;
      for await (const chunk of process.stdin) {
        const buffer = Buffer.from(chunk);
        bytes += buffer.length;
        if (bytes > MAX_INPUT_BYTES) throw new Error('Input is too large');
        chunks.push(buffer);
      }
      const input = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
      const result = await runCommand(values.operation, async () => {
        const result = observeResult(await executeOperation(values.operation, input));
        process.exitCode = result.code || 0;
        return result;
      }, {skip:isPreview(input, getOperationSchema(values.operation)?.requiresConfirmation)});
      console.log(JSON.stringify(result));
      process.exitCode = result.code || 0;
    }
  }
} catch {
  console.log(JSON.stringify({ ok: false, error: { code: 'INVALID_INPUT', write_occurred: false, message: 'Invalid arguments or JSON input; use --help or --schema' } }));
  process.exitCode = 2;
}

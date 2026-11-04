#!/usr/bin/env node
import { readStdin } from '../runtime/script-input.mjs';
import telemetry, { isPreview } from '../telemetry/main.mjs';
// 解析 OpenAPI 命令与 JSON 输入，调用运行时并输出结构化结果。
import { parseArgs } from 'node:util';
import { executeOperation, getOperationSchema } from '../runtime/operations.mjs';
const MAX_INPUT_BYTES = 2 * 1024 * 1024;
try {
  const { values } = parseArgs({
    options: {
      operation: { type: 'string' },
      schema: { type: 'boolean' },
      help: { type: 'boolean' },
    },
    strict: true,
    allowPositionals: false,
  });
  if (values.help) {
    console.log(
      'Usage: node scripts/api.mjs --operation NAME < input.json\n       node scripts/api.mjs --schema [--operation NAME]\nInput: one JSON object on stdin.',
    );
  } else {
    if (values.operation !== undefined && !getOperationSchema(values.operation))
      throw new Error('Unknown operation');
    if (values.schema) console.log(JSON.stringify(getOperationSchema(values.operation)));
    else {
      if (!values.operation) throw new Error('An operation is required');
      const input = JSON.parse(
        (await readStdin(MAX_INPUT_BYTES, new Error('Input is too large'))).toString('utf8') ||
          '{}',
      );
      const result = await telemetry.runCommand(
        {
          command: values.operation,
          skip: isPreview(input, getOperationSchema(values.operation)?.requiresConfirmation),
        },
        async () => {
          const result = await executeOperation(values.operation, input);
          process.exitCode = result.code || 0;
          return result;
        },
      );
      console.log(JSON.stringify(result));
    }
  }
} catch {
  console.log(
    JSON.stringify({
      ok: false,
      error: {
        code: 'INVALID_INPUT',
        write_occurred: false,
        message: 'Invalid arguments or JSON input; use --help or --schema',
      },
    }),
  );
  process.exitCode = 2;
}

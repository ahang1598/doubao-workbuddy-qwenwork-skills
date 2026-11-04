import { createRequire } from 'node:module';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { args } from '../lib/cli-utils.mjs';
import { readSlardarSdk } from '../lib/slardar-sdk.mjs';
import { readTelemetryTask } from '../lib/task-telemetry.mjs';
import { sendTelemetryBatch } from '../lib/slardar-node-transport.mjs';

const state = await readTelemetryTask(args().task);
if (
  state.env !== 'production' ||
  process.env.MAP_CREATE_TELEMETRY_DISABLED === '1'
)
  process.exit(0);
const directory = await mkdtemp(join(tmpdir(), 'map-slardar-'));
try {
  const { files } = readSlardarSdk();
  for (const name of ['node.cjs', 'machine.cjs'])
    await writeFile(join(directory, name), files[name]);
  const { Slardar } = createRequire(import.meta.url)(
    join(directory, 'node.cjs'),
  );
  const eventIds = await sendTelemetryBatch(Slardar, state);
  process.stdout.write(JSON.stringify({ event_ids: eventIds }));
} finally {
  await rm(directory, { recursive: true, force: true });
}

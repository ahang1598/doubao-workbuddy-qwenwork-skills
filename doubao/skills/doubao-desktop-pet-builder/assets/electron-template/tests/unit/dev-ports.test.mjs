import assert from 'node:assert/strict';
import net from 'node:net';
import test from 'node:test';
import { findAvailablePort, parsePort, selectDevelopmentPorts } from '../../tools/dev-ports.mjs';

test('parsePort rejects invalid values', () => {
  assert.throws(() => parsePort('900', 'PET_DEV_PORT'), /between 1024 and 65535/);
  assert.throws(() => parsePort('not-a-port', 'PET_DEV_PORT'), /integer TCP port/);
});

test('automatic selection moves past an occupied preferred port', async () => {
  const occupied = net.createServer();
  await new Promise((resolve) => occupied.listen(0, resolve));
  const address = occupied.address();
  assert.ok(address && typeof address === 'object');
  const selected = await findAvailablePort(address.port);
  assert.notEqual(selected, address.port);
  await new Promise((resolve) => occupied.close(resolve));
});

test('explicit occupied port fails with an actionable message', async () => {
  const occupied = net.createServer();
  await new Promise((resolve) => occupied.listen(0, resolve));
  const address = occupied.address();
  assert.ok(address && typeof address === 'object');
  await assert.rejects(
    selectDevelopmentPorts({ PET_DEV_PORT: String(address.port), PET_LOGGER_PORT: '19001' }),
    /already in use/,
  );
  await new Promise((resolve) => occupied.close(resolve));
});

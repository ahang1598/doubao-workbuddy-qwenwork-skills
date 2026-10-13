import test from 'node:test';
import assert from 'node:assert/strict';
import { TypingListener } from '../../src/main/typing-listener';

test('typing listener reports disabled settings explicitly', () => {
  const listener = new TypingListener();
  assert.deepEqual(listener.start(false, () => {}), { enabled: false, reason: 'disabled-by-settings' });
  listener.stop();
});

test('typing listener fails closed when the optional native provider is unavailable', () => {
  const listener = new TypingListener();
  assert.deepEqual(listener.start(true, () => {}), { enabled: false, reason: 'not-available' });
  listener.stop();
});

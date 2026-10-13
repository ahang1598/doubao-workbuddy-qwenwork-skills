import test from 'node:test';
import assert from 'node:assert/strict';
import type { PetState } from '../../src/shared/contracts';
import { PetStateMachine } from '../../src/renderer/pet/state-machine';

function state(id: string, overrides: Partial<PetState> = {}): PetState {
  return {
    id,
    triggers: [],
    frames: [`${id}-1.png`, `${id}-2.png`],
    frameDurationMs: 100,
    loop: false,
    priority: 20,
    interrupt: 'restart',
    cooldownMs: 0,
    direction: 'neutral',
    anchor: { x: 0.5, y: 0.95 },
    mirrorSafe: true,
    ...overrides,
  };
}

const idle = state('idle', { loop: true, priority: 10, interrupt: 'resume' });

test('timed looping activity returns to idle', () => {
  const machine = new PetStateMachine([idle, state('play', { loop: true })], 0);
  assert.equal(machine.start('play', 10, 250), true);
  assert.equal(machine.tick(259).stateId, 'play');
  assert.equal(machine.tick(260).stateId, 'idle');
  assert.equal(machine.tick(10_000).stateId, 'idle');
});

test('only idle loops indefinitely by default', () => {
  const machine = new PetStateMachine([idle, state('looping', { loop: true })], 0);
  machine.start('looping', 0);
  assert.equal(machine.tick(199).stateId, 'looping');
  assert.equal(machine.tick(200).stateId, 'idle');
});

test('priority, restart and resume rules are enforced', () => {
  const high = state('high', { priority: 80 });
  const restart = state('restart', { priority: 80, interrupt: 'restart' });
  const resume = state('resume', { priority: 80, interrupt: 'resume' });
  const low = state('low', { priority: 30 });
  const machine = new PetStateMachine([idle, high, restart, resume, low], 0);
  machine.start('high', 0, 500);
  assert.equal(machine.start('low', 10), false);
  assert.equal(machine.start('restart', 20, 500), true);
  assert.equal(machine.start('restart', 30, 500), true);
  assert.equal(machine.start('resume', 40, 500), true);
  assert.equal(machine.start('resume', 50, 500), false);
});

test('cooldown starts when an activity completes', () => {
  const action = state('action', { cooldownMs: 300 });
  const machine = new PetStateMachine([idle, action], 0);
  machine.start('action', 0, 100);
  machine.tick(100);
  assert.equal(machine.start('action', 399), false);
  assert.equal(machine.start('action', 400), true);
});

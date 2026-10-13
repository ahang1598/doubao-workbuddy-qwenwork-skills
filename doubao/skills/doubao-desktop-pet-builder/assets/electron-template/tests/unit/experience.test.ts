import test from 'node:test';
import assert from 'node:assert/strict';
import {
  localDateKey,
  MAX_TIMER_DELAY_MS,
  nextReminderDelay,
  parsePersistedStats,
  parseReminders,
  parseSettings,
} from '../../src/main/data-validation';
import { assertSettingsPatch } from '../../src/shared/contracts';

test('local date keys use calendar fields instead of UTC serialization', () => {
  const fakeLocalDate = {
    getFullYear: () => 2026,
    getMonth: () => 6,
    getDate: () => 28,
  } as Date;
  assert.equal(localDateKey(fakeLocalDate), '2026-07-28');
});

test('settings accept only complete, finite, whitelisted values', () => {
  const valid = { edgeSnap: true, alwaysOnTop: true, typingReaction: false, clickThrough: false, petScale: 0.8 };
  assert.deepEqual(parseSettings(valid), valid);
  assert.throws(() => parseSettings({ ...valid, petScale: Number.NaN }), /petScale/);
  assert.throws(() => parseSettings({ ...valid, petScale: 0.81 }), /petScale/);
  assert.throws(() => parseSettings({ ...valid, surprise: true }), /Unknown/);
  assert.throws(() => assertSettingsPatch({ edgeSnap: 1 }), /edgeSnap/);
  assert.throws(() => assertSettingsPatch({ constructor: true }), /Unknown/);
});

test('persisted stats and reminders reject malformed values', () => {
  const stats = {
    affection: 12,
    mood: 80,
    todayInteractions: 3,
    totalCompanionMs: 1234,
    lastInteractionDate: '2026-07-28',
  };
  assert.deepEqual(parsePersistedStats(stats), stats);
  assert.throws(() => parsePersistedStats({ ...stats, todayInteractions: 1.5 }), /todayInteractions/);
  assert.throws(() => parseReminders([{ id: 'x', text: '', dueAt: new Date().toISOString(), createdAt: new Date().toISOString() }]), /text/);
});

test('long reminders are split at the platform timer limit', () => {
  const now = Date.parse('2026-01-01T00:00:00.000Z');
  assert.equal(nextReminderDelay(new Date(now + 1_000).toISOString(), now), 1_000);
  assert.equal(nextReminderDelay(new Date(now + MAX_TIMER_DELAY_MS + 60_000).toISOString(), now), MAX_TIMER_DELAY_MS);
  assert.equal(nextReminderDelay(new Date(now - 1).toISOString(), now), 0);
});

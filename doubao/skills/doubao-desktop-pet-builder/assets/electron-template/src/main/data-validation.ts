import type { Reminder, Settings } from '../shared/contracts';

export interface PersistedStats {
  affection: number;
  mood: number;
  todayInteractions: number;
  totalCompanionMs: number;
  lastInteractionDate: string;
}

export const MAX_TIMER_DELAY_MS = 2_147_000_000;
export const PET_SCALES = [0.65, 0.8, 1, 1.2] as const;

function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new TypeError(`Invalid ${label}`);
  return value as Record<string, unknown>;
}

export function localDateKey(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function parseSettings(value: unknown): Settings {
  const obj = record(value, 'settings');
  const expected = new Set(['edgeSnap', 'alwaysOnTop', 'typingReaction', 'clickThrough', 'petScale']);
  for (const key of Object.keys(obj)) if (!expected.has(key)) throw new TypeError(`Unknown settings field: ${key}`);
  for (const key of ['edgeSnap', 'alwaysOnTop', 'typingReaction', 'clickThrough'] as const) {
    if (typeof obj[key] !== 'boolean') throw new TypeError(`Invalid settings field: ${key}`);
  }
  if (typeof obj.petScale !== 'number' || !Number.isFinite(obj.petScale) || !PET_SCALES.includes(obj.petScale as typeof PET_SCALES[number])) {
    throw new TypeError('Invalid settings field: petScale');
  }
  return {
    edgeSnap: obj.edgeSnap as boolean,
    alwaysOnTop: obj.alwaysOnTop as boolean,
    typingReaction: obj.typingReaction as boolean,
    clickThrough: obj.clickThrough as boolean,
    petScale: obj.petScale,
  };
}

export function parsePersistedStats(value: unknown): PersistedStats {
  const obj = record(value, 'stats');
  const finite = (key: keyof PersistedStats, min: number, max = Number.MAX_SAFE_INTEGER) => {
    const item = obj[key];
    if (typeof item !== 'number' || !Number.isFinite(item) || item < min || item > max) throw new TypeError(`Invalid stats field: ${key}`);
    return item;
  };
  const lastInteractionDate = obj.lastInteractionDate;
  if (typeof lastInteractionDate !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(lastInteractionDate)) {
    throw new TypeError('Invalid stats field: lastInteractionDate');
  }
  const todayInteractions = finite('todayInteractions', 0);
  if (!Number.isInteger(todayInteractions)) throw new TypeError('Invalid stats field: todayInteractions');
  return {
    affection: finite('affection', 0, 300),
    mood: finite('mood', 0, 100),
    todayInteractions,
    totalCompanionMs: finite('totalCompanionMs', 0),
    lastInteractionDate,
  };
}

export function parseReminders(value: unknown): Reminder[] {
  if (!Array.isArray(value)) throw new TypeError('Invalid reminders');
  return value.map((item) => {
    const obj = record(item, 'reminder');
    if (typeof obj.id !== 'string' || obj.id.length < 1 || obj.id.length > 100) throw new TypeError('Invalid reminder id');
    if (typeof obj.text !== 'string' || obj.text.trim().length < 1 || obj.text.length > 500) throw new TypeError('Invalid reminder text');
    if (typeof obj.dueAt !== 'string' || !Number.isFinite(Date.parse(obj.dueAt))) throw new TypeError('Invalid reminder dueAt');
    if (typeof obj.createdAt !== 'string' || !Number.isFinite(Date.parse(obj.createdAt))) throw new TypeError('Invalid reminder createdAt');
    return { id: obj.id, text: obj.text, dueAt: obj.dueAt, createdAt: obj.createdAt };
  });
}

export function nextReminderDelay(dueAt: string, now = Date.now()): number {
  return Math.min(MAX_TIMER_DELAY_MS, Math.max(0, Date.parse(dueAt) - now));
}

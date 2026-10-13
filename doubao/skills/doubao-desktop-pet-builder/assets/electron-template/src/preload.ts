import { contextBridge, ipcRenderer, webUtils } from 'electron';
import type { InteractionResult, InteractionSpec, PetAPI, PetStats, Reminder, RuntimeFailureReport, RuntimeReadyReport, Settings, StateActivity, TypingStatus } from './shared/contracts';

function subscribe<T>(channel: string, listener: (value: T) => void): () => void {
  const wrapped = (_event: Electron.IpcRendererEvent, value: T) => listener(value);
  ipcRenderer.on(channel, wrapped);
  return () => ipcRenderer.removeListener(channel, wrapped);
}

const api: PetAPI = {
  settings: {
    get: () => ipcRenderer.invoke('settings:get') as Promise<Settings>,
    update: (patch) => ipcRenderer.invoke('settings:update', patch) as Promise<Settings>,
  },
  reminders: {
    list: () => ipcRenderer.invoke('reminders:list') as Promise<Reminder[]>,
    save: (input) => ipcRenderer.invoke('reminders:save', input) as Promise<Reminder>,
    remove: (id) => ipcRenderer.invoke('reminders:remove', id) as Promise<boolean>,
  },
  interactions: {
    list: () => ipcRenderer.invoke('interactions:list') as Promise<InteractionSpec[]>,
    trigger: (id) => ipcRenderer.invoke('interactions:trigger', id) as Promise<InteractionResult>,
    stats: () => ipcRenderer.invoke('interactions:stats') as Promise<PetStats>,
  },
  files: {
    getPathForFile: (file) => webUtils.getPathForFile(file),
    put: (paths) => ipcRenderer.invoke('files:put', paths),
    openPocket: () => ipcRenderer.invoke('files:open-pocket') as Promise<void>,
  },
  window: {
    beginDrag: () => ipcRenderer.invoke('window:drag-begin') as Promise<void>,
    updateDrag: () => ipcRenderer.invoke('window:drag-update') as Promise<void>,
    endDrag: () => ipcRenderer.invoke('window:drag-end') as Promise<void>,
    showContextMenu: () => ipcRenderer.invoke('window:show-context-menu') as Promise<void>,
    showReminder: () => ipcRenderer.invoke('window:show-reminder') as Promise<void>,
    showDashboard: () => ipcRenderer.invoke('window:show-dashboard') as Promise<void>,
    hideReminder: () => ipcRenderer.invoke('window:hide-reminder') as Promise<void>,
    hideDashboard: () => ipcRenderer.invoke('window:hide-dashboard') as Promise<void>,
    hidePet: () => ipcRenderer.invoke('window:hide-pet') as Promise<void>,
  },
  runtime: {
    ready: (report: RuntimeReadyReport) => ipcRenderer.invoke('runtime:ready', report) as Promise<void>,
    fail: (report: RuntimeFailureReport) => ipcRenderer.invoke('runtime:fail', report) as Promise<void>,
  },
  events: {
    onStateActivity: (listener) => subscribe<StateActivity>('state:activity', listener),
    onReminder: (listener) => subscribe<Reminder>('reminder:due', listener),
    onReminderCompose: (listener) => subscribe<void>('reminder:compose', listener),
    onStats: (listener) => subscribe<PetStats>('pet:stats', listener),
    onTypingStatus: (listener) => subscribe<TypingStatus>('typing:status', listener),
  },
};

contextBridge.exposeInMainWorld('petAPI', api);
if (process.env.PET_E2E === '1') {
  contextBridge.exposeInMainWorld('__petE2E', {
    snapshot: () => ipcRenderer.invoke('runtime:e2e-snapshot'),
    quit: () => ipcRenderer.invoke('runtime:e2e-quit'),
  });
}

function currentRole(): 'pet' | 'dashboard' | 'reminder' | undefined {
  const pathname = window.location.pathname;
  if (pathname.includes('/pet_window/')) return 'pet';
  if (pathname.includes('/dashboard_window/')) return 'dashboard';
  if (pathname.includes('/reminder_window/')) return 'reminder';
  return undefined;
}

function reportRendererFailure(message: string): void {
  const role = currentRole();
  if (!role) return;
  void ipcRenderer.invoke('runtime:renderer-failed', { role, message });
}

window.addEventListener('error', (event) => {
  reportRendererFailure(event.error instanceof Error ? event.error.stack || event.error.message : event.message);
});

window.addEventListener('unhandledrejection', (event) => {
  reportRendererFailure(event.reason instanceof Error ? event.reason.stack || event.reason.message : String(event.reason));
});

window.addEventListener('DOMContentLoaded', () => {
  const role = currentRole();
  if (!role) {
    reportRendererFailure(`Cannot resolve renderer role from ${window.location.pathname}`);
    return;
  }
  window.setTimeout(() => {
    void ipcRenderer.invoke('runtime:renderer-ready', { role, bootstrapComplete: true });
  }, 0);
});

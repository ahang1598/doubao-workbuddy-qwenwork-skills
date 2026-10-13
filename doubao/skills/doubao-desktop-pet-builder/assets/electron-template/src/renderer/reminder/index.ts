import spec from '../../../pet-spec.json';
import type { PetSpec, Reminder } from '../../shared/contracts';
import './index.css';

const petSpec = spec as PetSpec;

// 设置主题色
const theme = petSpec.experience.theme;
document.documentElement.style.setProperty('--primary', theme.primary);
document.documentElement.style.setProperty('--accent', theme.accent);
document.documentElement.style.setProperty('--background', theme.background);
document.documentElement.style.setProperty('--surface', theme.surface);
document.documentElement.style.setProperty('--text', theme.text);
document.documentElement.style.setProperty('--muted', theme.muted);
document.documentElement.style.setProperty('--radius', `${theme.cornerRadius}px`);

const textInput = document.getElementById('reminder-text') as HTMLInputElement;
const timeInput = document.getElementById('reminder-time') as HTMLInputElement;
const saveBtn = document.getElementById('save-btn') as HTMLButtonElement;
const cancelBtn = document.getElementById('cancel-btn') as HTMLButtonElement;

// 设置默认时间为1小时后
function setDefaultTime(): void {
  const now = new Date();
  now.setHours(now.getHours() + 1);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  timeInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
}

setDefaultTime();

// 保存提醒
saveBtn.addEventListener('click', async () => {
  const text = textInput.value.trim();
  const time = timeInput.value;

  if (!text || !time) {
    return;
  }

  try {
    await window.petAPI?.reminders.save({
      text,
      dueAt: new Date(time).toISOString(),
    });
    textInput.value = '';
    setDefaultTime();
    await window.petAPI?.window.hideReminder();
  } catch (error) {
    console.error('Failed to save reminder:', error);
  }
});

// 取消
cancelBtn.addEventListener('click', async () => {
  textInput.value = '';
  setDefaultTime();
  await window.petAPI?.window.hideReminder();
});

// 监听提醒触发
window.petAPI?.events.onReminder((reminder: Reminder) => {
  // 显示提醒
  textInput.value = reminder.text;
  timeInput.value = new Date(reminder.dueAt).toLocaleString();
});

// 监听打开提醒编辑器
window.petAPI?.events.onReminderCompose(() => {
  setDefaultTime();
  textInput.focus();
});

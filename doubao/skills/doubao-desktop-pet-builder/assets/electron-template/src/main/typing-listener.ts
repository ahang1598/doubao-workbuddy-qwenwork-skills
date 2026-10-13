import type { TypingStatus } from '../shared/contracts';

export class TypingListener {
  private running = false;
  private callback: (() => void) | undefined;

  start(enabled: boolean, callback: () => void): TypingStatus {
    this.callback = callback;
    if (!enabled) {
      this.running = false;
      return { enabled: false, reason: 'disabled-by-settings' };
    }
    // 简化版：不实际监听键盘，只返回状态
    // 完整实现需要 uiohook-napi 等原生库
    this.running = false;
    return { enabled: false, reason: 'not-available' };
  }

  stop(): void {
    this.running = false;
    this.callback = undefined;
  }
}

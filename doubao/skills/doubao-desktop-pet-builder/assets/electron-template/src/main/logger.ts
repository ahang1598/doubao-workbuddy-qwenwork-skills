import { mkdir } from 'node:fs/promises';
import { appendFile } from 'node:fs/promises';
import path from 'node:path';

export class JsonLogger {
  private filePath: string;
  private initialized = false;

  constructor(filePath: string) {
    this.filePath = filePath;
  }

  private async ensureDir(): Promise<void> {
    if (this.initialized) return;
    await mkdir(path.dirname(this.filePath), { recursive: true });
    this.initialized = true;
  }

  async write(level: string, event: string, data: Record<string, unknown> = {}): Promise<void> {
    try {
      await this.ensureDir();
      const entry = {
        timestamp: new Date().toISOString(),
        level,
        event,
        ...data,
      };
      await appendFile(this.filePath, JSON.stringify(entry) + '\n', 'utf8');
    } catch {
      // 日志写入失败不应该影响主程序
    }
  }
}

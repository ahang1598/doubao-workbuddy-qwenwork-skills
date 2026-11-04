#!/usr/bin/env node
// Node 命令行桥接入口：启动 Lite Python 命令，或通过管道接收并转发 Python 方法请求。
// 只负责进程入口和通信分派，不推导任务结果或统计状态。
import { runLiteCommand } from './commands/lite.mjs';
import { reportRuntimeFailure } from './diagnostics/events.mjs';
import { pending, submit, send, startSpool } from './diagnostics/outbox.mjs';
import { settleWithin } from './utils/common.mjs';
import { readMessages } from './utils/io.mjs';

async function dispatchPython(method, facts = {}, context = {}) {
  switch (method) {
    case 'send':
      return send(facts.events, context, facts.wait);
    case 'submit':
      return submit(facts.event, context);
    case 'outbox_start':
      startSpool(context);
      return true;
    case 'report_runtime_failure':
      return reportRuntimeFailure(facts.detail, context.env || process.env);
    default:
      throw Error('Unknown Python telemetry method');
  }
}

const mode = process.argv[2];
if (mode === '--python') {
  try {
    for await (const request of readMessages(process.stdin, 4 * 1024 * 1024)) {
      // 普通事件写入后无需返回空确认；需要落盘/发送结果的请求仍等待答复。
      const notify = request.method === 'send' && !request.facts?.wait;
      try {
        let timer;
        const value = await Promise.race([
          Promise.resolve().then(() =>
            dispatchPython(request.method, request.facts, request.context),
          ),
          new Promise((_, reject) => {
            timer = setTimeout(() => reject(Error('deadline')), 3000);
          }),
        ]).finally(() => clearTimeout(timer));
        if (notify) continue;
        const response = JSON.stringify({ value: value ?? null });
        process.stdout.write(
          Buffer.byteLength(response) <= 4 * 1024 * 1024 ? response + '\n' : '{"error":true}\n',
        );
      } catch {
        if (notify) continue;
        process.stdout.write('{"error":true}\n');
      }
    }
  } catch {
    /* Broken local transport never replays a business operation. */
  }
  await settleWithin(pending, 3000);
} else {
  const [python, entry, ...args] = process.argv.slice(2);
  await runLiteCommand(python, entry, args).catch(() => {
    process.exitCode = 1;
  });
}

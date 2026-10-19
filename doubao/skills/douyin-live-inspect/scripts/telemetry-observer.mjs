#!/usr/bin/env node
import {parseArgs} from 'node:util';
import {startObserver, stopObserver} from '../runtime/telemetry-observer.cjs';

try {
  const {values} = parseArgs({options: {port: {type: 'string'}, stop: {type: 'boolean'}, help: {type: 'boolean', short: 'h'}}});
  if (values.help) {
    console.log('用法：node scripts/telemetry-observer.mjs [--port 端口] | --stop\n打开输出的本机网页查看新埋点，Ctrl+C 或 --stop 关闭。默认不保存历史记录。');
  } else if (values.stop) {
    if (values.port !== undefined) throw new Error('--stop 不接受 --port；请使用启动时相同的配置目录');
    console.log(await stopObserver() ? '埋点观察服务已关闭。' : '当前配置目录没有运行中的埋点观察服务。');
  } else {
    const observer = await startObserver({port: values.port === undefined ? 0 : Number(values.port)});
    console.log(`埋点观察服务已开启：${observer.url}\n与 Skill 使用同一本机用户及配置目录；Ctrl+C 或另一个终端执行 node scripts/telemetry-observer.mjs --stop 关闭。\n已捕获表示进入 SDK 发送通道，不代表线上平台入库成功。`);
    const stop = () => observer.stop().catch(() => { process.exitCode = 1; });
    for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.once(signal, stop);
  }
} catch (error) {
  console.error(`埋点观察服务操作失败：${error.code || error.message}`);
  process.exitCode = 1;
}

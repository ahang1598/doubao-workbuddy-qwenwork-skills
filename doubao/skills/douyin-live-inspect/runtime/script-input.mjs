// 读取脚本的完整管道输入；容量由调用方指定，解析及业务校验留在原命令。
// 先拼接字节再解码，避免中文字符跨块时损坏；首行协议不使用此函数。
export async function readStdin(limit, overflowError) {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    const bytes = Buffer.from(chunk);
    size += bytes.length;
    if (size > limit) throw overflowError;
    chunks.push(bytes);
  }
  return Buffer.concat(chunks);
}

// 创建任务和准备复盘只读首行，不等宿主关闭 stdin；两者沿用相同的对象协议。
export async function readJsonLine(limit) {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    const bytes = Buffer.from(chunk);
    size += bytes.length;
    if (size > limit)
      throw Object.assign(new Error('stdin input is too large'), { code: 'INVALID_INPUT' });
    chunks.push(bytes);
    if (bytes.includes(10)) break;
  }
  try {
    const value = JSON.parse(Buffer.concat(chunks).toString('utf8').split(/\r?\n/, 1)[0]);
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
    return value;
  } catch {
    throw Object.assign(new Error('stdin must contain one JSON object'), { code: 'INVALID_INPUT' });
  }
}

// ==================== claw_pipe_http.js - HTTP/1.1 over Windows 命名管道客户端 ====================
// 功能：桌面（管道）形态下，skill 的云端接口调用经主进程 SkillApiProxy（\\.\pipe\claw-skill）转发。
//       业务鉴权由主进程注入，skill 侧零业务凭证，仅携带 CLAW_SKILL_TOKEN 本机防借用令牌。
// 说明：Node 标准库不直接支持 Windows 命名管道，这里用 fs（CreateFile 按字节流读写）实现，
//       仅实现本 skill 所需的最小子集（每请求一连接 + 显式 Content-Length + Connection: close）。
import fs from 'fs';

// 默认管道（主进程 SkillApiProxy）
const DEFAULT_PIPE_PATH = '\\\\.\\pipe\\claw-skill';

// ERROR_PIPE_BUSY = 231：服务端管道实例暂时占满，等位重试
const ERROR_PIPE_BUSY = 231;
const CONNECT_TIMEOUT_MS = 10000;
const HEAD_MAX_BYTES = 64 * 1024;
const CRLF = Buffer.from('\r\n', 'ascii');
const HEADER_END = Buffer.from('\r\n\r\n', 'ascii');

/**
 * 同步短暂自旋等待（Windows 同步管道连接重试用）
 * @param {number} ms
 */
function busyWait(ms) {
    const at = Date.now() + ms;
    while (Date.now() < at) { /* spin */ }
}

/**
 * np://claw-skill → \\\\.\\pipe\\claw-skill（authority 段即管道名）
 * @param {string} url
 * @returns {string}
 */
export function pipePathFromUrl(url) {
    const rest = url.replace(/^np:\/\//, '');
    const name = rest.split('/')[0].trim();
    if (!name) throw new Error(`np:// URL 缺少管道名: ${url}`);
    return '\\\\.\\pipe\\' + name;
}

/**
 * 连接命名管道（CreateFile 语义，ERROR_PIPE_BUSY / 管道暂不可用时等位重试）。返回 fd。
 * @param {string} pipePath
 * @returns {number}
 */
function connectPipe(pipePath) {
    const deadline = Date.now() + CONNECT_TIMEOUT_MS;
    for (;;) {
        try {
            // 'r+' = 读+写（GENERIC_READ | GENERIC_WRITE）
            return fs.openSync(pipePath, 'r+');
        } catch (err) {
            const busy = err && (err.errno === -ERROR_PIPE_BUSY ||
                err.code === 'EPIPE' || err.code === 'EAGAIN' || err.code === 'ENOENT');
            if (busy && Date.now() < deadline) {
                busyWait(50);
                continue;
            }
            throw new Error(`连接命名管道失败 ${pipePath}: ${err.message}`);
        }
    }
}

/**
 * 写入全部字节
 * @param {number} fd
 * @param {Buffer} data
 */
function writeAllSync(fd, data) {
    let offset = 0;
    while (offset < data.length) {
        offset += fs.writeSync(fd, data, offset, data.length - offset);
    }
}

/**
 * 读取响应头（至 \r\n\r\n），返回 {head, rest}
 * @param {number} fd
 * @returns {{head: Buffer, rest: Buffer}}
 */
function readHead(fd) {
    const chunks = [];
    let total = 0;
    for (;;) {
        const buf = Buffer.alloc(65536);
        const n = fs.readSync(fd, buf, 0, buf.length, null);
        if (n === 0) throw new Error('读取响应头时连接被关闭');
        const chunk = Buffer.from(buf.slice(0, n));
        chunks.push(chunk);
        total += n;
        if (total > HEAD_MAX_BYTES) throw new Error('响应头超限（>64KiB）');
        const joined = Buffer.concat(chunks);
        const headEnd = joined.indexOf('\r\n\r\n');
        if (headEnd >= 0) {
            return {head: joined.slice(0, headEnd), rest: joined.slice(headEnd + 4)};
        }
        if (joined.length === 0) throw new Error('响应头为空');
    }
}

/**
 * 解析响应头 => {status, headers}
 * @param {Buffer} head
 * @returns {{status: number, headers: object}}
 */
function parseHead(head) {
    const lines = head.toString('latin1').split('\r\n');
    const first = lines[0].split(' ');
    const status = parseInt(first[1], 10);
    if (isNaN(status)) throw new Error(`非法响应行: ${lines[0]}`);
    const headers = {};
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i];
        if (!line || line.indexOf(':') === -1) continue;
        const idx = line.indexOf(':');
        headers[line.slice(0, idx).trim().toLowerCase()] = line.slice(idx + 1).trim();
    }
    return {status, headers};
}

/**
 * 读取到 EOF（请求固定携带 Connection: close）。
 * @param {number} fd
 * @param {Buffer} prefix 已经随响应头一起读到的 body 前缀
 * @returns {Buffer}
 */
function readToEof(fd, prefix) {
    const chunks = [prefix];
    for (;;) {
        const buf = Buffer.alloc(65536);
        const n = fs.readSync(fd, buf, 0, buf.length, null);
        if (n === 0) break;
        chunks.push(Buffer.from(buf.slice(0, n)));
    }
    return Buffer.concat(chunks);
}

/**
 * 解码 HTTP/1.1 chunked body。
 *
 * chunk size 是字节数，必须始终使用 Buffer 切片；若先转成 UTF-8 字符串，中文等
 * 多字节内容会导致边界错位。支持 chunk extension 与结束块后的 trailer。
 *
 * @param {Buffer} encodedBody 带 chunk framing 的原始响应体
 * @returns {Buffer} 去除 framing 后的实际响应体
 */
export function decodeChunkedBody(encodedBody) {
    if (!Buffer.isBuffer(encodedBody)) {
        throw new TypeError('chunked 响应体必须是 Buffer');
    }

    const chunks = [];
    let total = 0;
    let offset = 0;

    for (;;) {
        const lineEnd = encodedBody.indexOf(CRLF, offset);
        if (lineEnd < 0) throw new Error('chunked 响应不完整：缺少 chunk size 行结束符');

        const sizeLine = encodedBody.subarray(offset, lineEnd).toString('ascii');
        const sizeToken = sizeLine.split(';', 1)[0].trim();
        if (!/^[0-9a-fA-F]+$/.test(sizeToken)) {
            throw new Error(`chunked 响应格式错误：非法 chunk size "${sizeLine}"`);
        }

        const size = Number.parseInt(sizeToken, 16);
        if (!Number.isSafeInteger(size)) {
            throw new Error(`chunked 响应格式错误：chunk size 超出安全范围 "${sizeLine}"`);
        }
        offset = lineEnd + CRLF.length;

        if (size === 0) {
            // 无 trailer：0\r\n\r\n；有 trailer：0\r\nKey: value\r\n\r\n。
            if (offset + CRLF.length > encodedBody.length) {
                throw new Error('chunked 响应不完整：结束块缺少终止空行');
            }
            if (encodedBody.subarray(offset, offset + CRLF.length).equals(CRLF)) {
                offset += CRLF.length;
            } else {
                const trailerEnd = encodedBody.indexOf(HEADER_END, offset);
                if (trailerEnd < 0) throw new Error('chunked 响应不完整：trailer 未结束');
                offset = trailerEnd + HEADER_END.length;
            }
            if (offset !== encodedBody.length) {
                throw new Error('chunked 响应格式错误：结束块后存在多余数据');
            }
            return Buffer.concat(chunks, total);
        }

        const dataEnd = offset + size;
        if (dataEnd + CRLF.length > encodedBody.length) {
            throw new Error('chunked 响应不完整：chunk 数据长度不足');
        }
        if (!encodedBody.subarray(dataEnd, dataEnd + CRLF.length).equals(CRLF)) {
            throw new Error('chunked 响应格式错误：chunk 数据后缺少 CRLF');
        }

        chunks.push(encodedBody.subarray(offset, dataEnd));
        total += size;
        offset = dataEnd + CRLF.length;
    }
}

/**
 * 读取响应体剩余部分（Transfer-Encoding: chunked 优先，其次 Content-Length，
 * 最后读至 EOF / Connection: close）。
 * @param {number} fd
 * @param {object} headers 解析后的响应头
 * @param {Buffer} rest 头之后已读出的 body 前缀
 * @returns {Buffer}
 */
function readBody(fd, headers, rest) {
    const transferEncoding = String(headers['transfer-encoding'] || '').toLowerCase();
    if (transferEncoding.split(',').some(value => value.trim() === 'chunked')) {
        return decodeChunkedBody(readToEof(fd, rest));
    }

    const bodyChunks = [rest];
    let received = rest.length;
    const contentLength = headers['content-length'];
    if (contentLength && /^\d+$/.test(contentLength)) {
        const target = parseInt(contentLength, 10);
        while (received < target) {
            const buf = Buffer.alloc(65536);
            const n = fs.readSync(fd, buf, 0, buf.length, null);
            if (n === 0) break;
            bodyChunks.push(Buffer.from(buf.slice(0, n)));
            received += n;
        }
        const body = Buffer.concat(bodyChunks);
        if (body.length < target) {
            throw new Error(`响应体不完整：期望 ${target} 字节，实际 ${body.length} 字节`);
        }
        return body.subarray(0, target);
    }
    return readToEof(fd, rest);
}

/**
 * 发送一个 HTTP/1.1 请求并经命名管道收回完整响应（非流式，读至 EOF 或 Content-Length）。
 * @param {string} method
 * @param {string} requestPath
 * @param {object} [opts]
 * @param {Buffer|string} [opts.body]
 * @param {object} [opts.headers]
 * @param {string} [opts.pipePath]
 * @param {string} [opts.token]
 * @returns {{status: number, headers: object, text: string, json: () => object}}
 */
export function pipeRequest(method, requestPath, opts = {}) {
    const {
        body = '',
        headers = {},
        pipePath = DEFAULT_PIPE_PATH,
        token = ''
    } = opts;

    let p = requestPath;
    if (!p.startsWith('/')) p = '/' + p;
    const bodyBuf = typeof body === 'string' ? Buffer.from(body, 'utf-8') : body;

    const hdrs = {
        'Host': 'claw-skill',
        'Connection': 'close',
        'Content-Length': String(bodyBuf.length)
    };
    if (token) hdrs['Authorization'] = `Bearer ${token}`;
    for (const [k, v] of Object.entries(headers)) hdrs[k] = v;

    const headLines = [
        `${method} ${p} HTTP/1.1`,
        ...Object.entries(hdrs).map(([k, v]) => `${k}: ${v}`),
        '',
        ''
    ].join('\r\n');

    const requestBytes = Buffer.concat([Buffer.from(headLines, 'ascii'), bodyBuf]);

    const fd = connectPipe(pipePath);
    try {
        writeAllSync(fd, requestBytes);
        const {head, rest} = readHead(fd);
        const {status, headers: respHeaders} = parseHead(head);
        const bodyBuffer = readBody(fd, respHeaders, rest);
        const text = bodyBuffer.toString('utf-8');
        return {
            status,
            headers: respHeaders,
            text,
            json() {
                return JSON.parse(text);
            }
        };
    } finally {
        try { fs.closeSync(fd); } catch (_) { /* ignore */ }
    }
}

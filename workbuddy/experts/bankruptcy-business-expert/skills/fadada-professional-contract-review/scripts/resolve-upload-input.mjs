/**
 * 将显式上传参数解析为本地文件路径。
 *
 * 会话附件必须按 attachment ID 精确匹配 RICHEEAI_ATTACHMENTS；
 * 不允许在缺少选择器时默认使用第一个附件。
 */
export function resolveUploadFilePath(args) {
  const [selector, value] = args;

  if (selector === '--attachment-id') {
    if (!value) {
      throw new Error('--attachment-id 后必须提供附件 ID');
    }
    const attachments = parseAttachments();
    const attachment = attachments.find(item => item?.id === value);
    if (!attachment || typeof attachment.path !== 'string' || !attachment.path) {
      const available = attachments
        .map(item => `${item?.id || '(无ID)'}:${item?.name || '(未命名)'}`)
        .join(', ');
      throw new Error(`未找到附件 ID: ${value}。可用附件: ${available || '(无)'}`);
    }
    return attachment.path;
  }

  if (selector === '--file-path') {
    if (!value) {
      throw new Error('--file-path 后必须提供文件路径');
    }
    return value;
  }

  // 保留原有显式位置参数用法，兼容用户直接提供的本地路径。
  if (selector && !selector.startsWith('--')) {
    return selector;
  }

  throw new Error('必须使用 --attachment-id <附件ID> 或 --file-path <文件路径> 明确指定文件');
}

function parseAttachments() {
  const raw = process.env.RICHEEAI_ATTACHMENTS;
  if (!raw) return [];
  try {
    const attachments = JSON.parse(raw);
    return Array.isArray(attachments) ? attachments : [];
  } catch {
    throw new Error('RICHEEAI_ATTACHMENTS 格式无效');
  }
}

// 本文件负责“新建检测请求”的入口分流：
// 校验请求是否合法、探测账号状态、判断正式版能力，并返回给宿主用于展示的版本选择或下一步动作。
import { existsSync } from 'node:fs';
import { detectAccountEntryAsync } from './account-entry.mjs';
import { checkInspectionService, entryTimeout } from './inspection-service.mjs';
import { createProbeSession } from './probe-session.mjs';

const choice = (id, label, description) => ({ id, label, description });
const formal = choice('formal', '使用正式版（推荐）', '登录火山引擎后，按已配置的业务场景使用更丰富的检测规则，支持视频附件与网络视频链接，任务和报告在云端集中管理；需开通质检服务并配置项目与场景。');
const lite = choice('lite', '使用 Lite（本地版）', '无需火山登录，使用内置电商、金融、汽车精简规则，支持直播与本地视频检测，通过本地报告或对话查看结果。');
// 根据当前探测结果向宿主声明需要呈现的用户选择卡片。
const interactions = {
  choose_formal_or_lite_initial: {
    title: '选择质检版本',
    message: '请选择版本：① 正式版（推荐）——登录火山引擎，使用按业务配置的丰富规则并云端管理任务和报告；② Lite 本地版——免登录，使用内置精简规则并通过本地报告或对话查看结果。两个版本均支持直播质检、多视频检测、质检报告和直播内容复盘。',
    options: [formal,
      choice('lite', '免登录使用 Lite（本地版）', lite.description)],
  },
  choose_lite_or_login: {
    title: '选择质检执行方式', message: '火山引擎认证当前不可用，本次使用哪种方式？',
    options: [lite, choice('login', '继续登录火山引擎', '授权完成后回到当前对话回复“已授权”，继续正式版质检。')],
  },
  choose_formal_or_lite: {
    title: '选择质检版本', message: '暂时无法确认正式版是否可用，本次尚未创建检测任务。请选择正式版（推荐）或 Lite 本地版。',
    options: [{ ...formal, id: 'inspect_formal' }, lite],
  },
};

// 统一构造不可继续执行的结果，避免各校验分支返回不一致的数据结构。
const blocked = (reason, stage = 'validation') => ({ ok: false, command: 'inspect-entry', data: {
  route: 'blocked', reason, next_action: 'resolve_blocker', activation_guidance_required: false,
  diagnostics: { stage, category: reason, attempts: 0 },
} });

export async function inspectEntry(input = {}, { env = process.env, budgetMs = 10_000, root = new URL('../', import.meta.url) } = {}) {
  const session = createProbeSession({ budgetMs });
  let result;
  try {
    // 仅接受尚未创建任务的线上直播或视频检测请求。
    if (!['live', 'video'].includes(input.kind) || input.environment !== 'online' || input.task_state !== 'not_created'
        || (input.profile !== undefined && (typeof input.profile !== 'string' || !input.profile.trim()))
        || (input.allow_lite !== undefined && typeof input.allow_lite !== 'boolean')) {
      result = blocked('invalid_new_request_context');
    } else if (!['scripts/detect-account-entry.mjs', 'scripts/check-inspection-service.mjs',
      'runtime/account-entry.mjs', 'runtime/inspection-service.mjs', 'runtime/probe-session.mjs', 'SKILL.md']
      .every(path => existsSync(new URL(path, root)))) {
      // 入口依赖缺失时禁止继续，避免后续探测产生误导性结果。
      result = blocked('skill_installation_incomplete', 'installation');
    } else {
      // 先检测本地账号态：已登录时才继续确认正式版服务能力。
      const account = await detectAccountEntryAsync({ env, session, profile:input.profile });
      if (account.state === 'profile_present') {
        // 已确认存在可用账号后，再进一步判断正式版服务是否开通、项目是否可用。
        result = await checkInspectionService(input, { env, session });
      } else if (account.state === 'unknown' && account.reason === 'profile_check_timeout') {
        // 账号探测耗尽时间预算时，返回可重试的统一超时结果。
        result = entryTimeout(input, 'account');
      } else {
        // 未登录或账号态未知时，交由宿主引导用户选择正式版登录或 Lite 本地版。
        const unavailable = input.allow_lite === false;
        result = { ok: !unavailable, data: {
          // route 只描述当前分流结论；真正进入哪个子流程由宿主根据 next_action 继续推进。
          route: unavailable ? 'blocked' : account.state === 'unknown' ? 'clarify' : 'select',
          reason: account.reason, next_action: unavailable ? 'resolve_blocker' : 'choose_formal_or_lite_initial',
          activation_guidance_required: false,
          diagnostics: { stage: 'account', category: account.state, attempts: 0 },
        } };
      }
    }
  } catch {
    // 区分整体会话超时和其他入口异常，便于调用方决定重试或排障。
    result = session.expired ? entryTimeout(input, session.stage) : blocked('entry_check_failed', session.stage);
  } finally {
    await session.close();
  }
  result.command = 'inspect-entry';
  result.data.timings = session.timings();
  const interaction = interactions[result.data.next_action];
  if (interaction && result.data.route !== 'blocked') {
    // 卡片不可用时仍可使用同一份选项数据生成文本兜底，保证排序与文案一致。
    result.data.requires_user_input = true;
    result.data.interaction = structuredClone(interaction);
    // 卡片标签与最终聊天回复共用同一有序数据源。
    // 这是交付约定；只有宿主能够确认是否实际收到用户回答。
    result.data.interaction.fallback_text = [
      interaction.message,
      ...interaction.options.map((option, index) => `${index + 1}. **${option.label}**：${option.description}`),
      '请直接回复 1 / 2，或点击卡片中的对应选项（如已显示）。',
    ].join('\n\n');
  }
  return result;
}

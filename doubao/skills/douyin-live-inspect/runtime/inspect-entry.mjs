// 本文件负责“新建检测请求”的入口分流：
// 先展示版本选择；仅显式选择正式版后探测服务能力。
import { existsSync } from 'node:fs';
import { checkInspectionService, entryTimeout } from './inspection-service.mjs';
import { createProbeSession } from './probe-session.mjs';
import workflow from '../telemetry/workflow/state.mjs';

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
        || (input.mode !== undefined && !['lite','formal'].includes(input.mode))
        || (input.mode === 'lite' && input.allow_lite === false)
        || (input.allow_lite !== undefined && typeof input.allow_lite !== 'boolean')) {
      result = blocked('invalid_new_request_context');
    } else if (!['scripts/detect-account-entry.mjs', 'scripts/check-inspection-service.mjs',
      'runtime/account-entry.mjs', 'runtime/inspection-service.mjs', 'runtime/probe-session.mjs', 'SKILL.md']
      .every(path => existsSync(new URL(path, root)))) {
      // 入口依赖缺失时禁止继续，避免后续探测产生误导性结果。
      result = blocked('skill_installation_incomplete', 'installation');
    } else {
      if (input.mode === 'formal') {
        result = await checkInspectionService(input, { env, session,
          onAccount: accountId => workflow.account(accountId, { env }),
        });
      } else if (input.mode === 'lite') {
        result = {ok:true, data:{route:'lite', reason:'explicit_version_selection', next_action:'start_lite'}};
      } else {
        // 账号存在不代表用户选择了正式版；选择前不读取账号或调用正式服务。
        result = {ok:true, data:{route:'select', reason:'version_selection_required',
          next_action:'choose_formal_or_lite_initial', activation_guidance_required:false,
          diagnostics:{stage:'version_selection', category:'selection_required', attempts:0}}};
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
    if (input.allow_lite === false) {
      result.data.interaction.options = [structuredClone(formal)];
      result.data.interaction.message = '本次请求不允许使用 Lite，请确认使用正式版后继续。';
    }
    // 卡片标签与最终聊天回复共用同一有序数据源。
    // 这是交付约定；只有宿主能够确认是否实际收到用户回答。
    result.data.interaction.fallback_text = [
      result.data.interaction.message,
      ...result.data.interaction.options.map((option, index) => `${index + 1}. **${option.label}**：${option.description}`),
      '请回复对应选项，或点击卡片中的选项（如已显示）。',
    ].join('\n\n');
  }
  return result;
}

"""Safe validation feedback shared by single and batch review submissions."""

ERRORS = {
    'review context superseded': ('REVIEW_SUPERSEDED', '原合同已被接管；查询原 context 的恢复回执，不重交或续领。', 'review-state'),
    'segment skipped': ('SEGMENT_SKIPPED', '该段已跳过判别，请 review-next 继续下一段，不补交规则结果。', 'review-next'),
    'missing ASR cannot clear speech rule': ('ASR_EVIDENCE_MISSING', '缺少语音证据，不能提交 no_hit；请读取最新片段及恢复状态。', 'review-next'),
    'video recap not supported': ('VIDEO_RECAP_NOT_SUPPORTED', '视频仅提供质检报告。', 'report'),
    'recap evidence changed': ('RECAP_EVIDENCE_CHANGED', '证据已更新，请重新 recap-input --begin 后提交。', 'recap-input --begin'),
    'recap already saved for evidence version': ('RECAP_ALREADY_SAVED', '同版本复盘已保存，请读取 recap-report。', 'recap-report'),
    'evidence changed; read segment again': ('EVIDENCE_CHANGED', '重新读取片段，依据最新证据提交 evidence_revision。', 'review-next'),
    'missing or unseen frames cannot clear image rule': ('FRAMES_NOT_REVIEWED', '查看本段全部可用图片并提交 images_viewed；证据不足时使用 insufficient。', 'review-next'),
    'each frozen rule requires one decision': ('RULES_INCOMPLETE', '按当前任务规则逐条提交一次判定，不替换为其他任务或新版规则。', 'review-next'),
    'segment already reviewed': ('ALREADY_REVIEWED', '本段已完成，继续读取下一段。', 'review-next'),
    'segment evidence not ready': ('EVIDENCE_NOT_READY', '本段媒体仍在处理，稍后读取。', 'status'),
}


def upstream_review_error(error, *, fallback=False, protocol_v2=False):
    mapped=FIELDS.get(str(error)) if protocol_v2 or isinstance(error,ReviewValidationError) else None
    if mapped:
        code,field,message=mapped
        return {'code':code,'message':message,'next_action':'review-submit',
                'segment_id':getattr(error,'segment_id',None),'rule_id':getattr(error,'rule_id',None),
                'field':getattr(error,'field',None) or field,
                **({'allowed_evidence_ids':error.allowed_evidence_ids} if hasattr(error,'allowed_evidence_ids') else {})}
    detail = ERRORS.get(str(error)) if isinstance(error, ValueError) else None
    if detail is None:
        if not fallback: return None
        detail = ('INVALID_REVIEW', '判定格式无效，请按本次片段和冻结规则修正，仅重试失败项。', 'review-next')
    code, message, action = detail
    return {'code': code, 'message': message, 'next_action': action}


FIELDS = {
    'explicit review confirmation required': ('REVIEW_CONFIRMATION_REQUIRED','reviewed','完成本段判断后填写 reviewed=true 和简短 summary。'),
    'batch requires 1..5 segments': ('BATCH_FORMAT_INVALID','segments','segments 须为含1至5项的数组；只重交失败项。'),
    'batch requires 1..20 segments': ('BATCH_FORMAT_INVALID','segments','segments 须为含1至20项的数组；只重交失败项。'),
    'image description required': ('IMAGE_DESCRIPTION_REQUIRED','events.description','补充实际所见图片的具体说明。'),
    'invalid viewed image IDs': ('VIEWED_IMAGES_INVALID','images_viewed','仅填本批返回并实际查看的图片ID。'),
    'each frozen rule requires one decision': ('RULES_INCOMPLETE','rules','按本次模板逐条填写全部冻结规则。'),
    'stale or missing review batch': ('BATCH_BINDING_INVALID', 'context_id', '沿用本次领取的 context_id；过期时重新领取，不猜测代次。'),
    'stale or missing review context': ('CONTEXT_INVALID', 'context_id', '使用本次任务返回的提交模板。'),
    'foreign context segment': ('CONTEXT_SEGMENT_INVALID', 'segment_id', '只提交本批绑定的片段。'),
    'review batch cancellation or dispatch pending': ('BATCH_NOT_SUBMITTABLE', 'context_id', '先核对宿主派发或取消状态。'),
    'host task binding required': ('HOST_BINDING_REQUIRED', 'context_id', '登记实际宿主任务 ID 后提交。'),
    'each rule channel requires a decision': ('CHANNELS_INCOMPLETE', 'channels', '按模板填写本规则的所有渠道。'),
    'invalid channel decision': ('CHANNEL_DECISION_INVALID', 'channels', '渠道须包含合法 status 和具体 reason。'),
    'disabled image channel must be not_checked': ('IMAGE_SCOPE_MISMATCH', 'channels.image', '本任务已关闭画面检测，image 渠道须保留 not_checked；规则顶层仅按字幕判定。'),
    'speech-only conclusion must be a speech judgment': ('SPEECH_SCOPE_MISMATCH', 'channels.speech', '仅字幕任务的 speech 渠道须填 hit、no_hit 或 insufficient。'),
    'missing speech evidence requires insufficient': ('ASR_EVIDENCE_MISSING', 'status', '已取得字幕中的真实命中可填 hit；其余规则在证据不足时填 insufficient，不可用 no_hit 清除。'),
    'speech-only conclusion must match speech channel': ('CONCLUSION_CONFLICT', 'status', '仅字幕任务的规则顶层结论须与 speech 渠道一致；纯画面规则为不适用。'),
    'unseen image channel cannot be cleared': ('IMAGE_EVIDENCE_MISSING', 'channels.image', '查看本段可用图片；无图时不可提交 no_hit，依赖画面的条件用 insufficient。'),
    'missing speech channel cannot be cleared': ('SPEECH_EVIDENCE_MISSING', 'channels.speech', '语音缺口不得用 no_hit 清除；依赖缺失部分用 insufficient。'),
    'channel hit requires matching evidence': ('CHANNEL_EVIDENCE_MISMATCH', 'events', '命中引用对应渠道的本段证据。'),
    'hit requires a hit channel': ('CONCLUSION_CONFLICT', 'status', '最终命中必须有对应命中渠道。'),
    'channel result contradicts conclusion': ('CONCLUSION_CONFLICT', 'status', '保留模型语义判断，但不能用 no_hit 覆盖命中或证据不足渠道。'),
    'invalid semantic decision': ('DECISION_INVALID', 'status', '填写合法结论和具体依据。'),
    'hits require evidence events only': ('EVENTS_INVALID', 'events', '命中须有证据事件；非命中事件为空。'),
    'foreign evidence': ('EVIDENCE_BINDING_INVALID', 'events', '每个事件用 evidence_ids 数组，仅引用 allowed_evidence_ids；不要使用单数 evidence_id。'),
    'missing ASR cannot clear speech rule': ('ASR_EVIDENCE_MISSING', 'status', '本段 speech.can_clear=false；请一次修复本段所有含 speech 且为 no_hit 的规则。有真实命中证据可保留 hit，其余填 insufficient，不逐条重交。'),
    'missing or unseen frames cannot clear image rule': ('FRAMES_NOT_REVIEWED', 'status', '无图或未看图不能清除视觉风险；依赖缺图的条件用 insufficient。'),
}

class ReviewValidationError(ValueError):
    def __init__(self, message, segment_id=None, rule_id=None, field=None):
        super().__init__(message)
        self.segment_id=segment_id;self.rule_id=rule_id;self.field=field

def contextual(error,segment_id,rule_id,index):
    name=str(error)
    field=FIELDS.get(name, ('','decision',''))[1]
    return ReviewValidationError(name,segment_id,rule_id,f'rules[{index}].{field}')

"""Allowlisted review diagnostics: no submitted prose or transport data escapes."""

LEGACY_ERRORS = {
    'task binding mismatch': ('TASK_BINDING_MISMATCH', 'task_id', '使用原任务编号。', 'review-next'),
    'unknown segment': ('SEGMENT_UNKNOWN', 'segment_id', '重新读取原任务片段。', 'review-next'),
    'evidence changed; read segment again': ('EVIDENCE_CHANGED', 'evidence_revision', '重新读取最新证据版本。', 'review-next'),
    'segment already reviewed': ('ALREADY_REVIEWED', 'segment_id', '本段已完成，继续下一段。', 'review-next'),
    'confirm scene before review': ('SCENE_REQUIRED', 'scenario', '先确认场景。', 'scene-confirm'),
    'segment evidence not ready': ('EVIDENCE_NOT_READY', 'segment_id', '媒体仍在处理，稍后读取。', 'status'),
    'each frozen rule requires one decision': ('RULES_INCOMPLETE', 'rules', '每条冻结规则必须有且只有一次判定。', 'repair-review-input'),
    'invalid viewed image IDs': ('IMAGE_IDS_INVALID', 'images_viewed', '使用本段真实图片编号。', 'repair-review-input'),
    'invalid semantic decision': ('SEMANTIC_DECISION_INVALID', 'status', '使用合法判定状态并填写判断依据。', 'repair-review-input'),
    'missing ASR cannot clear speech rule': ('ASR_EVIDENCE_MISSING', 'status', '缺少语音证据，请使用 insufficient。', 'repair-review-input'),
    'missing or unseen frames cannot clear image rule': ('FRAMES_NOT_REVIEWED', 'status', '查看全部可用图片；证据不足时使用 insufficient。', 'repair-review-input'),
    'hits require evidence events only': ('HIT_EVENTS_INVALID', 'events', '命中必须有证据事件；非命中不得携带事件。', 'repair-review-input'),
    'invalid evidence event': ('EVIDENCE_EVENT_INVALID', 'events', '证据事件必须是对象。', 'repair-review-input'),
    'foreign evidence': ('EVIDENCE_IDS_INVALID', 'evidence_ids', '引用本段真实证据编号。', 'repair-review-input'),
    'duplicate evidence IDs': ('EVIDENCE_IDS_DUPLICATED', 'evidence_ids', '同一事件不得重复引用相同证据。', 'repair-review-input'),
    'evidence channel not allowed by rule': ('EVIDENCE_CHANNEL_INVALID', 'evidence_ids', '使用规则允许的证据类型。', 'repair-review-input'),
    'image must be viewed before judgment': ('IMAGE_NOT_VIEWED', 'evidence_ids', '查看引用图片后再提交。', 'repair-review-input'),
    'image description required': ('IMAGE_DESCRIPTION_REQUIRED', 'description', '填写图片证据描述。', 'repair-review-input'),
    'evidence outside segment': ('EVIDENCE_RANGE_INVALID', 'evidence_ids', '重新读取本段证据时间范围。', 'review-next'),
}


class ReviewError(ValueError):
    def __init__(self, code, field, message, segment_id=None, *, retryable=True, next_action='repair-review-input'):
        super().__init__(message)
        self.detail = dict(code=code, field=field, message=message,
                           segment_id=segment_id if type(segment_id) is int else None,
                           retryable=retryable, next_action=next_action)


def legacy_review_error(reason, segment_id=None, rule_index=None, event_index=None):
    code, field, message, action = LEGACY_ERRORS[reason]
    if rule_index is not None and field in {'status','events','evidence_ids','description'}:
        field = f'rules[{rule_index}].' + (f'events[{event_index}].' if event_index is not None and field != 'events' else '') + field
    error = ReviewError(code, field, message, segment_id, next_action=action)
    # Preserve legacy ValueError matching for callers; the CLI uses only detail.
    error.args = (reason,)
    return error


def review_error(error, segment_id=None, rule_index=None, event_index=None, *, fallback=False, protocol_v2=False):
    if isinstance(error, str):
        return legacy_review_error(error, segment_id, rule_index, event_index)
    if isinstance(error, ReviewError):return error.detail
    return upstream_review_error(error, fallback=fallback, protocol_v2=protocol_v2)


RULE_LOAD_ERRORS = {
    'rule request must be an object': ('RULE_INPUT_INVALID','input','提交规则追加 JSON 对象。','rules-load'),
    'unsupported rule bundle': ('RULE_BUNDLE_INVALID','bundle','仅支持 finance 或 ecommerce。','rules-load'),
    'task binding mismatch': ('TASK_BINDING_MISMATCH','task_id','使用领取合同的原任务 ID。','review-next'),
    'task uses a fixed rule snapshot': ('RULE_SNAPSHOT_FIXED','bundle','任务规则固定，继续原合同；不得声称已追加专项。','review-next'),
    'no pending evidence': ('RULE_EVIDENCE_UNAVAILABLE','segment_id','重新领取未完成片段，引用其证据。','review-next'),
    'stale rule evidence': ('RULE_EVIDENCE_CHANGED','evidence_revision','重新领取最新证据版本。','review-next'),
    'invalid rule evidence': ('RULE_EVIDENCE_INVALID','evidence_ids','只引用本段实际字幕或图片 ID，images_viewed 仅填实际已看图片。','rules-load'),
    'rule image evidence not viewed': ('RULE_IMAGE_NOT_VIEWED','images_viewed','查看引用的图片或改用足够的实际字幕证据。','rules-load'),
    'rule reason required': ('RULE_REASON_REQUIRED','reason','填写证据支持的行业适用理由。','rules-load'),
}

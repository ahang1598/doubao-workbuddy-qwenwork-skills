"""Safe validation feedback shared by single and batch review submissions."""

ERRORS = {
    'specialist rules must be loaded before judgment': ('RULES_INCOMPLETE','先按 content_route 的业务对象调用 rules-load，再使用新合同提交；加载失败须保留专项缺口。','rules-load'),
    'content route required': ('DECISION_INVALID','每段填写 content_route 的 type、reason 和 evidence_ids；无法确定专项时填 undetermined。','review-submit'),
    'content route requires actual evidence': ('EVIDENCE_BINDING_INVALID','content_route 须引用本段真实依据；无任何证据时只能填 undetermined。','review-submit'),
    'review batch timed out': ('LIVE_BATCH_REVIEW_TIMEOUT', '本批次已超时，保留已保存结果及未完成片段，重新领取待判定内容。', 'review-next'),
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
                **{key:getattr(error,key) for key in ('diagnostic_reason','allowed_qa_ids','allowed_statuses') if hasattr(error,key)},
                **({'missing_qa_ids':error.missing_qa_ids} if hasattr(error,'missing_qa_ids') else {}),
                **({'allowed_evidence_ids':error.allowed_evidence_ids} if hasattr(error,'allowed_evidence_ids') else {})}
    detail = ERRORS.get(str(error)) if isinstance(error, ValueError) else None
    if detail is None:
        if not fallback: return None
        detail = ('INVALID_REVIEW', '判定格式无效，请按本次片段和冻结规则修正，仅重试失败项。', 'review-next')
    code, message, action = detail
    return {'code': code, 'message': message, 'next_action': action}


FIELDS = {
    'qa question dismissal': ('DECISION_INVALID','qa_checks','疑问评论须逐条检查；重复提问也应提取并用 similar_to 归组，不能以重复或合并标为非问题。'),
    'qa candidate unchecked': ('DECISION_INVALID','qa_checks','存在候选回答：关联原文，或仅对该问题填写 checked_evidence_ids（allowed_evidence_ids 全部）及商品、条件不匹配的具体理由。'),
    'similar question requires same product and offer': ('DECISION_INVALID','qa_observations','不同商品或套餐不能合并问题；修正 similar_to。'),
    'invalid qa observations': ('DECISION_INVALID','qa_observations','新问题引用本段证据并逐字摘录，有回答再填原话，每段最多40项；无问答填 []，存在待查项时仍须完成 qa_checks。'),
    'qa coverage incomplete': ('DECISION_INVALID','qa_checks','问答检查遗漏：按 missing_qa_ids 补提取问题/原文回答，或填写本段未找到回答、评论非问题/语义不清的具体原因；只重交失败段。'),
    'invalid qa checks': ('DECISION_INVALID','qa_checks','剩余待查项填写 ids、status、非空 reason；历史问题仅用 unanswered，评论仅用 not_question/unclear。已有问答自动完成，不重复填。'),
    'invalid qa check target': ('DECISION_INVALID','qa_checks','仅填写未被问答处理的待查 ID，不重复、不混入外部 ID，不用未找到回答覆盖已有回答。'),
    'qa previous segment pending': ('DECISION_INVALID','qa_checks','先提交本批前面的片段，再续查其中新增的问题；保留已成功片段，只重交失败项。'),
    'invalid qa evidence': ('EVIDENCE_BINDING_INVALID','qa_observations','问答引用本段真实证据；图片必须先查看并列入 images_viewed。'),
    'qa quote must match evidence': ('EVIDENCE_BINDING_INVALID','qa_observations','问答逐字摘录引用字幕，不改写或补造内容。'),
    'qa reply requires known question': ('DECISION_INVALID','qa_observations.reply_to','reply_to 使用已记录问题的 id，先提交同批前段问题，不猜测未记录问题。'),
    'answer_complete must be boolean': ('DECISION_INVALID','qa_observations.answer_complete','answer_complete 只填 true/false；只有明确完整回答才填 true。'),
    'answered question requires speech or staff comment': ('EVIDENCE_BINDING_INVALID','qa_observations.answer_complete','已解答须引用本段字幕或角色为 host/room_admin 的评论原话，图片和身份不明的评论不能确认。'),
    'comment answer requires room staff role': ('EVIDENCE_BINDING_INVALID','qa_observations.answer_evidence_ids','评论回答仅引用单条 host/room_admin 评论，不按昵称或文字猜测助播身份，不与字幕混引。'),
    'similar question requires known comment question': ('DECISION_INVALID','qa_observations.similar_to','similar_to 仅用于新评论问题，引用上下文或本批前项的评论问题id；无可靠同类问题时省略。'),
    'cannot regroup an existing comment question': ('DECISION_INVALID','qa_observations.similar_to','同一评论问题已归类，不通过重复提取改组；保留原记录。'),
    'sales observation required': ('DECISION_INVALID','sales_observation','按模板填写商品观察；无法确认填 unknown，不省略字段。'),
    'sales observation requires change=same/switch/unknown/none': ('DECISION_INVALID','sales_observation.change','填写 same、switch、unknown 或 none。'),
    'sales observation requires actual evidence IDs': ('EVIDENCE_BINDING_INVALID','sales_observation.evidence_ids','商品切换、套餐变化和催单必须引用本段真实证据 ID。'),
    'sales observation image must be viewed': ('IMAGE_NOT_VIEWED','images_viewed','商品和催单引用的图片须先查看并列入 images_viewed。'),
    'sales product/offer must be short text': ('DECISION_INVALID','sales_observation','product 和 offer 须为不超过240字的字符串。'),
    'sales same requires a confirmed previous product; use switch or unknown': ('DECISION_INVALID','sales_observation.change','先完成同批前段；已有商品不明时重新用 switch 识别，或填 unknown。'),
    'sales switch requires product': ('DECISION_INVALID','sales_observation.product','切换或首次识别时填写主推商品名称。'),
    'unknown/none sales observation cannot assign a product': ('DECISION_INVALID','sales_observation','unknown 或 none 时 product、offer 留空。'),
    'invalid sales claims': ('DECISION_INVALID','sales_observation.claims','claims 须为不超过30项的数组；未推介商品时为空。'),
    'invalid sales claim kind': ('DECISION_INVALID','sales_observation.claims','kind 填 last_round、countdown、stock 或 adjustment。'),
    'sales claim value must be a nonnegative count/seconds or null': ('DECISION_INVALID','sales_observation.claims','仅倒计时/库存填写非负整数 value，未知填 null。'),
    'sales stock requires subject (product/gift/redemption quota)': ('DECISION_INVALID','sales_observation.claims','stock 必须填写 subject，区分主商品、赠品和换购名额；不超过120字。'),
    'invalid sales image description': ('DECISION_INVALID','sales_observation.claims','图片说明须为不超过500字的字符串。'),
    'sales image claim requires description': ('IMAGE_DESCRIPTION_REQUIRED','sales_observation.claims','引用图片须描述实际所见的催单或活动说明。'),
    'content route required': ('DECISION_INVALID','content_route','每段填写 content_route 的 type、reason 和 evidence_ids；无法确定专项时填 undetermined。'),
    'content route requires actual evidence': ('EVIDENCE_BINDING_INVALID','content_route.evidence_ids','引用本段不重复的真实依据；无任何证据时只能填 undetermined。'),
    'image must be viewed before judgment': ('IMAGE_NOT_VIEWED','images_viewed','主张、对照和路由引用的图片都须实际查看后列入 images_viewed。'),
    'evidence channel not allowed by rule': ('EVIDENCE_CHANNEL_INVALID','events','主张与对照都只能引用规则允许渠道的证据。'),
    'evidence outside segment': ('EVIDENCE_RANGE_INVALID','events','主张与对照证据时间都须与当前片段相交。'),
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
    'invalid counterpart evidence': ('COUNTERPART_EVIDENCE_INVALID', 'events.counterpart_evidence_ids', '对照证据须为本段不重复的真实证据 ID。'),
    'absolute claim basis required': ('ABSOLUTE_CLAIM_BASIS', 'events.claim_quote', '引用实际完整主张，按单一主张选择 direct 或 contradiction；不能核实填 insufficient。'),
    'counterpart quote required': ('COUNTERPART_QUOTE_REQUIRED', 'events.counterpart_quote', '填写独立同口径材料中与宣传矛盾的原文，重复主张不作反证。'),
    'counterpart evidence required': ('COUNTERPART_EVIDENCE_REQUIRED', 'events.counterpart_evidence_ids', '此规则命中还需引用与主张不同的对照证据；无对照材料时，已有独立风险线索且依赖核验填 insufficient，否则重新判断为 no_hit。'),
    'counterpart evidence not allowed': ('COUNTERPART_EVIDENCE_UNEXPECTED', 'events.counterpart_evidence_ids', '仅 evidence_gate=counterpart 的规则填写对照证据。'),
    'missing ASR cannot clear speech rule': ('ASR_EVIDENCE_MISSING', 'status', '本段 speech.can_clear=false；请一次修复本段所有含 speech 且为 no_hit 的规则。有真实命中证据可保留 hit，其余填 insufficient，不逐条重交。'),
    'missing or unseen frames cannot clear image rule': ('FRAMES_NOT_REVIEWED', 'status', '本段有图先实际查看并填写 images_viewed；无图时 image=insufficient，不能仅因缺图填 not_applicable。一次修复本段所有含 image 的规则：speech=no_hit 且 image=insufficient 时顶层也为 insufficient；保留真实 hit。'),
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
    'invalid counterpart evidence': ('COUNTERPART_EVIDENCE_INVALID', 'counterpart_evidence_ids', '对照证据须为本段不重复的真实证据编号。', 'repair-review-input'),
    'absolute claim basis required': ('ABSOLUTE_CLAIM_BASIS', 'claim_quote', '引用实际完整主张，按单一主张选择 direct 或 contradiction；不能核实填 insufficient。', 'repair-review-input'),
    'counterpart quote required': ('COUNTERPART_QUOTE_REQUIRED', 'counterpart_quote', '填写独立同口径材料中与宣传矛盾的原文，重复主张不作反证。', 'repair-review-input'),
    'counterpart evidence required': ('COUNTERPART_EVIDENCE_REQUIRED', 'counterpart_evidence_ids', '此规则命中还需引用与主张不同的对照证据；无对照材料时，已有独立风险线索且依赖核验填 insufficient，否则重新判断为 no_hit。', 'repair-review-input'),
    'counterpart evidence not allowed': ('COUNTERPART_EVIDENCE_UNEXPECTED', 'counterpart_evidence_ids', '仅 evidence_gate=counterpart 的规则填写对照证据。', 'repair-review-input'),
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
    if rule_index is not None and field in {'status','events','evidence_ids','counterpart_evidence_ids','description'}:
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
    'unsupported rule bundle': ('RULE_BUNDLE_INVALID','bundle','仅支持 finance、ecommerce 或 automotive。','rules-load'),
    'task binding mismatch': ('TASK_BINDING_MISMATCH','task_id','使用领取合同的原任务 ID。','review-next'),
    'task uses a fixed rule snapshot': ('RULE_SNAPSHOT_FIXED','bundle','任务规则固定，继续原合同；不得声称已追加专项。','review-next'),
    'no pending evidence': ('RULE_EVIDENCE_UNAVAILABLE','segment_id','重新领取未完成片段，引用其证据。','review-next'),
    'stale rule evidence': ('RULE_EVIDENCE_CHANGED','evidence_revision','重新领取最新证据版本。','review-next'),
    'invalid rule evidence': ('RULE_EVIDENCE_INVALID','evidence_ids','只引用本段实际字幕或图片 ID，images_viewed 仅填实际已看图片。','rules-load'),
    'rule image evidence not viewed': ('RULE_IMAGE_NOT_VIEWED','images_viewed','查看引用的图片或改用足够的实际字幕证据。','rules-load'),
    'rule reason required': ('RULE_REASON_REQUIRED','reason','填写证据支持的行业适用理由。','rules-load'),
}

"""Persist evidence-backed audience questions and host replies within one task."""
import copy
import hashlib
import re


INSTRUCTION = (
    'qa_observations 提取明确的观众提问（含主播明确转述）与主播回答；没有观众问题时，不从主播自问自答、修辞或普通推销虚构新问题。'
    '已有观众问题时，后续商品介绍、自问自答或促销说明只要实际回答了问题，也应关联，不要求点名观众或说“回答你”；无问答填 []。'
    '新问题填 question_evidence_ids、question（逐字摘录），有回答再填 answer_evidence_ids、answer（逐字摘录）；未回答不猜。'
    '回答前段问题时仅填 reply_to、answer_evidence_ids、answer；reply_to 复制 qa_context 的 id。新问题与本段回答放在同一条 observation，不另造 reply_to 或猜问题 ID。'
    'viewer_context 中单条评论可作观众问题；author_role=host/room_admin 的单条评论也可作主播/管理员（助播）回答，仍用 answer_evidence_ids 引用，不新增提交字段。无角色的评论不猜身份，不作确认回答；评论不能作风险命中证据。'
    '每段先提取观众的具体问题（无问号也可），不把刷屏、好评、催福利、指令或助播自问自答当问题；再检查本段ASR与有角色的评论是否回答 qa_context 的问题，同条评论不重复新建。'
    '每个新评论问题同时填写 question_scope、question_category、topic：question_scope 只能是 public 或 personalized；具体订单、地址、物流单、退款/售后个案归 personalized，交客服跟进；可由主播统一讲清的商品、价格、发货规则、售后规则和购买操作归 public。question_category 只能是 product、price、delivery、after_sales、purchase、other；topic 用简短、可复用的规范主题名，例如“发货时效与快递”。public 的同类问题使用完全相同的 topic，不把不同商品、套餐、对象或条件硬合并；personalized 不合并为主播答疑主题。'
    '先逐条判断评论指向的商品：明确写出商品名的不得留空，结合上下文已确认指代的沿用 sales_observation 或 qa_context 中同一商品的规范名；请求其他商品必须单独归属，不能挂到当前商品。商品归属明确时填写 question_product、question_offer（无套餐留空）、question_detail（只写一个具体疑问，例如圆珠是否足银，不合并含量、空心、氧化等细节；同商品同条件的“怎么打理/怎么清洗”使用同一具体疑问名，但能否机洗、能否手洗等不同条件分别保留）；不能因正在介绍某商品就猜评论归属，不明确留空。'
    'qa_context 按商品和具体疑问取代表问题，related_questions 保留同组原始提问。一次回答适用多个已知问题时，reply_to 指代表问题，applies_to 只列确实适用的其他问题id（最多7个）；必须同商品、套餐、具体细节，逐题检查时间与条件，不整组默认解答。'
    '重复提问仍逐条保留：每条 observation 只引用一条评论，同一评论只提取一次。同商品、套餐和具体条件的同义问题使用相同 question_detail，程序自动归组，默认不填 similar_to。仅需显式关联时才复制已知问题 ID，且商品、套餐、具体疑问必须一致；不猜本批新问题 ID。归类不代表其他问题已解答。reply_to/applies_to 中每个问题本次只出现一次，已放入 applies_to 的问题不再单独提交。'
    '先读完整字幕列出明确答复，再对照本段及历史问题关联；“没有/不支持/不知道何时上架”也可完整回答是否有售或是否已知的问题，不把否定答复当未回答。'
    '例如“有银梳子吗”对应“银梳子没有”；“7cm戴多大”对应“7厘米54”。单位写法和中文数字可同义理解，但答案仍逐字引用，不能改写数字或跨商品套用。'
    '未关联理由必须针对问题实际问的内容；商品有无、上架时间、材质不能一律写成尺寸或条件不匹配。候选已经明确回答时应保存回答，不用 unclear 绕过关联。'
    '有回答时加 answer_complete 布尔值：仅本段ASR或有角色的评论明确回答同一商品、对象及条件下的整个问题才填 true；只回应部分、答非所问、泛泛推销或关系不明填 false。完整摘录必要条件与否定，不只截开头一句；没有回答不填回答字段。'
    '图片引用须实际查看；读不清不提取。口播及画面回答照常检查所有风险规则，并结合问题、回答中的对象、条件、否定及澄清判定。'
    'qa_context 的历史问答仅补充理解，不能当成本段证据或自动推翻前段风险；只有同一商品、同一条件才能作语义补充，范围不明填 insufficient。'
)

QUESTION_SCOPES = {'public', 'personalized'}
QUESTION_CATEGORIES = {'product', 'price', 'delivery', 'after_sales', 'purchase', 'other'}
QUESTION_CATEGORY_LABELS = {
    'product': '商品本身', 'price': '价格与权益', 'delivery': '快递运输',
    'after_sales': '售后服务', 'purchase': '购买与操作', 'other': '其他问题',
}


def _compact(value, limit=120):
    return re.sub(r'\s+', '', value).strip()[:limit]


def _fallback_scope(text):
    normalized = _compact(text)
    # A rule question such as "支持退货吗" belongs in the host FAQ; make an item
    # personalized only when the text actually points to this viewer's case.
    personal = ('我的订单', '我订单', '我这单', '这单', '没收到货', '一直没到', '地址', '改地址',
                '订单号', '催发货', '物流单', '为什么不给我', '帮我查', '怎么还没')
    return 'personalized' if any(term in normalized for term in personal) else 'public'


def _fallback_category(text):
    normalized = _compact(text)
    if any(term in normalized for term in ('快递', '发货', '物流', '运费', '包邮', '到货', '仓')):
        return 'delivery'
    if any(term in normalized for term in ('退款', '退货', '换货', '售后', '赔', '过敏包退')):
        return 'after_sales'
    if any(term in normalized for term in ('价格', '多少钱', '到手', '优惠', '券', '赠品', '套餐', '折扣')):
        return 'price'
    if any(term in normalized for term in ('链接', '下单', '怎么买', '库存', '拍', '付款')):
        return 'purchase'
    if any(term in normalized for term in ('成分', '配料', '规格', '保质期', '口感', '功效', '适合', '怎么吃', '质量')):
        return 'product'
    return 'other'


def _topic_key(scope, category, topic):
    return hashlib.sha256(f'{scope}\x1f{category}\x1f{_compact(topic).lower()}'.encode()).hexdigest()[:20]


def _question_metadata(item, text):
    scope = item.get('question_scope') if isinstance(item, dict) else None
    category = item.get('question_category') if isinstance(item, dict) else None
    topic = item.get('topic') if isinstance(item, dict) else None
    explicit_topic = isinstance(topic, str) and bool(topic.strip())
    scope = scope if scope in QUESTION_SCOPES else _fallback_scope(text)
    category = category if category in QUESTION_CATEGORIES else _fallback_category(text)
    topic = _compact(topic if explicit_topic else text)
    if not topic:
        topic = '待确认问题'
    return {'question_scope': scope, 'question_category': category, 'topic': topic,
            'topic_key': _topic_key(scope, category, topic), '_topic_explicit': explicit_topic}


def _status_counts(items):
    counts = {'answered': 0, 'reply_detected': 0, 'pending': 0, 'unanswered':0}
    for item in items:
        status=question_status(item)
        counts[status]=counts.get(status,0)+1
    return counts


def interaction_optimization(questions):
    """Project stored comment questions into host and customer-service actions."""
    public, personalized = [], []
    for question in questions:
        if question.get('source') != 'viewer_comment':
            continue
        (personalized if question.get('question_scope') == 'personalized' else public).append(question)
    topics = {}
    for question in public:
        key = answer_scope(question) or question.get('topic_key') or _topic_key('public', question.get('question_category', 'other'), question.get('topic', question['question']))
        topic = topics.setdefault(key, {'topic': (question['product'] + ' · ' + question['question_detail']) if answer_scope(question) else question.get('topic', question['question']),
            'category': question.get('question_category', 'other'), 'items': [], 'latest': 0})
        topic['items'].append(question)
        topic['latest'] = max(topic['latest'], question.get('start_ms', 0))
    topic_rows = []
    scripts = {
        'product': '在商品讲解段补充“是什么—适合谁—关键参数”的标准三句。',
        'price': '报价时同步说明链接号、规格和权益条件。',
        'delivery': '在固定答疑段统一说明发货时效、快递和例外条件。',
        'after_sales': '主播只说明公开售后规则；具体订单转客服核对。',
        'purchase': '重复明确链接位置、下单步骤和库存状态。',
        'other': '先补齐商品或条件，再决定是否纳入固定话术。',
    }
    for topic in topics.values():
        items = topic.pop('items')
        counts = _status_counts(items)
        questioners = questioner_counts(items)
        complete = counts['answered'] == len(items) and len(items) > 0
        topic_rows.append({**topic, 'question_count': len(items), **questioners, **counts,
            'answer_status': 'answered' if complete else 'partial' if counts['answered'] or counts['reply_detected'] else 'pending' if counts['pending'] else 'evidence_unavailable' if counts.get('evidence_unavailable') else 'unanswered',
            'action': '保留为下场主播标准答疑话术，并继续核对商品和套餐变化。' if complete else scripts[topic['category']],
            'questions': [{key: item[key] for key in ('id', 'question', 'start_ms', 'end_ms', 'answers', 'author_nickname', 'author_role') if key in item} for item in items[:5]]})
    topic_rows.sort(key=lambda item: (-item['question_count'], -item['latest'], item['topic']))
    category_rows = []
    for category in QUESTION_CATEGORY_LABELS:
        rows = [item for item in topic_rows if item['category'] == category]
        if not rows:
            continue
        category_rows.append({'category': category, 'label': QUESTION_CATEGORY_LABELS[category],
            'topic_count': len(rows), 'question_count': sum(item['question_count'] for item in rows),
            'answered_count': sum(item['answered'] for item in rows)})
    personal_rows = []
    for question in personalized:
        status = question_status(question)
        personal_rows.append({'question': question['question'], 'category': question.get('question_category', 'other'),
            'category_label': QUESTION_CATEGORY_LABELS.get(question.get('question_category', 'other'), QUESTION_CATEGORY_LABELS['other']),
            'status': status, 'author_nickname': question.get('author_nickname'), 'author_role': question.get('author_role'),
            'start_ms': question.get('start_ms', 0),
            'action': '转客服按订单、地址或售后条件核对；不要求主播在公开场合逐条答复。'})
    personal_rows.sort(key=lambda item: item['start_ms'], reverse=True)
    public_counts = _status_counts(public)
    return {'public': {'question_count': len(public), 'topic_count': len(topic_rows), **public_counts,
                       'categories': category_rows, 'topics': topic_rows[:12]},
            'personalized': {'question_count': len(personalized), **_status_counts(personalized), 'items': personal_rows[:12]},
            'scope': '公共问题用于优化主播文案与固定答疑；个性化问题转客服。仅基于本次采集并完成识别的评论，未采集或未分类不计入回答表现。'}

CHECK_INSTRUCTION_V2 = (
    'qa_checklist 是本段必查项：已有 qa_observations 提取的问题及原文回答自动完成对应检查，不重复填写。'
    '其余在 qa_checks 写 {ids:[待查ID],status:"unanswered|not_question|unclear",reason:"具体原因"}；'
    'unanswered 仅用于历史待解答问题，表示本段未找到回答；not_question/unclear 仅用于未提取的评论，表示非问题/语义不清。'
    '同原因的刷屏或表情可合并 ids；含疑问线索的评论须逐条检查，不能以重复/同主题/已合并为由填 not_question。重复提问仍逐条提取，由商品、套餐、规范具体疑问自动归组。'
    '新问题有候选却不关联回答时，也需用评论ID在 qa_checks 填 unanswered/unclear 和 checked_evidence_ids；提取问题不等于检查回答。'
    '同批前段新提取的问题也要续查；相同回答可分别 reply_to 多个已知问题，不自动传播解答状态。'
    '本段无对应回答不代表整场未回答；不得用未检查、跳过或虚构原文凑齐检查。'
)

FOCUS_INSTRUCTION_V2 = (
    '先看每段 qa_focus 中并列的问题与候选原文，再填写 qa_observations/qa_checks。'
    '候选是本地文字召回，不是已解答结论；核对商品、套餐、否定和完整条件。'
    '例如已知问题“小灯泡多少量”，后续“小灯泡买三十、送三十、到手六十毫升”可关联为回答，即使它是在介绍商品。'
    '问题未指定套餐时，可摘录并明确回答适用的套餐，不因问题 product/offer 字段为空就忽略；含义或条件仍不明时不确认完整回答。'
    '有候选但不关联回答时，qa_checks 仅填单个ID，附 checked_evidence_ids 列出所有候选原文ID，reason 具体说明不匹配的商品或条件；不能笼统写未回答。无候选也要检查完整字幕和有角色的评论。'
)


CHECK_INSTRUCTION = ('qa_checklist 中每项必须提取问答或填写 qa_checks 的 ids/status/reason；历史问题用 unanswered，评论用 not_question/unclear。重复提问仍需提取，不当作非问题。')
FOCUS_INSTRUCTION = ('先看每段 qa_focus 中并列的问题与候选原文，再填写原有 qa_observations/qa_checks。候选仅为容量文字线索，核对商品、套餐、否定和条件；未关联时说明具体原因。')

def question_like(text):
    return bool(re.fullmatch(r'(?:保质期|规格|成分|价格|尺码|生产日期|配料表)[?？。！!]*', text.strip()) or re.search(r'[?？]|吗|么|哪|多少|几[岁个盒件天号]|什么|啥|怎么|多久|多大|能不能|有没有|是不是', text))


def generic_unanswered(reason):
    return not re.sub(r'本段|记录中|未|没有|找到|识别|对应|回答|问题|明确|针对|观众|主播|这些|提问|该|到|与|的|给出|所问|尺寸|条件|不匹配|匹配|或|[。 ，,；;\s]', '', reason)


def _recall_text(text):
    """Equivalent unit spelling for recall, never rewrite stored evidence."""
    text = _compact(text).lower().replace('公分','厘米').replace('㎝','厘米').replace('㎜','毫米')
    text = re.sub(r'(?<=\d)cm(?![a-z])', '厘米', text)
    text = re.sub(r'(?<=\d)mm(?![a-z])', '毫米', text)
    digits = str.maketrans('零一二两三四五六七八九', '01223456789')
    return re.sub(r'(?<![十百千万零一二两三四五六七八九])[零一二两三四五六七八九](?:点[零一二两三四五六七八九]+)?(?=厘米|毫米)',
                  lambda m:m[0].translate(digits).replace('点','.'), text)


def answer_candidates(question, segment):
    """Lexical and synonym recall only; candidates are never answer verdicts."""
    text = _recall_text(question['question'])
    families = [('保质期','效期'), ('加糖','含糖','无糖','糖'),
                ('冷藏','常温','保存'), ('发货','快递'), ('价格','多少钱','块','元'),
                ('几岁','多大','岁','宝宝','孩子','小孩'),
                ('打理','清洗','水洗','手洗','机洗','干洗','局部洗','哪里脏了'),
                ('什么码','多大码','尺码','穿的','穿的是','m码','l码'),
                ('起球','摩擦'), ('弹性','弹力'), ('加单','补货','库存','断码')]
    terms = set()
    for family in families:
        if any(word in text for word in family):
            if family[0] == '加糖' and '乳糖' in text:continue
            terms.update(family)
    measures = re.findall(r'\d+(?:\.\d+)?(?:厘米|毫米)', text)
    terms.update(measures)
    clean = re.sub(r'请问|这个|这款|你们|有什么|不一样|是不是|可以|多少|怎么|什么|哪个|什么时候|啥时候|吗|呢|啊|呀|的|和|有|没', '', text)
    words = re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]+', clean)
    terms.update(w for word in words for w in (word[i:i+2] for i in range(len(word)-1)))
    terms -= {'能喝','能带','能戴','不能','时候'}
    speech = sorted(segment.get('subtitles', []), key=lambda u:u['start_ms'])
    candidates, seen = [], set()
    for index, item in enumerate(speech):
        if item['end_ms'] < question['start_ms'] or item['id'] in seen:continue
        literal = _recall_text(item['text'])
        hits = {term for term in terms if term in literal}
        if measures and not any(re.search(r'(?<![\d.])'+re.escape(m),literal) for m in measures):continue
        if not hits or hits == {'糖'} and '乳糖' in literal:continue
        window = [item]
        if index and item['start_ms']-speech[index-1]['end_ms'] <= 3000 and speech[index-1]['start_ms'] >= question['start_ms']:
            window.insert(0,speech[index-1])
        for following in speech[index+1:index+3]:
            if following['start_ms']-window[-1]['end_ms'] > 3000 or following['end_ms']-item['start_ms'] > 20000:break
            window.append(following)
        seen.update(u['id'] for u in window)
        candidates.append({'source':'speech','evidence':[{k:u[k] for k in ('id','text','start_ms','end_ms')} for u in window]})
        if len(candidates) == 2:break
    return candidates


def focus(previous, segment, *, version=1):
    """Pair bounded pending questions with literal capacity clues, never verdicts."""
    if version >= 2:
        known = {q['id']:q for q in previous}
        selected = [known[k] for k,v in check_targets(previous,segment,version=2).items() if v=='question']
        recorded = {ref for q in previous for ref in q.get('evidence_ids',[])}
        selected += [{'id':c['id'],'question':c['text'],'start_ms':c['start_ms'],'answers':[]}
                     for c in segment.get('viewer_context',{}).get('comments',[])
                     if c['id'] not in recorded and question_like(c['text'])]
        return [{'question_id':q['id'],'question':q['question'],'product':q.get('product',''),
                 'offer':q.get('offer',''),'status':question_status(q),
                 'candidates':answer_candidates(q,segment)} for q in selected]
    known = {q['id']: q for q in previous}
    pending = [known[key] for key, kind in check_targets(previous, segment).items() if kind == 'question']
    speech = sorted(segment.get('subtitles', []), key=lambda s: s['start_ms'])
    quantity = re.compile(r'[0-9零一二两三四五六七八九十百千万点半]+\s*(?:毫升|毫克|千克|公斤|克|升|(?:ml|kg|g)(?![a-z]))', re.I)
    rows = []
    for question in pending:
        text = re.sub(r'\s+', '', question['question']).lower()
        match = re.search(r'(?:是|有|的)?(?:多少(?:量|毫升|克|ml|g)|几(?:毫升|克|ml|g)|多大容量|容量多少)', text)
        anchor = re.sub(r'^(?:请问|想问一下|这个|这款)+', '', text[:match.start()]).strip('，,：:') if match else ''
        candidates, seen = [], set()
        if len(anchor) >= 2:
            for index, item in enumerate(speech):
                if anchor not in re.sub(r'\s+', '', item['text']).lower() or item['start_ms'] < question['start_ms']:
                    continue
                # Keep adjacent lines together: buy thirty / gift thirty / sixty ml.
                window = [item]
                for following in speech[index + 1:index + 4]:
                    if following['start_ms'] - window[-1]['end_ms'] > 3000 or following['end_ms'] - item['start_ms'] > 20000:
                        break
                    window.append(following)
                if index and item['start_ms'] - speech[index - 1]['end_ms'] <= 3000 and speech[index - 1]['start_ms'] >= question['start_ms']:
                    window.insert(0, speech[index - 1])
                if not quantity.search(''.join(s['text'] for s in window)) or item['id'] in seen:
                    continue
                seen.update(s['id'] for s in window)
                candidates.append({'source':'speech', 'evidence':[
                    {k:s[k] for k in ('id','text','start_ms','end_ms')} for s in window]})
                if len(candidates) == 3:
                    break
        rows.append({'question_id':question['id'], 'question':question['question'],
                     'product':question.get('product', ''), 'offer':question.get('offer', ''),
                     'status':question_status(question), 'candidates':candidates})
    return rows


def review_diagnostic(previous, segment, observations, checks, provided_focus, *, version=1):
    """Local audit separates supplied context from same-batch replay-only clues."""
    normalized = {q['id']: q for q in observations}
    normalized.update({ref:q for q in observations if q.get('source')=='viewer_comment' for ref in q['evidence_ids']})
    dispositions = {key:c for c in checks for key in c['ids']}
    supplied = {q['question_id']:q for q in provided_focus}
    items = []
    for row in focus(previous, segment, version=version):
        key = row['question_id']
        answers = normalized.get(key, {}).get('answers', [])
        check = dispositions.get(key, {})
        outcome = ('answered' if any(a.get('answer_complete') is True for a in answers) else
                   'reply_detected' if answers else 'question_extracted' if key in normalized else 'candidate_unanswered' if row['candidates'] and check.get('status') == 'unanswered' else
                   'no_candidate' if check.get('status') == 'unanswered' else 'not_checked')
        items.append({**row, 'provided_to_model':key in supplied, 'outcome':outcome,
                      'check_status':check.get('status'), 'check_reason':check.get('reason', ''),
                      'answer_evidence_ids':[ref for a in answers for ref in a['evidence_ids']]})
    return {'matcher':'literal_reply_v2' if version>=2 else 'capacity_literal_v1', 'provided_focus':copy.deepcopy(provided_focus), 'questions':items}


def check_targets(previous, segment, *, version=1):
    known = {q['id']: q for q in previous}
    pending = sorted((q for q in known.values() if question_status(q) != 'answered'),
                     key=lambda q: (bool(answer_candidates(q,segment)) if version>=2 else False, q['start_ms'], q['id']))[-8:]
    targets = {q['id']: 'question' for q in pending}
    recorded = {ref for q in known.values() if q.get('source') == 'viewer_comment' for ref in q['evidence_ids']}
    targets.update({c['id']: 'comment' for c in segment.get('viewer_context', {}).get('comments', [])
                    if c['id'] not in recorded})
    return targets


def check_coverage(checks, observations, previous, segment, *, version=1, required_previous=None, errors=None):
    """Require a disposition for each bounded input; meaning remains the reviewer's job."""
    from runtime.review_errors import ReviewValidationError
    targets = check_targets(previous if required_previous is None else required_previous, segment, version=version)
    # Earlier items from the frozen template remain valid when same-batch questions
    # enter the latest-eight window; they do not enlarge the required window.
    known = {q['id']: q for q in previous}
    allowed = {q['id']:'question' for q in known.values() if question_status(q) != 'answered'} | targets
    resolved = {}
    for question in observations:
        if question.get('source') == 'viewer_comment':
            for ref in question['evidence_ids']:
                if ref in targets: resolved[ref] = 'question_extracted'
        if question['answers']:
            if question['id'] in allowed:
                resolved[question['id']] = question_status(question)
            for answer in question['answers']:
                if answer.get('source') == 'room_comment':
                    for ref in answer['evidence_ids']:
                        if ref in targets: resolved[ref] = 'staff_reply'
    if not isinstance(checks, list) or len(checks) > len(allowed):
        error = ValueError('invalid qa checks');error.field='qa_checks'
        if errors is None:raise error
        errors.append(error)
        if not isinstance(checks,list):checks=[]
    result = [{'ids':[key], 'status':status} for key,status in resolved.items()]
    focused = {r['question_id']:r for r in focus(previous,segment,version=version)} if version>=2 else {}
    comments = {c['id']:c for c in segment.get('viewer_context',{}).get('comments',[])}
    extracted_pending = {ref for q in observations if not q['answers'] for ref in q.get('evidence_ids',[])
                         if focused.get(ref,{}).get('candidates')}
    for ref in extracted_pending:
        if resolved.get(ref)=='question_extracted':resolved.pop(ref)
    for check_index, item in enumerate(checks):
        previous_resolved = resolved.copy() if errors is not None else None
        try:
            def invalid(message, reason, *, ids=(), statuses=()):
                error = ReviewValidationError(message, segment['id'], field=f'qa_checks[{check_index}]')
                error.diagnostic_reason = reason
                error.allowed_qa_ids = list(ids)
                error.allowed_statuses = list(statuses)
                return error
            if not isinstance(item, dict) or set(item)-({'ids','status','reason','checked_evidence_ids'} if version>=2 else {'ids','status','reason'}) or not {'ids','status','reason'} <= set(item):
                raise invalid('invalid qa checks', 'invalid_fields_or_value')
            ids, status, reason = item['ids'], item['status'], item['reason']
            if (not isinstance(ids, list) or not ids or not isinstance(status, str) or not isinstance(reason, str)
                    or not reason.strip() or len(reason) > 500):
                raise invalid('invalid qa checks', 'invalid_fields_or_value')
            row_error_count = len(errors) if errors is not None else 0
            for key in ids:
                try:
                    if not isinstance(key, str) or key not in allowed or key in resolved:
                        raise invalid('invalid qa check target', 'already_resolved' if isinstance(key,str) and key in resolved else 'unknown_target', ids=[i for i in allowed if i not in resolved])
                    statuses = {'unanswered','unclear'} if key in extracted_pending else {'unanswered'} if allowed[key] == 'question' else {'not_question','unclear'}
                    if status not in statuses:
                        raise invalid('invalid qa checks', 'invalid_status', ids=[key], statuses=sorted(statuses))
                    if version >= 2:
                        comment = comments.get(key)
                        if comment and question_like(comment['text']):
                            if len(ids) != 1 or status == 'not_question' and re.search(r'重复|合并|同主题',reason):
                                raise ReviewValidationError('qa question dismissal', segment['id'], field='qa_checks')
                        candidates = focused.get(key,{}).get('candidates',[])
                        if candidates:
                            expected = {e['id'] for row in candidates for e in row['evidence']}
                            checked = item.get('checked_evidence_ids',[])
                            if generic_unanswered(reason) or len(ids)!=1 or not isinstance(checked,list) or any(not isinstance(i,str) for i in checked) or set(checked)!=expected or len(checked)!=len(expected):
                                error = ReviewValidationError('qa candidate unchecked', segment['id'], field=f'qa_checks[{check_index}]')
                                error.allowed_evidence_ids = sorted(expected)
                                error.allowed_qa_ids = [key]
                                error.diagnostic_reason = 'candidate_unchecked'
                                raise error
                    resolved[key] = status
                except (ValueError,TypeError,KeyError) as error:
                    if errors is None:raise
                    if not getattr(error,'field',None) or error.field=='qa_checks':error.field=f'qa_checks[{check_index}]'
                    errors.append(error)
            if errors is not None and len(errors)>row_error_count:
                resolved=previous_resolved
                continue
            result.append({'ids':ids, 'status':status, 'reason':reason.strip(),
                           **({'checked_evidence_ids':item['checked_evidence_ids']} if 'checked_evidence_ids' in item else {})})
        except (ValueError, TypeError, KeyError) as error:
            if errors is None:raise
            resolved = previous_resolved
            if not getattr(error,'field',None) or error.field=='qa_checks':error.field=f'qa_checks[{check_index}]'
            errors.append(error)
    missing = [key for key in targets if key not in resolved]
    if missing:
        error = ReviewValidationError('qa coverage incomplete', segment['id'], field='qa_checks')
        error.missing_qa_ids = missing
        error.allowed_qa_ids = missing
        error.diagnostic_reason = 'coverage_incomplete'
        if errors is None:raise error
        errors.append(error)
    return result


def question_status(question):
    if any(a.get('answer_complete') is True for a in question['answers']):
        return 'answered'
    if question['answers'] or question.get('answers_omitted'):return 'reply_detected'
    if question.get('check_state')=='evidence_unavailable':return 'evidence_unavailable'
    return 'unanswered' if question.get('check_state')=='checked' else 'pending'


def questioner_counts(questions):
    comments = {ref:q for q in questions if q.get('source') == 'viewer_comment'
                for ref in q['evidence_ids']}
    return {'comment_question_count':len(comments),
            'questioner_count':len({q['author_id'] for q in comments.values() if q.get('author_id')}),
            'unknown_author_question_count':sum(not q.get('author_id') for q in comments.values())}


def summarize(segments):
    from runtime.report_data import public_text
    segments = list(segments)
    questions = {}
    comment_ids = {}
    for segment in sorted(segments, key=lambda s: (s['start_ms'], s['id'])):
        if segment.get('review_status') != 'done':
            continue
        if segment.get('qa_review_status') == 'done':
            from runtime.qa_workflow import valid
            if not valid(segment):continue
        for item in (segment.get('qa_review_result') if segment.get('qa_review_status') == 'done' else segment.get('review_result') or {}).get('qa_observations', []):
            key = item['id']
            if item.get('source') == 'viewer_comment':
                identity = (tuple(item['evidence_ids']), ''.join(item['question'].split()))
                key = comment_ids.setdefault(identity, key)
            question = questions.setdefault(key, {**copy.deepcopy(item), 'id':key, 'answers': []})
            seen = {(a['segment_id'], tuple(a['evidence_ids'])) for a in question['answers']}
            for answer in item['answers']:
                key = (answer['segment_id'], tuple(answer['evidence_ids']))
                if key not in seen:
                    question['answers'].append(copy.deepcopy(answer)); seen.add(key)
    for segment in segments:
        supplements = segment.get('qa_answer_supplements', [])
        if not supplements:continue
        from runtime.qa_workflow import digest, segment_source
        current_hash = digest(segment_source(segment))
        for supplement in supplements:
            if supplement['source_hash'] != current_hash:continue
            row = supplement['question']
            identity = (tuple(row['evidence_ids']), ''.join(row['question'].split()))
            key = comment_ids.get(identity, row['id']) if row.get('source') == 'viewer_comment' else row['id']
            target = questions.get(key)
            if not target or any(target.get(k) != row.get(k) for k in ('question','evidence_ids','product','offer','question_detail')):continue
            seen = {(a['segment_id'], tuple(a['evidence_ids'])) for a in target['answers']}
            for answer in row['answers']:
                if (answer['segment_id'], tuple(answer['evidence_ids'])) not in seen:
                    target['answers'].append(copy.deepcopy(answer))
                    seen.add((answer['segment_id'], tuple(answer['evidence_ids'])))
    for item in questions.values():
        item['question'] = public_text(item['question'])
        item['product'] = public_text(item.get('product', ''))
        item['offer'] = public_text(item.get('offer', ''))
        for answer in item['answers']:
            answer['text'] = public_text(answer['text'])
            answer['product'] = public_text(answer.get('product', ''))
            answer['offer'] = public_text(answer.get('offer', ''))
        item['answers'].sort(key=lambda a: (a['start_ms'], a['segment_id']))
        item['status'] = question_status(item)
        if item.get('source') == 'viewer_comment':
            metadata = _question_metadata(item, item['question'])
            for key, value in metadata.items():
                if key != '_topic_explicit':
                    item.setdefault(key, value)
            item.setdefault('group_id', item['id'])
            item['group_question'] = public_text(item.get('group_question', item['question']))
    ordered = sorted(questions.values(), key=lambda q: (q['start_ms'], q['id']))
    project_topics(ordered)
    previous = {}
    for question in ordered:
        question.pop('previous_question_id', None)
        author = question.get('author_id') if question.get('source') == 'viewer_comment' else None
        if author:
            if author in previous:
                question['previous_question_id'] = previous[author]
            previous[author] = question['id']
    return ordered


def answer_scope(question):
    """Only explicit product and precise detail support shared answers."""
    if question.get('question_scope') == 'personalized':
        return None
    product, detail = question.get('product','').strip(), question.get('question_detail','').strip()
    return (product, question.get('offer','').strip(), detail) if product and detail else None


def applies_to_ids(question, previous, product):
    scope=answer_scope(question)
    if not scope or not product or (product.get('product'),product.get('offer',''))!=scope[:2]:return []
    return [q['id'] for q in context_questions(previous) if q['id']!=question['id'] and answer_scope(q)==scope]


def project_topics(questions):
    explained = {}
    for question in questions:
        scope = answer_scope(question)
        if scope:
            for answer in question['answers']:
                if answer.get('answer_complete') is True and answer.get('product') == scope[0] and answer.get('offer','') == scope[1]:
                    if scope not in explained or answer['start_ms'] > explained[scope]['start_ms']:
                        explained[scope] = answer
    for question in questions:
        question.pop('topic_explanation',None)
        scope = answer_scope(question)
        if scope:
            question['group_id'] = 'scope:' + hashlib.sha256('\x1f'.join(scope).encode()).hexdigest()[:20]
            question['group_question'] = question['product'] + ' · ' + question['question_detail']
        if scope in explained:
            question['topic_explanation'] = copy.deepcopy(explained[scope])


def context_questions(previous):
    result = {}
    for question in previous:
        result[question['id']] = question
        for member in question.get('related_questions',[]):
            result.setdefault(member['id'], member)
    return list(result.values())


def context(segments, before_ms, *, lookahead=(), pending_only=False):
    items = summarize(s for s in segments if s['end_ms'] <= before_ms)
    if pending_only:
        speech = [u for segment in lookahead for u in segment.get('subtitles',[])]
        if not speech:return []
        cutoff = min(before_ms, min(u.get('context_start_ms',u['start_ms']) for u in speech))
        items = [q for q in items if q['start_ms'] < cutoff and q.get('question_detail','').strip()]
    pending = [q for q in items if q['status'] != 'answered']
    answered = [] if pending_only else [q for q in items if q['status'] == 'answered']
    if lookahead:
        from difflib import SequenceMatcher
        comments = [c['text'] for s in lookahead for c in s.get('viewer_context',{}).get('comments',[])]
        def priority(q):
            return (any(answer_candidates(q,s) for s in lookahead),
                    any(SequenceMatcher(None,_compact(q['question']),_compact(text)).ratio() >= .75 for text in comments),
                    q['start_ms'])
        pending.sort(key=priority)
        answered.sort(key=priority)
    def representatives(rows):
        groups = {}
        for q in rows:
            key = answer_scope(q) or (('unresolved',q['id']) if pending_only else
                ('unresolved', q.get('product',''), q.get('offer',''), _compact(q['question'])))
            groups.setdefault(key, []).append(q)
        chosen = sorted(groups.values(), key=lambda group: rows.index(group[-1]))[-8:]
        result = []
        for group in chosen:
            q = copy.deepcopy(group[-1])
            members = group[-8:-1]
            q['related_questions'] = [{k:copy.deepcopy(v) for k,v in m.items()
                if k not in {'answers','related_questions','topic_explanation'}} for m in members]
            q['related_count'] = len(group)
            q['related_omitted_count'] = max(0,len(group)-8)
            result.append(q)
        return result
    pending = representatives(pending)
    answered = representatives(answered)
    # Full evidence remains on disk; bounded excerpts are sufficient for continuity.
    return [{**q, 'question': q['question'][:500], 'answers':[
        {**a, 'text': a['text'][:800]} for a in q['answers'][-2:]]} for q in pending + answered]


def normalize(value, segment, viewed, previous, product=None, *, errors=None, max_items=40):
    if not isinstance(value, list) or len(value) > max_items:
        error = ValueError('invalid qa observations');error.field='qa_observations'
        if errors is None:raise error
        errors.append(error);return []
    evidence = {u['id']: {**u, 'kind': 'speech'} for u in segment.get('subtitles', [])}
    evidence.update({f['id']: {**f, 'kind': 'image'} for f in segment.get('frames', [])})
    evidence.update({c['id']: {**c, 'kind':'comment'} for c in segment.get('viewer_context', {}).get('comments', [])})
    known = {q['id']: q for q in context_questions(previous)}
    result, seen = [], set()

    def invalid(message, reason='invalid_question_fields', field=''):
        from runtime.review_errors import ReviewValidationError
        error = ReviewValidationError(message, segment['id'], field=f'qa_observations[{index}]' + ('.'+field if field else ''))
        error.diagnostic_reason = reason
        if message in {'qa reply requires known question','similar question requires known comment question'}:
            error.allowed_qa_ids = list(known)
        if message == 'invalid qa evidence':
            error.allowed_evidence_ids = list(evidence)
        return error

    def excerpt(ids, quote, *, answer=False):
        if (not isinstance(ids, list) or not ids
                or any(not isinstance(i, str) or i not in evidence for i in ids) or len(set(ids)) != len(ids)):
            raise invalid('invalid qa evidence')
        items = [evidence[i] for i in ids]
        if answer and any(e['kind'] == 'comment' for e in items):
            if len(items) != 1 or items[0].get('author_role') not in {'host', 'room_admin'}:
                raise invalid('comment answer requires room staff role')
        if any(e['kind'] == 'image' and e['id'] not in viewed for e in items):
            raise invalid('invalid qa evidence')
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 2000:
            raise invalid('invalid qa observations')
        if any(e['kind'] == 'comment' for e in items) and (len(items) != 1 or items[0]['kind'] != 'comment'):
            raise invalid('comment question requires one comment')
        if all(e['kind'] in {'speech', 'comment'} for e in items):
            source = ''.join(e['text'] for e in sorted(items, key=lambda e: e['start_ms']))
            if ''.join(quote.split()) not in ''.join(source.split()):
                from runtime.review_errors import ReviewValidationError
                error = ReviewValidationError('qa quote must match evidence', segment['id'],
                    field=f'qa_observations[{index}].' + ('answer' if answer else 'question'))
                error.allowed_evidence_ids = ids
                error.diagnostic_reason = 'quote_not_in_referenced_text'
                raise error
        start = min(e.get('start_ms', e.get('time_ms', segment['start_ms'])) for e in items)
        end = max(e.get('end_ms', e.get('time_ms', start)) for e in items)
        comment = items[0]['kind'] == 'comment'
        return {**({'source':'room_comment' if answer else 'viewer_comment', 'time_basis':'received',
                    **{k:items[0][k] for k in ('author_role', 'author_id', 'author_nickname') if k in items[0]}} if comment else {}),
                'text': quote.strip(), 'start_ms': start, 'end_ms': end,
                'evidence_ids': ids, 'segment_id': segment['id'],
                'product': '' if comment else (product or {}).get('product', ''),
                'offer': '' if comment else (product or {}).get('offer', '')}

    for index, item in enumerate(value):
        previous_seen = seen.copy() if errors is not None else None
        try:
            if not isinstance(item, dict):
                raise invalid('invalid qa observations')
            reply = item.get('reply_to')
            if 'applies_to' in item and not reply:
                raise invalid('invalid qa observations', 'applies_to_requires_reply', 'applies_to')
            if reply:
                if not isinstance(reply, str) or reply not in known or item.get('question_evidence_ids') or item.get('question'):
                    raise invalid('qa reply requires known question')
                question = {**copy.deepcopy(known[reply]), 'answers': []}
            else:
                quote = excerpt(item.get('question_evidence_ids'), item.get('question'))
                question = {'id': f"{segment['id']}:q{index + 1}",
                            'question': quote.pop('text'), **quote, 'answers': []}
                if question.get('source') == 'viewer_comment':
                    prior = next((q for q in previous if q.get('source') == 'viewer_comment'
                                  and q['evidence_ids'] == question['evidence_ids']
                                  and ''.join(q['question'].split()) == ''.join(question['question'].split())), None)
                    if prior:
                        question = {**copy.deepcopy(prior), 'answers': []}
            if question['id'] in seen:
                raise invalid('invalid qa observations', 'duplicate_question')
            seen.add(question['id'])
            metadata = {'_topic_explicit': False}
            if not reply:
                for field, target in [('question_product','product'),('question_offer','offer'),('question_detail','question_detail')]:
                    if field in item:
                        text = item[field]
                        if not isinstance(text,str) or len(text)>240:
                            raise invalid('invalid qa observations', 'invalid_scope', field)
                        question[target] = text.strip()
                if not question.get('product'):
                    products = {q.get('product','').strip() for q in known.values()}
                    products.add((product or {}).get('product','').strip())
                    explicit = [name for name in products if len(name) >= 2 and name in question['question']]
                    if len(explicit) == 1:question['product'] = explicit[0]
                metadata = _question_metadata(item, question['question'])
                question.update({key: value for key, value in metadata.items() if key != '_topic_explicit'})
            if question.get('question_scope') == 'public' and 'similar_to' in item:
                similar = item['similar_to']
                target = known.get(similar) if isinstance(similar, str) else None
                if (reply or question.get('source') != 'viewer_comment' or not target
                        or target.get('source') != 'viewer_comment' or target['id'] == question['id']
                        or target.get('question_scope','public') != 'public'):
                    raise invalid('similar question requires known comment question')
                if ((answer_scope(question) or answer_scope(target)) and answer_scope(question)!=answer_scope(target)) or any(question.get(k) and target.get(k) and question[k]!=target[k] for k in ('product','offer')):
                    raise invalid('similar question requires same product and offer')
                group_id = target.get('group_id', target['id'])
                if question.get('group_id') and question['group_id'] != group_id:
                    raise invalid('cannot regroup an existing comment question')
                question.update(group_id=group_id, group_question=target.get('group_question', target['question']))
                for key in ('topic','topic_key','question_category'):
                    if key in target:question[key]=target[key]
            elif question.get('question_scope') == 'public' and metadata.get('_topic_explicit'):
                question.update(group_id='topic:' + question['topic_key'], group_question=question['topic'])
            elif question.get('source') == 'viewer_comment':
                question.setdefault('group_id', question['id'])
                question.setdefault('group_question', question['question'])
            if answer_scope(question):
                question['group_id'] = 'scope:' + hashlib.sha256('\x1f'.join(answer_scope(question)).encode()).hexdigest()[:20]
                question['group_question'] = question['product'] + ' · ' + question['question_detail']
            if item.get('answer_evidence_ids'):
                answer = excerpt(item['answer_evidence_ids'], item.get('answer'), answer=True)
                if 'answer_complete' in item:
                    if type(item['answer_complete']) is not bool:
                        raise invalid('answer_complete must be boolean')
                    if item['answer_complete'] and any(evidence[i]['kind'] != 'speech' for i in item['answer_evidence_ids']) and answer.get('source') != 'room_comment':
                        raise invalid('answered question requires speech or staff comment')
                    answer['answer_complete'] = item['answer_complete']
                if answer['end_ms'] < question['start_ms']:
                    raise invalid('invalid qa observations', 'answer_before_question', 'answer_evidence_ids')
                question['answers'].append(answer)
            elif reply or item.get('answer') or 'answer_complete' in item:
                raise invalid('invalid qa observations', 'answer_evidence_required', 'answer_evidence_ids')
            applies = item.get('applies_to', [])
            if (not isinstance(applies,list) or len(applies)>7 or any(not isinstance(k,str) for k in applies)
                    or len(set(applies))!=len(applies)):
                raise invalid('invalid qa observations', 'invalid_applies_to', 'applies_to')
            linked = []
            compatible=applies_to_ids(question,list(known.values()),product)
            for target_index,target_id in enumerate(applies):
                target = known.get(target_id)
                if not target or target_id in seen:
                    error=invalid('qa reply requires known question', 'unknown_or_duplicate_target', f'applies_to[{target_index}]')
                    error.allowed_qa_ids=[key for key in compatible if key not in seen]
                    raise error
                if not question['answers'] or target_id not in compatible:
                    error=invalid('applies_to requires identical product, offer and question_detail; use separate reply_to rows for distinct scopes and verify each answer', 'answer_scope_mismatch', f'applies_to[{target_index}]')
                    error.allowed_qa_ids=[key for key in compatible if key not in seen]
                    raise error
                if any(a['end_ms'] < target['start_ms'] for a in question['answers']):
                    raise invalid('invalid qa observations', 'answer_before_question', f'applies_to[{target_index}]')
                linked.append({**copy.deepcopy(target),'answers':copy.deepcopy(question['answers'])})
                seen.add(target_id)
            result.append(question)
            result.extend(linked)
            known[question['id']] = question
        except (ValueError, TypeError, KeyError) as error:
            if errors is None:raise
            seen = previous_seen
            if not getattr(error,'field',None):error.field=f'qa_observations[{index}]'
            errors.append(error)
    return result


def markers(questions):
    result = []
    for question in questions:
        result.append({'id': question['id'], 'kind': 'question', 'start_ms': question['start_ms'],
                       'end_ms': question['end_ms'], 'text': question['question']})
        for answer in question['answers']:
            result.append({'id': question['id'] + ':' + str(answer['segment_id']), 'kind': 'answer',
                           'start_ms': answer['start_ms'], 'end_ms': answer['end_ms'],
                           'text': answer['text'], 'question': question['question']})
    return result

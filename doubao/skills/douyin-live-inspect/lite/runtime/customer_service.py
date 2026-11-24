"""Customer-service reference projected from evidenced product statements and questions."""
from runtime.report_data import public_text

LABELS = {'price':'价格与优惠', 'package':'规格与到手内容', 'gift':'赠品与换购条件',
          'usage':'适用范围', 'fulfillment':'发货', 'after_sales':'售后'}


def normalize_facts(value, evidence, viewed):
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError('invalid service facts')
    result = []
    for fact in value:
        if not isinstance(fact, dict) or fact.get('kind') not in LABELS:
            raise ValueError('invalid service fact kind')
        text, ids = fact.get('text'), fact.get('evidence_ids')
        if (not isinstance(text, str) or not text.strip() or len(text) > 800 or
                not isinstance(ids, list) or not ids or
                any(not isinstance(i, str) or i not in evidence for i in ids) or len(set(ids)) != len(ids)):
            raise ValueError('service facts require text and actual evidence IDs')
        if any(evidence[i]['kind'] == 'image' and i not in viewed for i in ids):
            raise ValueError('service fact image must be viewed')
        items = [evidence[i] for i in ids]
        result.append({'kind':fact['kind'], 'text':public_text(text), 'evidence_ids':ids,
                       'start_ms':min(e.get('start_ms', e.get('time_ms', 0)) for e in items),
                       'end_ms':max(e.get('end_ms', e.get('time_ms', 0)) for e in items),
                       'quote':' / '.join(public_text(e['text']) for e in items if e['kind'] == 'speech')})
    return result


def build(segments, questions, room):
    cards = {}
    for segment in sorted(segments, key=lambda s:(s['start_ms'], s['id'])):
        observation = (segment.get('review_result') or {}).get('sales_observation') or {}
        if segment.get('review_status') != 'done' or not observation.get('product_id'):
            continue
        # Different offers are separate cards: never carry a gift/price into a new offer.
        key = observation['product_id']
        card = cards.setdefault(key, {'product':public_text(observation['product']),
            'offer':public_text(observation.get('offer', '')), 'facts':[], 'start_ms':segment['start_ms'],
            'end_ms':segment['end_ms']})
        card['end_ms'] = segment['end_ms']
        card['facts'].extend({**f, 'segment_id':segment['id'], 'label':LABELS[f['kind']]}
                             for f in observation.get('service_facts', []))
    for card in cards.values():
        # Keep all evidence for changed wording; do not silently declare the latest promise correct.
        card['facts'] = list({(f['kind'], f['text']):f
                             for f in card['facts']}.values())
        card['unrecorded'] = [label for kind,label in LABELS.items()
                              if not any(f['kind'] == kind for f in card['facts'])]
    groups = {}
    for q in questions:
        if q.get('source') != 'viewer_comment':
            continue
        # Only model-linked similar questions, and only when their explicit scope matches.
        key = (q.get('group_id', q['id']) if q.get('product') and q.get('offer') else q['id'],
               q.get('product', ''), q.get('offer', ''))
        group = groups.setdefault(key, {'question':public_text(q.get('group_question', q['question'])),
            'product':public_text(q.get('product', '')), 'offer':public_text(q.get('offer', '')),
            'questions':[], 'answers':[], 'start_ms':q['start_ms'], 'end_ms':q['end_ms']})
        group['questions'].append({'id':q['id'], 'evidence_ids':q['evidence_ids'],
                                  'source':'viewer_comment',
                                  **{k:q[k] for k in ('author_id','author_nickname','author_role') if k in q},
                                  'text':q['question'], 'start_ms':q['start_ms'], 'end_ms':q['end_ms']})
        group['end_ms'] = max(group['end_ms'], q['end_ms'])
        group['answers'].extend(q.get('answers', []))
    from runtime.interactions import questioner_counts
    for group in groups.values():
        group.update(questioner_counts(group['questions']))
        # Multiple extracted questions from the same comment count as one observation in this topic.
        group['count'] = len({i for q in group['questions'] for i in q['evidence_ids']})
        group['answers'] = list({(a['segment_id'], tuple(a['evidence_ids'])):a for a in group['answers']}.values())
        group['answer_status'] = ('recorded' if any(a.get('answer_complete') is True for a in group['answers'])
                                  else 'partial' if group['answers'] else 'unrecorded')
        group['action'] = ('客服核对适用条件后复用回答；重复问题可补入商品页或置顶说明。'
                           if group['answer_status'] == 'recorded' else
                           '交客服或运营核实口径；必要时更新商品页或置顶说明，不要求主播逐条补答。')
    topics = sorted(groups.values(), key=lambda g:(-g['count'], g['start_ms']))
    for topic in topics:
        topic['question_total'] = len(topic['questions'])
        topic['answer_total'] = len(topic['answers'])
        topic['questions'] = topic['questions'][:5]
        topic['answers'] = topic['answers'][-3:]
    return {'products':list(cards.values()), 'topic_total':len(topics), 'topics':topics[:20],
            'comment_status':room.get('status', 'not_collected'),
            'scope':'仅按本次范围内采集并识别的评论计数，不代表全场人数或需求比例；未记录公开回答不等于客服未处理。',
            'notice':'以下为直播中记录的口径，未经商家或交易系统核验。按商品套餐分别展示，时间不同的说法需核对；未提取到不等于未讲或不提供。'}

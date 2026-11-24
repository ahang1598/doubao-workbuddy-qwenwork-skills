"""Evidence-bound product observations; counters are derived from saved segments."""
import copy
import hashlib
import json


def enabled(task):
    return task.get('kind', 'live') == 'live' and (
        task.get('scenario') in {'电商', '汽车', '生活服务'}
        or bool(set(task.get('loaded_rule_bundles', [])) & {'ecommerce', 'automotive', 'life_service'}))


def template():
    return {'change': 'unknown', 'scene': '', 'product': '', 'product_id': '', 'offer': '', 'summary': '', 'evidence_ids': [], 'service_facts': []}


INSTRUCTION = (
    'service_facts 为客服参考口径：仅摘录本段明确归属当前主商品套餐的事实，格式 {kind,text,evidence_ids}；kind 为 price（价格及优惠条件）、package（规格与到手内容）、gift（赠品/换购及领取条件）、usage（适用范围与限制）、fulfillment（发货）、after_sales（售后）。'
    'text 保留对象、否定和必要条件，不补造价格、权益或客服承诺；原话不清、商品归属不明则不提取，不把赠品属性记为主商品属性。未提到的类别留空，不表示主播未讲或商家不提供；不把这些口播当作已验证的经营事实。'
    'sales_observation 只记事实，不计数：首次或主推商品切换填 change=switch、product（品牌+品名/型号）、offer（规格/套餐及已知活动条件）并引用本段证据；'
    '同商品填 same，product 复用历史名称，以便前段尚未保存时独立识别；套餐/价格/活动变化时填写新的完整 offer，否则留空沿用。换回旧商品复用 sales_context.products 中的名称。'
    '识别前先核对 sales_context.current 和 products，以及同批此前已识别的商品。已有商品填写其 product_id 并原样复用 product，不因简称、规格补充或省略而重新命名；新商品 product_id 留空。'
    '例如历史“不粘煎锅（26厘米）”，本段只说“不粘煎锅”且没有换款证据，仍是历史商品，沿用原名称和 product_id；反向补充26厘米也不改原商品名，规格写入 offer。'
    '品牌、型号或明确不同规格不可仅凭品类相同合并；只有明确换品才切换，商品不确定时默认沿用最近确认的商品名。切回旧商品仍须有本段证据；历史价格和活动条件不可当作本段新事实。'
    'summary 用100字以内概括本轮商品介绍的要点，不逐句复述；同商品有新要点时结合已有摘要更新，无变化留空沿用，切换商品重新概括。'
    '没有历史商品且无法确认填 unknown；已有历史商品时 unknown 也会默认沿用最近确认的商品，不新增事实。明确未主推商品填 none。闲聊时填 change=none、scene=chat，并引用本段证据，只标记闲聊，不摘录闲聊主题或摘要；其他非商品内容 scene=other。商品段 scene 留空。背景陈列、赠品、竞品提及不算切换。'
    '不再提取催单记录，省略 claims；旧模板有 claims 时填 []。同批按时间填写；没有已确认的当前商品不能填 same。'
)


def identity(product, offer):
    return hashlib.sha256(json.dumps([product, offer], ensure_ascii=False).encode()).hexdigest()[:16]


def current(segment):
    if not segment or segment.get('review_status') != 'done':
        return None
    observation = (segment.get('review_result') or {}).get('sales_observation')
    if not observation or observation.get('change') in {'unknown', 'none'}:
        return None
    return {k: copy.deepcopy(observation.get(k, '')) for k in ('product', 'offer', 'product_id', 'summary')}


def short_summary(text):
    from runtime.report_data import public_text
    text = ' '.join(public_text(text).split())
    return text if len(text) <= 100 else text[:99] + '…'


def context(segments, before_ms):
    previous = sorted((s for s in segments if s['end_ms'] <= before_ms), key=lambda s: (s['start_ms'], s['id']))
    products = {}
    for segment in previous:
        item = current(segment)
        if item:
            products.pop(item['product'], None)
            products[item['product']] = item
    return {'current': next(reversed(products.values()), None),
            'products': list(products.values())}


def normalize(value, segment, viewed, base, products=()):
    if not isinstance(value, dict) or value.get('change') not in {'same', 'switch', 'unknown', 'none'}:
        raise ValueError('sales observation requires change=same/switch/unknown/none')
    evidence = {x['id']: dict(x, kind='speech') for x in segment.get('subtitles', [])}
    evidence.update({x['id']: dict(x, kind='image') for x in segment.get('frames', [])})

    def refs(ids, required=False):
        if (not isinstance(ids, list) or any(not isinstance(i, str) or i not in evidence for i in ids)
                or len(set(ids)) != len(ids) or (required and not ids)):
            raise ValueError('sales observation requires actual evidence IDs')
        if any(evidence[i]['kind'] == 'image' and i not in viewed for i in ids):
            raise ValueError('sales observation image must be viewed')
        return ids

    change = value['change']
    scene = value.get('scene', '')
    if scene not in {'', 'chat', 'other'} or (scene and change != 'none'):
        raise ValueError('sales scene requires none with chat/other')
    product, offer = value.get('product', ''), value.get('offer', '')
    if any(not isinstance(s, str) or len(s) > 240 for s in (product, offer)):
        raise ValueError('sales product/offer must be short text')
    product, offer = product.strip(), offer.strip()
    product_id = value.get('product_id') or ''
    if not isinstance(product_id, str):
        raise ValueError('sales product_id must reference a historical product')
    reused = next((p for p in ([base] if base else []) + list(products)
                   if p.get('product_id') == product_id), None) if product_id else None
    if product_id and (not reused or change not in {'same', 'switch'}):
        raise ValueError('sales product_id must reference a historical product')
    if reused:
        product = reused['product']
    summary = short_summary(value.get('summary', '')) if isinstance(value.get('summary', ''), str) else ''
    ids = refs(value.get('evidence_ids', []), change == 'switch' or bool(offer) or scene == 'chat')
    if change == 'unknown' and base:
        # Carry identity only; an uncertain observation supplies no new sales facts.
        return {**template(), **copy.deepcopy(base), 'change': 'same', 'claims': []}
    if change == 'same':
        if not base or (reused and reused['product'] != base['product']):
            raise ValueError('sales same requires a confirmed previous product; use switch or unknown')
        product, offer = base['product'], offer or base['offer']
        summary = summary or base.get('summary', '')
    elif change == 'switch':
        if not product:
            raise ValueError('sales switch requires product')
    else:
        summary = ''
        if product or offer:
            raise ValueError('unknown/none sales observation cannot assign a product')
    claims = value.get('claims', [])
    if not isinstance(claims, list) or len(claims) > 30 or (change == 'none' and claims):
        raise ValueError('invalid sales claims')
    events = []
    for claim in claims:
        if not isinstance(claim, dict) or claim.get('kind') not in {'last_round', 'countdown', 'stock', 'adjustment'}:
            raise ValueError('invalid sales claim kind')
        claim_ids = refs(claim.get('evidence_ids'), True)
        number = claim.get('value')
        if number is not None and (type(number) is not int or not 0 <= number <= 1000000
                                   or claim['kind'] not in {'stock', 'countdown'}):
            raise ValueError('sales claim value must be a nonnegative count/seconds or null')
        subject = claim.get('subject', '').strip() if isinstance(claim.get('subject', ''), str) else None
        if subject is None or len(subject) > 120 or (claim['kind'] == 'stock' and not subject):
            raise ValueError('sales stock requires subject (product/gift/redemption quota)')
        items = sorted((evidence[i] for i in claim_ids), key=lambda e: e.get('start_ms', e.get('time_ms', 0)))
        start = min(e.get('start_ms', e.get('time_ms', segment['start_ms'])) for e in items)
        end = max(e.get('end_ms', e.get('time_ms', start)) for e in items)
        description = claim.get('description', '')
        if not isinstance(description, str) or len(description) > 500:
            raise ValueError('invalid sales image description')
        if any(e['kind'] == 'image' for e in items) and not description.strip():
            raise ValueError('sales image claim requires description')
        text = ' / '.join(e['text'] for e in items if e['kind'] == 'speech')
        if description.strip():
            text += (' / ' if text else '') + description.strip()
        events.append({'kind': claim['kind'], 'subject': subject, 'value': number, 'evidence_ids': claim_ids,
                       'start_ms': start, 'end_ms': end, 'text': text})
    from runtime.customer_service import normalize_facts
    facts = normalize_facts(value.get('service_facts', []), evidence, viewed)
    if facts and change not in {'same', 'switch'}:
        raise ValueError('service facts require a confirmed product')
    return {'change': change, 'scene': scene, 'product': product, 'offer': offer, 'summary': summary, 'service_facts': facts,
            'product_id': identity(product, offer) if product else None,
            'evidence_ids': ids, 'claims': events}


def summarize(segments, *, findings=(), questions=(), end_ms=None, include_timeline=True):
    from runtime.report_data import public_text
    groups, unknown, observed = {}, [], 0
    ordered = sorted(segments, key=lambda s: (s['start_ms'], s['id']))
    for segment in ordered:
        observation = (segment.get('review_result') or {}).get('sales_observation')
        if segment.get('review_status') != 'done' or not observation:
            continue
        observed += 1
        # Unknown package/offer must not accumulate unrelated promotion claims.
        known = observation.get('product_id') and observation.get('offer')
        group = None
        if known:
            key = observation['product_id']
            group = groups.setdefault(key, {'product_id': key, 'product': public_text(observation['product']),
                'offer': public_text(observation['offer']), 'events': []})
        for event in observation['claims']:
            row = {**event, 'segment_id': segment['id'], 'text': public_text(event['text']), 'subject': public_text(event.get('subject', ''))}
            (group['events'] if group is not None else unknown).append(row)
    for group in groups.values():
        # A retry or duplicated evidence cannot inflate counts.
        unique = {(e['kind'], e['start_ms'], e['end_ms'], e.get('subject', ''), e['text']): e for e in group['events']}
        group['events'] = sorted(unique.values(), key=lambda e: (e['start_ms'], e['end_ms']))
        last = {}
        resets = []
        for event in group['events']:
            kind, number = event['kind'], event['value']
            if kind == 'adjustment':
                subject = event.get('subject', '')
                last = {key: value for key, value in last.items() if key[1] != subject} if subject else {}
                continue
            key = (kind, event.get('subject', ''))
            previous = last.get(key)
            if (previous and number is not None and previous['value'] is not None
                    and event['start_ms'] >= previous['end_ms']
                    and event['start_ms'] > previous['start_ms']):
                reset = (kind == 'stock' and number > previous['value']) or (
                    kind == 'countdown' and event['start_ms'] + number * 1000 >
                    previous['start_ms'] + previous['value'] * 1000 + 5000)
                if reset:
                    resets.append({'kind': kind, 'before': previous, 'after': event})
            if kind in {'stock', 'countdown'}:
                last[key] = event
        group.update(mention_count=sum(e['kind'] != 'adjustment' for e in group['events']),
                     last_round_count=sum(e['kind'] == 'last_round' for e in group['events']),
                     adjustment_count=sum(e['kind'] == 'adjustment' for e in group['events']),
                     reset_count=len(resets), resets=resets)
        frequent = len({e['segment_id'] for e in group['events'] if e['kind'] != 'adjustment'}) >= 3
        group['status'] = 'warning' if resets else 'observe'
        group['reason'] = ('已识别商品套餐，尚未记录催单。' if not group['mention_count'] else
                           '同一商品套餐的倒计时或名额疑似重置，尚需核实实际活动及解释；不计入确认风险。' if resets else
                           '多个片段反复催单，仅提示关注；重复次数不证明活动虚假。' if frequent else
                           '已记录催单事实，未发现可确认的重置。')
    latest = next((s for s in reversed(ordered) if s.get('review_status') == 'done'
                   and (s.get('review_result') or {}).get('sales_observation')), None)
    active = current(latest)
    if active:
        active = {k: public_text(v) for k, v in active.items()}
    warnings = [
        {'id': f"sales-{group['product_id']}-{index}", 'status': 'warning',
         'rule_name': '疑似催单重置', 'start_ms': reset['after']['start_ms'],
         'end_ms': reset['after']['end_ms'], 'text': reset['after']['text'],
         'reason': group['reason'], 'previous_start_ms': reset['before']['start_ms'],
         'previous_text': reset['before']['text']}
        for group in groups.values() for index, reset in enumerate(group['resets'])]
    claims = [event for group in groups.values() for event in group['events']] + unknown
    from runtime.interactions import markers as qa_markers
    return {'observed_segments': observed, 'current': active, 'current_at_ms': latest['end_ms'] if latest else None,
            'groups': list(groups.values()), 'unassigned_events': unknown,
            'timeline': product_timeline(ordered, claims, list(findings) + warnings, interactions=qa_markers(questions), end_ms=end_ms) if include_timeline else []}


def product_timeline(segments, claims, findings, *, interactions=(), end_ms=None):
    """Build display periods from observations, including the unlabelled opening."""
    from runtime.report_data import public_text
    end = max([s['end_ms'] for s in segments] + [end_ms or 0])
    if end <= 0:
        return []
    boundaries = {0: [], end: []}
    for segment in segments:
        start, stop = max(0, segment['start_ms']), min(end, segment['end_ms'])
        if stop <= start:
            continue
        boundaries.setdefault(start, []).append((True, segment))
        boundaries.setdefault(stop, []).append((False, segment))
    rows, active = [], {}
    opening = True
    times = sorted(boundaries)
    for index, start in enumerate(times[:-1]):
        for entering, segment in boundaries[start]:
            if entering:
                active[segment['id']] = segment
            else:
                active.pop(segment['id'], None)
        stop = times[index + 1]
        observations = [current(s) for s in active.values()]
        known = bool(observations) and all(observations) and len({o['product'] for o in observations}) == 1
        none = bool(active) and all(s.get('review_status') == 'done' and
            (s.get('review_result') or {}).get('sales_observation', {}).get('change') == 'none' for s in active.values())
        item = dict(observations[0]) if known else {}
        if known and len({o['product_id'] for o in observations}) > 1:
            item.update(product_id=None, offer='')
        status = 'known' if known else 'none' if none else 'unknown'
        scene = ('chat' if none and all((s.get('review_result') or {}).get('sales_observation', {}).get('scene') == 'chat'
                                       for s in active.values()) else '')
        reason = ('' if known else '明确未主推商品' if none else '未采集或无片段记录' if not active else
                  '片段尚未完成审核' if any(s.get('review_status') != 'done' for s in active.values()) else
                  '未记录商品识别' if any(not (s.get('review_result') or {}).get('sales_observation') for s in active.values()) else
                  '商品归属待确认')
        row = {'start_ms': start, 'end_ms': stop, 'status': status, 'scene': scene,
               'product_id': item.get('product_id'), 'product': public_text(item.get('product', '')),
               'offer': public_text(item.get('offer', '')), 'reason': reason,
               'segment_ids': list(active), 'claims': [], 'risks': [], 'interactions': []}
        # The recording clock starts before the first segment. Once its product
        # is known, fold the opening offset and contiguous unlabelled intro into it.
        if opening and known and rows:
            row['start_ms'] = 0
            row['segment_ids'] = list(dict.fromkeys(
                sid for period in [*rows, row] for sid in period['segment_ids']))
            rows.clear()
        if opening:
            opening = status == 'unknown' and (
                (not active and start == 0) or
                (len(active) == 1 and next(iter(active.values())).get('review_status') not in {'skipped','failed'}))
        # Timeline follows products; promotion counters still use product+offer.
        if rows and all(rows[-1][key] == row[key] for key in ('status', 'scene', 'product', 'reason')):
            if rows[-1]['product_id'] != row['product_id']:
                rows[-1].update(product_id=None, offer='')
            rows[-1]['end_ms'] = stop
            rows[-1]['segment_ids'] = list(dict.fromkeys(rows[-1]['segment_ids'] + row['segment_ids']))
        else:
            rows.append(row)
    ordered_segments = sorted(segments, key=lambda s: (s['start_ms'], s['id']))
    for row in rows:
        summaries, product_summary = [], ''
        for segment in ordered_segments:
            if row['status'] != 'known' or segment['id'] not in row['segment_ids'] or not current(segment):
                continue
            review = segment.get('review_result') or {}
            product_summary = (review.get('sales_observation') or {}).get('summary') or product_summary
            summary = short_summary(review.get('summary', ''))
            if summary and summary not in {'已核验', '未命中', '无风险'} and summary not in summaries:
                summaries.append(summary)
        row['summary'] = short_summary(product_summary or '；'.join(summaries))
    # Existing judgments keep their own IDs and grading. Association is temporal, not attribution.
    for field, events in (('claims', claims), ('risks', findings), ('interactions', interactions)):
        for row in rows:
            seen = set()
            for event in events:
                start, stop = event['start_ms'], event['end_ms']
                overlaps = (start < row['end_ms'] and stop > row['start_ms']) if stop > start else row['start_ms'] <= start < row['end_ms']
                if not overlaps:
                    continue
                key = event.get('id') or (event.get('kind'), start, stop, event.get('subject'), event.get('text'))
                if key in seen:
                    continue
                seen.add(key)
                row[field].append({key: public_text(value) if isinstance(value, str) else value for key, value in event.items()})
            row[field].sort(key=lambda event: (event['start_ms'], event['end_ms']))
    return rows

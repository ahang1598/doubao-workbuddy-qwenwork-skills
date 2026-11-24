#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import math
import re
import sys


class ValidationError(ValueError):
    pass


def _write_json(payload):
    text = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(',', ':'),
    )
    sys.stdout.write(text + '\n')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f'duplicate JSON key: {key!r}')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValidationError(f'invalid JSON numeric constant: {value}')


def _check_keys(value, required, optional, path):
    if type(value) is not dict:
        raise ValidationError(f'{path} must be an object')
    keys = set(value)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - optional)
    if missing:
        raise ValidationError(f'{path} missing required fields: {missing}')
    if unknown:
        raise ValidationError(f'{path} has unknown fields: {unknown}')


def _parse_timestamp(value, path):
    if type(value) is not str or not value or value != value.strip():
        raise ValidationError(
            f'{path} must be a non-empty timezone-aware ISO8601 string'
        )
    if re.search(r'-00(?::?00(?::?00(?:[.,]\d+)?)?)?$', value):
        raise ValidationError(f'{path} uses an ambiguous unknown UTC offset')

    normalized = value
    if value.endswith(('Z', 'z')):
        normalized = value[:-1] + '+00:00'
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(f'{path} is not a valid ISO8601 timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f'{path} must include an explicit UTC offset')
    return parsed.astimezone(dt.timezone.utc)


def _parse_aware(value, path):
    utc = _parse_timestamp(value, path)
    raw = value
    if raw.endswith(('Z', 'z')):
        raw = raw[:-1] + '+00:00'
    return utc, dt.datetime.fromisoformat(raw)


def _local_date(value):
    return value.date()


def _positive_number(value, path):
    if type(value) not in (int, float):
        raise ValidationError(f'{path} must be a number, not a boolean or string')
    try:
        numeric = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f'{path} must be finite') from exc
    if not math.isfinite(numeric):
        raise ValidationError(f'{path} must be finite')
    if numeric <= 0:
        raise ValidationError(f'{path} must be positive')
    return numeric


def _finite_number(value, path):
    if type(value) not in (int, float):
        raise ValidationError(f'{path} must be a number, not a boolean or string')
    try:
        numeric = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f'{path} must be finite') from exc
    if not math.isfinite(numeric):
        raise ValidationError(f'{path} must be finite')
    return numeric


def _count(value, path):
    if type(value) is not int:
        raise ValidationError(f'{path} must be a nonnegative integer')
    if value < 0:
        raise ValidationError(f'{path} must be a nonnegative integer')
    return value


def _nonempty_str(value, path):
    if type(value) is not str or not value or value != value.strip():
        raise ValidationError(
            f'{path} must be a non-empty string without surrounding whitespace'
        )
    return value


def _bool(value, path):
    if type(value) is not bool:
        raise ValidationError(f'{path} must be a boolean')
    return value


def _string_array(value, path, *, allow_empty=True):
    if type(value) is not list:
        raise ValidationError(f'{path} must be an array')
    if not allow_empty and not value:
        raise ValidationError(f'{path} must not be empty')
    result = []
    seen = set()
    for index, item in enumerate(value):
        text = _nonempty_str(item, f'{path}[{index}]')
        if text in seen:
            raise ValidationError(f'{path}[{index}] duplicates {text!r}')
        seen.add(text)
        result.append(text)
    return result


def _fold(text):
    return ''.join(char.casefold() for char in text if not char.isspace())


def _contains_alias(haystack, alias):
    folded_alias = _fold(alias)
    return bool(folded_alias) and folded_alias in _fold(haystack)


def _validate_query_requirements(items, path):
    if type(items) is not list:
        raise ValidationError(f'{path} must be an array')
    seen = set()
    for index, item in enumerate(items):
        item_path = f'{path}[{index}]'
        status_probe = item.get('status') if type(item) is dict else None
        optional = set() if status_probe == 'present' else {'missing'}
        _check_keys(item, {'name', 'status'}, optional, item_path)
        name = _nonempty_str(item['name'], f'{item_path}.name')
        if name in seen:
            raise ValidationError(f'{item_path}.name duplicates {name!r}')
        seen.add(name)
        status = _nonempty_str(item['status'], f'{item_path}.status')
        if status not in {'present', 'unknown', 'missing'}:
            raise ValidationError(
                f'{item_path}.status must be present, unknown, or missing'
            )
        if status == 'present':
            if 'missing' in item:
                raise ValidationError(
                    f'{item_path}.missing must be omitted when status is present'
                )
        else:
            _nonempty_str(item.get('missing'), f'{item_path}.missing')


def _validate_clues(items, path):
    if type(items) is not list:
        raise ValidationError(f'{path} must be an array')
    seen = set()
    for index, item in enumerate(items):
        item_path = f'{path}[{index}]'
        _check_keys(item, {'id', 'horizon', 'horizon_source'}, set(), item_path)
        clue_id = _nonempty_str(item['id'], f'{item_path}.id')
        if clue_id in seen:
            raise ValidationError(f'{item_path}.id duplicates {clue_id!r}')
        seen.add(clue_id)
        horizon = _nonempty_str(item['horizon'], f'{item_path}.horizon')
        if horizon not in {
            'intraday',
            'multi_day',
            'multi_week',
            'quarter',
            'unknown',
        }:
            raise ValidationError(f'{item_path}.horizon is not an allowed scale')
        source = _nonempty_str(
            item['horizon_source'], f'{item_path}.horizon_source'
        )
        if source not in {'material', 'user_window', 'none'}:
            raise ValidationError(
                f'{item_path}.horizon_source is not an allowed source'
            )
        if horizon == 'unknown' and source != 'none':
            raise ValidationError(
                f'{item_path}.horizon_source must be none when horizon is unknown'
            )
        if horizon != 'unknown' and source == 'none':
            raise ValidationError(
                f'{item_path}.horizon_source cannot be none when a scale is asserted'
            )


def _validate_session_gap(value, path, as_of):
    if value is None:
        return
    applicable_probe = value.get('applicable') if type(value) is dict else None
    if applicable_probe is False:
        _check_keys(value, {'applicable', 'skip_reason'}, set(), path)
        _bool(value['applicable'], f'{path}.applicable')
        _nonempty_str(value['skip_reason'], f'{path}.skip_reason')
        return
    _check_keys(
        value,
        {'applicable', 'last_close_at', 'gap_kind', 'items'},
        {'no_new_information'},
        path,
    )
    if not _bool(value['applicable'], f'{path}.applicable'):
        raise ValidationError(f'{path}.applicable must be true in this branch')
    last_close, last_close_local = _parse_aware(
        value['last_close_at'], f'{path}.last_close_at'
    )
    if last_close >= as_of:
        raise ValidationError(f'{path}.last_close_at must be earlier than as_of')
    gap_kind = _nonempty_str(value['gap_kind'], f'{path}.gap_kind')
    if gap_kind not in {'cross_day', 'closed_session'}:
        raise ValidationError(f'{path}.gap_kind must be cross_day or closed_session')
    as_of_local = as_of.astimezone(last_close_local.tzinfo)
    if gap_kind == 'cross_day' and _local_date(last_close_local) == _local_date(
        as_of_local
    ):
        raise ValidationError(
            f'{path}.gap_kind=cross_day requires last_close_at and as_of on different dates'
        )
    no_new = False
    if 'no_new_information' in value:
        no_new = _bool(value['no_new_information'], f'{path}.no_new_information')
    items = value.get('items')
    if type(items) is not list:
        raise ValidationError(f'{path}.items must be an array')
    if no_new and items:
        raise ValidationError(
            f'{path}.items must be empty when no_new_information is true'
        )
    if not no_new and not items:
        raise ValidationError(
            f'{path}.items must be non-empty unless no_new_information is true'
        )
    for index, item in enumerate(items):
        item_path = f'{path}.items[{index}]'
        _check_keys(
            item,
            {'info', 'first_visible_at', 'status', 'priced_in'},
            {'expectation_evidence'},
            item_path,
        )
        _nonempty_str(item['info'], f'{item_path}.info')
        visible = item['first_visible_at']
        if visible == 'unknown':
            parsed_visible = None
        else:
            parsed_visible = _parse_timestamp(visible, f'{item_path}.first_visible_at')
            if parsed_visible <= last_close:
                raise ValidationError(
                    f'{item_path}.first_visible_at must be after last_close_at'
                )
            if parsed_visible > as_of:
                raise ValidationError(
                    f'{item_path}.first_visible_at must not be after as_of'
                )
        _nonempty_str(item['status'], f'{item_path}.status')
        priced = _nonempty_str(item['priced_in'], f'{item_path}.priced_in')
        if priced not in {'yes', 'no', 'unknown'}:
            raise ValidationError(
                f'{item_path}.priced_in must be yes, no, or unknown'
            )
        if priced == 'yes':
            if parsed_visible is None:
                raise ValidationError(
                    f'{item_path}.priced_in cannot be yes when first_visible_at is unknown'
                )
            if item.get('expectation_evidence') is not True:
                raise ValidationError(
                    f'{item_path}.expectation_evidence must be true '
                    'before priced_in can be yes'
                )
        elif 'expectation_evidence' in item and type(
            item['expectation_evidence']
        ) is not bool:
            raise ValidationError(
                f'{item_path}.expectation_evidence must be a boolean'
            )


def _validate_metrics(items, path):
    if type(items) is not list:
        raise ValidationError(f'{path} must be an array')
    seen = set()
    aliases = []
    has_mainline = False
    for index, item in enumerate(items):
        item_path = f'{path}[{index}]'
        _check_keys(
            item,
            {'name', 'formula', 'unit', 'forbidden_aliases', 'role'},
            set(),
            item_path,
        )
        name = _nonempty_str(item['name'], f'{item_path}.name')
        if name in seen:
            raise ValidationError(f'{item_path}.name duplicates {name!r}')
        seen.add(name)
        _nonempty_str(item['formula'], f'{item_path}.formula')
        _nonempty_str(item['unit'], f'{item_path}.unit')
        role = _nonempty_str(item['role'], f'{item_path}.role')
        if role not in {'mainline', 'supplemental'}:
            raise ValidationError(
                f'{item_path}.role must be mainline or supplemental'
            )
        if role == 'mainline':
            has_mainline = True
        forbidden = _string_array(
            item['forbidden_aliases'],
            f'{item_path}.forbidden_aliases',
            allow_empty=False,
        )
        aliases.extend(forbidden)
    if items and not has_mainline:
        raise ValidationError(f'{path} must include at least one mainline metric')
    return aliases


def _reject_forbidden(text, aliases, path):
    for alias in aliases:
        if _contains_alias(text, alias):
            raise ValidationError(f'{path} contains forbidden alias {alias!r}')


def _validate_artifacts(items, path):
    if type(items) is not list:
        raise ValidationError(f'{path} must be an array')
    digest = re.compile(r'^[0-9a-f]{64}$')
    opened = []
    for index, item in enumerate(items):
        item_path = f'{path}[{index}]'
        _check_keys(
            item,
            {'name', 'text', 'sha256', 'accepted_rows', 'summary_claims'},
            set(),
            item_path,
        )
        _nonempty_str(item['name'], f'{item_path}.name')
        text = item['text']
        if type(text) is not str or not text:
            raise ValidationError(f'{item_path}.text must be the reopened file contents')
        sha256 = _nonempty_str(item['sha256'], f'{item_path}.sha256')
        if digest.fullmatch(sha256) is None:
            raise ValidationError(f'{item_path}.sha256 must be 64 lowercase hex digits')
        actual = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if actual != sha256:
            raise ValidationError(
                f'{item_path}.sha256 does not match sha256 of text'
            )
        rows = item['accepted_rows']
        if type(rows) is not list or not rows:
            raise ValidationError(f'{item_path}.accepted_rows must be a non-empty string array')
        for row_index, row in enumerate(rows):
            row_text = _nonempty_str(row, f'{item_path}.accepted_rows[{row_index}]')
            if row_text not in text:
                raise ValidationError(
                    f'{item_path}.accepted_rows[{row_index}] is not in reopened text'
                )
        claims = item['summary_claims']
        if type(claims) is not list:
            raise ValidationError(f'{item_path}.summary_claims must be an array')
        for claim_index, claim in enumerate(claims):
            claim_text = _nonempty_str(
                claim, f'{item_path}.summary_claims[{claim_index}]'
            )
            if claim_text not in text:
                raise ValidationError(
                    f'{item_path}.summary_claims[{claim_index}] is not in reopened text'
                )
        opened.append({'text': text, 'rows': rows})
    return opened


def _validate_ranking(value, path, artifacts):
    if value is None:
        return []
    possible_probe = value.get('possible') if type(value) is dict else None
    if possible_probe is False:
        _check_keys(value, {'possible', 'items'}, set(), path)
        _bool(value['possible'], f'{path}.possible')
        items = value['items']
        if items != []:
            raise ValidationError(f'{path}.items must be an empty array when ranking is not possible')
        return []
    _check_keys(value, {'possible', 'order', 'source_rows', 'items'}, set(), path)
    if not _bool(value['possible'], f'{path}.possible'):
        raise ValidationError(f'{path}.possible must be true in this branch')
    order = _nonempty_str(value['order'], f'{path}.order')
    if order not in {'asc', 'desc'}:
        raise ValidationError(f'{path}.order must be asc or desc')
    rows = value['source_rows']
    if type(rows) is not list or not rows:
        raise ValidationError(f'{path}.source_rows must be a non-empty array')
    parsed_rows = []
    for index, row in enumerate(rows):
        row_path = f'{path}.source_rows[{index}]'
        _check_keys(row, {'key', 'sort_value', 'display'}, set(), row_path)
        key = _nonempty_str(row['key'], f'{row_path}.key')
        display = _nonempty_str(row['display'], f'{row_path}.display')
        sort_value = _finite_number(row['sort_value'], f'{row_path}.sort_value')
        if key not in display:
            raise ValidationError(f'{row_path}.key must appear in display')
        if index > 0:
            previous = parsed_rows[index - 1]['sort_value']
            if order == 'desc' and sort_value > previous:
                raise ValidationError(
                    f'{row_path}.sort_value breaks descending source_rows order'
                )
            if order == 'asc' and sort_value < previous:
                raise ValidationError(
                    f'{row_path}.sort_value breaks ascending source_rows order'
                )
        parsed_rows.append({'key': key, 'sort_value': sort_value, 'display': display})
    items = value['items']
    if type(items) is not list or not items:
        raise ValidationError(f'{path}.items must be a non-empty array when ranking is possible')
    for index, item in enumerate(items):
        item_path = f'{path}.items[{index}]'
        _check_keys(
            item,
            {'label', 'claim_type', 'source', 'value', 'row_index', 'place'},
            {'artifact_index'},
            item_path,
        )
        _nonempty_str(item['label'], f'{item_path}.label')
        claim_type = _nonempty_str(item['claim_type'], f'{item_path}.claim_type')
        if claim_type not in {
            'leader',
            'laggard',
            'strongest',
            'weakest',
            'other',
        }:
            raise ValidationError(
                f'{item_path}.claim_type must be leader, laggard, strongest, weakest, or other'
            )
        source = _nonempty_str(item['source'], f'{item_path}.source')
        if source not in {'table', 'calculation', 'file'}:
            raise ValidationError(
                f'{item_path}.source must be table, calculation, or file'
            )
        rank_value = _nonempty_str(item['value'], f'{item_path}.value')
        if type(item['row_index']) is not int:
            raise ValidationError(f'{item_path}.row_index must be an integer')
        if type(item['place']) is not int or item['place'] < 1:
            raise ValidationError(f'{item_path}.place must be a positive integer')
        row_index = item['row_index']
        place = item['place']
        if row_index < 0 or row_index >= len(parsed_rows):
            raise ValidationError(f'{item_path}.row_index is out of range')
        if place != row_index + 1:
            raise ValidationError(
                f'{item_path}.place must equal row_index+1 in the declared order'
            )
        if claim_type in {'leader', 'strongest'} and place != 1:
            raise ValidationError(
                f'{item_path}.claim_type={claim_type} must bind to place 1'
            )
        if claim_type in {'laggard', 'weakest'} and place != len(parsed_rows):
            raise ValidationError(
                f'{item_path}.claim_type={claim_type} must bind to the last ordered row'
            )
        bound = parsed_rows[row_index]
        if rank_value not in bound['display'] and rank_value != bound['key']:
            raise ValidationError(
                f'{item_path}.value is not in the bound source row'
            )
        if source == 'file':
            if 'artifact_index' not in item:
                raise ValidationError(
                    f'{item_path}.artifact_index is required when source is file'
                )
            if type(item['artifact_index']) is not int:
                raise ValidationError(f'{item_path}.artifact_index must be an integer')
            artifact_index = item['artifact_index']
            if artifact_index < 0 or artifact_index >= len(artifacts):
                raise ValidationError(f'{item_path}.artifact_index is out of range')
            artifact = artifacts[artifact_index]
            if bound['display'] not in artifact['text']:
                raise ValidationError(
                    f'{item_path} bound row is not in the reopened artifact'
                )
        elif 'artifact_index' in item:
            raise ValidationError(
                f'{item_path}.artifact_index must be omitted unless source is file'
            )
    places = [item['place'] for item in items]
    rows = [item['row_index'] for item in items]
    if len(places) != len(set(places)):
        raise ValidationError(f'{path}.items place values must be unique')
    if len(rows) != len(set(rows)):
        raise ValidationError(f'{path}.items row_index values must be unique')
    if 1 not in places:
        raise ValidationError(f'{path}.items must include place 1 when ranking is possible')
    return [row['display'] for row in parsed_rows]


def _validate_delivery_contract(value, path, as_of):
    _check_keys(
        value,
        set(),
        {
            'query_requirements',
            'clues',
            'session_gap',
            'metrics',
            'mainline_text',
            'mainline_terms',
            'ranking',
            'artifacts',
        },
        path,
    )
    if 'query_requirements' in value:
        _validate_query_requirements(
            value['query_requirements'], f'{path}.query_requirements'
        )
    if 'clues' in value:
        _validate_clues(value['clues'], f'{path}.clues')
    if 'session_gap' in value:
        _validate_session_gap(value['session_gap'], f'{path}.session_gap', as_of)
    aliases = []
    if 'metrics' in value:
        aliases = _validate_metrics(value['metrics'], f'{path}.metrics')
        if value['metrics']:
            mainline_text = _nonempty_str(
                value.get('mainline_text'), f'{path}.mainline_text'
            )
            _reject_forbidden(mainline_text, aliases, f'{path}.mainline_text')
            for metric in value['metrics']:
                if metric['role'] == 'mainline' and not _contains_alias(
                    mainline_text, metric['name']
                ):
                    raise ValidationError(
                        f'{path}.mainline_text must cite mainline metric {metric["name"]!r}'
                    )
    elif 'mainline_text' in value:
        raise ValidationError(f'{path}.mainline_text requires metrics')
    if 'mainline_terms' in value:
        if not aliases:
            raise ValidationError(f'{path}.mainline_terms requires metrics')
        terms = _string_array(
            value['mainline_terms'], f'{path}.mainline_terms', allow_empty=False
        )
        for index, term in enumerate(terms):
            _reject_forbidden(term, aliases, f'{path}.mainline_terms[{index}]')
    artifacts = []
    if 'artifacts' in value:
        artifacts = _validate_artifacts(value['artifacts'], f'{path}.artifacts')
    displays = []
    if 'ranking' in value:
        displays = _validate_ranking(value['ranking'], f'{path}.ranking', artifacts)
    if displays and artifacts:
        for art_index, artifact in enumerate(value['artifacts']):
            for claim_index, claim in enumerate(artifact['summary_claims']):
                if not any(claim in display for display in displays):
                    raise ValidationError(
                        f'{path}.artifacts[{art_index}].summary_claims[{claim_index}] '
                        'is not bound to an accepted ranking row'
                    )
    return {**value, 'passed': True}


def _validate(payload):
    _check_keys(payload, {'as_of', 'observations'}, {'delivery_contract'}, 'input')
    as_of_text = payload['as_of']
    as_of = _parse_timestamp(as_of_text, 'as_of')

    observations = payload['observations']
    if type(observations) is not list:
        raise ValidationError('observations must be an array')

    seen_ids = {}
    output_observations = []

    for index, observation in enumerate(observations):
        path = f'observations[{index}]'
        _check_keys(
            observation,
            {'id', 'observed_at', 'available_at'},
            {'quote', 'breadth'},
            path,
        )

        observation_id = observation['id']
        if (
            type(observation_id) is not str
            or not observation_id
            or observation_id != observation_id.strip()
        ):
            raise ValidationError(
                f'{path}.id must be a non-empty string without surrounding whitespace'
            )
        if observation_id in seen_ids:
            first_index = seen_ids[observation_id]
            raise ValidationError(
                f'{path}.id duplicates observations[{first_index}].id: '
                f'{observation_id!r}'
            )
        seen_ids[observation_id] = index

        observed_at = _parse_timestamp(
            observation['observed_at'], f'{path}.observed_at'
        )
        available_at = _parse_timestamp(
            observation['available_at'], f'{path}.available_at'
        )

        quote_data = None
        quote = observation.get('quote')
        if quote is not None:
            _check_keys(quote, {'last', 'previous_close'}, set(), f'{path}.quote')
            quote_data = (
                _positive_number(quote['last'], f'{path}.quote.last'),
                _positive_number(
                    quote['previous_close'], f'{path}.quote.previous_close'
                ),
            )

        breadth_data = None
        breadth = observation.get('breadth')
        if breadth is not None:
            _check_keys(
                breadth,
                {'up', 'down', 'unchanged', 'total'},
                set(),
                f'{path}.breadth',
            )
            up = _count(breadth['up'], f'{path}.breadth.up')
            down = _count(breadth['down'], f'{path}.breadth.down')
            unchanged = _count(
                breadth['unchanged'], f'{path}.breadth.unchanged'
            )
            total = _count(breadth['total'], f'{path}.breadth.total')
            if total <= 0:
                raise ValidationError(f'{path}.breadth.total must be positive')
            if up + down + unchanged != total:
                raise ValidationError(
                    f'{path}.breadth counts must sum exactly to total'
                )
            breadth_data = (up, down, total)

        reasons = []
        if observed_at > as_of:
            reasons.append('observed_at_after_as_of')
        if available_at > as_of:
            reasons.append('available_at_after_as_of')
        eligibility = not reasons

        quote_metrics = None
        breadth_metrics = None
        if eligibility and quote_data is not None:
            last, previous_close = quote_data
            return_pct = (last / previous_close - 1.0) * 100.0
            if not math.isfinite(return_pct):
                raise ValidationError(
                    f'{path}.quote produces a nonfinite return_pct'
                )
            quote_metrics = {'return_pct': return_pct}
        if eligibility and breadth_data is not None:
            up, down, total = breadth_data
            breadth_metrics = {
                'up_share': up / total,
                'down_share': down / total,
            }

        output_observations.append(
            {
                'id': observation_id,
                'eligibility': eligibility,
                'reasons': reasons,
                'metrics': {
                    'quote': quote_metrics,
                    'breadth': breadth_metrics,
                },
            }
        )

    result = {'as_of': as_of_text, 'observations': output_observations}
    if 'delivery_contract' in payload:
        result['delivery_contract'] = _validate_delivery_contract(
            payload['delivery_contract'], 'delivery_contract', as_of
        )
    return result


def main():
    if len(sys.argv) != 2:
        _write_json(
            {
                'error': {
                    'type': 'usage_error',
                    'message': (
                        'usage: python3 scripts/briefing_checks.py INPUT.json '
                        '(or - for stdin)'
                    ),
                }
            }
        )
        return 2

    source = sys.argv[1]
    try:
        if source == '-':
            raw = sys.stdin.read()
        else:
            with open(source, 'r', encoding='utf-8') as handle:
                raw = handle.read()
    except (OSError, UnicodeError) as exc:
        _write_json(
            {'error': {'type': 'input_error', 'message': str(exc)}}
        )
        return 2

    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        _write_json(
            {
                'error': {
                    'type': 'malformed_json',
                    'message': (
                        f'{exc.msg} at line {exc.lineno} column {exc.colno}'
                    ),
                }
            }
        )
        return 2
    except ValidationError as exc:
        _write_json(
            {'error': {'type': 'validation_error', 'message': str(exc)}}
        )
        return 2

    try:
        result = _validate(payload)
    except ValidationError as exc:
        _write_json(
            {'error': {'type': 'validation_error', 'message': str(exc)}}
        )
        return 2

    _write_json(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

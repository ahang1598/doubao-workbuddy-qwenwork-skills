"""Compile exact workbook associations into content-only sparse edits."""
import hashlib
from pathlib import Path
import re

from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import column_index_from_string, range_boundaries

from _edit_scope import _in_scope
from sheet_data import Match, UniqueLookup


class _WorkbookLookup(UniqueLookup):
    def _key(self, row):
        return super()._key({field: int(value) if type(value) is float and value.is_integer() else value
                             for field, value in row.items()})


def _object(value, allowed, required, where):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError('{}字段不匹配；仅支持{}'.format(where, ', '.join(allowed)))


def _column(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Z]{1,3}', value):
        raise ValueError('列映射必须使用大写Excel列字母')
    index = column_index_from_string(value)
    if index > 16384:
        raise ValueError('列映射越出Excel范围')
    return index


def _selection(workbook, value, where):
    _object(value, ('sheet', 'range'), ('sheet', 'range'), where)
    name, address = value['sheet'], value['range']
    if not isinstance(name, str) or name not in workbook.sheetnames:
        raise ValueError('{}子表不存在'.format(where))
    if not isinstance(address, str) or not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*', address):
        raise ValueError('{}必须是有界数据区，不含表头，如A2:C20'.format(where))
    left, top, right, bottom = range_boundaries(address)
    sheet = workbook[name]
    if not 1 <= left <= right <= min(sheet.max_column, 16384) or not 1 <= top <= bottom <= min(sheet.max_row, 1048576):
        raise ValueError('{}范围越界或倒序，不能扩展原布局'.format(where))
    return sheet, (left, top, right, bottom)


def _mapping(value, target_bounds, reference_bounds, where):
    if not isinstance(value, dict) or not value:
        raise ValueError('{}必须是非空目标列到来源列映射'.format(where))
    for target, reference in value.items():
        target_index, reference_index = _column(target), _column(reference)
        if not target_bounds[0] <= target_index <= target_bounds[2] or not reference_bounds[0] <= reference_index <= reference_bounds[2]:
            raise ValueError('{}列不在指定数据区内'.format(where))
    return value


def _value(sheet, row, column, special_ranges):
    cell = sheet.cell(row, _column(column))
    if any(left <= cell.column <= right and top <= row <= bottom
           for left, top, right, bottom in special_ranges):
        raise ValueError('关联取数不读取数组公式或Data Table公式结果区：{}!{}'.format(sheet.title, cell.coordinate))
    if isinstance(cell, MergedCell) or cell.data_type in ('f', 'e') or type(cell.value).__name__ == 'CellRichText':
        raise ValueError('关联取数不把公式、错误值、合并从属格或富文本当作普通来源值：{}!{}'.format(sheet.title, cell.coordinate))
    return cell.value


def _matched_values(match, columns, needed, override, spec, sheet_name, row):
    """Project an existing match without dropping candidates or tuple fields."""
    fields = list(dict.fromkeys(columns.values()))
    mapped = match.project(fields, distinct=spec.get('distinct', False))
    if not needed:
        return {}
    if spec['mode'] == 'unique':
        if len(mapped) != 1:
            raise ValueError('目标{}!{}存在多候选，未写出文件；补充明确键/例外或按任务选择all，不取首条'.format(sheet_name, row))
        return {target: mapped[0][reference] for target, reference in needed.items()}
    if override and len(mapped) > 1:
        raise ValueError('多候选元组不能用单值例外覆盖部分字段；按任务定义完整结果，未写出文件')
    packed = Match(mapped).text_columns(fields)
    if packed['overflow']:
        raise ValueError('目标{}!{}完整候选超出单格容量，未写出文件；在允许的明细区保留完整候选，不裁剪或擅自插行'.format(sheet_name, row))
    texts = dict(zip(fields, packed['columns']))
    return {target: texts[reference] for target, reference in needed.items()}


def compile_lookup(workbook, spec, source, load_reference, scope, index_special_formulas):
    _object(spec, ('reference', 'target', 'keys', 'columns', 'mode', 'distinct', 'only_empty', 'overrides'),
            ('reference', 'target', 'keys', 'columns', 'mode'), 'lookup')
    if spec['mode'] not in ('unique', 'all'):
        raise ValueError('mode必须为unique或all，不能猜测多候选取首条')
    for name in ('distinct', 'only_empty'):
        if name in spec and type(spec[name]) is not bool:
            raise ValueError('{}必须是布尔值'.format(name))
    reference = spec['reference']
    _object(reference, ('file', 'sheet', 'range'), ('sheet', 'range'), 'reference')
    external = None
    reference_path = None
    reference_hash = None
    try:
        reference_book = workbook
        if 'file' in reference:
            if not isinstance(reference['file'], str) or not reference['file']:
                raise ValueError('reference.file必须为文件路径')
            reference_path = Path(reference['file']).resolve()
            if reference_path != Path(source).resolve():
                reference_hash = hashlib.sha256(reference_path.read_bytes()).hexdigest()
                external = load_reference(reference_path)
                reference_book = external
        ref_sheet, ref_bounds = _selection(reference_book, {key:value for key,value in reference.items() if key != 'file'}, 'reference')
        target_sheet, target_bounds = _selection(workbook, spec['target'], 'target')
        special_ranges = {sheet: index_special_formulas([sheet])[sheet.title]
                          for sheet in dict.fromkeys((ref_sheet, target_sheet))}
        keys = _mapping(spec['keys'], target_bounds, ref_bounds, 'keys')
        columns = _mapping(spec['columns'], target_bounds, ref_bounds, 'columns')
        if set(keys) & set(columns):
            raise ValueError('关联结果不能覆盖目标匹配键列')
        for row in range(target_bounds[1], target_bounds[3]+1):
            for column in columns:
                if not _in_scope(scope, target_sheet.title, column+str(row)):
                    raise ValueError('关联目标超出scope：{}!{}{}'.format(target_sheet.title, column, row))
        reference_fields = list(dict.fromkeys(list(keys.values()) + list(columns.values())))
        records = [{field:_value(ref_sheet, row, field, special_ranges[ref_sheet]) for field in reference_fields}
                   for row in range(ref_bounds[1], ref_bounds[3]+1)]
        key_fields = list(dict.fromkeys(keys.values()))
        if len(key_fields) != len(keys):
            raise ValueError('匹配键的来源列不能重复')
        lookup = _WorkbookLookup(records, key_fields)
        overrides = spec.get('overrides', [])
        if not isinstance(overrides, list):
            raise ValueError('overrides必须为显式例外数组')
        override_index = {}
        for item in overrides:
            _object(item, ('key', 'values'), ('key', 'values'), 'override')
            if not isinstance(item['key'], list) or len(item['key']) != len(keys):
                raise ValueError('override.key按keys顺序提供完整键值')
            _object(item['values'], tuple(columns), (), 'override.values')
            if not item['values']:
                raise ValueError('override.values不能为空')
            key = lookup._key(dict(zip(key_fields, item['key'])))
            if key is None or key in override_index:
                raise ValueError('例外键不能为空或重复')
            override_index[key] = item['values']
        edits = []
        counts = dict(matched_rows=0, missing_rows=0, preserved_cells=0, overridden_cells=0)
        for row in range(target_bounds[1], target_bounds[3]+1):
            query = {reference:_value(target_sheet, row, target, special_ranges[target_sheet])
                     for target,reference in keys.items()}
            key = lookup._key(query)
            override = override_index.get(key, {})
            active = {target:reference for target,reference in columns.items()
                      if not spec.get('only_empty', True) or target_sheet.cell(row, _column(target)).value is None
                      or target_sheet.cell(row, _column(target)).value == ''}
            counts['preserved_cells'] += len(columns)-len(active)
            if not active:
                continue
            match = lookup.find(query)
            values = {}
            needed = {target:reference for target,reference in active.items() if target not in override}
            if match.status == 'missing':
                counts['missing_rows'] += 1
                if not any(target in active for target in override):
                    continue
            else:
                counts['matched_rows'] += 1
            if spec['mode']=='all' and len(active)!=len(columns):
                raise ValueError('多候选关联目标部分已填，不能保证元组对应；按用户授权整组更新或单独处理，未写出文件')
            if match.status != 'missing':
                values.update(_matched_values(match, columns, needed, override, spec, target_sheet.title, row))
            values.update({target:value for target,value in override.items() if target in active})
            for value in values.values():
                if isinstance(value, str) and len(value.encode('utf-16-le')) // 2 > 32767:
                    raise ValueError('关联结果超出单格文本容量，未写出文件；保留完整来源，不裁剪')
            counts['overridden_cells'] += sum(target in active for target in override)
            edits.extend(dict(sheet=target_sheet.title, cell=target+str(row), value=value) for target,value in values.items())
        if reference_hash is not None:
            if hashlib.sha256(reference_path.read_bytes()).hexdigest() != reference_hash:
                raise ValueError('关联期间来源文件变化，未生成输出')
        return edits, counts, reference_path
    finally:
        if external is not None:
            external.close()

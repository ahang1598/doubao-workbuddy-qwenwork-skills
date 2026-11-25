"""Streaming field mapping, exact-key lookup and source-text slicing.

These helpers transform records during normal reads/writes. They neither open
workbooks nor infer business fields, normalize identities or evaluate formulas.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
import math
from numbers import Integral, Real
from operator import index
import re


_INVALID_XML_CHARACTERS = re.compile(r'[^\t\n\r\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]')
_FORMULA_DICT_ERROR = 'formula values require {"formula": "=..."}'


def _check_xml_characters(value):
    invalid = _INVALID_XML_CHARACTERS.search(value)
    if invalid:
        raise ValueError('XML 1.0 forbids character U+{:04X}'.format(ord(invalid.group())))


def _check_xml_attribute(value):
    _check_xml_characters(value)
    if not any(char in value for char in '\t\n\r'):
        return
    # XML backends differ in how they escape whitespace inside attributes.
    from openpyxl.xml.functions import Element, fromstring, xmlfile
    with BytesIO() as serialized:
        with xmlfile(serialized) as writer:
            writer.write(Element('attribute', value=value))
        restored = fromstring(serialized.getvalue()).get('value')
    if restored != value:
        raise ValueError('XML attribute whitespace cannot be written losslessly by this writer; '
                         'preserve the original text and use a lossless writing path')


def _check_literal_text(value, preserves_carriage_returns):
    _check_written_text(value, preserves_carriage_returns)
    if re.search(r"_[xX][0-9A-Fa-f]{4}_", value):
        raise ValueError('literal OOXML escape text cannot be written losslessly by this writer; '
                         'preserve the original text and use a lossless writing path, do not rewrite or remove it')


def _check_written_text(value, preserves_carriage_returns):
    _check_xml_characters(value)
    # XML readers normalize literal carriage returns emitted by the standard library writer.
    if not preserves_carriage_returns and '\r' in value:
        raise ValueError('text containing carriage returns cannot be written losslessly by this writer; '
                         'preserve the original text and use a lossless writing path, do not rewrite or remove it')


def _fields(values, where):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("{} must be a nonempty field list".format(where))
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("{}: name empty headers explicitly, using source column coordinates".format(where))
    if len(set(values)) != len(values):
        raise ValueError("{}: duplicate fields; distinguish them by full header or source column".format(where))
    return tuple(values)


def check_cell_capacity(value, formula=False):
    limit = 8192 if formula else 32767
    if len(value.encode('utf-16-le')) // 2 > limit:
        kind = 'formula' if formula else 'text'
        raise ValueError('{} exceeds Excel {} UTF-16 unit limit; do not truncate'.format(kind, limit))


def _check_cell_text(value, preserves_carriage_returns):
    _check_literal_text(value, preserves_carriage_returns)
    check_cell_capacity(value)


def _check_formula_text(formula, preserves_carriage_returns, error):
    if not isinstance(formula, str):
        raise ValueError(error)
    _check_written_text(formula, preserves_carriage_returns)
    if not formula.startswith('=') or not formula[1:].strip():
        raise ValueError(error)
    check_cell_capacity(formula, formula=True)


def _check_native_formula_metadata(formula, kind):
    array = kind == 'array'
    references = ('ref',) if array else ('ref', 'r1', 'r2')
    flags = () if array else ('dt2D', 'dtr', 'ca', 'del1', 'del2')
    allowed = {'t', *references, *flags}
    if array:
        allowed.add('text')
    error = 'native formula metadata cannot be written losslessly by this writer'
    if formula.t != kind or set(vars(formula)) - allowed:
        raise ValueError(error)
    for name in references:
        reference = getattr(formula, name)
        # Missing references reload as None, but the data-table reader requires ref.
        if reference is None and (array or name != 'ref'):
            continue
        if not isinstance(reference, str) or not reference:
            raise ValueError(error)
    for name in flags:
        if getattr(formula, name) not in (False, True, '0', '1', 'false', 'true'):
            raise ValueError(error)
    for _, attribute in formula:
        _check_xml_attribute(attribute)


def _check_numeric_cell(value, safe_string):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('nonfinite values must be handled by the task missing-value policy')
        serialized = safe_string(value)
        if (not serialized or Decimal(serialized) != value
                or Decimal(str(float(serialized))) != value):
            raise ValueError('decimal cannot be stored exactly; use text to preserve the source value')
    elif isinstance(value, Integral):
        try:
            integer = int.__int__(value) if isinstance(value, int) else index(value)
            serialized = safe_string(value)
            exact = (serialized and Decimal(serialized) == integer
                     and int(float(integer)) == integer)
        except (OverflowError, TypeError, ValueError):
            exact = False
        if not exact:
            raise ValueError('integer cannot be stored exactly; use text for identifiers')
    elif isinstance(value, Real):
        try:
            # NumPy scalar comparisons can round the reloaded value to the input dtype.
            ratio = (float.as_integer_ratio(value) if isinstance(value, float)
                     else value.as_integer_ratio())
        except (OverflowError, ValueError) as exc:
            raise ValueError('nonfinite values must be handled by the task missing-value policy') from exc
        serialized = safe_string(value)
        reloaded = float(serialized) if serialized else math.inf
        if not math.isfinite(reloaded) or reloaded.as_integer_ratio() != ratio:
            raise ValueError('float cannot be stored exactly; use text to preserve the source value')
    else:
        # openpyxl stores its registered NumPy booleans as numeric 0 and 1.
        if safe_string(value) != str(int(bool(value))):
            raise ValueError('numeric value cannot be stored exactly; use text to preserve the source value')


def _check_temporal_cell(value, cell):
    from openpyxl.cell.cell import get_time_format
    from openpyxl.compat import safe_string
    from openpyxl.styles.numbers import is_date_format, is_timedelta_format
    from openpyxl.utils.datetime import from_excel, from_ISO8601, to_excel, to_ISO8601
    from openpyxl.worksheet._reader import _cast_number

    if getattr(value, 'tzinfo', None) is not None:
        raise ValueError('Excel does not support timezones; use text to preserve the source value')
    workbook = cell.parent.parent
    expected = value
    error = 'date/time value cannot be stored exactly; use text to preserve the source value'
    try:
        if workbook.iso_dates and not isinstance(value, timedelta):
            reloaded = from_ISO8601(to_ISO8601(value))
        else:
            number_format = cell.number_format
            if not is_date_format(number_format):
                number_format = get_time_format(type(value))
            serial = _cast_number(safe_string(to_excel(value, workbook.epoch)))
            reloaded = from_excel(serial, workbook.epoch, timedelta=is_timedelta_format(number_format))
            # Numeric date cells reload as a midnight datetime.
            if isinstance(value, date) and not isinstance(value, datetime):
                expected = datetime.combine(value, time())
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(error) from exc
    if reloaded != expected or getattr(reloaded, 'fold', 0) != getattr(expected, 'fold', 0):
        raise ValueError(error)


class MappedTable:
    """Compile all source schemas before streaming rows in one shared order.

    Each source has fields, rows and optional rename/omit. Without output_fields,
    the output is the ordered union. No values are normalized; fields absent in a
    source are None. rows must yield arrays, never truncated positional zips.
    """
    def __init__(self, sources, output_fields=None):
        if not isinstance(sources, (list, tuple)) or not sources:
            raise ValueError("sources must be a nonempty list")
        self._sources = []
        union = []
        union_keys = set()
        for i, source in enumerate(sources, 1):
            if not isinstance(source, dict) or set(source) - {"fields", "rows", "rename", "omit"}:
                raise ValueError("source {} accepts fields/rows/rename/omit".format(i))
            fields = _fields(source.get("fields"), "source {} fields".format(i))
            if "rows" not in source:
                raise ValueError("source {} needs rows".format(i))
            rename, omit = source.get("rename", {}), source.get("omit", [])
            if not isinstance(rename, dict) or not isinstance(omit, (list, tuple)):
                raise ValueError("rename must be a mapping and omit a field list")
            if any(not isinstance(k, str) for k in omit) or len(set(omit)) != len(omit):
                raise ValueError("omit must contain distinct source field names")
            if (set(rename) | set(omit)) - set(fields) or set(rename) & set(omit):
                raise ValueError("rename/omit must refer to distinct existing source fields")
            kept = [(j, rename.get(k, k)) for j, k in enumerate(fields) if k not in omit]
            if kept:
                _fields([k for _, k in kept], "source {} mapped fields".format(i))
            for _, key in kept:
                if key not in union_keys:
                    union.append(key)
                    union_keys.add(key)
            self._sources.append((fields, kept, iter(source["rows"])))
        self.fields = _fields(union if output_fields is None else output_fields, "output_fields")
        missing = set(union) - set(self.fields)
        if missing:
            raise ValueError("output_fields mismatch: unmapped {}; map all fields, "
                             "use source omit only for requested column removal".format(sorted(missing)))
        positions = {key: i for i, key in enumerate(self.fields)}
        self._sources = [(fields, [(j, positions[key]) for j, key in kept], rows)
                         for fields, kept, rows in self._sources]

    def __iter__(self):
        for i, (fields, positions, rows) in enumerate(self._sources, 1):
            for n, values in enumerate(rows, 1):
                if not isinstance(values, (list, tuple)) or len(values) != len(fields):
                    raise ValueError("source {} row {} needs {} values; do not truncate or shift fields".format(
                        i, n, len(fields)))
                result = [None] * len(self.fields)
                for src, dst in positions:
                    result[dst] = values[src]
                yield result

    def write_to(self, worksheet, header_row, start_column=1):
        if type(header_row) is not int or not 1 <= header_row < 1048576:
            raise ValueError('header_row must leave room for data within Excel rows')
        if type(start_column) is not int or not 1 <= start_column <= 16385 - len(self.fields):
            raise ValueError('mapped fields exceed Excel columns')
        from openpyxl import LXML
        from openpyxl.cell.cell import TIME_TYPES
        from openpyxl.cell.rich_text import CellRichText, TextBlock
        from openpyxl.compat import NUMERIC_TYPES, safe_string
        from openpyxl.worksheet.formula import ArrayFormula, DataTableFormula

        for field in self.fields:
            _check_cell_text(field, preserves_carriage_returns=LXML)
        for column, field in enumerate(self.fields, start_column):
            cell = worksheet.cell(header_row, column)
            cell.value, cell.data_type = field, 's'
        count = 0
        for row_number, values in enumerate(self, header_row + 1):
            if row_number > 1048576:
                raise ValueError('mapped records exceed Excel rows')
            for column, value in enumerate(values, start_column):
                cell = worksheet.cell(row_number, column)
                if isinstance(value, dict):
                    if set(value) != {'formula'}:
                        raise ValueError(_FORMULA_DICT_ERROR)
                    formula = value['formula']
                    _check_formula_text(formula, LXML, _FORMULA_DICT_ERROR)
                    cell.value = formula
                else:
                    if isinstance(value, bytes):
                        value = str(value, cell.encoding)
                    if isinstance(value, str):
                        _check_cell_text(value, LXML)
                    elif isinstance(value, CellRichText):
                        _check_cell_text(str(value), LXML)
                        for run in value:
                            if not isinstance(run, (str, TextBlock)):
                                raise ValueError('rich text runs must contain text or styled text')
                            _check_literal_text(str(run), LXML)
                            if isinstance(run, TextBlock) and run.font.rFont is not None:
                                _check_xml_attribute(run.font.rFont)
                    elif isinstance(value, ArrayFormula):
                        _check_formula_text(value.text, LXML, 'array formula values require text in the form "=..."')
                        _check_native_formula_metadata(value, 'array')
                    elif isinstance(value, DataTableFormula):
                        _check_native_formula_metadata(value, 'dataTable')
                    elif isinstance(value, TIME_TYPES):
                        _check_temporal_cell(value, cell)
                    elif not isinstance(value, bool) and isinstance(value, NUMERIC_TYPES):
                        _check_numeric_cell(value, safe_string)
                    if isinstance(value, str) and value == '':
                        # Write an empty inline string element so the cell reloads as text.
                        cell.value = CellRichText()
                    else:
                        cell.value = value
                        if isinstance(value, str):
                            cell.data_type = 's'
            count += 1
        return count


class Match:
    """A lookup outcome; only an unambiguous match exposes a single value."""
    def __init__(self, candidates):
        self.candidates = tuple(dict(row) for row in candidates)
        self.status = "missing" if not self.candidates else "unique" if len(self.candidates) == 1 else "ambiguous"

    def value(self, field):
        if self.status != "unique":
            raise ValueError("{} match has no single value; preserve the target or handle the conflict".format(
                self.status))
        return self.candidates[0][field]

    def project(self, fields, distinct=False):
        """Keep candidate tuples together; deduplicate only when requested.

        Projection preserves source order, types, punctuation and empty values.
        Distinct applies to whole tuples, not to each output field separately.
        """
        fields = _fields(fields, 'project fields')
        if type(distinct) is not bool:
            raise ValueError('distinct must be a boolean')
        projected, seen = [], set()
        for candidate in self.candidates:
            if set(fields) - set(candidate):
                raise ValueError('candidate lacks requested fields: {}'.format(
                    sorted(set(fields) - set(candidate))))
            record = {field: candidate[field] for field in fields}
            if distinct:
                identity = tuple((type(record[field]), record[field]) for field in fields)
                try:
                    if identity in seen:
                        continue
                    seen.add(identity)
                except TypeError as exc:
                    raise ValueError('distinct projection requires hashable field values') from exc
                if any(type(value) is float and not math.isfinite(value) for value in record.values()):
                    raise ValueError('distinct projection requires finite values')
            projected.append(record)
        return tuple(projected)

    def text_columns(self, fields, distinct=False, separator='\n', limit=32767):
        """Pack a shared prefix of text tuples and return every overflow tuple.

        Text is never normalized or truncated. None is displayed as empty text;
        numeric/date formatting must be explicit before using this text view.
        The conservative limit counts UTF-16 units, including separators.
        """
        fields = _fields(fields, 'text fields')
        if not isinstance(separator, str) or not separator:
            raise ValueError('separator must be nonempty text')
        if type(limit) is not int or not 1 <= limit <= 32767:
            raise ValueError('limit must be an integer from 1 to 32767')
        records = self.project(fields, distinct=distinct)
        rendered = []
        for record in records:
            if any(value is not None and not isinstance(value, str) for value in record.values()):
                raise ValueError('text columns require text or None; format other values explicitly')
            rendered.append(tuple('' if record[field] is None else record[field] for field in fields))
        try:
            separator_size = len(separator.encode('utf-16-le')) // 2
            lengths = [tuple(len(value.encode('utf-16-le')) // 2 for value in values) for values in rendered]
        except UnicodeEncodeError as exc:
            raise ValueError('text contains unpaired Unicode surrogates') from exc
        used = [0] * len(fields)
        count = 0
        for sizes in lengths:
            next_sizes = [used[index] + size + (separator_size if count else 0)
                          for index, size in enumerate(sizes)]
            if any(size > limit for size in next_sizes):
                break
            used = next_sizes
            count += 1
        return dict(columns=tuple(separator.join(values[index] for values in rendered[:count])
                                  for index in range(len(fields))), inline_rows=count,
                    overflow=records[count:])


class UniqueLookup:
    """Index an in-memory reference table once; preserve duplicate-key conflicts.

    Keys retain types and text exactly. None/empty-string keys do not match.
    Any normalization must be performed explicitly before indexing and querying.
    """
    def __init__(self, records, key_fields):
        self.key_fields = _fields(key_fields, "key_fields")
        self._index = {}
        for row in records:
            key = self._key(row)
            if key is not None:
                self._index.setdefault(key, []).append(dict(row))

    def _key(self, row):
        if not isinstance(row, dict):
            raise ValueError("lookup records must be mappings")
        key = []
        for field in self.key_fields:
            if field not in row:
                raise ValueError("lookup record lacks key field {}".format(field))
            value = row[field]
            if value is None or value == "":
                return None
            if type(value) not in (str, int, float, bool) or (type(value) is float and not math.isfinite(value)):
                raise ValueError("lookup keys must be finite scalar values")
            key.append((type(value).__name__, value))
        return tuple(key)

    def find(self, record):
        return Match(self._index.get(self._key(record), ()))


def extract_span(source, start, end):
    """Slice original text by Unicode code-point offsets, end exclusive."""
    if not isinstance(source, str):
        raise ValueError("extraction source must be text, not a formula or coerced value")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(source):
        raise ValueError("span must satisfy 0 <= start < end <= source length (Unicode characters)")
    return source[start:end]

"""Split the worksheet qualifiers and endpoints of an Excel range operand."""
from openpyxl.formula.translate import Translator
from openpyxl.utils.cell import column_index_from_string

MAX_EXCEL_COLUMN = 16384


def axis_range(endpoints, *, allow_qualified_columns=False):
    """Return the unqualified address of a whole-row or whole-column range."""
    coordinates = ':'.join(address for _, address in endpoints)
    if Translator.ROW_RANGE_RE.fullmatch(coordinates):
        return coordinates
    columns = Translator.COL_RANGE_RE.fullmatch(coordinates)
    if not columns or (endpoints[-1][0] and '$' not in coordinates and not allow_qualified_columns):
        return None
    # Bare out-of-grid columns may be defined names. A dollar sign makes
    # the endpoint explicit, so the translator can still reject it if invalid.
    if any(not column.startswith('$') and column_index_from_string(column) > MAX_EXCEL_COLUMN
           for column in columns.groups()):
        return None
    return coordinates


def split_reference(operand):
    """Return the leading @ operator and (qualifier including !, address or name) endpoints."""
    intersection = '@' if operand.startswith('@') else ''
    operand = operand[len(intersection):]
    colons, bangs = [], []
    quoted, brackets, escaped = False, 0, False
    for index, char in enumerate(operand):
        if quoted:
            if char == "'":
                quoted = False
        elif escaped:
            escaped = False
        elif brackets and char == "'":
            escaped = True
        elif char == "'":
            quoted = True
        elif char == '[':
            brackets += 1
        elif char == ']':
            brackets -= 1
        elif not brackets and char == ':':
            colons.append(index)
        elif not brackets and char == '!':
            bangs.append(index)
        if brackets < 0:
            break

    if quoted or brackets:
        raise ValueError(f'unsupported range reference: {operand}')

    if len(bangs) == 1 and colons and colons[0] < bangs[0]:
        first = operand[:colons[0]]
        right_qualifier = operand[colons[0] + 1:bangs[0]]
        right = operand[bangs[0] + 1:]
        first_is_cell = Translator.CELL_REF_RE.fullmatch(first)
        pair = first + ':' + right
        explicit_right = right_qualifier.startswith(("'", '[')) or (
            first_is_cell and len(colons) == 1 and not Translator.CELL_REF_RE.fullmatch(right))
        if not first or not right_qualifier:
            raise ValueError(f'ambiguous range reference: {operand}')
        if not explicit_right:
            # Keep 3-D qualifiers such as Jan:Mar! intact when the left side
            # cannot also be the coordinate of a separate endpoint.
            if (first_is_cell or first.startswith('$') or Translator.ROW_RANGE_RE.fullmatch(pair)
                    or Translator.COL_RANGE_RE.fullmatch(pair)):
                raise ValueError(f'ambiguous range reference: {operand}')
            colons = colons[1:]

    if len(colons) > 1:
        raise ValueError(f'unsupported range reference: {operand}')
    parts, start = [], 0
    for end in colons + [len(operand)]:
        delimiters = [bang for bang in bangs if start <= bang < end]
        if len(delimiters) > 1 or delimiters == [start]:
            raise ValueError(f'unsupported range reference: {operand}')
        address_start = delimiters[0] + 1 if delimiters else start
        if address_start == end:
            raise ValueError(f'unsupported range reference: {operand}')
        parts.append((operand[start:address_start], operand[address_start:end]))
        start = end + 1
    return intersection, parts

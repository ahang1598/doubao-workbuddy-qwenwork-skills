"""Write fixed-rate, end-of-period loan formulas into an authorized result block.

Inputs are cell references, not copied amounts. Dates, fees and non-monthly day
count conventions remain the caller's responsibility. No files are opened or saved.
"""
import re

from openpyxl.utils import absolute_coordinate, get_column_letter, quote_sheetname
from openpyxl.utils.cell import range_boundaries


FIELDS = ('period', 'opening', 'principal', 'interest', 'payment', 'closing')
METHODS = ('annuity', 'equal_principal', 'interest_only')


def _reference(value, sheet_name):
    if not isinstance(value, str) or not re.fullmatch(
            r"(?:(?:'(?:[^']|'')+'|[\w\u0080-\uffff]+)!)?\$?[A-Za-z]{1,3}\$?[1-9][0-9]*", value):
        raise ValueError('loan inputs must be single A1 cell references, not amounts or expressions')
    address = value.rsplit('!', 1)[-1].replace('$', '')
    column, row, _, _ = range_boundaries(address)
    if column > 16384 or row > 1048576:
        raise ValueError('input reference exceeds Excel bounds')
    sheet = value.rsplit('!', 1)[0] if '!' in value else quote_sheetname(sheet_name)
    return sheet + '!' + absolute_coordinate(address.upper())


def write_schedule(worksheet, principal, rate, periods, method, capacity,
                   start_row=1, start_column=1, digits=2, column_map=None):
    """Write six formula fields without headers; return absolute ranges and SUMs.

    rate is the periodic rate; periods is an integer input. capacity reserves the
    maximum supported term; excess/invalid inputs return #N/A rather than a partial
    schedule. digits=None retains precision; integer digits rounds each component.
    column_map places fields in an existing layout without touching other columns.
    """
    principal, rate, periods = (_reference(value, worksheet.title) for value in (principal, rate, periods))
    if method not in METHODS:
        raise ValueError('method must be one of ' + ', '.join(METHODS))
    if type(capacity) is not int or capacity < 1:
        raise ValueError('capacity must be a positive integer')
    if (type(start_row) is not int or type(start_column) is not int or start_row < 1
            or start_row + capacity - 1 > 1048576 or not 1 <= start_column <= 16384):
        raise ValueError('schedule exceeds Excel bounds')
    if digits is not None and (type(digits) is not int or not 0 <= digits <= 10):
        raise ValueError('digits must be None or an integer from 0 to 10')
    if column_map is None:
        if start_column + len(FIELDS) - 1 > 16384:
            raise ValueError('schedule exceeds Excel bounds')
        column_indices = {field: start_column + offset for offset, field in enumerate(FIELDS)}
    else:
        if start_column != 1 or not isinstance(column_map, dict) or set(column_map) != set(FIELDS):
            raise ValueError('column_map requires all six fields and no start_column')
        if any(type(index) is not int or not 1 <= index <= 16384 for index in column_map.values()):
            raise ValueError('column_map must contain Excel column numbers')
        if len(set(column_map.values())) != len(FIELDS):
            raise ValueError('column_map fields must use distinct columns')
        column_indices = column_map
    for reference in (principal, rate, periods):
        sheet, address = reference.rsplit('!', 1)
        sheet = sheet[1:-1].replace("''", "'") if sheet.startswith("'") else sheet
        if sheet.casefold() == worksheet.title.casefold():
            column, row, _, _ = range_boundaries(address)
            if (start_row <= row < start_row + capacity
                    and column in column_indices.values()):
                raise ValueError('schedule must not overwrite its input cells')
    columns = {field: get_column_letter(index) for field, index in column_indices.items()}
    invalid = ('IF(AND(ISNUMBER({0}),ISNUMBER({1}),ISNUMBER({2})),'
               'OR({0}<=0,{1}<0,{2}<1,{2}>{3},MOD({2},1)<>0),TRUE)')\
        .format(principal, rate, periods, capacity)

    def rounded(expression):
        return expression if digits is None else 'ROUND({},{})'.format(expression, digits)

    for offset in range(capacity):
        row = start_row + offset
        period = offset + 1
        cells = {field: column + str(row) for field, column in columns.items()}
        opening = rounded(principal) if offset == 0 else columns['closing'] + str(row - 1)
        if method == 'annuity':
            part = 'PPMT({},{},{},-{})'.format(rate, period, periods, principal)
            interest = 'IPMT({},{},{},-{})'.format(rate, period, periods, principal)
        elif method == 'equal_principal':
            part, interest = '{}/{}'.format(principal, periods), '{}*{}'.format(cells['opening'], rate)
        else:
            part, interest = '0', '{}*{}'.format(cells['opening'], rate)
        part = 'IF({}={}, {},MIN({},MAX(0,{})))'.format(
            period, periods, cells['opening'], cells['opening'], rounded(part))
        expressions = dict(period=str(period), opening=opening, principal=part,
                           interest=rounded(interest),
                           payment=rounded('{}+{}'.format(cells['principal'], cells['interest'])),
                           closing=rounded('{}-{}'.format(cells['opening'], cells['principal'])))
        for field in FIELDS:
            worksheet[cells[field]] = '=IF({},NA(),IF({}>{},"",{}))'.format(
                invalid, period, periods, expressions[field])
    sheet = quote_sheetname(worksheet.title)
    ranges = {
        field: '{}!${}${}:${}${}'.format(sheet, column, start_row, column, start_row + capacity - 1)
        for field, column in columns.items()
    }
    return dict(columns=columns, ranges=ranges, input_formula='=' + rounded(principal),
                totals={field: '=SUM({})'.format(ranges[field]) for field in ('principal', 'interest', 'payment')})

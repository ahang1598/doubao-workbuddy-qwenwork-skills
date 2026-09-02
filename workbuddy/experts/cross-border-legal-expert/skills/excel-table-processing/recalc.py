#!/usr/bin/env python3
"""
Deprecated placeholder for the removed headless formula recalculation workflow.
"""

import json
import sys
from pathlib import Path


REMOVAL_MESSAGE = (
    'Headless formula recalculation has been removed from this repository. '
    'LibreOffice is no longer a dependency of the xlsx skill. '
    'Formulas can still be written and preserved, but calculated values must be '
    'refreshed by opening the workbook in Excel or another spreadsheet application.'
)


def recalc(filename, timeout=30):
    del timeout
    if not Path(filename).exists():
        return {'error': f'File {filename} does not exist'}
    return {
        'status': 'unsupported',
        'error': REMOVAL_MESSAGE,
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: python recalc.py <excel_file> [timeout_seconds]')
        print()
        print(REMOVAL_MESSAGE)
        sys.exit(1)

    filename = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    print(json.dumps(recalc(filename, timeout), indent=2))
    sys.exit(1)


if __name__ == '__main__':
    main()

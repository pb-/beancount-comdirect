import re
from datetime import datetime
from csv import DictReader
from functools import reduce

from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.number import Decimal
from beancount.ingest import importer

ENCODING = 'ISO-8859-1'
FIELDS = (
    'Buchungstag',
    'Wertstellung (Valuta)',
    'Vorgang',
    'Buchungstext',
    'Umsatz in EUR',
    '',
)
HEADER_ROW = ';'.join(f'"{field}"' if field else '' for field in FIELDS)


def _skip_preamble(f):
    """Skip preamble/header and return the number of lines skipped."""
    first_line = next(f).strip()

    # Older exports (ca. 2016) do not have a preamble
    if first_line == HEADER_ROW:
        return 1

    if first_line != ';':
        raise InvalidFormatException

    date_pattern = r'\d{2}\.\d{2}\.\d{4}'
    preamble_patterns = (
        f'"Umsätze Girokonto";"Zeitraum: {date_pattern} - {date_pattern}";$',
        '"Neuer Kontostand";"[0-9,.]+ EUR";$',
        '$',
        re.escape(HEADER_ROW) + '$',
    )

    for pattern in preamble_patterns:
        line = next(f).strip()
        if not re.compile(pattern).match(line):
            raise InvalidFormatException

    return 5


def _identify(f):
    try:
        _skip_preamble(f)
        return True
    except (InvalidFormatException, StopIteration):
        pass

    return False


def _finish_key_value(state):
    if not state['current_key']:
        return state

    return {
        **state,
        'parsed': {
            **state['parsed'],
            state['current_key']: ' '.join(state['current_words']),
        },
        'current_key': None,
        'current_words': [],
    }


def _parse_reduce(state, word):
    keys = ('Auftraggeber', 'Empfänger', 'Buchungstext')

    if word.endswith(':') and word[:-1] in keys:
        return {
            **_finish_key_value(state),
            'current_key': word[:-1],
            'current_words': [],
        }

    return {
        **state,
        'current_words': [*state['current_words'], word],
    }


def _parse_text(text):
    result = reduce(
        _parse_reduce,
        text.split(' '),
        {'parsed': {}, 'current_key': None, 'current_words': []},
    )
    return _finish_key_value(result)['parsed']


def _extract(f, file_name, account):
    entries = []
    line = 1 + _skip_preamble(f)
    reader = DictReader(f, fieldnames=FIELDS, delimiter=';')

    for row in reader:
        raw_date = row['Buchungstag']
        if raw_date == 'offen':
            continue
        if raw_date.startswith('Umsätze'):
            break
        raw_amount = row['Umsatz in EUR']
        parsed_text = _parse_text(row['Buchungstext'])

        payee = parsed_text.get('Auftraggeber') or parsed_text.get('Empfänger')
        description = parsed_text.get('Buchungstext')
        date = datetime.strptime(raw_date, '%d.%m.%Y').date()
        amount = Amount(
            Decimal(raw_amount.replace('.', '').replace(',', '.')), 'EUR'
        )
        posting = data.Posting(account, amount, None, None, None, None)
        meta = data.new_metadata(file_name, line)

        entries.append(
            data.Transaction(
                meta,
                date,
                '*',
                payee,
                description,
                data.EMPTY_SET,
                data.EMPTY_SET,
                [posting],
            )
        )

        line += 1

    return entries


class GiroImporter(importer.ImporterProtocol):
    def __init__(self, account):
        self.account = account

    def file_account(self, _):
        return self.account

    def identify(self, file_memo):
        with open(file_memo.name, encoding=ENCODING) as f:
            return _identify(f)

    def extract(self, file_memo, existing_entries=None):
        with open(file_memo.name, encoding=ENCODING) as f:
            return _extract(f, file_memo.name, self.account)


class InvalidFormatException(Exception):
    pass

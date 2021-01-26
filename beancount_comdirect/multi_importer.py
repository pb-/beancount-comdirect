import re
from datetime import datetime
from csv import DictReader
from functools import reduce

from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.number import Decimal
from beancount.ingest import importer

from beancount_comdirect import accounts

ENCODING = 'ISO-8859-1'


def _header_row(fields):
    return ';'.join(f'"{field}"' if field else '' for field in fields)


def _pattern_for(account_type):
    date_pattern = r'\d{2}\.\d{2}\.\d{4}'
    type_ = re.escape(account_type)
    return re.compile(
        f'"Umsätze {type_}";"Zeitraum: {date_pattern} - {date_pattern}";$'
    )


def _skip_preamble(f, account_structure):
    """Skip preamble/header and return the number of lines skipped."""
    line_number = 0
    first_line = next(f).strip()
    line_number += 1

    if first_line != ';':
        raise InvalidFormatException

    account_header_pattern = _pattern_for(account_structure['label'])

    while True:
        line = next(f).strip()
        line_number += 1
        if account_header_pattern.match(line):
            break

    if account_structure['type'] != accounts.BROKERAGE:
        line = next(f).strip()
        line_number += 1
        balance_pattern = '"Neuer Kontostand";"[0-9,.]+ EUR";$'
        if not re.compile(balance_pattern).match(line):
            raise InvalidFormatException

    line = next(f).strip()
    line_number += 1
    if line:
        raise InvalidFormatException

    line = next(f).strip()
    line_number += 1
    if line != _header_row(account_structure['fields']):
        raise InvalidFormatException

    return line_number


def _identify(f, account_structure):
    try:
        _skip_preamble(f, account_structure)
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


def _extract(f, file_name, account_structure, account):
    entries = []
    line = 1 + _skip_preamble(f, account_structure)
    reader = DictReader(
        f, fieldnames=account_structure['fields'], delimiter=';'
    )

    for row in reader:
        raw_date = row['Buchungstag']
        if raw_date == 'offen':
            # These are incomplete
            continue
        if raw_date.startswith('Umsätze'):
            # Next account type starts here
            break
        raw_amount = row['Umsatz in EUR']
        parsed_text = _parse_text(row['Buchungstext'])

        payee = parsed_text.get('Auftraggeber') or parsed_text.get('Empfänger')
        description = parsed_text.get('Buchungstext') or row['Buchungstext']
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


class MultiImporter(importer.ImporterProtocol):
    def __init__(self, account_type, account):
        self.account_structure = accounts.STRUCTURE[account_type]
        self.account = account

    def file_account(self, _):
        return self.account

    def identify(self, file_memo):
        with open(file_memo.name, encoding=ENCODING) as f:
            return _identify(f, self.account_structure)

    def extract(self, file_memo, existing_entries=None):
        with open(file_memo.name, encoding=ENCODING) as f:
            return _extract(
                f, file_memo.name, self.account_structure, self.account
            )


class InvalidFormatException(Exception):
    pass

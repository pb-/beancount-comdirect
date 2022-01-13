import re
from datetime import datetime, timedelta
from csv import DictReader
from functools import reduce

from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.number import Decimal
from beancount.core.position import Cost
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

def _skip_preamble_balance(f, account_structure):
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
        balance_pattern = '"Neuer Kontostand";"(?P<raw_amount>[0-9,.]+) EUR";$'
        m = re.compile(balance_pattern).match(line)
        if not m:
            raise InvalidFormatException
        else:
            raw_amount = m.group('raw_amount')
    else:
        raw_amount = False

    line = next(f).strip()
    line_number += 1
    if line:
        raise InvalidFormatException

    line = next(f).strip()
    line_number += 1
    if line != _header_row(account_structure['fields']):
        raise InvalidFormatException

    return (line_number, raw_amount)

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


def _number_to_us(number):
    return number.replace('.', '').replace(',', '.')


def _extract(f, file_name, account_structure, account):
    entries = []
    (line, closing_balance) = _skip_preamble_balance(f, account_structure)
    line += 1
    reader = DictReader(
        f, fieldnames=account_structure['fields'], delimiter=';'
    )

    last_date = False

    for row in reader:
        raw_date = row['Buchungstag']
        
        # Conditions to skip the row / break the loop
        if raw_date.startswith('Umsätze'):
            # Next account type starts here
            break
        if raw_date == 'Keine Umsätze vorhanden.':
            # accounts/credit cards with no transactions in this period
            continue
        if raw_date == 'offen':
            # These are incomplete / not booked yet
            continue
        
        meta = data.new_metadata(file_name, line)
        # assign opening balance
        if raw_date == 'Alter Kontostand':
            balance_pattern = '(?P<raw_amount>[0-9,.]+) EUR'
            m = re.compile(balance_pattern).match(row[account_structure['fields'][1]]) 
            if m is not False:
                raw_amount = m.group('raw_amount')
                entries.append(data.Balance(
                    data.new_metadata(file_name, line),
                    last_date,
                    account,
                    Amount(Decimal(_number_to_us(raw_amount)), 'EUR'),
                    None,
                    None
                    ))
            # skips quietly if extraction fails
            continue
        
        raw_amount = row['Umsatz in EUR']
        date = datetime.strptime(raw_date, '%d.%m.%Y').date()
        if last_date is False and closing_balance:
            # trigger on first transaction (newest) -> get date
            # Closing balance extracted from preamble
            entries.append(data.Balance(
                    data.new_metadata(file_name, line),
                    # Closing balance is opening balance for next day
                    date + timedelta(days=1),
                    account,
                    Amount(Decimal(_number_to_us(closing_balance)), 'EUR'),
                    None,
                    None
                    ))
        last_date = date
        amount = Amount(Decimal(_number_to_us(raw_amount)), 'EUR')

        if account_structure['type'] != accounts.BROKERAGE:
            parsed_text = _parse_text(row['Buchungstext'])

            payee = parsed_text.get('Auftraggeber') or parsed_text.get(
                'Empfänger'
            )
            description = (
                parsed_text.get('Buchungstext') or row['Buchungstext']
            )
            posting = data.Posting(account, amount, None, None, None, None)

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
        else:  # BROKERAGE
            cash_account = 'FIXME:cash'
            fees_account = 'FIXME:fees'

            instrument = row['WKN']
            instrument_units = Amount(Decimal(row['Stück / Nom.']), instrument)
            per_unit_cost = Cost(
                Decimal(_number_to_us(row['Ausführungskurs'])),
                row['Währung'],
                None,
                None,
            )
            description = row['Bezeichnung']

            postings = [
                data.Posting(cash_account, -amount, None, None, None, None),
                data.Posting(fees_account, None, None, None, None, None),
                data.Posting(
                    account,
                    instrument_units,
                    per_unit_cost,
                    None,
                    None,
                    None,
                ),
            ]

            entries.append(
                data.Transaction(
                    meta,
                    date,
                    '*',
                    None,
                    description,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    postings,
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

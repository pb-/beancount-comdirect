import re
from datetime import datetime
from csv import DictReader

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
TEXT_PATTERN = re.compile(
    '(Auftraggeber|Empfänger): (?P<payee>.*) '
    'Buchungstext: (?P<description>.*)'
)


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


def _extract(f, file_name, account):
    entries = []
    line = 1 + _skip_preamble(f)
    reader = DictReader(f, fieldnames=FIELDS, delimiter=';')

    for row in reader:
        raw_date = row['Buchungstag']
        raw_amount = row['Umsatz in EUR']
        booking_text = TEXT_PATTERN.match(row['Buchungstext'])
        if not booking_text:
            raise InvalidFormatException(
                f'could not parse line {line}: {row["Buchungstext"]}')

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
                None,
                booking_text.group('payee'),
                booking_text.group('description'),
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

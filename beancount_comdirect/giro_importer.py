import re

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
    first_line = next(f).strip()

    # Older exports (ca. 2016) do not have a preamble
    if first_line == HEADER_ROW:
        return

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


def _identify(f):
    try:
        _skip_preamble(f)
        return True
    except (InvalidFormatException, StopIteration):
        pass

    return False


def _extract(f):
    pass


class GiroImporter(importer.ImporterProtocol):
    def __init__(self, account):
        self.account = account

    def file_account(self):
        return self.account

    def identify(self, file_memo):
        with open(file_memo.name, file_encoding=ENCODING) as f:
            return _identify(f)

    def extract(self, file_memo, existing_entries=None):
        with open(file_memo.name, file_encoding=ENCODING) as f:
            return _extract(f)


class InvalidFormatException(Exception):
    pass

from io import StringIO
from textwrap import dedent

from beancount_comdirect.giro_importer import _identify, HEADER_ROW


def test_identify_empty_file():
    assert not _identify(StringIO())


def test_identify_irrelevant_file():
    assert not _identify(StringIO('hello world'))


def test_identiy_premature_eof():
    assert not _identify(StringIO(';\n"Ums'))


def test_identiy_minimal_old_file():
    assert _identify(StringIO(HEADER_ROW + '\n'))


def test_identify_minimal_file():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        """  # noqa
    assert _identify(StringIO(dedent(contents)))

from io import StringIO
from textwrap import dedent

from beancount_comdirect.giro_importer import _identify, _extract, HEADER_ROW


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


def test_extract_minimal():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        """  # noqa
    assert not _extract(StringIO(dedent(contents)), 'some-file', 'some-acc')


def test_extract_basic():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        "06.01.2021";"06.01.2021";"Lastschrift / Belastung";"Auftraggeber: PayPal (Europe) S.a.r.l. et Cie., S.C.A. Buchungstext: . FLIPDISH, Ihr Einkauf bei FLIPDIS H Ref. AA00000000000000/0000";"-9,00";
        "04.01.2021";"04.01.2021";"Übertrag / Überweisung";"Empfänger: Max MusterKto/IBAN: DE00000000000000000000 BLZ/BIC: XXXXXXXXXXX Buchungstext: Miete Schlossallee 1 Ref. A000000000000000/0";"-12001,02";
        """  # noqa
    assert _extract(StringIO(dedent(contents)), 'some-file', 'some-account')

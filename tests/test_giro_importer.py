from io import StringIO
from textwrap import dedent

from beancount_comdirect.giro_importer import _identify, _extract
from beancount_comdirect import accounts


def test_identify_empty_file():
    assert not _identify(StringIO(), accounts.STRUCTURE[accounts.CHECKING])


def test_identify_irrelevant_file():
    assert not _identify(
        StringIO('hello world'), accounts.STRUCTURE[accounts.CHECKING]
    )


def test_identiy_premature_eof():
    assert not _identify(
        StringIO(';\n"Ums'), accounts.STRUCTURE[accounts.CHECKING]
    )


def test_identify_minimal_checking_file():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        """  # noqa
    assert _identify(
        StringIO(dedent(contents)), accounts.STRUCTURE[accounts.CHECKING]
    )


def test_identify_with_credit_file():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";



        "Umsätze Visa-Karte (Kreditkarte)";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"0,33 EUR";

        "Buchungstag";"Umsatztag";"Vorgang";"Referenz";"Buchungstext";"Umsatz in EUR";
        """  # noqa
    assert _identify(
        StringIO(dedent(contents)), accounts.STRUCTURE[accounts.CREDIT]
    )


def test_identify_with_brokerage_file():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";



        "Umsätze Depot";"Zeitraum: 01.10.2010 - 16.01.2021";

        "Buchungstag";"Geschäftstag";"Stück / Nom.";"Bezeichnung";"WKN";"Währung";"Ausführungskurs";"Umsatz in EUR";
        """  # noqa
    assert _identify(
        StringIO(dedent(contents)), accounts.STRUCTURE[accounts.BROKERAGE]
    )


def test_extract_minimal():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        """  # noqa
    assert not _extract(
        StringIO(dedent(contents)),
        'some-file',
        accounts.STRUCTURE[accounts.CHECKING],
        'some-acc',
    )


def test_extract_basic():
    contents = """\
        ;
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        "06.01.2021";"06.01.2021";"Lastschrift / Belastung";"Auftraggeber: PayPal (Europe) S.a.r.l. et Cie., S.C.A. Buchungstext: . FLIPDISH, Ihr Einkauf bei FLIPDIS H Ref. AA00000000000000/0000";"-9,00";
        "04.01.2021";"04.01.2021";"Übertrag / Überweisung";"Empfänger: Max MusterKto/IBAN: DE00000000000000000000 BLZ/BIC: XXXXXXXXXXX Buchungstext: Miete Schlossallee 1 Ref. A000000000000000/0";"-12001,02";
        """  # noqa
    transactions = _extract(
        StringIO(dedent(contents)),
        'some-file',
        accounts.STRUCTURE[accounts.CHECKING],
        'some-acc',
    )

    assert len(transactions) == 2

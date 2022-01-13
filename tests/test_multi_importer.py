from io import StringIO
from textwrap import dedent
from datetime import date
from decimal import Decimal

from beancount_comdirect.multi_importer import _identify, _extract
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
        
        "Umsätze Girokonto";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"1.134,11 EUR";

        "Buchungstag";"Wertstellung (Valuta)";"Vorgang";"Buchungstext";"Umsatz in EUR";
        """  # noqa
    assert _identify(
        StringIO(dedent(contents)), accounts.STRUCTURE[accounts.CHECKING]
    )


def test_identify_with_credit_file():
    contents = """\
        
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
    first, second = transactions

    assert first.date == date(2021, 1, 6)
    assert first.payee == 'PayPal (Europe) S.a.r.l. et Cie., S.C.A.'
    assert (
        first.narration
        == '. FLIPDISH, Ihr Einkauf bei FLIPDIS H Ref. AA00000000000000/0000'
    )
    assert len(first.postings) == 1
    [posting] = first.postings
    assert posting.account == 'some-acc'
    assert posting.units.number == Decimal('-9')

    assert second.date == date(2021, 1, 4)
    assert (
        second.payee
        == 'Max MusterKto/IBAN: DE00000000000000000000 BLZ/BIC: XXXXXXXXXXX'
    )
    assert second.narration == 'Miete Schlossallee 1 Ref. A000000000000000/0'
    assert len(second.postings) == 1
    [posting] = second.postings
    assert posting.account == 'some-acc'
    assert posting.units.number == Decimal('-12001.02')


def test_extract_credit():
    contents = """\
        
        "Umsätze Visa-Karte (Kreditkarte)";"Zeitraum: 01.10.2010 - 16.01.2021";
        "Neuer Kontostand";"0,00 EUR";

        "Buchungstag";"Umsatztag";"Vorgang";"Referenz";"Buchungstext";"Umsatz in EUR";
        "30.04.2020";"30.04.2020";"Visa-Kartenabrechnung";"000000000000801";" SUMME MONATSABRECHNUNG VISA ";"56,10";
        """  # noqa
    transactions = _extract(
        StringIO(dedent(contents)),
        'some-file',
        accounts.STRUCTURE[accounts.CREDIT],
        'some-acc',
    )

    assert len(transactions) == 1
    [transaction] = transactions

    assert transaction.date == date(2020, 4, 30)
    assert not transaction.payee
    assert transaction.narration == ' SUMME MONATSABRECHNUNG VISA '
    assert len(transaction.postings) == 1
    [posting] = transaction.postings
    assert posting.account == 'some-acc'
    assert posting.units.number == Decimal('56.10')


def test_extract_brokerage():
    contents = """\
        
        "Umsätze Depot";"Zeitraum: 01.10.2010 - 16.01.2021";

        "Buchungstag";"Geschäftstag";"Stück / Nom.";"Bezeichnung";"WKN";"Währung";"Ausführungskurs";"Umsatz in EUR";
        "15.04.2020";"14.04.2020";"100";"SAP SE";"716460";"EUR";"51,91";"5.200,30";
        """  # noqa
    transactions = _extract(
        StringIO(dedent(contents)),
        'some-file',
        accounts.STRUCTURE[accounts.BROKERAGE],
        'some-acc',
    )

    assert len(transactions) == 1
    [transaction] = transactions
    assert transaction.date == date(2020, 4, 15)
    assert not transaction.payee
    assert transaction.narration == 'SAP SE'
    assert len(transaction.postings) == 3
    cash, fee, instrument = transaction.postings
    assert cash.units.number == Decimal('-5200.30')
    assert not fee.units
    assert instrument.units.number == 100
    assert instrument.units.currency == '716460'
    assert instrument.cost.number == Decimal('51.91')
    assert instrument.cost.currency == 'EUR'

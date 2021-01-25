CHECKING = 'checking'
CREDIT = 'credit'
SAVINGS = 'savings'
BROKERAGE = 'brokerage'

STRUCTURE = {
    CHECKING: {
        'type': CHECKING,
        'label': 'Girokonto',
        'has_balance': True,
        'fields': [
            'Buchungstag',
            'Wertstellung (Valuta)',
            'Vorgang',
            'Buchungstext',
            'Umsatz in EUR',
            '',
        ],
    },
    SAVINGS: {
        'type': SAVINGS,
        'label': 'Tagesgeld PLUS-Konto',
        'has_balance': True,
        'fields': [
            'Buchungstag',
            'Wertstellung (Valuta)',
            'Vorgang',
            'Buchungstext',
            'Umsatz in EUR',
            '',
        ],
    },
    CREDIT: {
        'type': CREDIT,
        'label': 'Visa-Karte (Kreditkarte)',
        'has_balance': True,
        'fields': [
            'Buchungstag',
            'Umsatztag',
            'Vorgang',
            'Referenz',
            'Buchungstext',
            'Umsatz in EUR',
            '',
        ],
    },
    BROKERAGE: {
        'type': BROKERAGE,
        'label': 'Depot',
        'has_balance': False,
        'fields': [
            'Buchungstag',
            'Geschäftstag',
            'Stück / Nom.',
            'Bezeichnung',
            'WKN',
            'Währung',
            'Ausführungskurs',
            'Umsatz in EUR',
            '',
        ],
    },
}

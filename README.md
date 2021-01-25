# beancount-comdirect

A [beancount](https://github.com/beancount/beancount) importer for [comdirect](https://comdirect.de). **Work in progress.**


## Usage

```python
from beancount_comdirect.giro_importer import GiroImporter
from beancount_comdirect.accounts import (
    CHECKING, SAVINGS, BROKERAGE, CREDIT
)

CONFIG = [
    # Note that you have to configure the importer once per each account type
    # that want to enable (CSVs always contain all accounts).

    GiroImporter(CHECKING, 'Assets:Checking'),
    # GiroImporter(SAVINGS, 'Assets:Savings'),
    # GiroImporter(BROKERAGE, 'Assets:Stocks'),
    # GiroImporter(CREDIT, 'Liabilities:Credit'),
]
```

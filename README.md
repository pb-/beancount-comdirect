# beancount-comdirect

A [beancount](https://github.com/beancount/beancount) importer for [comdirect](https://comdirect.de). **Work in progress.**


## Usage

```python
from beancount_comdirect.multi_importer import MultiImporter
from beancount_comdirect.accounts import (
    CHECKING, SAVINGS, BROKERAGE, CREDIT
)

CONFIG = [
    # Note that you have to configure the importer once per each account type
    # that want to enable (CSVs always contain all accounts).

    MultiImporter(CHECKING, 'Assets:Checking'),
    # MultiImporter(SAVINGS, 'Assets:Savings'),
    # MultiImporter(BROKERAGE, 'Assets:Stocks'),
    # MultiImporter(CREDIT, 'Liabilities:Credit'),
]
```

# StockXAPI
API for StockX using Python.

## Requirements
Install all requirements using:
```
pip install -r requirements.txt
```
## Demo Use
```python
from stockx import StockXAPI
stockx = StockXAPI()

products = stockx.search_items('supreme', output_data=['name', 'id', ['market', 'lastSale']])
for product in products:
    print(product)
```

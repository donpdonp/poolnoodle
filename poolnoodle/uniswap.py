from decimal import Decimal

#class Uniswap:
    #def __init__(self, chain: str, contract_addr: str):
def price(x: Decimal, y: Decimal, x_add: Decimal):
    k = x * y
    out = k / (x + x_add) - y
    return x_add / out

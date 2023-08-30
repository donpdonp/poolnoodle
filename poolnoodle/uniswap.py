from decimal import Decimal

#class Uniswap:
    #def __init__(self, chain: str, contract_addr: str):

    # UniswapV2Library.sol
    # function getAmountOut(uint amountIn, uint reserveIn, uint reserveOut) internal pure returns (uint amountOut) {
    #     require(amountIn > 0, 'UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT');
    #     require(reserveIn > 0 && reserveOut > 0, 'UniswapV2Library: INSUFFICIENT_LIQUIDITY');
    #     uint amountInWithFee = amountIn.mul(997);
    #     uint numerator = amountInWithFee.mul(reserveOut);
    #     uint denominator = reserveIn.mul(1000).add(amountInWithFee);
    #     amountOut = numerator / denominator;
    # }

def price(x: Decimal, y: Decimal, x_add: Decimal):
    k = x * y
    out = k / (x + x_add) - y
    return -1 * x_add / out

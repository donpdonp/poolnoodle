from decimal import Decimal

# UniswapV2Library.sol
# function getAmountOut(uint amountIn, uint reserveIn, uint reserveOut) internal pure returns (uint amountOut) {
#     require(amountIn > 0, 'UniswapV2Library: INSUFFICIENT_INPUT_AMOUNT');
#     require(reserveIn > 0 && reserveOut > 0, 'UniswapV2Library: INSUFFICIENT_LIQUIDITY');
#     uint amountInWithFee = amountIn.mul(997);
#     uint numerator = amountInWithFee.mul(reserveOut);
#     uint denominator = reserveIn.mul(1000).add(amountInWithFee);
#     amountOut = numerator / denominator;
# }


def getAmountOut(amountIn: Decimal, reserveIn: Decimal, reserveOut: Decimal):
    amountInWithFee = amountIn * 997
    numerator = amountInWithFee * reserveOut
    denominator = (reserveIn * 1000) + amountInWithFee
    return numerator / denominator


def price(x: Decimal, y: Decimal, x_add: Decimal):
    return x_add / getAmountOut(x_add, x, y)

from decimal import Decimal
from typing import List

#class Curve:
    #def __init__(self, chain: str, contract_addr: str):
def price(A: int, x: Decimal, y: Decimal, x_add: Decimal):
    # constant sum -> D = (x+y)
    # constant product -> (D/2)^2 =  (x*y)
    out = get_D([x + x_add, y], A)
    return x_add / out


# https://github.com/curvefi/curve-contract/blob/master/contracts/pools/steth/StableSwapSTETH.vy#L211
def get_D(xp: List[Decimal], amp: int) -> Decimal:
    """
    D invariant calculation in non-overflowing integer operations
    iteratively

    A * sum(x_i) * n**n + D = A * D * n**n + D**(n+1) / (n**n * prod(x_i))

    Converging solution:
    D[j+1] = (A * n**n * sum(x_i) - D[j]**(n+1) / (n**n prod(x_i))) / (A * n**n - 1)
    """
    N_COINS = len(xp)
    A_PRECISION = 18
    S: Decimal = Decimal(0)
    Dprev: Decimal = Decimal(0)

    for _x in xp:
        S += _x
    if S == 0:
        return Decimal(0)

    D: Decimal= S
    Ann: Decimal = Decimal(amp * N_COINS)
    for _i in range(255):
        D_P: Decimal = D
        for _x in xp:
            D_P = D_P * D / (_x * N_COINS + 1)  # +1 is to prevent /0
        Dprev = D
        D = (Ann * S / A_PRECISION + D_P * N_COINS) * D / ((Ann - A_PRECISION) * D / A_PRECISION + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                return D
        else:
            if Dprev - D <= 1:
                return D
    # convergence typically occurs in 4 rounds or less, this should be unreachable!
    # if it does happen the pool is borked and LPs can withdraw via `remove_liquidity`
    raise

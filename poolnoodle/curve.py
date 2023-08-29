from decimal import Decimal
from typing import List

#class Curve:
    #def __init__(self, chain: str, contract_addr: str):
def price(A: int, x: Decimal, y: Decimal, x_add: Decimal, fee: Decimal):
    # constant sum -> D = (x+y)
    # constant product -> (D/2)^2 =  (x*y)
    out = get_dy(0, 1, x_add, [x, y], A, fee)
    return x_add / out

def get_dy(i: int, j: int, dx: Decimal, xp: List[Decimal], amp: int, fee: Decimal) -> Decimal:
    N_COINS = len(xp)
    FEE_DENOMINATOR = 10 ** 10
    x: Decimal = xp[i] + dx
    y: Decimal = get_y(i, j, x, xp, amp)
    dy: Decimal = xp[j] - y - 1
    fee2: Decimal = fee * dy / FEE_DENOMINATOR
    return dy - fee2

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


def get_y(i: int, j: int, x: Decimal, xp: List[Decimal], amp: int) -> Decimal:
    #Calculate x[j] if one makes x[i] = x

    #Done by solving quadratic equation iteratively.
    #x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    #x_1**2 + b*x_1 = c

    #x_1 = (x_1**2 + c) / (2*x_1 + b)
    #
    # x in the input is converted to the same price/precision
    N_COINS = len(xp)
    A_PRECISION = 18

    #assert i != j       # dev: same coin
    #assert j >= 0       # dev: j below zero
    #assert j < N_COINS  # dev: j above N_COINS

    # should be unreachable, but good for safety
    #assert i >= 0
    #assert i < N_COINS

    D: Decimal = get_D(xp, amp)
    Ann: int= amp * N_COINS
    c: Decimal = D
    S_: Decimal = Decimal(0)
    _x: Decimal = Decimal(0)
    y_prev: Decimal = Decimal(0)

    for _i in range(N_COINS):
        if _i == i:
            _x = x
        elif _i != j:
            _x = xp[_i]
        else:
            continue
        S_ += _x
        c = c * D / (_x * N_COINS)
    c = c * D * A_PRECISION / (Ann * N_COINS)
    b: Decimal = S_ + D * A_PRECISION / Ann  # - D
    y: Decimal = D
    for _i in range(255):
        y_prev = y
        y = (y*y + c) / (2 * y + b - D)
        # Equality with the precision of 1
        if y > y_prev:
            if y - y_prev <= 1:
                return y
        else:
            if y_prev - y <= 1:
                return y
    raise


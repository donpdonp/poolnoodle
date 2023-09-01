import logging
import time
import sys
import yaml
import requests
import web3.constants
from web3.datastructures import AttributeDict
from web3 import Web3, HTTPProvider
from pathlib import Path
from eth_account import Account
from decimal import *
from poolnoodle import uniswap,curve
from poolnoodle.coin import Coin
from poolnoodle.pool import Pool
from poolnoodle.util import *

CONFIG = yaml.safe_load(Path("config.yaml").read_text())

def logger_init():
    logger = logging.getLogger()
    logging.getLogger("web3.RequestManager").setLevel(logging.DEBUG)
    return logger


def do_curve(amount_to_send_wei: Decimal, buy: bool):
    curve_steth_pool_address = "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"  # steth
    # https://curve.fi/#/ethereum/pools/steth/deposit
    curve_abi = Path("abi/curve.abi").read_text()
    curve_pool = w3.eth.contract(address=curve_steth_pool_address, abi=curve_abi)

    curve_t0 = curve_pool.functions.coins(0).call(block_identifier=LAST_BLOCK)  # eth
    curve_t1 = curve_pool.functions.coins(1).call(block_identifier=LAST_BLOCK)  # steth
    curve_fee = Decimal(curve_pool.functions.fee().call(block_identifier=LAST_BLOCK)) / Decimal(1e10)
    

    curve_A = curve_pool.functions.A().call(block_identifier=LAST_BLOCK)
    print(f"curve t0:{curve_t0} t1:{curve_t1} fee:{curve_fee} A:{curve_A}")
    curve_t0_reserve: Decimal = Decimal(curve_pool.functions.balances(0).call(block_identifier=LAST_BLOCK))
    curve_t1_reserve: Decimal = Decimal(curve_pool.functions.balances(1).call(block_identifier=LAST_BLOCK))
    curve_reserve_price = curve_t0_reserve / curve_t1_reserve
    print(
        f"curve reserves t0: {w3.from_wei(curve_t0_reserve, 'ether')} t1: {w3.from_wei(curve_t1_reserve, 'ether')} reserve price t0/t1: {curve_reserve_price} w/ {curve_fee} fee price: {curve_reserve_price * (1+curve_fee)}"
    )
    curve_reserve_calc_price = curve.price(curve_A, curve_t0_reserve, curve_t1_reserve, Decimal(1), curve_fee)
    print(f"curve reserve calc price {curve_reserve_calc_price} w/ fee {curve_reserve_calc_price * (1+curve_fee)} (fee {curve_fee})")
    curve_calc_price = curve.price(curve_A, curve_t0_reserve, curve_t1_reserve, amount_to_send_wei, curve_fee)
    print(f"curve calc price {curve_calc_price } w/ fee {curve_calc_price*(1+curve_fee)} after buying {amount_to_send_wei}")

    if buy:
        in_market = 0
        out_market = 1
    else:
        in_market = 1
        out_market = 0
    # def get_dy_underlying(i: int128, j: int128, dx: uint256) -> uint256:
    # How much of underlying token j you'll get in exchange for dx of token i, including the fee.
    curve_amount_wei = curve_pool.functions.get_dy(in_market, out_market, amount_to_send_wei).call(
        block_identifier=LAST_BLOCK
    )
    curve_price_wei = Decimal(amount_to_send_wei) / Decimal(curve_amount_wei)
    curve_price_nofee = curve_price_wei / Decimal(1 - curve_fee)
    print(
        f"curve get_dy t0 {amount_to_send_wei} amount out t1 {curve_amount_wei} price t0/t1 {curve_price_wei} eth"
    )
    # curve_amount3_wei = curve.functions.get_dy(1, 0, curve_amount_wei).call(
    #     block_identifier=LAST_BLOCK
    # )
    # curve_price3_wei = Decimal(curve_amount3_wei) / Decimal(curve_amount_wei)
    # print(
    #     f"curve get_dy t1 {curve_amount_wei} amount out t0 {curve_amount3_wei} price t0/t1 {curve_price3_wei} eth"
    # )
    # curve_price_change = (curve_price_wei - curve_price3_wei) / Decimal(1-curve_fee)
    # print(
    #     f"curve loop eth->steth->eth profit {curve_amount3_wei - curve_amount_wei} wei. {curve_price_change} price change"
    # )
    return curve_amount_wei


def do_uniswap(starting_wei: Decimal, buy: bool):
    uniswap_permit2_abi = Path("abi/permit2.abi").read_text()
    uniswap_permit2_address = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
    uniswap_permit2 = w3.eth.contract(
        address=uniswap_permit2_address, abi=uniswap_permit2_abi
    )

    # uniswap_pool_address = "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc" #usdc
    uniswap_pool_address = "0x4028DAAC072e492d34a3Afdbef0ba7e35D8b55C4"  # steth
    # https://v2.info.uniswap.org/pair/0x4028DAAC072e492d34a3Afdbef0ba7e35D8b55C4
    uniswap_pool_abi = Path("abi/uniswap-pair.abi").read_text()
    uniswap_pool = w3.eth.contract(address=uniswap_pool_address, abi=uniswap_pool_abi)
    uniswap_universal_router_address = "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B"
    uniswap_router2_address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    uniswap_router2_abi = Path("abi/uniswap-router.abi").read_text()
    uniswap_router2 = w3.eth.contract(
        address=uniswap_router2_address, abi=uniswap_router2_abi
    )

    # uniswap_pool_allowance = uniswap_pool.functions.allowance(
    #    uniswap_pool_address, account.address
    # ).call(block_identifier=LAST_BLOCK)
    # print("uniswap_pool_allowance", uniswap_pool_allowance)

    uniswap_t0 = uniswap_pool.functions.token0().call(
        block_identifier=LAST_BLOCK
    )  # steth
    uniswap_t1 = uniswap_pool.functions.token1().call(
        block_identifier=LAST_BLOCK
    )  # weth
    uniswap_fee: Decimal = Decimal(0.003)
    print(f"uniswap t0: {uniswap_t0} t1: {uniswap_t1} fee: {uniswap_fee}")
    uniswap_reserves = uniswap_pool.functions.getReserves().call(
        block_identifier=LAST_BLOCK
    )
    uniswap_t0_reserve: Decimal = Decimal(uniswap_reserves[0])
    uniswap_t1_reserve: Decimal = Decimal(uniswap_reserves[1])
    uniswap_reserve_price: Decimal = uniswap_t1_reserve / uniswap_t0_reserve
    print(
        f"uniswap reserves t0: {uniswap_t0_reserve} t1: {uniswap_t1_reserve} reserve price t1/t0 {uniswap_reserve_price} w/ fee {uniswap_reserve_price/Decimal(1-uniswap_fee)}"
    )

    if buy:
        in_market = 1
        out_market = 0
    else:
        in_market = 0
        out_market = 1

    uniswap_reserve_calc_price = uniswap.price(Decimal(uniswap_reserves[in_market]),Decimal(uniswap_reserves[out_market]), Decimal(1))
    print(f"uniswap reserve calc price {uniswap_reserve_calc_price} w/ fee {uniswap_reserve_calc_price * (1+uniswap_fee)} (fee {uniswap_fee})")
    uniswap_calc_price = uniswap.price(Decimal(uniswap_reserves[in_market]),Decimal(uniswap_reserves[out_market]), starting_wei)
    print(f"uniswap calc buy {starting_wei} price {uniswap_calc_price }")

    # // given an input amount of an asset and pair reserves, returns the maximum output amount of the other asset
    # function getAmountOut(uint amountIn, uint reserveIn, uint reserveOut) internal pure returns (uint amountOut) {
    uniswap_amount_out_wei: Decimal = uniswap_router2.functions.getAmountOut(
        starting_wei, uniswap_reserves[in_market], uniswap_reserves[out_market]
    ).call(block_identifier=LAST_BLOCK)
    uniswap_amount_price: Decimal = starting_wei / Decimal(uniswap_amount_out_wei)
    uniswap_amount_price_nofee: Decimal = uniswap_amount_price / Decimal(
        1 - uniswap_fee
    )
    print(
        f"uniswap getAmountOut t1 {starting_wei} out t0 {uniswap_amount_out_wei} price {starting_wei / uniswap_amount_out_wei} eth"
    )
    # uniswap_amount_out2_wei = uniswap_router2.functions.getAmountOut(
    #     uniswap_amount_out_wei, uniswap_reserves[0], uniswap_reserves[1]
    # ).call(block_identifier=LAST_BLOCK)
    # uniswap_calc_price = Decimal(uniswap_amount_out2_wei) / Decimal(starting_wei)
    # uniswap_price_change = (uniswap_calc_price - uniswap_amount_price) / Decimal(1-uniswap_fee)
    # print(
    #     f"uniswap loop eth->steth->eth {uniswap_amount_out2_wei - starting_wei} profit. {uniswap_price_change} price change"
    # )
    return uniswap_amount_out_wei

logger = logger_init()
steth_coin = Coin("ethereum", "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
weth_coin = Coin("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=ethereum,staked-ether"
coin_prices = requests.get(COINGECKO_URL).json()
eth_price_usd = Decimal(coin_prices[0]["current_price"])
steth_price_usd = Decimal(coin_prices[1]["current_price"])

INFURA_URL = "https://mainnet.infura.io/v3/" + CONFIG["keys"]["infura"]
w3 = Web3(HTTPProvider(INFURA_URL))
if len(sys.argv) > 1 and sys.argv[1]:
    LAST_BLOCK = int(sys.argv[1])
else:
    LAST_BLOCK = w3.eth.block_number
print("Latest Ethereum block number", LAST_BLOCK)

account = Account.from_key(CONFIG["keys"]["wallet"])
if len(sys.argv) > 2 and sys.argv[2]:
    balance_wei = w3.to_wei(sys.argv[2], "ether")
else:
    balance_wei = w3.eth.get_balance(account.address) * 0.9  # leave 10% for fees
amount_to_send_wei = w3.to_wei(balance_wei, "wei")
amount_to_send_eth = w3.from_wei(amount_to_send_wei, "ether")
print(
    f"{account.address} balance {w3.from_wei(balance_wei, 'ether')} eth amount_to_send {amount_to_send_eth} eth"
)

cleft = do_curve(amount_to_send_wei, True)
cu_ending_wei = do_uniswap(cleft, False)
print(f"-> curve->uniswap {(cu_ending_wei - amount_to_send_wei)/10**18}")
uleft = do_uniswap(amount_to_send_wei, True)
uc_ending_wei = do_curve(uleft, False)
print(f"-> uniswap->curve {(uc_ending_wei - amount_to_send_wei)/10**18}")
ending_wei = cu_ending_wei
if uc_ending_wei > cu_ending_wei:
    ending_wei = uc_ending_wei

print(
    f"remaining_wei = amount_to_send_wei {amount_to_send_wei} - ending_wei {ending_wei}"
)
remaining_wei = ending_wei - amount_to_send_wei
uniswap_gas = 240000
curve_gas = 180000
gas_price = 25  # todo
total_gas_wei = (uniswap_gas + curve_gas) * 1e9 * gas_price
pl_word = "profit" if remaining_wei > 0 else "loss"
print(
    f"** {pl_word} {remaining_wei/1e18:.6f} eth - total_gas {w3.from_wei(total_gas_wei, 'ether'):.6f} eth"
)

if remaining_wei > total_gas_wei:
    nonce = w3.eth.get_transaction_count(account.address)
else:
    print(
        f"no opp. gas fee exceeds profit by {w3.from_wei(total_gas_wei - remaining_wei, 'ether'):.6f} "
    )

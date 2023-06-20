from web3.datastructures import AttributeDict
from web3 import Web3, HTTPProvider
import web3.constants
from pathlib import Path
import requests
from eth_account import Account
from decimal import *
import logging
import time
import sys
from poolnoodle.coin import Coin
import yaml

CONFIG = yaml.safe_load(Path('config.yaml').read_text())

steth_coin = Coin("ethereum", "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
weth_coin = Coin("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")

def coinprint(v, usd):
    return f"{v:.5f} (${v*usd:.2f})"

logger = logging.getLogger()
logging.getLogger("web3.RequestManager").setLevel(logging.DEBUG)

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=ethereum,staked-ether"
)
coin_prices = requests.get(COINGECKO_URL).json()
eth_price_usd = Decimal(coin_prices[0]["current_price"])
steth_price_usd = Decimal(coin_prices[1]["current_price"])

INFURA_URL = "https://mainnet.infura.io/v3/"+CONFIG["keys"]["infura"]
w3 = Web3(HTTPProvider(INFURA_URL))
print("Latest Ethereum block number", w3.eth.block_number)

account = Account.from_key(CONFIG["keys"]["wallet"])
balance_wei = w3.eth.get_balance(account.address)
amount_to_send_wei = w3.to_wei(balance_wei * 0.9, "wei")  # 90% of balance
amount_to_send_eth = w3.from_wei(amount_to_send_wei, "ether")
print(f"{account.address} balance {w3.from_wei(balance_wei, 'ether')} eth amount_to_send {amount_to_send_eth} eth")

curve_steth_pool_address = "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"  # steth
# https://curve.fi/#/ethereum/pools/steth/deposit
curve_abi = Path("abi/curve.abi").read_text()
curve = w3.eth.contract(address=curve_steth_pool_address, abi=curve_abi)

curve_t0 =  curve.functions.coins(0).call()
curve_t1 =  curve.functions.coins(1).call()
print(
    f"curve t0:{curve_t0} t1:{curve_t1}"
)
curve_t0_reserve = curve.functions.balances(0).call()
curve_t1_reserve = curve.functions.balances(1).call()
curve_fee = 0.0004 # curve.functions.fee().call() / 1e10
curve_reserve_price = curve_t0_reserve/curve_t1_reserve
print(f"curve reserves t0: {curve_t0_reserve} t1: {curve_t1_reserve} t0/t1: {curve_reserve_price} w/ 0.04% fee {curve_reserve_price * (1+curve_fee)}")

# def get_dy_underlying(i: int128, j: int128, dx: uint256) -> uint256:
# How much of underlying token j you'll get in exchange for dx of token i, including the fee.
curve_amount_wei = curve.functions.get_dy(0, 1, amount_to_send_wei).call()
curve_price_wei = Decimal(amount_to_send_wei) / Decimal(curve_amount_wei)
curve_price_eth = w3.from_wei(curve_price_wei, 'ether')
print(f"curve in t0 {amount_to_send_wei} amount out t1 {curve_amount_wei} price {curve_price_wei} eth")

uniswap_permit2_abi = Path("abi/permit2.abi").read_text()
uniswap_permit2_address = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
uniswap_permit2 = w3.eth.contract(address=uniswap_permit2_address, abi=uniswap_permit2_abi)

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

uniswap_pool_allowance = uniswap_pool.functions.allowance(
    uniswap_pool_address, account.address
).call()
print("uniswap_pool_allowance", uniswap_pool_allowance)

uniswap_t0 = uniswap_pool.functions.token0().call()
uniswap_t1 = uniswap_pool.functions.token1().call()
print(f"uniswap t0: {uniswap_t0} t1: {uniswap_t1}")
uniswap_reserves = uniswap_pool.functions.getReserves().call()
uniswap_t0_reserve = uniswap_reserves[0]
uniswap_t1_reserve = uniswap_reserves[1]
uniswap_fee = 0.003
uniswap_reserve_price = uniswap_t1_reserve/uniswap_t0_reserve
print(f"uniswap reserves t0: {uniswap_t0_reserve} t1: {uniswap_t1_reserve} price t1/t0 {uniswap_reserve_price} price w/ 0.3% fee {uniswap_reserve_price*(1+uniswap_fee)}")
print(f"uniswap reserves t0: {uniswap_t0_reserve} t1: {uniswap_t1_reserve} price t0/t1 {1/uniswap_reserve_price} price w/ 0.3% fee {(1/uniswap_reserve_price)*(1-uniswap_fee)}")

uniswap_route_path = [uniswap_t1, uniswap_t0]
# function getAmountsOut(uint amountIn, address[] memory path) internal view returns (uint[] memory amounts);
uniswap_amounts_out_wei = uniswap_router2.functions.getAmountsOut(amount_to_send_wei, uniswap_route_path).call()
uniswap_amount_wei = uniswap_amounts_out_wei[1]
uniswap_price_eth = Decimal(uniswap_amounts_out_wei[0]) / Decimal(uniswap_amounts_out_wei[1])
print(f"uniswap getAmountsOut [t1, t0] {uniswap_amounts_out_wei} price {uniswap_price_eth}")

uniswap_amount_out_wei = uniswap_router2.functions.getAmountOut( w3.to_wei(1, 'ether'), uniswap_reserves[1], uniswap_reserves[0] ).call()
print(f"uniswap getAmountOut 1 eth t1 {10**18} out t0 {uniswap_amount_out_wei} price {10**18 / uniswap_amount_out_wei} grr {uniswap_amount_out_wei / 10**18}")
uniswap_amount_out2_wei = uniswap_router2.functions.getAmountOut( w3.to_wei(1, 'ether'), uniswap_reserves[0], uniswap_reserves[1] ).call()
print(f"uniswap getAmountOut 1 eth t0 {10**18} out t1 {uniswap_amount_out2_wei} price {10**18 / uniswap_amount_out_wei} grr {uniswap_amount_out_wei / 10**18}")
uniswap_amount_out3_wei = uniswap_router2.functions.getAmountOut( uniswap_amount_out2_wei, uniswap_reserves[1], uniswap_reserves[0] ).call()
print(f"uniswap getAmountOut 1 eth t1 {uniswap_amount_out2_wei} out t0 {uniswap_amount_out3_wei} price {10**18 / uniswap_amount_out_wei} grr {uniswap_amount_out_wei / 10**18}")
print(f"quick loop {(1e18 - uniswap_amount_out3_wei) / 1e18} loss")

nonce = w3.eth.get_transaction_count(account.address)
steth_amount_diff_wei = abs(curve_amount_wei - uniswap_amount_wei)
print(f"steth_amount_diff_wei {steth_amount_diff_wei} = curve_amount_wei {curve_amount_wei} - uniswap_amount_wei {uniswap_amount_wei}")
print(f"** steth_amount_diff_wei {steth_amount_diff_wei} {coinprint(w3.from_wei(steth_amount_diff_wei, 'ether'), steth_price_usd)}")
print(f"** amount_diff per eth {steth_amount_diff_wei / amount_to_send_wei}")

print(f"if curve_amount_wei {curve_amount_wei} < uniswap_amount_wei {uniswap_amount_wei} = {curve_amount_wei < uniswap_amount_wei}")
if curve_amount_wei < uniswap_amount_wei:
    print(f"-> curve to uniswap")
    # 0: eth 1: steth
    # exchange(i,j,dx,min_dy)
    # i: Index value for the coin to send
    # j: Index value of the coin to receive
    # _dx: Amount of i being exchanged
    # _min_dy: Minimum amount of j to receive
    # Returns the actual amount of coin j received.
    # tx = curve.functions.exchange(0, 1, 0, 0).estimate_gas()
    # print("curve tx ", tx)
    # ttx = tx.build_transaction({"nonce": nonce})
    # print("curve build_transaction", ttx)
    # gas_estimate = w3.eth.estimate_gas(ttx)
    # print(f"gas_estimate {gas_estimate}")
else:
    print(f"-> uniswap to curve")
    slip_percent = 0.0
    slip_value = Decimal(1 - slip_percent / 100)
    min_to_receive = int(uniswap_amount_wei * slip_value )  # 0.1% slippage
    print(f"slip percent {slip_percent}% value {slip_value} = min_to_receive {min_to_receive}")
    deadline = int(time.time()) + (1000 * 15) # 30 sec
    path = [uniswap_t1, uniswap_t0]

    print(
        f"swapExactTokensForTokens amount_to_send:{amount_to_send_wei},",
        f"min_to_receive:{min_to_receive} {path} {account.address} deadline:{deadline} ({time.asctime(time.localtime(deadline))})",
    )

    # function swapExactTokensForTokens( uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external returns (uint[] memory amounts);
    tx = uniswap_router2.functions.swapExactETHForTokens(
        min_to_receive,
        path,
        account.address,
        deadline,
    ).build_transaction(
        {"from": account.address, "nonce": nonce, "value": amount_to_send_wei}
    )  # gas 187556
    print("tx", tx)

    gas_cost_gwei = float(
        requests.get(
            "https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey=8SWWRK1EIPCW21FR4QGRC4P9MQQTVKAJF2"
        ).json()["result"]["FastGasPrice"]
    )
    gas_cost_wei = w3.to_wei(gas_cost_gwei, "gwei")
    gas_cost_eth = w3.from_wei(gas_cost_wei, "ether")
    tx_gas = tx["gas"]
    gas_fee_eth = tx_gas * gas_cost_eth
    print(
        f"ETH coingecko ${eth_price_usd:.2f} gas price {gas_cost_gwei}gwei gas {tx_gas} gas fee {coinprint(gas_fee_eth, eth_price_usd)}"
    )

    tx_signed = w3.eth.account.sign_transaction(tx, account.key)

    curve_amount2_wei = curve.functions.get_dy(1, 0, min_to_receive).call()
    print(f"curve min_to_receive t1 {min_to_receive} returns t0 {curve_amount2_wei}")

    revenue_wei = curve_amount2_wei - amount_to_send_wei
    revenue_eth = w3.from_wei(revenue_wei, 'ether')
    profit_eth = revenue_eth - gas_cost_eth*2
    print(f"revenue_eth {revenue_eth} - gasx2 {gas_cost_eth*2} = profit_eth {profit_eth}")
    if profit_eth > 0:
        print("GO!")
        # tx_hash = w3.eth.send_raw_transaction(tx_signed.rawTransaction)

        # step 2, curve
        min_curve = int(min_to_receive * 0.99)
        tx = curve.functions.exchange(
            1, 0, min_curve, 0
        ).estimate_gas()  # steth -> eth
        print(f"curve.exchange(1,0,{min_to_receive})")
        print("curve tx ", tx)
        ttx = tx.build_transaction({"nonce": nonce})
    else:
        print("STOP!")
        print(f"Breakeven eth {gas_fee_eth*2/revenue_eth:.4f}")

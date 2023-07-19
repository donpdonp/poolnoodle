def curve_buy():
    1
    # 0: eth 1: steth
    # exchange(i,j,dx,min_dy)
    # i: Index value for the coin to send
    # j: Index value of the coin to receive
    # _dx: Amount of i being exchanged
    # _min_dy: Minimum amount of j to receive
    # Returns the actual amount of coin j received.
    # tx = curve.functions.exchange(0, 1, amount_to_send_wei, 0).estimate_gas()
    # print("curve tx ", tx)
    # ttx = tx.build_transaction({"nonce": nonce})
    # print("curve build_transaction", ttx)
    # gas_estimate = w3.eth.estimate_gas(ttx)
    # print(f"gas_estimate {gas_estimate}")


def uniswap_buy():
    slip_percent = 0.0
    slip_value = Decimal(1 - slip_percent / 100)
    min_to_receive = int(uniswap_amount_wei * slip_value)  # 0.1% slippage
    print(
        f"slip percent {slip_percent}% value {slip_value} = min_to_receive {min_to_receive}"
    )
    deadline = int(time.time()) + (1000 * 15)  # 30 sec
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

    curve_amount2_wei = curve.functions.get_dy(1, 0, min_to_receive).call(
        block_identifier=LAST_BLOCK
    )
    print(f"curve min_to_receive t1 {min_to_receive} returns t0 {curve_amount2_wei}")

    revenue_wei = abs(curve_amount2_wei - amount_to_send_wei)
    print(
        f"revenue_wei {revenue_wei} = curve_amount2_wei {curve_amount2_wei} - amount_to_send_wei {amount_to_send_wei}"
    )
    revenue_eth = w3.from_wei(revenue_wei, "ether")
    profit_eth = revenue_eth - gas_fee_eth * 2
    print(
        f"revenue_eth {revenue_eth} - gasx2 {gas_fee_eth*2} = profit_eth {coinprint(profit_eth, eth_price_usd)}"
    )
    if profit_eth > 0:
        print("GO!")
        # tx_hash = w3.eth.send_raw_transaction(tx_signed.rawTransaction)

        # step 2, curve
        min_curve = int(min_to_receive * 0.99)
        tx = curve.functions.exchange(1, 0, min_curve, 0).estimate_gas()  # steth -> eth
        print(f"curve.exchange(1,0,{min_to_receive})")
        print("curve tx ", tx)
        ttx = tx.build_transaction({"nonce": nonce})
    else:
        print("STOP!")
        print(f"Breakeven eth {gas_fee_eth*2/revenue_eth:.4f}")

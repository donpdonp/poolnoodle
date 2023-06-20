# ERC20_ABI = Path("abi/erc20.abi").read_text()
# usdc_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
# dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
# weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
# usdc = w3.eth.contract(address=usdc_address, abi=ERC20_ABI)
# usdc_balance = usdc.functions.balanceOf(account.address).call()
# usdc_decimals = usdc.functions.decimals().call()
# print("usdc balance", f"${usdc_balance / 10**usdc_decimals}", usdc_decimals, "decimals")

# usdc_allowance = usdc.functions.allowance(
#     _owner=account.address, _spender=uniswap_router2_address
# ).call()
# print(
#     f"usdc.allowance from {account.address} spender <uniswap.router2> = {usdc_allowance}"
# )
# if usdc_allowance == 0:
#     nonce = w3.eth.get_transaction_count(account.address)
#     approve_tx = usdc.functions.approve(
#         _spender=uniswap_router2_address, _value=(2**256) - 1
#     ).build_transaction({"from": account.address, "nonce": nonce})
#     print("approve_tx", type(approve_tx), approve_tx)
#     approve_tx_signed = w3.eth.account.sign_transaction(approve_tx, account.key)
#     # tx_hash = w3.eth.send_raw_transaction(approve_tx_signed.rawTransaction)
#     # print("usdc approve:", tx_hash.hex())
#     sys.exit(0)

class Coin:
    def __init__(self, chain: str, contract_addr: str):
        if len(contract_addr) != 42:
            raise Exception(f"bad contract address {contract_addr}")
        self.chain = chain
        self.contract_addr = contract_addr

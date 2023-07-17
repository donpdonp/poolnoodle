// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

import './interfaces/IUniswapV2Pair.sol';
import './interfaces/ICurvePair.sol';

address constant curve_steth = 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022;
address constant uniswap_steth = 0x4028DAAC072e492d34a3Afdbef0ba7e35D8b55C4;

contract twostep {
  function swap(uint out) public payable {
    ICurvePair curve = ICurvePair(curve_steth);
    out = curve.exchange(1, 0, msg.value, 0);
    IUniswapV2Pair uniswap = IUniswapV2Pair(uniswap_steth);
    uniswap.swap(out, out, msg.sender, "0x");
  }
}

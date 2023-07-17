// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.5.0;

interface ICurvePair {

    function exchange(
      uint i,
      uint j,
      uint dx,
      uint min_dy
    ) external returns (uint out) ;
}

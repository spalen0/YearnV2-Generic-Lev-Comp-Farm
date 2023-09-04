// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

interface IVelodromeRouter {

    struct Route {
        address from;
        address to;
        bool stable;
        address factory;
    }

    function sortTokens(address tokenA, address tokenB) external pure returns (address token0, address token1);

    // calculates the CREATE2 address for a pair without making any external calls
    /// @notice Wraps around poolFor(tokenA,tokenB,stable,_factory) for backwards compatibility to Velodrome v1
    function pairFor(address tokenA, address tokenB, bool stable, address _factory) external view returns (address pool);

    // fetches and sorts the reserves for a pair
    function getReserves(address tokenA, address tokenB, bool stable, address _factory) external view returns (uint reserveA, uint reserveB);

    // performs chained getAmountOut calculations on any number of pairs
    function getAmountsOut(uint amountIn, Route[] memory routes) external view returns (uint[] memory amounts);

    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        Route[] calldata routes,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);

    function swapExactETHForTokens(uint amountOutMin, Route[] calldata routes, address to, uint deadline)
        external
        payable
        returns (uint[] memory amounts);

    function swapExactTokensForETH(uint amountIn, uint amountOutMin, Route[] calldata routes, address to, uint deadline)
        external
        returns (uint[] memory amounts);

    function UNSAFE_swapExactTokensForTokens(
        uint[] memory amounts,
        Route[] calldata routes,
        address to,
        uint deadline
    ) external returns (uint[] memory);
}

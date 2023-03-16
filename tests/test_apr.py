from itertools import count
from brownie import Wei, reverts, Contract, interface
from utils import actions, checks, utils
from useful_methods import (
    stateOfStrat,
    stateOfVault,
    genericStateOfStrat,
    genericStateOfVault,
)
import pytest


def test_apr(
    chain,
    accounts,
    token,
    vault,
    strategy,
    interface,
    user,
    strategist,
    gov,
    amount,
    RELATIVE_APPROX,
):
    # Deposit to the vault
    # gov = accounts.at(vault.governance(), force=True)
    comp = interface.ERC20(strategy.comp())
    user_balance_before = token.balanceOf(user)
    actions.user_deposit(user, vault, token, amount)

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    strategy.setProfitFactor(1, {"from": gov})
    # assert enormousrunningstrategy.profitFactor() == 1
    vault.setManagementFee(
        0, {"from": gov}
    )  # set management fee to 0 so that time works

    strategy.setMinCompToSell(1e15, {"from": gov})
    # enormousrunningstrategy.setMinWant(0, {"from": gov})
    # assert enormousrunningstrategy.minCompToSell() == 1
    strategy.harvest({"from": gov})
    chain.sleep(21600)

    print("mgm fee: ", vault.managementFee())
    print("perf fee: ", vault.performanceFee())

    startingBalance = vault.totalAssets()

    for i in range(2):  # TODO: see how many times we can run this
        waitBlock = 25
        print(f"\n----wait {waitBlock} blocks----")
        # wait(waitBlock, chain)
        chain.mine(waitBlock)
        ppsBefore = vault.pricePerShare()

        strategy.harvest({"from": gov})
        # wait 6 hours. shouldnt mess up next round as compound uses blocks
        print("Locked: ", vault.lockedProfit())
        assert vault.lockedProfit() > 0  # some profit should be unlocked
        chain.sleep(21600)  # sonne uses seconds, not blocks
        chain.mine(1)

        ppsAfter = vault.pricePerShare()

        # stateOfStrat(enormousrunningstrategy, dai, comp)
        # stateOfVault(vault, enormousrunningstrategy)

        profit = (vault.totalAssets() - startingBalance).to("ether")
        strState = vault.strategies(strategy)
        totalReturns = strState.dict()["totalGain"]
        totaleth = totalReturns.to("ether")
        print(f"Real Profit: {profit:.5f}")
        difff = profit - totaleth
        print(f"Diff: {difff}")
        print(f"PPS: {ppsAfter}")

        print(f"PPS Diff: {ppsAfter - ppsBefore}")
        assert ppsAfter - ppsBefore > 0  # pps should have risen

        blocks_per_year = 31_536_000
        assert startingBalance != 0
        time = (i + 1) * waitBlock
        assert time != 0
        ppsProfit = (ppsAfter - ppsBefore) / 1e18 / waitBlock * blocks_per_year
        apr = (totalReturns / startingBalance) * (blocks_per_year / time)
        print(f"implied apr assets: {apr:.8%}")
        print(f"implied apr pps: {ppsProfit:.8%}")

    print(strategy.minWant() / 1e18)
    stateOfStrat(strategy, token, comp)


def test_apr_alt(
    chain,
    gov,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
    sonne_comptroller,
):

    strategy.setMinCompToSell(1, {"from": gov})
    strategy.setIterations(20, {"from": gov})
    _, collateral_target, _ = sonne_comptroller.markets(strategy.cToken())
    print(f"collateral_target: {collateral_target/1e18:.6f}")
    strategy.setCollateralTarget(collateral_target - 0.02e18, {"from": gov})

    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    strategy.tend({"from": strategist})
    strategy.tend({"from": strategist})
    
    status_levcomp(strategy, token, vault)
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    utils.sleep(3600*24*7)
    chain.mine(1)

    status_levcomp(strategy, token, vault)
    vault.revokeStrategy(strategy.address, {"from": gov})
    strategy.setCollateralTarget(0, {"from": gov})
    status_levcomp(strategy, token, vault)
    _, borrows = strategy.getCurrentPosition()
    n = 0
    while borrows > strategy.minWant():
        print("Tending ...")
        strategy.tend({"from": strategist})
        status_levcomp(strategy, token, vault)
        _, borrows = strategy.getCurrentPosition()
        n+=1
    print(f"iterations: {n}")
    strategy.harvest({"from": strategist})
    status_levcomp(strategy, token, vault)
    print(
        f"APR: {(token.balanceOf(vault)-amount)*52/amount:.2%} on {amount/10**token.decimals():,.2f}"
    )
    assert amount <= token.balanceOf(vault)


def status_levcomp(strategy, token=None, vault=None):
    if isinstance(strategy, str):
        strategy = Contract(strategy)

    if token == None:
        token = Contract(strategy.want())

    if vault == None:
        vault = Contract(strategy.vault())

    status = vault.strategies(strategy).dict()

    print(f"\n--- state of {strategy.name()} {vault.symbol()} {vault.apiVersion()} ---")
    print(f"Debt Ratio {status['debtRatio']}")
    print(f"Total Debt {_to_units(vault, status['totalDebt']):,.2f}")
    print(f"Total Gain {_to_units(vault, status['totalGain']):,.2f}")
    print(f"Total Loss {_to_units(vault, status['totalLoss']):,.2f}")

    decimals = token.decimals()
    deposits, borrows = strategy.getCurrentPosition()
    print("Want:", "{:,.1f}".format(token.balanceOf(strategy) / (10 ** decimals)))
    print("borrows:", "{:,.1f}".format(borrows / (10 ** decimals)))
    print("deposits:", "{:,.1f}".format(deposits / (10 ** decimals)))
    realbalance = token.balanceOf(strategy) + deposits - borrows
    print("total assets real:", "{:,.1f}".format(realbalance / (10 ** decimals)))

    print(
        "total assets estimate:",
        "{:,.1f}".format(strategy.estimatedTotalAssets() / (10 ** decimals)),
    )
    if deposits == 0:
        collat = 0
    else:
        collat = borrows / deposits
    leverage = 1 / (1 - collat)
    print(f"calculated collat: {collat:.5%}")
    storedCollat = strategy.storedCollateralisation() / 1e18
    print(f"stored collat: {storedCollat:.5%}")
    print(f"leverage: {leverage:.5f}x")
    assert collat <= 0.95
    print("Expected Profit:", strategy.expectedReturn() / (10 ** decimals))
    toLiquidation = strategy.getblocksUntilLiquidation()
    print("Weeks to liquidation:", toLiquidation / 44100)
    print()


def _to_units(token, amount):
    return amount / (10 ** token.decimals())

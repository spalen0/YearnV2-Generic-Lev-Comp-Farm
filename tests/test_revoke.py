import pytest
from utils import actions, checks, utils


def test_revoke_strategy_from_vault(
    chain, token, vault, strategy, amount, user, gov, RELATIVE_APPROX
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    chain.sleep(1)
    strategy.setCollateralTarget(
        strategy.collateralTarget() / 2,
        {"from": gov},
    )
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # In order to pass this tests, you will need to implement prepareReturn.
    vault.revokeStrategy(strategy.address, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    utils.strategy_status(vault, strategy)
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    utils.strategy_status(vault, strategy)
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    utils.strategy_status(vault, strategy)
    assert pytest.approx(token.balanceOf(vault.address), rel=RELATIVE_APPROX) == amount


def test_revoke_strategy_from_strategy(
    chain, token, vault, strategy, amount, gov, user, RELATIVE_APPROX
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    strategy.setCollateralTarget(
        strategy.collateralTarget() / 2,
        {"from": gov},
    )
    chain.sleep(1)
    tx = strategy.harvest(
        {"from": gov}
    )  # TODO: see why this fails on function _withdrawSome
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    strategy.setEmergencyExit()
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert pytest.approx(token.balanceOf(vault.address), rel=RELATIVE_APPROX) == amount


def test_revoke_with_profit(
    chain, token, vault, strategy, amount, user, gov, RELATIVE_APPROX
):
    actions.user_deposit(user, vault, token, amount)
    strategy.setCollateralTarget(
        strategy.collateralTarget() / 2,
        {"from": gov},
    )
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    actions.generate_profit(strategy, 20)

    # Revoke strategy
    # In order to pass this tests, you will need to implement prepareReturn.
    vault.revokeStrategy(strategy.address, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert pytest.approx(token.balanceOf(vault.address), rel=RELATIVE_APPROX) == amount

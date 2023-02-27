import brownie
from brownie import Contract
import pytest
from utils import actions, checks, utils


def test_triggers(chain, gov, vault, strategy, token, amount, user, strategist, sonne_comptroller):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)
    chain.sleep(1)
    strategy.harvest()

    assert strategy.harvestTrigger(1e15) == False
    chain.sleep(86400 + 60)
    chain.mine()
    assert strategy.harvestTrigger(1e15) == True

    strategy.harvest()

    tx = strategy.setCollateralTarget(
        sonne_comptroller.markets(strategy.cToken())[1] - 1000,
        {"from": gov},
    )
    assert strategy.harvestTrigger(1e15) == False
    chain.sleep(86400)
    chain.mine()
    assert strategy.harvestTrigger(1e15) == True

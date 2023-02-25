from utils import actions
import brownie
from brownie import Contract
import pytest


def test_healthcheck(user, vault, token, amount, strategy, chain, strategist, gov):
    # Deposit to the vault
    actions.user_deposit(user, vault, token, amount)

    assert strategy.doHealthCheck() == False
    assert strategy.healthCheck() == "0x0000000000000000000000000000000000000000"

    strategy.setHealthCheck("0x3d8f58774611676fd196d26149c71a9142c45296", {"from": gov})
    assert strategy.healthCheck() == "0x3d8f58774611676fd196d26149c71a9142c45296"
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    chain.sleep(24 * 3600)
    chain.mine(1)

    strategy.setDoHealthCheck(True, {"from": gov})

    loss_amount = actions.generate_loss(strategy)
    # Harvest should revert because the loss in unacceptable
    with brownie.reverts("!healthcheck"):
        strategy.harvest({"from": strategist})

    # we disable the healthcheck
    strategy.setDoHealthCheck(False, {"from": gov})

    # the harvest should go through, taking the loss
    tx = strategy.harvest({"from": strategist})
    assert tx.events["Harvested"]["loss"] <= loss_amount # harvested loss is lower because sonne earns on seconds, not on blocks

    vault.withdraw({"from": user})
    assert token.balanceOf(user) < amount  # user took losses

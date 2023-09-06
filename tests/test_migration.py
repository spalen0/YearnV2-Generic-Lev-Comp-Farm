# TODO: Add tests that show proper migration of the strategy to a newer one
#       Use another copy of the strategy to simulate the migration
#       Show that nothing is lost!

import pytest
from utils import actions


def test_migration(
    chain,
    token,
    cToken,
    vault,
    strategy,
    velodrome_router,
    velodrome_pool_factory,
    sonne,
    sonne_comptroller,
    weth,
    amount,
    Strategy,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
):
    # Deposit to the vault and harvest
    actions.user_deposit(user, vault, token, amount)

    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # migrate to a new strategy
    new_strategy = strategist.deploy(
        Strategy, vault, cToken, velodrome_router, velodrome_pool_factory, sonne, sonne_comptroller, 1
    )
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )

    # check that harvest work as expected
    new_strategy.harvest({"from": gov})
    supply, borrow = new_strategy.getCurrentPosition()
    assert supply > 0
    assert borrow > 0

import pytest
from brownie import config
from brownie import Contract, interface

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture
def gov(accounts):
    yield accounts.at("0xC0E2830724C946a6748dDFE09753613cd38f6767", force=True)


@pytest.fixture
def strat_ms(accounts):
    yield accounts.at("0x72a34AbafAB09b15E7191822A679f28E067C4a16", force=True)


@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


token_addresses = { 
    "USDT": "0x94b008aa00579c1307b0ef2c499ad98a8ce58e58",
    "DAI": "0xda10009cbd5d07dd0cecc66161fc93d7c9000da1",
    "USDC": "0x7f5c764cbc14f9669b88837ca1490cca17c31607",
    "OP": "0x4200000000000000000000000000000000000042",
    "WBTC": "0x68f180fcce6836688e9084f035309e29bf0a2095",
    "WETH": "0x4200000000000000000000000000000000000006",
    "wstETH": "0x1f32b1c2345538c0c6f582fcb022739c4a194ebb",
    "sUSD": "0x8c6f28f2F1A3C87F0f938b96d27520d9751ec8d9",
}

# TODO: uncomment those tokens you want to test as want
@pytest.fixture(
    params=[
        "USDC",
        "USDT",
        "DAI",
        "OP",
        "WETH",
        "sUSD",
    ],
    scope="session",
    autouse=True,
)
def token(interface, request):
    yield interface.ERC20(token_addresses[request.param])


cToken_addresses = {
    "USDC": "0xEC8FEa79026FfEd168cCf5C627c7f486D77b765F",
    "USDT": "0x5Ff29E4470799b982408130EFAaBdeeAE7f66a10",
    "DAI": "0x5569b83de187375d43FBd747598bfe64fC8f6436",
    "OP": "0x8cD6b19A07d754bF36AdEEE79EDF4F2134a8F571",
    "WBTC": "0x33865e09a572d4f1cc4d75afc9abcc5d3d4d867d",
    "WETH": "0xf7B5965f5C117Eb1B5450187c9DcFccc3C317e8E",
    "wstETH": "0x26AaB17f27CD1c8d06a0Ad8E4a1Af8B1032171d5",
    "sUSD": "0xd14451E0Fa44B18f08aeB1E4a4d092B823CaCa68",
}


@pytest.fixture(scope="function")
def cToken(token):
    yield interface.CErc20I(cToken_addresses[token.symbol()])


whale_addresses = {
    "USDC": "0xebe80f029b1c02862b9e8a70a7e5317c06f62cae",
    "USDT": "0x0d0707963952f2fba59dd06f2b425ace40b492fe",
    "DAI": "0x1eed63efba5f81d95bfe37d82c8e736b974f477b",
    "OP": "0x2a82ae142b2e62cb7d10b55e323acb1cab663a26",
    "WBTC": "0x33865e09a572d4f1cc4d75afc9abcc5d3d4d867d",
    "WETH": "0x85149247691df622eaf1a8bd0cafd40bc45154a9",
    "wstETH": "0xc6c1e8399c1c33a3f1959f2f77349d74a373345c",
    "sUSD": "0x061b87122ed14b9526a813209c8a59a633257bab",
}


@pytest.fixture(scope="session", autouse=True)
def token_whale(token):
    yield whale_addresses[token.symbol()]


cToken_whale_addresses = {
    "USDC": "0xebe80f029b1c02862b9e8a70a7e5317c06f62cae",
    "USDT": "0x0d0707963952f2fba59dd06f2b425ace40b492fe",
    "DAI": "0xad32aa4bff8b61b4ae07e3ba437cf81100af0cd7",
    "OP": "0x2a82ae142b2e62cb7d10b55e323acb1cab663a26",
    "WBTC": "0x33865e09a572d4f1cc4d75afc9abcc5d3d4d867d",
    "WETH": "0x6202a3b0be1d222971e93aab084c6e584c29db70",
    "wstETH": "0x53b6fe8c6fa6b95119853f2929c8c6d61f437236",
    "sUSD": "0x418c0fc22d28f232fddaee148b38e5df38674abf",
}


@pytest.fixture(scope="session", autouse=True)
def cToken_whale(token):
    yield cToken_whale_addresses[token.symbol()]


# @pytest.fixture(autouse=True)
# def withdraw_whale_liquidity(cToken_whale, cToken, token, strategy):
#    borrows = cToken.borrowBalanceCurrent(cToken_whale, {'from': cToken_whale}).return_value
#    supply = cToken.balanceOfUnderlying(cToken_whale, {'from': cToken_whale}).return_value
#    print(f"borrow: {borrows/ 10 ** token.decimals()}")
#    print(f"supply: {supply/ 10 ** token.decimals()}")
#    comptroller = Contract(cToken.comptroller())
#    l, collatFactor, c = comptroller.markets(cToken)

#    amount = supply - borrows / collatFactor * 1e18

#    print(f"Withdrawing {amount/10**token.decimals()} {token.symbol()}")
#    print(f"Available liquidity: {cToken.getCash()/10**token.decimals()}")
#    cToken.redeemUnderlying(amount, {'from': cToken_whale})
#    print(f"Available liquidity: {cToken.getCash()/10**token.decimals()}")

token_prices = {
    "USDT": 1,
    "USDC": 1,
    "DAI": 1,
    "OP": 2,
    "WBTC": 24_000,
    "WETH": 1_800,
    "wstETH": 1_800,
    "sUSD": 1,
}


@pytest.fixture(autouse=True)
def amount(token, token_whale, user):
    # this will get the number of tokens (around $1m worth of token)
    amillion = round(1_000_000 / token_prices[token.symbol()])
    amount = amillion * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate a whale address
    if amount > token.balanceOf(token_whale):
        amount = token.balanceOf(token_whale)
    token.transfer(user, amount, {"from": token_whale})
    print(f"Amount: {amount / 10 ** token.decimals()}")
    yield amount


@pytest.fixture
def weth(interface):
    token_address = (  # USDC is used as middle token
        "0x4200000000000000000000000000000000000006"
    )
    yield interface.ERC20(token_address)


@pytest.fixture
def sonne_comptroller(interface):
    token_address = "0x60CF091cD3f50420d50fD7f707414d0DF4751C58"
    yield interface.ComptrollerI(token_address)


@pytest.fixture
def sonne(interface):
    token_address = "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0"
    yield interface.ERC20(token_address)


@pytest.fixture
def velodrome_router(interface):
    token_address = "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858"
    yield interface.IVelodromeRouter(token_address)


@pytest.fixture
def weth_amount(user, weth):
    weth_amount = 10 ** weth.decimals()
    weth.transfer(user, weth_amount, {"from": whale_addresses["WETH"]})
    yield weth_amount


@pytest.fixture(scope="function", autouse=True)
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2**256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    yield vault


@pytest.fixture
def reentry_test(user, ReentryTest):
    reentry_test = user.deploy(ReentryTest)
    yield reentry_test


min_want_values = {
    "USDT": 1e6,
    "USDC": 1e6,
    "DAI": 1e18,
    "OP": 1e18,
    "WBTC": 1e3,
    "WETH": 1e14,
    "wstETH": 1e13,
    "sUSD": 1e18,
}

collateral_target_values = {
    "USDT": 80,
    "USDC": 80,
    "DAI": 80,
    "OP": 0.1,
    "WBTC": 55,
    "WETH": 45,
    "wstETH": 50,
    "sUSD": 50,
}


@pytest.fixture
def collateral_target(token):
    yield collateral_target_values[token.symbol()] * 1e16


velo_want_stable_values = {
    "USDT": True,
    "USDC": True,
    "DAI": True,
    "OP": False,
    "WBTC": False,
    "WETH": False,
    "wstETH": False,
    "sUSD": True,
}

@pytest.fixture
def velo_want_stable(token):
    yield velo_want_stable_values[token.symbol()]


@pytest.fixture
def velodrome_route(token):
    yield velodrome_route_values[token.symbol()]

# pools related to these routes





velodrome_route_values = {
    "USDT": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
                1,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ]],

    "USDC": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ]],

    "DAI": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                1,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ]],

    "OP": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
                "0x4200000000000000000000000000000000000042",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ]],

    "WBTC": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
                0,
                "0x25CbdDb98b35ab1FF77413456B31EC81A6B6B746"
            ]],

    "WETH": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0x9e1028F5F1D5eDE59748FFceE5532509976840E0",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x9e1028F5F1D5eDE59748FFceE5532509976840E0",
                "0x4200000000000000000000000000000000000006",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ]],

    "wstETH": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ]],

    "sUSD": [[
                "0x1DB2466d9F5e10D7090E7152B68d62703a2245F0",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                0,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                1,
                "0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a"
            ],
            [
                "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                "0x8c6f28f2F1A3C87F0f938b96d27520d9751ec8d9",
                1,
                "0x25CbdDb98b35ab1FF77413456B31EC81A6B6B746"
            ]],
}

@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    Strategy,
    gov,
    cToken,
    velodrome_router,
    sonne,
    sonne_comptroller,
    velodrome_route,
    token,
    collateral_target,
):
    strategy = strategist.deploy(
        Strategy, vault, cToken, velodrome_router, sonne, sonne_comptroller, 1, velodrome_route
    )
    strategy.setKeeper(keeper)
    strategy.setMinWant(min_want_values[token.symbol()], {"from": gov})
    strategy.setCollateralTarget(collateral_target, {"from": gov})
    strategy.setIsVeloWantStable(velo_want_stable_values[token.symbol()], {"from": gov})
    profit_factor_adjustment = token_prices["WETH"] / token_prices[token.symbol()] * 10 ** (18 - token.decimals())
    strategy.setProfitFactor(strategy.profitFactor() * profit_factor_adjustment, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2**256 - 1, 0, {"from": gov})
    yield strategy


@pytest.fixture
def factory(
    LevCompFactory,
    vault,
    cToken,
    strategist,
    gov,
    velodrome_router,
    sonne,
    sonne_comptroller,
    velodrome_route,
):
    factory = strategist.deploy(
        LevCompFactory,
        vault,
        cToken,
        velodrome_router,
        sonne,
        sonne_comptroller,
        1,
        velodrome_route,
    )
    yield factory


@pytest.fixture(scope="session", autouse=True)
def RELATIVE_APPROX():
    yield 1e-5

// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy, StrategyParams, VaultAPI} from "@yearnvaults/contracts/BaseStrategy.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/math/Math.sol";
import "./Interfaces/Compound/CErc20I.sol";
import "./Interfaces/Compound/ComptrollerI.sol";
import "./Interfaces/Velodrome/IVelodromeRouter.sol";

interface IERC20Extended is IERC20 {
    function decimals() external view returns (uint8);

    function name() external view returns (string memory);

    function symbol() external view returns (string memory);
}

interface IEthToWant {
    function ethToWant(uint256 input) external view returns (uint256);
}

contract Strategy is BaseStrategy {

    address private constant USDC = 0x7F5c764cBc14f9669B88837ca1490cCa17c31607;
    address private constant WETH = 0x4200000000000000000000000000000000000006;

    // Comptroller address for compound.finance
    ComptrollerI public compound;

    //Only three tokens we use
    address public comp;
    CErc20I public cToken;

    uint256 private secondsPerBlock; //1 for fantom. 13 for ethereum, Sonne uses 1 block per second for caluclations

    IVelodromeRouter public currentRouter; // velodrome router only
    address public ethToWantOracle;

    uint256 public collateralTarget; // total borrow / total supply ratio we are targeting (100% = 1e18)
    uint256 public blocksToLiquidationDangerZone; // minimum number of blocks before liquidation

    uint256 public minWant; // minimum amount of want to act on

    // Rewards handling
    bool public dontClaimComp; // enable/disables COMP claiming
    uint256 public minCompToSell; // minimum amount of COMP to be sold

    uint256 public iterations; //number of loops we do
    bool public forceMigrate;

    IVelodromeRouter.route[] public sellRewardsRoute;

    constructor(address _vault, address _cToken, address _router, address _comp, address _comptroller, uint256 _secondsPerBlock, IVelodromeRouter.route[] memory _routes) public BaseStrategy(_vault) {
        _initializeThis(_cToken, _router, _comp, _comptroller, _secondsPerBlock, _routes);
    }

    function approveTokenMax(address token, address spender) internal {
        IERC20(token).safeApprove(spender, type(uint256).max);
    }

    function name() external view override returns (string memory) {
        return "GenLevSonneNoFlash";
    }

    function initialize(address _vault, address _cToken, address _router, address _comp, address _comptroller, uint256 _secondsPerBlock, IVelodromeRouter.route[] memory _routes) external {
        _initialize(_vault, msg.sender, msg.sender, msg.sender);
        _initializeThis(_cToken, _router, _comp, _comptroller, _secondsPerBlock, _routes);
    }

    function _initializeThis(address _cToken, address _router, address _comp, address _comptroller, uint256 _secondsPerBlock, IVelodromeRouter.route[] memory _routes) internal {
        cToken = CErc20I(_cToken);
        require(cToken.underlying() == address(want), "Wrong underlying");
        comp = _comp;
        secondsPerBlock = _secondsPerBlock;
        compound = ComptrollerI(_comptroller);
        require(IERC20Extended(address(want)).decimals() <= 18); // dev: want not supported
        currentRouter = IVelodromeRouter(_router);

        //pre-set approvals
        approveTokenMax(comp, address(currentRouter));
        approveTokenMax(address(want), address(cToken));
        
        // You can set these parameters on deployment to whatever you want
        maxReportDelay = 86400; // once per 24 hours
        profitFactor = 100_000; // multiple before triggering harvest 
        debtThreshold = 1e30;
        iterations = 20; //standard 20 for Sonne on Optimism

        // set minWant to 1e-5 want
        minWant = uint256(uint256(10)**uint256((IERC20Extended(address(want))).decimals())).div(1e5);
        minCompToSell = 100 ether; //may need to be changed depending on what comp is, sonne price is 0,3$, value should be above 1e15
        collateralTarget = 0.71 ether; // change depending on the collateral, for stablecoins it can be heigher
        blocksToLiquidationDangerZone = 604800 / secondsPerBlock; // time until liquidation zone should be 1 week

        for (uint i = 0; i < _routes.length; i++) {
            sellRewardsRoute.push(_routes[i]);
        }
    }

    function setPriceOracle(address _oracle) external onlyAuthorized {
        ethToWantOracle = _oracle;
    }

    /*
     * Control Functions
     */
    function setBlocksToLiquidationDangerZone(uint256 _blocksToLiquidationDangerZone) external onlyGovernance {
        blocksToLiquidationDangerZone = _blocksToLiquidationDangerZone;
    }

    function setDontClaimComp(bool _dontClaimComp) external management {
        dontClaimComp = _dontClaimComp;
    }

    function setRouter(address _newRouter) external onlyGovernance {
        require(_newRouter != address(0), "Router cannot be 0");
        currentRouter = IVelodromeRouter(_newRouter);
    }

    function setForceMigrate(bool _force) external onlyGovernance {
        forceMigrate = _force;
    }

    function setMinCompToSell(uint256 _minCompToSell) external management {
        minCompToSell = _minCompToSell;
    }

    function setIterations(uint256 _iterations) external management {
        require(_iterations > 0 && _iterations <= 100);
        iterations = _iterations;
    }

    function setMinWant(uint256 _minWant) external management {
        minWant = _minWant;
    }

    function setCollateralTarget(uint256 _collateralTarget) external management {
        (, uint256 collateralFactorMantissa, ) = compound.markets(address(cToken));
        require(collateralFactorMantissa > _collateralTarget);
        collateralTarget = _collateralTarget;
    }

    function setRewardBehavior(uint256 _minCompToSell, bool _dontClaimComp) external management {
        minCompToSell = _minCompToSell;
        dontClaimComp = _dontClaimComp;
    }

    /*
     * Base External Facing Functions
     */
    /*
     * An accurate estimate for the total amount of assets (principle + return)
     * that this strategy is currently managing, denominated in terms of want tokens.
     */
    function estimatedTotalAssets() public view override returns (uint256) {
        (uint256 deposits, uint256 borrows) = getCurrentPosition();

        uint256 _claimableComp = predictCompAccrued();
        uint256 currentComp = balanceOfToken(comp);

        // Use touch price. it doesnt matter if we are wrong as this is not used for decision making
        uint256[] memory amounts = currentRouter.getAmountsOut(_claimableComp.add(currentComp), sellRewardsRoute);
        uint256 estimatedWant = amounts[amounts.length - 1];
        uint256 conservativeWant = estimatedWant.mul(9).div(10); //10% pessimist

        return balanceOfToken(address(want)).add(deposits).add(conservativeWant).sub(borrows);
    }

    function balanceOfToken(address token) internal view returns (uint256) {
        return IERC20(token).balanceOf(address(this));
    }

    //predicts our profit at next report
    function expectedReturn() public view returns (uint256) {
        uint256 estimateAssets = estimatedTotalAssets();

        uint256 debt = vault.strategies(address(this)).totalDebt;
        if (debt > estimateAssets) {
            return 0;
        } else {
            return estimateAssets.sub(debt);
        }
    }

    /*
     * Provide a signal to the keeper that `tend()` should be called.
     * (keepers are always reimbursed by yEarn)
     *
     * NOTE: this call and `harvestTrigger` should never return `true` at the same time.
     * tendTrigger should be called with same gasCost as harvestTrigger
     */
    function tendTrigger(uint256 gasCost) public view override returns (bool) {
        if (harvestTrigger(gasCost)) {
            //harvest takes priority
            return false;
        }

        return getblocksUntilLiquidation() <= blocksToLiquidationDangerZone;
    }

    /*****************
     * Public non-base function
     ******************/

    //Calculate how many blocks until we are in liquidation based on current interest rates
    //WARNING does not include compounding so the estimate becomes more innacurate the further ahead we look
    //equation. Compound doesn't include compounding for most blocks
    //((deposits*colateralThreshold - borrows) / (borrows*borrowrate - deposits*colateralThreshold*interestrate));
    function getblocksUntilLiquidation() public view returns (uint256) {
        (, uint256 collateralFactorMantissa, ) = compound.markets(address(cToken));

        (uint256 deposits, uint256 borrows) = getCurrentPosition();

        uint256 borrrowRate = cToken.borrowRatePerBlock();

        uint256 supplyRate = cToken.supplyRatePerBlock();

        uint256 collateralisedDeposit = deposits.mul(collateralFactorMantissa).div(1e18);

        uint256 denom1 = borrows.mul(borrrowRate);
        uint256 denom2 = collateralisedDeposit.mul(supplyRate);

        if (denom2 >= denom1) {
            return type(uint256).max;
        } else {
            uint256 numer = collateralisedDeposit.sub(borrows);
            uint256 denom = denom1.sub(denom2);
            //minus 1 for this block
            return numer.mul(1e18).div(denom);
        }
    }

    // This function makes a prediction on how much comp is accrued
    // It is not 100% accurate as it uses current balances in Compound to predict into the past
    function predictCompAccrued() public view returns (uint256) {
        (uint256 deposits, uint256 borrows) = getCurrentPosition();
        if (deposits == 0) {
            return 0; // should be impossible to have 0 balance and positive comp accrued
        }

        uint256 distributionPerBlockSupply = compound.compSupplySpeeds(address(cToken));
        uint256 distributionPerBlockBorrow = compound.compBorrowSpeeds(address(cToken));

        uint256 totalBorrow = cToken.totalBorrows();

        //total supply needs to be echanged to underlying using exchange rate
        uint256 totalSupplyCtoken = cToken.totalSupply();
        uint256 totalSupply = totalSupplyCtoken.mul(cToken.exchangeRateStored()).div(1e18);

        uint256 blockShareSupply = 0;
        if (totalSupply > 0) {
            blockShareSupply = deposits.mul(distributionPerBlockSupply).div(totalSupply);
        }

        uint256 blockShareBorrow = 0;
        if (totalBorrow > 0) {
            blockShareBorrow = borrows.mul(distributionPerBlockBorrow).div(totalBorrow);
        }

        //how much we expect to earn per block
        uint256 blockShare = blockShareSupply.add(blockShareBorrow);

        //last time we ran harvest
        uint256 lastReport = vault.strategies(address(this)).lastReport;
        uint256 blocksSinceLast = (block.timestamp.sub(lastReport)).div(secondsPerBlock); 

        return blocksSinceLast.mul(blockShare);
    }

    //Returns the current position
    //WARNING - this returns just the balance at last time someone touched the cToken token. Does not accrue interst in between
    //cToken is very active so not normally an issue.
    function getCurrentPosition() public view returns (uint256 deposits, uint256 borrows) {
        (, uint256 ctokenBalance, uint256 borrowBalance, uint256 exchangeRate) = cToken.getAccountSnapshot(address(this));
        borrows = borrowBalance;

        deposits = ctokenBalance.mul(exchangeRate).div(1e18);
    }

    //statechanging version
    function getLivePosition() public returns (uint256 deposits, uint256 borrows) {
        deposits = cToken.balanceOfUnderlying(address(this));

        //we can use non state changing now because we updated state with balanceOfUnderlying call
        borrows = cToken.borrowBalanceStored(address(this));
    }

    //Same warning as above
    function netBalanceLent() public view returns (uint256) {
        (uint256 deposits, uint256 borrows) = getCurrentPosition();
        return deposits.sub(borrows);
    }

    /***********
     * internal core logic
     *********** */
    /*
     * A core method.
     * Called at beggining of harvest before providing report to owner
     * 1 - claim accrued comp
     * 2 - if enough to be worth it we sell
     * 3 - because we lose money on our loans we need to offset profit from comp.
     */
    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        _profit = 0;
        _loss = 0; // for clarity. also reduces bytesize

        if (balanceOfToken(address(cToken)) == 0) {
            uint256 wantBalance = balanceOfToken(address(want));
            //no position to harvest
            //but we may have some debt to return
            //it is too expensive to free more debt in this method so we do it in adjust position
            _debtPayment = Math.min(wantBalance, _debtOutstanding);
            return (_profit, _loss, _debtPayment);
        }

        (uint256 deposits, uint256 borrows) = getLivePosition();

        //claim comp accrued
        _claimComp();
        //sell comp
        _disposeOfComp();

        uint256 wantBalance = balanceOfToken(address(want));

        uint256 investedBalance = deposits.sub(borrows);
        uint256 balance = investedBalance.add(wantBalance);

        uint256 debt = vault.strategies(address(this)).totalDebt;

        //Balance - Total Debt is profit
        if (balance > debt) {
            _profit = balance.sub(debt);
            if (wantBalance < _profit) {
                //all reserve is profit
                _profit = wantBalance;
            } else if (wantBalance > _profit.add(_debtOutstanding)) {
                _debtPayment = _debtOutstanding;
            } else {
                _debtPayment = wantBalance.sub(_profit);
            }
        } else {
            //we will lose money until we claim comp then we will make money
            //this has an unintended side effect of slowly lowering our total debt allowed
            _loss = debt.sub(balance);
            _debtPayment = Math.min(wantBalance, _debtOutstanding);
        }
    }

    /*
     * Second core function. Happens after report call.
     *
     * Similar to deposit function from V1 strategy
     */
    function adjustPosition(uint256 _debtOutstanding) internal override {
        //emergency exit is dealt with in prepareReturn
        if (emergencyExit) {
            return;
        }

        //we are spending all our cash unless we have debt outstanding
        uint256 _wantBal = balanceOfToken(address(want));
        if (_wantBal < _debtOutstanding) {
            //this is graceful withdrawal. dont use backup
            //we use more than 1 because withdrawunderlying causes problems with 1 token due to different decimals
            if (balanceOfToken(address(cToken)) > 1) {
                _withdrawSome(_debtOutstanding.sub(_wantBal));
            }

            return;
        }

        (uint256 position, bool deficit) = _calculateDesiredPosition(_wantBal.sub(_debtOutstanding), true);

        //if we are below minimun want change it is not worth doing
        //need to be careful in case this pushes to liquidation
        uint256 i = 0;
        while (position > minWant) {
            position = position.sub(_noFlashLoan(position, deficit));
            if (i >= iterations) {
                break;
            }
            i++;
        }

    }

    /*************
     * Very important function
     * Input: amount we want to withdraw
     *       cannot be more than we have
     * Returns amount we were able to withdraw. notall if user has some balance left
     *
     * Deleverage position -> redeem our cTokens
     ******************** */
    function _withdrawSome(uint256 _amount) internal returns (bool notAll) {
        (uint256 position, bool deficit) = _calculateDesiredPosition(_amount, false);

        //If there is no deficit we dont need to adjust position
        //if the position change is tiny do nothing
        if (deficit && position > minWant) {

            uint8 i = 0;
            //position will equal 0 unless we haven't been able to deleverage enough with flash loan
            //if we are not in deficit we dont need to do flash loan
            while (position > minWant.add(100)) {
                position = position.sub(_noFlashLoan(position, true));
                i++;
                //A limit set so we don't run out of gas
                if (i >= iterations) {
                    notAll = true;
                    break;
                }
            }
        }
        //now withdraw
        //if we want too much we just take max

        //This part makes sure our withdrawal does not force us into liquidation
        (uint256 depositBalance, uint256 borrowBalance) = getCurrentPosition();

        uint256 tempColla = collateralTarget;

        uint256 reservedAmount = 0;
        if (tempColla == 0) {
            tempColla = 1e15; // 0.001 * 1e18. lower we have issues
        }

        reservedAmount = borrowBalance.mul(1e18).div(tempColla);
        if (depositBalance >= reservedAmount) {
            uint256 redeemable = depositBalance.sub(reservedAmount);
            uint256 balan = cToken.balanceOf(address(this));
            if (balan > 1) {
                if (redeemable < _amount) {
                    cToken.redeemUnderlying(redeemable);
                } else {
                    cToken.redeemUnderlying(_amount);
                }
            }
        }

        if (collateralTarget == 0 && balanceOfToken(address(want)) > borrowBalance) {
            cToken.repayBorrow(borrowBalance);
        }
    }

    /***********
     *  This is the main logic for calculating how to change our lends and borrows
     *  Input: balance. The net amount we are going to deposit/withdraw.
     *  Input: dep. Is it a deposit or withdrawal
     *  Output: position. The amount we want to change our current borrow position.
     *  Output: deficit. True if we are reducing position size
     *
     *  For instance deficit =false, position 100 means increase borrowed balance by 100
     ****** */
    function _calculateDesiredPosition(uint256 balance, bool dep) internal returns (uint256 position, bool deficit) {
        //we want to use statechanging for safety
        (uint256 deposits, uint256 borrows) = getLivePosition();

        //When we unwind we end up with the difference between borrow and supply
        uint256 unwoundDeposit = deposits.sub(borrows);

        //we want to see how close to collateral target we are.
        //So we take our unwound deposits and add or remove the balance we are are adding/removing.
        //This gives us our desired future undwoundDeposit (desired supply)

        uint256 desiredSupply = 0;
        if (dep) {
            desiredSupply = unwoundDeposit.add(balance);
        } else {
            if (balance > unwoundDeposit) {
                balance = unwoundDeposit;
            }
            desiredSupply = unwoundDeposit.sub(balance);
        }

        //(ds *c)/(1-c)
        uint256 num = desiredSupply.mul(collateralTarget);
        uint256 den = uint256(1e18).sub(collateralTarget);

        uint256 desiredBorrow = num.div(den);
        if (desiredBorrow > 1e5) {
            //stop us going right up to the wire
            desiredBorrow = desiredBorrow.sub(1e5);
        }

        //now we see if we want to add or remove balance
        // if the desired borrow is less than our current borrow we are in deficit. so we want to reduce position
        if (desiredBorrow < borrows) {
            deficit = true;
            position = borrows.sub(desiredBorrow); //safemath check done in if statement
        } else {
            //otherwise we want to increase position
            deficit = false;
            position = desiredBorrow.sub(borrows);
        }
    }

    /*
     * Liquidate as many assets as possible to `want`, irregardless of slippage,
     * up to `_amount`. Any excess should be re-invested here as well.
     */
    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _amountFreed, uint256 _loss) {
        uint256 _balance = balanceOfToken(address(want));
        uint256 assets = netBalanceLent().add(_balance);

        (uint256 deposits, uint256 borrows) = getLivePosition();
        if (assets < _amountNeeded) {
            //if we cant afford to withdraw we take all we can
            //withdraw all we can

            //1 token causes rounding error with withdrawUnderlying
            if (balanceOfToken(address(cToken)) > 1) {
                _withdrawSome(deposits.sub(borrows));
            }

            _amountFreed = Math.min(_amountNeeded, balanceOfToken(address(want)));
        } else {
            if (_balance < _amountNeeded) {
                _withdrawSome(_amountNeeded.sub(_balance));

                //overflow error if we return more than asked for
                _amountFreed = Math.min(_amountNeeded, balanceOfToken(address(want)));
            } else {
                _amountFreed = _amountNeeded;
            }
        }

        // To prevent the vault from moving on to the next strategy in the queue
        // when we return the amountRequested minus dust, take a dust sized loss
        if (_amountFreed < _amountNeeded) {
            uint256 diff = _amountNeeded.sub(_amountFreed);
            if (diff <= minWant) {
                _loss = diff;
            }
        }
    }

    function _claimComp() internal {
        if (dontClaimComp) {
            return;
        }
        CTokenI[] memory tokens = new CTokenI[](1);
        tokens[0] = cToken;

        compound.claimComp(address(this), tokens);
    }

    //sell comp function
    function _disposeOfComp() internal {
        uint256 _comp = balanceOfToken(comp);
        if (_comp < minCompToSell) {
            return;
        }

        currentRouter.swapExactTokensForTokens(_comp, 0, sellRewardsRoute, address(this), now);

    }

    function setSellRewardsRoute(IVelodromeRouter.route[] memory _routes) external onlyVaultManagers {
        delete sellRewardsRoute; // clear the array
        for (uint256 i = 0; i < _routes.length; i++) {
            sellRewardsRoute.push(_routes[i]);
        }
    }

    //lets leave
    //if we can't deleverage in one go set collateralFactor to 0 and call harvest multiple times until delevered
    function prepareMigration(address _newStrategy) internal override {
        if (!forceMigrate) {
            (uint256 deposits, uint256 borrows) = getLivePosition();
            _withdrawSome(deposits.sub(borrows));

            (, , uint256 borrowBalance, ) = cToken.getAccountSnapshot(address(this));

            require(borrowBalance < 10_000);

            IERC20 _comp = IERC20(comp);
            uint256 _compB = balanceOfToken(address(_comp));
            if (_compB > 0) {
                _comp.safeTransfer(_newStrategy, _compB);
            }
        }
    }

    //Three functions covering normal leverage and deleverage situations
    // max is the max amount we want to increase our borrowed balance
    // returns the amount we actually did
    function _noFlashLoan(uint256 max, bool deficit) internal returns (uint256 amount) {
        //we can use non-state changing because this function is always called after _calculateDesiredPosition
        (uint256 lent, uint256 borrowed) = getCurrentPosition();

        //if we have nothing borrowed then we can't deleverage any more
        if (borrowed == 0 && deficit) {
            return 0;
        }
        if(lent == 0){
            cToken.mint(balanceOfToken(address(want)));
            (lent, borrowed) = getCurrentPosition();
        }

        (, uint256 collateralFactorMantissa, ) = compound.markets(address(cToken));

        if (deficit) {
            amount = _normalDeleverage(max, lent, borrowed, collateralFactorMantissa);
        } else {
            amount = _normalLeverage(max, lent, borrowed, collateralFactorMantissa);
        }
    }

    //maxDeleverage is how much we want to reduce by
    function _normalDeleverage(
        uint256 maxDeleverage,
        uint256 lent,
        uint256 borrowed,
        uint256 collatRatio
    ) internal returns (uint256 deleveragedAmount) {
        uint256 theoreticalLent = 0;

        //collat ration should never be 0. if it is something is very wrong... but just incase
        if (collatRatio != 0) {
            theoreticalLent = borrowed.mul(1e18).div(collatRatio);
        }
        deleveragedAmount = lent.sub(theoreticalLent);

        if (deleveragedAmount >= borrowed) {
            deleveragedAmount = borrowed;
        }
        if (deleveragedAmount >= maxDeleverage) {
            deleveragedAmount = maxDeleverage;
        }
        uint256 exchangeRateStored = cToken.exchangeRateStored();
        //redeemTokens = redeemAmountIn * 1e18 / exchangeRate. must be more than 0
        //a rounding error means we need another small addition
        if (deleveragedAmount.mul(1e18) >= exchangeRateStored && deleveragedAmount > 10) {
            deleveragedAmount = deleveragedAmount.sub(uint256(10));
            cToken.redeemUnderlying(deleveragedAmount);

            //our borrow has been increased by no more than maxDeleverage
            cToken.repayBorrow(deleveragedAmount);
        }
    }

    //maxDeleverage is how much we want to increase by
    function _normalLeverage(
        uint256 maxLeverage,
        uint256 lent,
        uint256 borrowed,
        uint256 collatRatio
    ) internal returns (uint256 leveragedAmount) {
        uint256 theoreticalBorrow = lent.mul(collatRatio).div(1e18);

        leveragedAmount = theoreticalBorrow.sub(borrowed);

        if (leveragedAmount >= maxLeverage) {
            leveragedAmount = maxLeverage;
        }
        if (leveragedAmount > 10) {
            leveragedAmount = leveragedAmount.sub(uint256(10));
            cToken.borrow(leveragedAmount);
            cToken.mint(balanceOfToken(address(want)));
        }
    }

    //emergency function that we can use to deleverage manually if something is broken
    function manualDeleverage(uint256 amount) external management {
        require(cToken.redeemUnderlying(amount) == 0);
        require(cToken.repayBorrow(amount) == 0);
    }

    //emergency function that we can use to deleverage manually if something is broken
    function manualReleaseWant(uint256 amount) external onlyGovernance {
        require(cToken.redeemUnderlying(amount) == 0); // dev: !manual-release-want
    }

    function protectedTokens() internal view override returns (address[] memory) {}

    //returns our current collateralisation ratio. Should be compared with collateralTarget
    function storedCollateralisation() public view returns (uint256 collat) {
        (uint256 lend, uint256 borrow) = getCurrentPosition();
        if (lend == 0) {
            return 0;
        }
        collat = uint256(1e18).mul(borrow).div(lend);
    }

    // -- Internal Helper functions -- //

    function ethToWant(uint256 _amtInWei) public view override returns (uint256) {
        if (ethToWantOracle != address(0)) {
            return IEthToWant(ethToWantOracle).ethToWant(_amtInWei);
        } else {
            return _amtInWei;
        }
    }

    function liquidateAllPositions() internal override returns (uint256 _amountFreed) {
        (_amountFreed, ) = liquidatePosition(vault.debtOutstanding());
        (uint256 deposits, uint256 borrows) = getCurrentPosition();

        uint256 position = deposits.sub(borrows);

        //we want to revert if we can't liquidateall
        if (!forceMigrate) {
            require(position < minWant);
        }
    }

    function mgtm_check() internal view {
        require(msg.sender == governance() || msg.sender == vault.management() || msg.sender == strategist, "!authorized");
    }

    modifier management() {
        mgtm_check();
        _;
    }
}

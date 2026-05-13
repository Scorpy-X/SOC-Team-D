# How PyPortfolioOpt Turns Constraints Into Holdings

This note answers one question:

**once we define the active Variant B band ranges, how does `PyPortfolioOpt`
actually produce the final holdings?**

Short answer:

- it is **not** graph exploration
- it is **not** brute-force search over every possible portfolio
- it is a constrained optimization problem

## The one-line explanation

The constraints define which portfolios are allowed.

`PyPortfolioOpt` then finds the best asset-weight combination inside that
allowed set.

## The actual code path in this repo

The allocation flow is:

1. `build_recommendation()`
2. `build_constraint_summary()`
3. `_optimize_portfolio()`
4. `_build_holdings()`

Inside `_optimize_portfolio()`, the main library calls are:

- `EfficientFrontier(...)`
- `add_sector_constraints(...)`
- `max_sharpe(...)`
- `clean_weights(...)`
- `portfolio_performance(...)`

## What goes into the optimizer

The optimizer receives four main inputs.

### 1. Asset table

From:

- `full_assets_df.csv`

Important fields:

- `ticker`
- `super_class`
- `total_expected_return`

### 2. Covariance matrix

From:

- `full_asset_covariance_df.csv`

Plain-English meaning:

- this tells the solver which assets tend to move together

### 3. Constraint summary

Built by:

- `build_constraint_summary()`

Current active contents:

- minimum class weights for the chosen band
- maximum class weights for the chosen band
- single-asset cap

### 4. Optimizer settings

From:

- `config/portfolio/v3.json`

Current example:

- objective = `max_sharpe`
- weight bounds = `[0.0, 0.4]`

## How the rules become math constraints

### Asset-level bounds

If the portfolio says each asset must be between `0%` and `40%`, that becomes:

- each weight must be at least `0.0`
- each weight must be at most `0.4`

### Class-level constraints

If the selected band says:

- Cash between `10%` and `20%`
- Equity between `20%` and `30%`

then the solver adds rules on the **sum** of the weights in those classes.

That is what `add_sector_constraints(...)` is doing.

## What `max_sharpe()` is doing

In the current experiment, the objective is:

- `max_sharpe`

Plain-English meaning:

- try to get strong expected return for the amount of risk being taken

This uses:

- expected returns
- covariance matrix

So the solver is not just chasing return.

It is also accounting for how risky the combined portfolio is and how the
assets move relative to one another.

## How holdings come out at the end

Once the solver returns weights:

1. `clean_weights(...)` removes tiny floating-point leftovers
2. zero-weight assets are effectively dropped
3. `_build_holdings()` converts the nonzero weights into holding objects

That is why the final output is a shorter holdings list instead of every asset
in the dataset.

## What to say in a defense

Good short version:

"We first define the allowed portfolio region using the selected investor band.
`PyPortfolioOpt` then solves for the best asset weights inside that region
using expected returns and covariance."

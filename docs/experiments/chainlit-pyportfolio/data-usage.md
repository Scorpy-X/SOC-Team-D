# Data Usage

## Main data sources

The portfolio engine now tries the live SOC API first and falls back to the
CSV snapshots in:

- `data/exports/full_assets_df.csv`
- `data/exports/full_asset_covariance_df.csv`

The correlation CSV is still useful for analysis and explanation, but the optimizer uses covariance directly in this version.

If you want to verify how the covariance table lines up with correlation plus volatility, see `covariance-validation.md`.

## Which dataframe features matter and why

### `ticker`

Use:

- asset identifier
- joins the asset table to the covariance matrix
- labels the final portfolio holdings

### `super_class`

Use:

- hard portfolio constraints
- examples: minimum Cash, maximum Equity

This is the most important category field for the optimizer in v1.
This is the most important category field for the active Variant B path.

### `asset_class`

Use:

- display and explanation
- shows more specific categories in the final result

Examples:

- `Short Government Bonds`
- `Global Tech Equity`
- `Real Estate Fund`

### `currency`

Use:

- display and explanation in the active Variant B path

It is not yet a hard portfolio constraint, but the final output still reports what kind of assets are being used.

### `total_expected_return`

Use:

- main return input to `PyPortfolioOpt`

Plain meaning:

- the backend treats this as the estimated yearly return for each asset

### `income_yield_ann`

Use:

- minimum income-yield rules for income-focused answers
- final portfolio summary metric

Plain meaning:

- how much yearly income an asset tends to pay

### `volatility_ann`

Use:

- display context for each holding
- covariance validation when rebuilding a check matrix from correlation

It is not the main risk input because the covariance matrix already captures how assets move and interact together.

In plain English:

- `volatility_ann` helps explain how risky one asset is by itself
- the covariance matrix goes further by also capturing how assets interact

### `modified_duration`

Use:

- duration cap for shorter-horizon or higher-liquidity users
- final portfolio summary metric

Plain meaning:

- how sensitive bond-like holdings are to interest-rate changes

### `expense_ratio_ann`

Use:

- final portfolio summary metric

Plain meaning:

- the weighted yearly fee drag from fund-like holdings

### `rate_beta`, `inflation_beta`, `fx_beta`

Use:

- final portfolio summary metrics only in the current active path

Plain meaning:

- rough sensitivity summaries for rates, inflation, and foreign-exchange effects

## Risk table

### `full_asset_covariance_df.csv`

Use:

- main risk input to `PyPortfolioOpt`

Plain meaning:

- a table showing how assets move together in risk terms

This matters because a portfolio is not just the risk of each asset by itself. It is also about how the assets interact.

The diagonal of this matrix lines up with `volatility_ann^2`, which is a useful sanity check.

## Not every field is a constraint

This is important.

Some fields are:

- optimizer inputs
- hard constraints
- output summaries

They are not all the same thing.

In this version:

- `total_expected_return` and covariance drive the allocation math
- `super_class` drives the active class constraints
- metric fields such as `income_yield_ann` and `modified_duration` are still available for reporting and optional future constraints
- several other fields are reported as summary metrics

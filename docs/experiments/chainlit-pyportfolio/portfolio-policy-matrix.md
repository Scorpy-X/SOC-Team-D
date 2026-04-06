# Portfolio Policy Matrix

This note explains the current active Variant B policy in plain English.

Source of truth:

- `config/portfolio/v2.json`

The main backend functions connected to this file are:

- `build_constraint_summary()`
- `_optimize_portfolio()`
- `build_recommendation()`

## What this file is doing

The selected investor band defines the allowed broad asset-class mix.

In other words:

- the band says what type of investor we are simulating
- the portfolio policy says what ranges are allowed for that band

## Current Variant B policy by band

| Band | Cash | Fixed Income | Equity | Fund | Plain-English meaning |
|------------|------------|------------|------------|------------|------------|
| Very Conservative | 20-30% | 60-70% | 0-10% | 0% | Highest stability tilt |
| Conservative | 10-20% | 50-60% | 20-30% | 0% | Stability first, some equity room |
| Balanced | 5-10% | 35-50% | 40-60% | 0% | Middle-ground profile |
| Growth | 0-10% | 10-30% | 60-80% | 0% | Clear growth tilt |
| Aggressive | 0-5% | 0-15% | 85-100% | 0% | Highest equity tilt |

Technical note:

- every band also keeps a `40%` single-asset cap
- that cap is a solver safeguard, not the main investor-policy story

## What is no longer active in Variant B

The active policy path does **not** use:

- answer-based overlays
- income-yield floors
- duration caps
- answer-driven cash adjustments
- answer-driven equity adjustments

Those ideas belonged to the older exploratory policy path.

## What `_optimize_portfolio()` actually receives

It receives four things:

- `assets`
  - the asset table from `full_assets_df.csv`
- `covariance`
  - the covariance matrix from `full_asset_covariance_df.csv`
- `constraints`
  - the min and max class ranges for the chosen band
- `optimizer_config`
  - the solver settings

The current solver settings are:

- objective: `max_sharpe`
- risk-free rate: `0.0`
- global weight bounds: `0.0` to `0.4`
- PSD repair: enabled

## What `PyPortfolioOpt` is doing for us

`PyPortfolioOpt` is handling the numerical part:

- build the optimization problem
- apply class constraints
- solve for weights
- calculate portfolio performance

It is **not** doing:

- questionnaire design
- investor-band assignment in the active chat demo
- policy design

## Outputs produced by the engine

The backend returns:

- `holdings`
  - ticker, weight, class, currency, expected return, income yield, volatility
- `metrics`
  - expected return, volatility, income yield, duration, expense ratio, and beta summaries
- `constraints`
  - the active band ranges and single-asset cap
- `notes`
  - the active demo-path explanation

## What to say in a defense

Good answer:

"The selected investor band defines the allowed class ranges. The optimizer is only used to choose the best holdings inside those ranges."
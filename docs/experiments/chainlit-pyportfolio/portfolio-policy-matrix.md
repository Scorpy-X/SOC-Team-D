# Portfolio Policy Matrix

This note explains the current active liquidity-aware profile policy in plain English.

Source of truth:

- `config/portfolio/v3.json`

The main backend functions connected to this file are:

- `build_constraint_summary()`
- `_optimize_portfolio()`
- `build_recommendation()`

## What this file is doing

The selected investor band defines the allowed broad asset-class mix.

In other words:

- the band says what type of investor we are simulating
- the portfolio policy says what ranges are allowed for that band

## Current profile policy by band

| Band | Cash | Fixed Income | Equity | Fund | Plain-English meaning |
|------------|------------|------------|------------|------------|------------|
| Very Conservative | 15-35% | 55-80% | 0-20% | 0-10% | Highest stability tilt |
| Conservative | 10-30% | 45-70% | 15-35% | 0-10% | Stability first, some equity room |
| Balanced | 5-20% | 25-55% | 35-65% | 0-15% | Middle-ground profile |
| Growth | 0-15% | 10-40% | 50-85% | 0-15% | Clear growth tilt |
| Aggressive | 0-10% | 0-25% | 70-100% | 0-20% | Highest equity tilt |

Technical note:

- every band keeps a `40%` single-asset cap
- the Cash minimum can be raised by the liquidity check before optimization
- that cap is a solver safeguard, not the main investor-policy story

## What is not active yet

The active policy path does **not** use:

- broad answer-based overlays beyond the Cash liquidity check
- income-yield floors
- duration caps
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

"The selected investor profile defines the allowed class ranges. The liquidity answers can raise the minimum Cash allocation or push the user toward a safer compatible profile. The optimizer is only used to choose holdings inside those approved constraints."

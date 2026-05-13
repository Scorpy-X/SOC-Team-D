# Bare PyPortfolioOpt Demo

This note exists to separate two things that are easy to blur together:

- the **actual optimizer call**
- the **extra product code** around that call

If your teammates say "PyPortfolioOpt is basically a function call with a matrix and some settings," this is the closest version of that idea in this repo.

## What This Demo Is For

Use this when you want to understand:

- what the optimizer is doing without Chainlit, FastAPI, SQLite, or questionnaire logic
- why `portfolio.py` is longer than the optimizer itself
- which parts of the repo are "real PyPortfolioOpt usage" versus project glue

Use this together with:

- `scripts/demo_bare_pypfopt.py`
- `backend/soc_advisor/portfolio.py`

## Run It

From the repo root:

```powershell
.\.venv\Scripts\python.exe scripts\demo_bare_pypfopt.py --band growth
```

You can switch the policy band:

```powershell
.\.venv\Scripts\python.exe scripts\demo_bare_pypfopt.py --band balanced --top 5
```

Important design choice:

- this demo uses the local snapshot CSVs on purpose
- it does **not** use the live SOC API
- that keeps the example stable and keeps the focus on the optimizer itself

Configurable live-data and CSV-snapshot behavior belongs to the product wrapper in `backend/soc_advisor/portfolio.py`, not to this stripped-down demo.

## What The Script Does

The script has two layers.

### Layer 1: tiny repo-specific setup

This part is still project-specific:

- load `data/exports/full_assets_df.csv`
- load `data/exports/full_asset_covariance_df.csv`
- align tickers
- read the chosen band from `config/portfolio/v3.json`

That setup is not PyPortfolioOpt. It is just getting the inputs ready.

### Layer 2: the bare optimizer core

This is the part that corresponds most closely to research-style usage:

1. take expected returns from the asset table
2. take the covariance matrix
3. clean the covariance matrix numerically if needed
4. create `EfficientFrontier`
5. apply class constraints
6. solve with `max_sharpe`
7. clean and print the weights

That is the real heart of the optimizer.

## The Bare Core

This is the key function from the script:

```python
def run_bare_optimizer(
    *,
    assets: pd.DataFrame,
    covariance: pd.DataFrame,
    super_class_minima: dict[str, float],
    super_class_maxima: dict[str, float],
    single_asset_cap: float,
    risk_free_rate: float,
) -> tuple[pd.Series, tuple[float, float, float]]:
    expected_returns = assets["total_expected_return"].astype(float)
    covariance_input = risk_models.fix_nonpositive_semidefinite(covariance.astype(float))

    optimizer = EfficientFrontier(
        expected_returns,
        covariance_input,
        weight_bounds=(0.0, single_asset_cap),
    )

    optimizer.add_sector_constraints(
        assets["super_class"].to_dict(),
        super_class_minima,
        super_class_maxima,
    )

    optimizer.max_sharpe(risk_free_rate=risk_free_rate)
    cleaned_weights = optimizer.clean_weights(cutoff=1e-4, rounding=6)
    weights = pd.Series(cleaned_weights, dtype=float)
    weights = weights[weights > 0].sort_values(ascending=False)

    performance = optimizer.portfolio_performance(
        verbose=False,
        risk_free_rate=risk_free_rate,
    )
    return weights, tuple(float(value) for value in performance)
```

That is the part you should mentally compress the optimizer down to.

## What Each Step Means In Plain English

### `expected_returns = assets["total_expected_return"]`

This is `mu`.

It tells the optimizer what return estimate each asset is bringing into the problem.

### `covariance_input = ...`

This is `S`.

It tells the optimizer how the assets move relative to one another, which is how diversification enters the calculation.

### `EfficientFrontier(...)`

This creates the optimization problem.

At this point, PyPortfolioOpt knows:

- the expected returns
- the covariance matrix
- the global weight bounds

### `add_sector_constraints(...)`

PyPortfolioOpt uses the word "sector," but in this project we use it for the broad portfolio buckets:

- Cash
- Fixed Income
- Equity
- Fund

So this line is how the chosen investor band becomes a mathematical rule.

Example:

- Equity must stay between 60% and 80%
- Fixed Income must stay between 10% and 30%
- Cash must stay between 0% and 10%

### `max_sharpe(...)`

This is the current objective in the project policy.

In plain language:

- choose the best return-to-risk trade-off
- while obeying the active constraints

### `clean_weights(...)`

This removes tiny numerical leftovers that are not meaningful for a user-facing portfolio.

### `portfolio_performance(...)`

This gives the high-level summary metrics:

- expected return
- volatility
- Sharpe ratio

## Why The Real Repo Code Is Longer

The real allocator in `backend/soc_advisor/portfolio.py` does much more than the core optimizer because it has to behave like product code, not notebook code.

It also has to:

- use the configured portfolio data mode, including live SOC data or saved snapshots
- validate the shape of the input frames
- align tickers defensively
- load versioned policy config
- build structured response objects
- attach metrics and notes for the API/chat UI
- handle errors cleanly for the rest of the app

That is why the file is much longer than the bare optimizer example.

The extra length is mostly **wrapper logic**, not extra portfolio theory.

## Mapping The Demo To The Real Allocator

Use this mapping when reading both side by side.

### Snapshot input loading in the demo

- `load_demo_inputs()`

Closest real equivalents:

- `load_snapshot_frames()`
- `load_portfolio_frames()`

### Band policy loading in the demo

- `load_band_policy()`

Closest real equivalents:

- `load_portfolio_config()`
- `build_constraint_summary()`

### Pure optimizer section in the demo

- `run_bare_optimizer()`

Closest real equivalents:

- `_prepare_covariance_input()`
- `_build_optimizer()`
- `_apply_super_class_constraints()`
- `_solve_weight_vector()`
- `_build_portfolio_metrics()`
- `_optimize_portfolio()`

### Demo printout

- `print_demo_report()`

Closest real equivalents:

- `_build_holdings()`
- `RecommendationSummary`
- `chat_formatting.py`

## What Is Project Glue Versus "Real PyPortfolioOpt"

If you are defending the system, a good mental split is:

### Real PyPortfolioOpt usage

- create `EfficientFrontier`
- apply class constraints
- choose an objective
- solve
- read weights and performance

### Project glue

- load files or API frames
- choose the policy band
- convert policy into constraint dictionaries
- save answers and sessions
- render chat text
- expose HTTP routes
- store results in SQLite

That split matters because you do **not** need to explain every line of the surrounding app code at the same mathematical level as the solver call.

## Why The PSD Warning Still Shows Up

You may still see a covariance warning when running the demo.

That happens because the saved covariance snapshot is slightly non-positive-semidefinite due to numerical precision.

The fix in this script:

```python
risk_models.fix_nonpositive_semidefinite(...)
```

is not changing the investment policy. It is a numerical cleanup step so the optimizer can solve the problem safely.

## What This Demo Does Not Do

This script intentionally does **not** show:

- questionnaire logic
- score calculation
- manual band selection UI
- FastAPI routes
- Chainlit message flow
- database writes
- live SOC fallback handling

That is deliberate.

If you want the smallest explainable view of the optimizer, those pieces are noise.

If you want the full product flow, go back to:

- `application-boundaries.md`
- `code-reading-guide.md`
- `backend/soc_advisor/portfolio.py`

## Best Way To Explain This In A Defense

If someone asks, "What is PyPortfolioOpt doing in your project?", the clean answer is:

1. we first decide what kind of portfolio is allowed for the selected investor band
2. we translate those policy limits into mathematical constraints
3. we pass expected returns, covariance, and those constraints into PyPortfolioOpt
4. PyPortfolioOpt solves for the portfolio weights
5. the rest of our code packages that result into something the app can store, display, and explain

That is the defensible separation.

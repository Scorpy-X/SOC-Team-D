# Application Boundaries

This experiment is not one monolithic app. It is a small stack with separate
roles.

## What Kind Of Application This Is

The active advisor prototype is a Python-backed, multi-surface application:

- `experiments/chainlit_chat/chat_app.py` is a **Chainlit web chat UI**
- `backend/soc_advisor/main.py` is a **FastAPI HTTP API**
- `backend/soc_advisor/services.py` is the **session/questionnaire service layer**
- `backend/soc_advisor/portfolio.py` is the **allocation wrapper around PyPortfolioOpt**

So:

- yes, there is a web app surface
- yes, there is a FastAPI backend
- yes, there is also a separate Chainlit web UI
- Chainlit is not the optimizer
- FastAPI is not the optimizer

## Where Chainlit Fits

Chainlit owns:

- browser chat state
- message routing
- the question -> review -> band -> submit conversation flow
- rendering the final recommendation back to the user

Chainlit does **not** own:

- questionnaire definitions
- answer validation rules
- scoring
- portfolio optimization

Those live in `backend/soc_advisor/`.

## Where FastAPI Fits

FastAPI is the HTTP shell over the same backend service layer.

It owns:

- route definitions
- request parsing
- database session injection
- response serialization

It does **not** decide:

- which question is next
- how an answer is validated
- how a profile is selected
- how the portfolio is optimized

## Where PyPortfolioOpt Fits

PyPortfolioOpt is the solver used **inside** `backend/soc_advisor/portfolio.py`.

It is not the whole product. It is the numerical optimizer step inside the
product wrapper.

Research-style bare usage looks roughly like:

```python
mu = assets["total_expected_return"]
S = covariance_matrix

ef = EfficientFrontier(mu, S, weight_bounds=(0.0, 0.4))
ef.add_sector_constraints(sector_mapper, lower_bounds, upper_bounds)
ef.max_sharpe()

weights = ef.clean_weights()
```

If you want this as a runnable repo example instead of pseudocode, use:

- `scripts/demo_bare_pypfopt.py`
- `bare-pypfopt-demo.md`

The current product wrapper adds the parts a notebook usually does not:

- load data from the configured source, with saved CSV snapshots as the default demo path
- align tickers between the asset table and covariance matrix
- translate the chosen band into class constraints
- repair small covariance PSD issues in memory before solving
- convert weights into holdings, metrics, and UI/API-ready response objects

## The Current Runtime Data Path

The allocator supports three data modes. The default local demo mode reads the
saved CSV snapshots directly. Live mode can be enabled when API access is
available.

The saved snapshot files are:

- `data/exports/full_assets_df.csv`
- `data/exports/full_asset_covariance_df.csv`

Important rule:

- it always uses a matched pair from one source
- it does not mix live assets with snapshot covariance, or vice versa

## Practical Mental Model

If you need the simplest explanation of the stack, use this:

- Chainlit = chat UI
- FastAPI = HTTP API
- `services.py` = application logic
- `portfolio.py` = policy translation + optimizer wrapper
- PyPortfolioOpt = solver used by the allocator

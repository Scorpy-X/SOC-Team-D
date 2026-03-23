# SOC Team D Week 2 Submission Repository

This is the private Week 2 submission repository for SOC Team D.

It is curated for demo reliability and technical traceability. The repo keeps
the current frontend demo, the reusable SOC data-access package, the main
notebook-based evidence, exported data snapshots, and the current questionnaire
draft.

## Start Here

- Demo setup: [`Setup Demo.cmd`](Setup%20Demo.cmd)
- Demo launch: [`Run Demo.cmd`](Run%20Demo.cmd)
- Week 2 summary: [`docs/submission/week-2-summary.md`](docs/submission/week-2-summary.md)
- Questionnaire draft: [`docs/submission/Investor Questionnaire Draft - Week 2.pdf`](docs/submission/Investor%20Questionnaire%20Draft%20-%20Week%202.pdf)
- Technical evidence notebook: [`notebooks/api_tryouts.ipynb`](notebooks/api_tryouts.ipynb)
- Browser-friendly notebook export: [`notebooks/api_tryouts.html`](notebooks/api_tryouts.html)
- Data evidence: [`data/exports/`](data/exports/)
- Problem framing note: [`docs/guides/problem-understanding.md`](docs/guides/problem-understanding.md)

## What This Submission Shows

- a working frontend advisory demo in `frontend/`
- a reusable Python SOC API package in `backend/soc_api/`
- notebook-based exploration of the challenge data
- exported asset, covariance, and correlation tables in `data/exports/`
- a cleaned Week 2 investor questionnaire draft in `docs/submission/`

## Current Demo Status

- the frontend demo currently uses mock recommendation data
- the demo does **not** require the Python backend
- the demo does **not** require an API key
- there is **no** separate `Run API.cmd` in this repo because this submission
  repo presents the backend honestly as a reusable Python package plus notebooks,
  not as a served application

## Demo Setup

### Quickest path

1. Double-click `Setup Demo.cmd`
2. Wait for setup to finish
3. Double-click `Run Demo.cmd`
4. Open `http://localhost:5173` if the browser does not open by itself

### Developer path

1. Double-click `Setup Dev.cmd`
2. Add your API key to `.env` only if you want live SOC API notebook work
3. Double-click `Run Demo.cmd` when you want the frontend

## Script Guide

- `Setup Demo.cmd`
  - checks Node/npm
  - installs frontend dependencies
  - does not set up Python
- `Setup Dev.cmd`
  - checks Python and Node/npm
  - creates `.venv`
  - installs `requirements.txt`
  - installs frontend dependencies
  - creates `.env` from `.env.example` when missing
- `Run Demo.cmd`
  - starts the frontend demo server
  - opens the demo URL
- `scripts/bootstrap_env.py`
  - command-line bootstrap for the full developer setup
- `scripts/start_demo.ps1`
  - PowerShell entrypoint behind `Run Demo.cmd`
- `scripts/start_frontend.ps1`
  - starts the frontend directly from a terminal

## Technical Evidence Kept In This Repo

- `backend/soc_api/raw.py`
  - direct API access and payload handling
- `backend/soc_api/frames.py`
  - dataframe conversion helpers for analysis work
- `notebooks/api_tryouts.ipynb`
  - main notebook used to explore and inspect the challenge data
- `notebooks/api_tryouts.html`
  - rendered notebook export for quick browser review
- `notebooks/full_assets_df_analysis.pdf`
  - one additional analysis artifact kept for reviewer-friendly evidence
- `data/exports/`
  - exported CSV/XLSX snapshots derived from the SOC data
- `frontend/CONTRACT.md`
  - current frontend request/response contract

## What Was Intentionally Left Out

- assignment brief files and internal drafting documents
- internal Codex/agent-only repo files
- exploratory backend scaffold work that belongs in `SOC exp`
- extra exploratory notebooks and support files that do not strengthen the Week 2 submission story

## Manual Setup

Use this only if the launcher scripts do not work on the machine:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm.cmd ci
cd ..
```

If `npm.cmd ci` fails on a Windows file-lock error, retry with:

```powershell
cd frontend
npm.cmd install
cd ..
```

The `.env` file matters only for live SOC API notebook work. The frontend demo
path does not need an API key.

If you want to import the Python package directly from another file in this
repo, add `backend` to `sys.path` first:

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "backend"))
```

Then import from `soc_api`, for example:

```python
from soc_api.frames import get_full_assets_df, get_asset_covariance_df
```
from soc_api.raw import get_assets_json
```

If you want everything exported by the package in one step, this also works:

```python
from soc_api import *
```

That style is most reasonable in a small notebook or scratch file. In larger
code, `import soc_api as api` is usually easier to read.

Without that `sys.path` step, Python will usually raise
`ModuleNotFoundError: No module named 'soc_api'`.

## Developer reference

The Python docstrings still live in the code and are useful inside an editor.

For a concise reference of:

- function names
- parameters
- return values
- which module to import from

use:

- `docs/guides/api-reference.md`

## Verification Standard

This repo now separates definitions into two categories:

- `verified`: the meaning is supported by the local SOC documentation, the API structure itself, or an official external source
- `inferred`: the local project docs do not define the exact formula, so the meaning is based on standard finance/statistics usage plus the column name

This matters for columns such as `rate_beta`, `inflation_beta`, `fx_beta`, and `semi_deviation_ann`. Those names strongly suggest a meaning, but the repo does not currently contain a project-specific formula for them.

## Dataframes

### Info endpoint tables

These are the small support tables loaded from `/api/soc/info/`:

- `dataset_info_df`
- `dataset_groups_df`
- `super_classes_df`
- `asset_classes_df`
- `currencies_df`
- `available_asset_fields_df`
- `default_asset_fields_df`

These tables describe the dataset itself. They are not return or risk tables.

If you want these as raw JSON instead of dataframes, use:

- `soc_api.raw.get_info_json()`

### `full_assets_df`

This is the main one-row-per-asset table. If you are coming from CSV work, this is the most natural starting point.

Each row is one asset. The descriptive columns tell you what the asset is. The numeric columns summarize estimated return, risk, or sensitivity.

| Column | Plain-English meaning | How to read the numbers | Status | Main source |
| --- | --- | --- | --- | --- |
| `ticker` | Short market symbol for an asset | It is an identifier, not a measurement | verified | [Investor.gov: stock symbol](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-symbol) |
| `super_class` | Broad bucket such as Equity or Fixed Income | Use it as a high-level grouping field | verified | local API docs plus `/api/soc/info/` |
| `asset_class` | More specific category inside the broad bucket | Use it for a finer grouping than `super_class` | verified | local API docs plus `/api/soc/info/` |
| `currency` | Money unit used for the asset | `USD` and `JMD` are currencies, not risk scores | verified | dataset field meaning |
| `total_expected_return` | Estimated total return over a year | Treat it as a model estimate, not a promise | verified | return terminology plus dataset field name |
| `income_yield_ann` | Income-related yield over one year | Higher values mean more of the return is expected to come from income | verified | [Investor.gov: yield](https://www.investor.gov/introduction-investing/investing-basics/glossary/yield) |
| `volatility_ann` | Annualized variability of returns | Higher values usually mean more uncertainty or wider swings | verified | [Investor.gov: measuring risk](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/updated-investor-bulletin-measuring-risk) |
| `semi_deviation_ann` | Downside-focused version of volatility | It pays more attention to bad downside moves than upside moves | inferred | standard finance usage of semi-deviation |
| `skewness` | Asymmetry of the return distribution | Positive and negative values indicate which side has the longer tail | verified | [NIST: skewness and kurtosis](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm) |
| `excess_kurtosis` | Tail-heaviness relative to a normal distribution | Larger values suggest more extreme outcomes than a normal distribution | verified | [NIST: skewness and kurtosis](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm) |
| `modified_duration` | Interest-rate sensitivity measure used for bonds | Larger values usually mean bond prices are more sensitive to rate changes | verified | [Investor.gov: modified duration](https://www.investor.gov/introduction-investing/investing-basics/glossary/modified-duration) |
| `rate_beta` | Sensitivity score for interest-rate moves | Read as "how rate-sensitive this asset seems to be" unless the project gives a formula later | inferred | beta naming convention plus field name |
| `inflation_beta` | Sensitivity score for inflation changes | Read as "how inflation-sensitive this asset seems to be" | inferred | beta naming convention plus field name and [FRED: inflation explainer](https://fredblog.stlouisfed.org/2023/08/what-is-inflation/) |
| `fx_beta` | Sensitivity score for foreign-exchange moves | Read as "how currency-sensitive this asset seems to be" | inferred | beta naming convention plus field name |
| `expense_ratio_ann` | Annual operating-cost ratio charged by a fund-like product | Higher values mean more annual cost drag | verified | [Investor.gov: expense ratio](https://www.investor.gov/introduction-investing/investing-basics/glossary/expense-ratio) |

Worked example using the current dataset snapshot:

- `CWPU` is labeled `Fixed Income` and `Short Government Bonds`, so this row is describing a bond-like fixed-income asset.
- `currency = JMD`, so the row is expressed in Jamaican dollars.
- `total_expected_return = 0.0584` and `income_yield_ann = 0.0584`, so in this row the expected return is being driven almost entirely by income rather than price appreciation.
- `volatility_ann = 0.0239` and `semi_deviation_ann = 0.0159`, which is consistent with a lower-volatility profile than many equity rows in this dataset.
- `modified_duration = 1.2713`, so the asset still shows some interest-rate sensitivity.
- `fx_beta = 0.0`, so this field is not showing currency sensitivity for this example.

That is a good example of how one row in `full_assets_df` mixes category labels, return estimates, risk measures, and sensitivity measures.

Raw JSON equivalent:

- `soc_api.raw.get_assets_json(...)`

### `full_asset_correlations_df`

This is the full asset-by-asset correlation matrix.

Each row and each column is an asset. Each cell compares one asset with another.

How to read the numbers:

- `1` means the two series move perfectly together on the standardized correlation scale
- `-1` means they move in opposite directions on that scale
- `0` means little linear relationship
- the diagonal is always `1` because each asset is perfectly correlated with itself
- the matrix is symmetric, so the value for asset A versus asset B should match the value for asset B versus asset A

Why this table is useful:

- correlation is standardized, so it is easier to compare relationship strength across different pairs than covariance is
- low or negative correlation can matter for diversification

What correlation does **not** mean:

- it does not prove causation
- it does not tell you the size of returns

Main sources:

- [pandas: `DataFrame.corr`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.corr.html)
- [NIST: correlation and covariance discussion](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc541.htm)

Raw JSON equivalent:

- `soc_api.raw.get_asset_correlations_json(...)`

### `full_asset_covariance_df`

This is the full asset-by-asset covariance matrix.

It serves a similar role to the correlation matrix, but the numbers are not standardized.

How to read the numbers exactly:

- a positive covariance means the two assets tend to be above or below their own averages at the same time
- a negative covariance means when one asset is above its own average, the other tends to be below its own average
- a covariance near `0` means little linear co-movement around their averages
- the diagonal entries are each asset's variance, so they measure that asset's own spread
- the off-diagonal entries measure joint movement between two different assets

What the size of the number means:

- bigger absolute values can indicate stronger co-movement
- but covariance also depends on the scale and volatility of the underlying series
- because of that, you should not compare covariance magnitudes as casually as correlation magnitudes
- two very volatile assets can have a larger covariance simply because their swings are bigger

Practical interpretation:

- use covariance when you want the raw-scale co-movement information
- use correlation when you want an easier strength comparison on a common scale

Worked example using the current dataset snapshot:

- `cov(CWPU, DTOT) = 0.001776`
- `corr(CWPU, DTOT) = 0.6324`
- `var(CWPU) = 0.000571`
- `var(DTOT) = 0.013806`

How to read that pair:

- the positive covariance means `CWPU` and `DTOT` tend to move in the same direction around their own averages
- the positive correlation supports the same-direction interpretation on a standardized scale
- `DTOT` has much larger variance than `CWPU`, so part of the covariance size is coming from the larger scale of `DTOT`'s movement
- this is exactly why covariance needs more care than correlation when you compare raw magnitudes

Main sources:

- [pandas: `DataFrame.cov`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.cov.html)
- [NumPy: `numpy.cov`](https://numpy.org/doc/stable/reference/generated/numpy.cov.html)
- [NIST: covariance matrix discussion](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc541.htm)

Raw JSON equivalent:

- `soc_api.raw.get_asset_covariance_json(...)`

### `full_subclass_correlations_df`

This is a correlation matrix at the asset-subclass level rather than the single-asset level.

You read the numbers the same way you read `full_asset_correlations_df`:

- near `1`: subclasses tend to move together
- near `-1`: subclasses tend to move in opposite directions
- near `0`: little linear relationship

This table is useful when you want to reason about broader group behavior instead of individual tickers.

Raw JSON equivalent:

- `soc_api.raw.get_subclass_correlations_json()`

### Single-asset detail lookup

The endpoint `/api/soc/assets/{ticker}/` is useful for backend explanations and drilldown.

Use:

- `soc_api.raw.get_asset_detail_json(ticker)` for the exact payload
- `soc_api.frames.get_asset_detail_frames(ticker)` for dataframe pieces

The dataframe version returns:

- `asset_df`
- `top_correlations_df`
- `top_covariance_df`

### General definitions

| Term | Meaning | Main source |
| --- | --- | --- |
| `asset` | One investable item in the dataset | dataset structure |
| `metadata` | Data about the dataset itself, such as counts, groups, and available fields | dataset structure |
| `API` | The online service you ask for data | standard software term |
| `authentication` | Proving you are allowed to use the API, usually with an API key | standard software term |
| `histogram` | Plot that groups numeric values into bins so you can see the distribution | [Matplotlib: `hist`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html) |
| `heatmap-style matrix plot` | Color-coded matrix view used to scan high and low values quickly | [Matplotlib: `imshow`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.imshow.html) |
| `Treasury bill` or `T-bill` | Short-term government security issued by the U.S. Treasury | [TreasuryDirect: Treasury bills](https://www.treasurydirect.gov/marketable-securities/treasury-bills/) |
| `government bond` | Debt issued by a government | standard fixed-income term |
| `corporate bond` | Debt issued by a company | [Investor.gov: corporate bonds](https://www.investor.gov/additional-resources/general-resources/glossary/corporate-bonds) |

## Source List

Local source:

- `docs/assn_intr/Dimension Depths Documentation - Barita SOC.pdf`

Official external sources:

- [Investor.gov: stock symbol](https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-symbol)
- [Investor.gov: yield](https://www.investor.gov/introduction-investing/investing-basics/glossary/yield)
- [Investor.gov: modified duration](https://www.investor.gov/introduction-investing/investing-basics/glossary/modified-duration)
- [Investor.gov: expense ratio](https://www.investor.gov/introduction-investing/investing-basics/glossary/expense-ratio)
- [Investor.gov: measuring risk](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/updated-investor-bulletin-measuring-risk)
- [Investor.gov: corporate bonds](https://www.investor.gov/additional-resources/general-resources/glossary/corporate-bonds)
- [TreasuryDirect: Treasury bills](https://www.treasurydirect.gov/marketable-securities/treasury-bills/)
- [FRED Blog: What is inflation?](https://fredblog.stlouisfed.org/2023/08/what-is-inflation/)
- [pandas: `DataFrame.corr`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.corr.html)
- [pandas: `DataFrame.cov`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.cov.html)
- [NumPy: `numpy.cov`](https://numpy.org/doc/stable/reference/generated/numpy.cov.html)
- [NIST: skewness and kurtosis](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm)
- [NIST: correlation and covariance discussion](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc541.htm)
- [Matplotlib: `hist`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html)
- [Matplotlib: `imshow`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.imshow.html)


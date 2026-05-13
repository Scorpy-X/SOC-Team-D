# SOC Team D Week 6 Submission Repository

This repository is the Week 6 submission snapshot for the SOC investor-advisor
prototype.

The system demonstrates a chat-based investment-advisor workflow. A user answers
a risk-profiling questionnaire, confirms money amounts before they are saved,
reviews the answers, receives a calculated investor profile, passes through a
liquidity and volatility check, and receives a proposed portfolio with a user
HTML report and a separate technical audit report.

The main Week 6 story is explainability. The repository now shows how the
prototype moves from questionnaire answers to an investor type, from investor
type to portfolio constraints, from constraints to PyPortfolioOpt holdings, and
from the final portfolio to user-facing and audit-facing explanations.

## Main Demo Path

1. Double-click `Setup Dev.cmd`.
2. Double-click `Run Chainlit Experiment.cmd`.
3. Open `http://localhost:8010` if the browser does not open automatically.
4. Complete the questionnaire.
5. Type `yes` to confirm each parsed money amount.
6. Review the answers and edit one if needed.
7. Continue to the risk check.
8. Type `yes` after the volatility notice.
9. Open the generated portfolio report from the chat.

The detailed user and audit reports are generated locally under `data/reports/`.
Those generated files are intentionally not committed.

## What The Prototype Does

The Week 6 prototype includes:

- a Chainlit chat interface for the guided investor profile workflow
- a typed questionnaire with multiple-choice and money amount answers
- automatic risk-profile scoring from questionnaire answers
- liquidity-aware profile compatibility checking
- automatic adjustment to the nearest safer compatible profile when liquidity requires it
- constrained portfolio construction using PyPortfolioOpt
- a short chat summary with key metrics and selected investments
- a user-facing HTML portfolio report
- a technical audit report with scoring, liquidity, formula, and optimizer trace details
- sample report generation for all five investor profiles
- optimizer validation and advisor-flow validation scripts

The separate `frontend/` demo remains in the repository, but the primary Week 6
submission path is the Chainlit advisor and reporting workflow.

## Step-By-Step System Flow

The active advisor flow is:

```text
questionnaire
-> money amount confirmation
-> answer review and optional edit
-> calculated investor profile
-> optional advisor/demo profile override
-> liquidity compatibility check
-> automatic safer-profile adjustment if needed
-> volatility notice
-> portfolio optimization
-> chat summary
-> user report and audit report
```

The user sees the simplified version of this flow. The audit report records the
technical trace that explains what happened internally.

## Active Configuration

The Week 6 snapshot uses:

- questionnaire: `config/questionnaires/v4.json`
- scoring: `config/scoring/v5.json`
- portfolio policy: `config/portfolio/v3.json`

These versions are intentionally explicit so that the submitted behavior can be
reproduced and explained.

## Questionnaire And Risk Scoring

The questionnaire has fourteen live questions, excluding the older currency
exposure question.

Questions 1-4 capture liquidity:

1. portfolio value
2. expected major withdrawal need
3. essential monthly expenses
4. desired emergency reserve

Questions 5-9 measure risk capacity:

5. current emergency fund
6. non-investment income stability
7. dependents and obligations
8. investment time horizon
9. investment phase

Questions 10-14 measure risk tolerance:

10. reaction to a 25% market drop
11. willingness to accept short-term losses
12. financial knowledge
13. investing experience
14. reaction to a hypothetical 30% portfolio decline

Each scoring answer is normalized between `0.0` and `1.0`.

Risk capacity is calculated as:

```text
capacity =
((Q5 * 0.20) + (Q6 * 0.30) + (Q7 * 0.15) + (Q8 * 0.35) + (Q9 * 0.35)) / 1.35
```

Risk tolerance is calculated as:

```text
tolerance =
((Q10 * 0.40) + (Q11 * 0.15) + (Q12 * 0.15) + (Q13 * 0.15) + (Q14 * 0.25)) / 1.10
```

The final questionnaire score is:

```text
final score = (capacity * 0.60) + (tolerance * 0.40)
```

The score maps to investor profiles:

| Score range | Investor profile |
| --- | --- |
| `0.00-0.20` | Very Conservative |
| `0.20-0.40` | Conservative |
| `0.40-0.60` | Balanced |
| `0.60-0.80` | Growth |
| `0.80-1.00` | Aggressive |

One cap rule is applied: if the user says they would sell everything after a
severe market drop, the maximum calculated profile is `Balanced`. This prevents
the system from assigning a highly growth-oriented profile to someone whose
decline response suggests they may exit during severe volatility.

The normalized final score is also displayed as a 1-10 risk score for easier
communication.

## Investor Types

The five investor profiles correspond to different balances between capital
preservation, income, growth, and expected portfolio movement.

| Profile | Meaning |
| --- | --- |
| Very Conservative | Focuses mainly on capital preservation and liquidity. |
| Conservative | Prioritizes stability and income with limited growth exposure. |
| Balanced | Mixes stabilizing assets with meaningful growth exposure. |
| Growth | Targets higher long-term growth and accepts more short-term movement. |
| Aggressive | Prioritizes long-term growth and assumes the investor can tolerate large short-term losses. |

The report explains the final profile in terms of risk capacity, risk tolerance,
and liquidity need. For example, a user may have high capacity but low tolerance;
in that case the system should avoid treating capacity alone as permission to
use the most aggressive portfolio.

## Liquidity Policy

Liquidity is handled separately from the risk-bucket score.

The system calculates required liquidity as:

```text
required liquidity = major expense withdrawal + (essential monthly expenses * emergency months)
```

The emergency-month mapping is:

| Questionnaire answer | Months used |
| --- | ---: |
| 0 months | `0` |
| 1-3 months | `2` |
| 4-6 months | `5` |
| More than 6 months | `9` |

The liquidity floor is:

```text
liquidity floor = required liquidity / portfolio value
```

Liquidity is applied to `Cash` only. If the calculated or selected profile can
support the required Cash level, the system continues normally. If the selected
profile cannot support that Cash level, the system automatically uses the
nearest safer compatible profile. If no configured profile can support the
liquidity floor, report generation is blocked.

Example:

```text
portfolio value = $100,000
major withdrawal = $22,000
monthly expenses = $0
emergency months = 0

required liquidity = $22,000 + ($0 * 0) = $22,000
liquidity floor = $22,000 / $100,000 = 22%
```

If the user was initially in `Growth`, the system checks the Growth Cash ceiling.
Growth allows Cash up to `15%`, so `22%` is incompatible. The system then moves
toward safer profiles until it finds one with enough Cash room. In this example,
`Conservative` can support up to `30%` Cash, so the report uses `Conservative`.

The user report discloses the adjustment in plain language. The audit report
records the formula, inputs, original profile, effective profile, and action.

## Portfolio Constraints

The active portfolio policy uses four broad investment types:

- Cash
- Fixed Income
- Equity
- Fund

The current profile ranges are:

| Profile | Cash | Fixed Income | Equity | Fund |
| --- | ---: | ---: | ---: | ---: |
| Very Conservative | `15-35%` | `55-80%` | `0-20%` | `0-10%` |
| Conservative | `10-30%` | `45-70%` | `15-35%` | `0-10%` |
| Balanced | `5-20%` | `25-55%` | `35-65%` | `0-15%` |
| Growth | `0-15%` | `10-40%` | `50-85%` | `0-15%` |
| Aggressive | `0-10%` | `0-25%` | `70-100%` | `0-20%` |

The single-asset cap is `40%`. This prevents the optimizer from putting an
unreasonably large part of the portfolio into one asset, even if that asset is
mathematically attractive under the expected return and covariance inputs.

When liquidity requires a higher Cash floor, the effective Cash minimum becomes:

```text
effective Cash minimum = max(configured Cash minimum, liquidity floor)
```

The Cash maximum is not raised. That is why incompatible profiles are adjusted
instead of forcing an infeasible portfolio.

## How PyPortfolioOpt Is Used

[PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) is the
optimization engine used after the system has selected the effective investor
profile and portfolio constraints. The library is not deciding the investor
type; it receives the project's approved inputs, constraints, and objective,
then solves for portfolio weights inside those limits.

The optimizer receives:

- expected annual return for each asset
- covariance matrix for the asset universe
- asset metadata such as ticker, investment type, asset class, and currency
- broad investment-type constraints from the selected profile
- a single-asset cap
- any Cash-floor overlay from the liquidity check

The flow is similar to the standard PyPortfolioOpt workflow:

```text
SOC asset data
  -> expected returns
  -> covariance / risk matrix
  -> PyPortfolioOpt EfficientFrontier
  -> project constraints and objective
  -> cleaned portfolio weights
  -> holdings, metrics, chat summary, and HTML reports
```

In other words, the system uses PyPortfolioOpt for the optimization stage, but
the advisory logic around it is ours: questionnaire scoring, liquidity policy,
profile constraints, report wording, audit traces, and validation scripts.

The simplified optimizer path is:

```python
mu = assets["total_expected_return"]
S = covariance_matrix

ef = EfficientFrontier(mu, S, weight_bounds=(0.0, single_asset_cap))
ef.add_sector_constraints(sector_mapper, lower_bounds, upper_bounds)
ef.max_sharpe(risk_free_rate=0.0)

weights = ef.clean_weights()
```

PyPortfolioOpt calls the broad bucket mapping `sector constraints`. In this
project, those sectors are the advisory investment types: Cash, Fixed Income,
Equity, and Fund.

The current objective is `max_sharpe`, meaning the optimizer searches for the
highest return-per-unit-of-volatility portfolio that still obeys the configured
constraints.

The covariance matrix is passed through a positive-semidefinite repair step
before optimization. That is a numerical stability step on the input matrix; it
does not change the investment policy.

## Why PyPortfolioOpt Is Credible

PyPortfolioOpt is not treated as a black-box financial advisor. It is used as a
portfolio optimization library that implements standard mean-variance portfolio
optimization techniques.

Its credibility comes from three layers:

1. it is a known, citable Python library for portfolio optimization work
2. it implements established Markowitz-style mean-variance optimization ideas
3. the project independently checks the same constrained problem using
   [SciPy](https://github.com/scipy/scipy)'s SLSQP optimizer path

The [SciPy SLSQP cross-check](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)
matters because SciPy is a general scientific-computing library, not a
portfolio-specific wrapper. Replaying the same objective, expected returns,
covariance matrix, bounds, and superclass constraints through SciPy gives an
independent numerical check that the integration is behaving as expected.

This does not prove that the recommendation is financially perfect. It supports
the narrower and more defensible claim: the implementation follows the stated
rules and the optimizer output can be independently replayed.

Useful references for judges and reviewers:

- [PyPortfolioOpt documentation](https://pyportfolioopt.readthedocs.io/)
- [PyPortfolioOpt GitHub repository](https://github.com/PyPortfolio/PyPortfolioOpt)
- [PyPortfolioOpt JOSS paper](https://joss.theoj.org/papers/10.21105/joss.03066)
- [SciPy documentation](https://docs.scipy.org/doc/scipy/)
- [SciPy GitHub repository](https://github.com/scipy/scipy)
- [SciPy SLSQP optimizer documentation](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)

## Validation And Testing Evidence

The repository includes automated tests and click-runnable validation scripts.
For reviewers who do not want to run the scripts, a committed evidence snapshot
is available under
[`docs/submission/week-6-evidence/`](docs/submission/week-6-evidence/).

Main commands:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp\pytest-week6-teamd
.\.venv\Scripts\python.exe scripts\run_advisor_flow_validation.py
.\.venv\Scripts\python.exe scripts\run_optimizer_validation.py
.\.venv\Scripts\python.exe scripts\generate_sample_investor_reports.py
```

Windows launchers are also provided:

- `Run Advisor Flow Validation.cmd`
- `Run Optimizer Validation.cmd`
- `Run Optimizer Developer Check.cmd`
- `Run Sample Investor Reports.cmd`

Advisor-flow validation checks:

- calculated questionnaire profile path
- advisor/demo profile override path
- unknown override rejection
- automatic liquidity adjustment for questionnaire profiles
- automatic liquidity adjustment for override profiles
- no-compatible-profile blocking
- volatility notice trace persistence

Optimizer validation checks every active profile in `config/portfolio/v3.json`.
For each profile, it reports:

- expected yearly return
- expected yearly movement
- estimated income
- holdings and weights
- Cash, Fixed Income, Equity, and Fund totals
- single-asset cap compliance
- superclass range compliance
- SciPy SLSQP cross-check result
- stress checks for return haircut, covariance shock, and largest-holding removal

Sample report generation creates one user report and one audit report for each
investor profile under `data/reports/samples/latest/`. These generated reports
are local review artifacts and are not committed.

## Chatbot And Report Design Rationale

The Chainlit interface and HTML report use a softer blue visual direction to
better align with Barita's brand direction while keeping the prototype calm and
readable. The goal was not to mimic a final production brand exactly; it was to
avoid a harsh generic AI interface and make the demo feel more like a financial
product.

Design choices include:

- light and dark theme support
- softer blue surfaces instead of purple-heavy AI styling
- readable report typography
- compact chat summaries
- detailed explanations moved into the HTML report
- a separate audit report for technical review

The user report is written for a client or reviewer. The audit report is written
for defense, debugging, and traceability.

## Repository Map

- `experiments/chainlit_chat/` - Chainlit chat controller
- `public/` - Chainlit theme, custom CSS, and custom review/report elements
- `backend/soc_advisor/` - questionnaire, scoring, liquidity, portfolio, reports, validation helpers
- `backend/soc_advisor/report_templates/` - user and audit HTML templates
- `backend/soc_api/` - SOC API/dataframe access helpers
- `config/questionnaires/` - questionnaire definitions
- `config/scoring/` - scoring policy definitions
- `config/portfolio/` - portfolio profile constraints
- `data/exports/` - saved SOC data snapshots used by default
- `scripts/` - launchers, validation runners, sample report generation
- `tests/` - automated Python test suite
- `docs/submission/` - weekly submission summaries and archive
- `docs/experiments/chainlit-pyportfolio/` - deeper explanation and validation notes

## Other Runtime Paths

`Run API.cmd` starts the FastAPI inspection path.

`Setup Demo.cmd` and `Run Demo.cmd` remain available for the secondary frontend
demo, but the frontend is not the main Week 6 submission identity.

## Important Limitations

This is still a prototype, not a final regulated advisory product.

Important limits:

- expected returns are estimates, not guarantees
- the risk score is a questionnaire policy model, not a full suitability framework
- the liquidity logic handles Cash reserve compatibility but not every possible financial-planning need
- the volatility notice is a simplified stress estimate, not formal VaR and not a guaranteed maximum loss
- data quality affects optimizer output
- optional OpenAI support, when enabled, rewrites report prose only and does not choose profiles, calculate metrics, or change holdings
- final investment policy and regulatory review would still require approval beyond this software prototype

## Historical Submission Material

Previous submission material is preserved as project history:

- `docs/submission/week-5-summary.md`
- `docs/submission/week-4-summary.md`
- `docs/submission/week-3-summary.md`
- `docs/submission/week-2-summary.md`
- `docs/submission/archive/`

Week 6 is now the primary repository story.

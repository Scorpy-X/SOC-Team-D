# Testing And Validation Evidence

This note explains how the SOC advisor prototype is tested and what those
tests can honestly prove.

The short version:

> The tests show that the implementation follows the documented rules, applies
> portfolio constraints consistently, records an audit trail, and can replay the
> optimizer through an independent numerical solver path. They do not prove that
> the financial recommendation is guaranteed correct or ready for regulated
> client use.

## What Was Tested

The validation evidence covers the main advisor path:

- questionnaire and scoring behavior
- liquidity compatibility behavior
- advisor override and liquidity-adjustment behavior
- portfolio constraint compliance
- independent SciPy optimizer cross-check
- stress checks
- report and audit trace output
- Chainlit browser smoke flow

This matters because the system is not defended by one claim such as "we used
PyPortfolioOpt." The stronger defense is that each major step can be checked,
replayed, and explained.

## Commands Used

The implementation was checked with:

```powershell
.\.venv\Scripts\python.exe -m compileall backend\soc_advisor experiments\chainlit_chat scripts
```

Purpose:

- catches syntax errors
- catches import-level issues in the advisor backend, Chainlit app, and scripts

The full automated test suite was run with:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp=tmp\pytest-docx-scoring
```

Latest observed result:

```text
83 passed, 39 warnings
```

The optimizer validation evidence pack can be run with:

```powershell
.\.venv\Scripts\python.exe scripts\run_optimizer_validation.py
```

Latest observed result:

```text
Overall result: PASS
```

The advisor-flow validation evidence pack can be run with:

```powershell
.\.venv\Scripts\python.exe scripts\run_advisor_flow_validation.py
```

That runner checks profile override, liquidity adjustment, and risk-check trace
behavior. It is intentionally separate from optimizer validation.

Both validation runners print their audit reports to the terminal and write
local logs under:

- `data/validation/optimizer-validation-latest.txt`
- `data/validation/optimizer-validation-<timestamp>.txt`
- `data/validation/advisor-flow-validation-latest.txt`
- `data/validation/advisor-flow-validation-<timestamp>.txt`

Those generated logs are local evidence artifacts and should not be committed
by default.

## Questionnaire And Scoring Checks

The tests check that the active questionnaire and scoring policy match the
documented design:

- questionnaire `v4` has 14 questions, excluding the currency-exposure question
- Q1-Q4 are liquidity questions and are separate from the risk-bucket score
- Q5-Q9 form the risk-capacity section
- Q10-Q14 form the risk-tolerance section
- Q10 includes `Do nothing / stay invested`
- Q14 uses the hypothetical 30% loss reaction question
- the final normalized score is translated into a user-facing `1` to `10` risk score

The scoring checks confirm:

- risk capacity is normalized by `1.35`
- risk tolerance is normalized by `1.10`
- the final score is `60% capacity + 40% tolerance`
- conservative-style answers map to `Very Conservative`
- aggressive-style answers map to `Aggressive`
- aggressive-style answers plus Q10 `sell everything` cap the profile at `Balanced`
- the displayed `1` to `10` score is clamped and mapped from the final normalized score

That last check is important. It means a user who says they would sell
everything after a major market drop cannot receive a high-risk calculated
profile from the automatic scoring path.

## Liquidity Compatibility Checks

Liquidity is checked separately from the risk score.

The tests confirm the emergency-month mapping:

- `0 months` -> `0`
- `1-3 months` -> `2`
- `4-6 months` -> `5`
- `More than 6 months` -> `9`

The liquidity formula is:

```text
required liquidity = major expense withdrawal + (essential monthly expenses * emergency months)
liquidity floor = required liquidity / portfolio value
```

The tests check that:

- compatible selected profiles stay unchanged
- incompatible profiles automatically move to the nearest safer compatible profile
- report generation is blocked when no profile can satisfy the liquidity floor
- missing or invalid liquidity answers fail clearly

Example:

```text
selected profile = Growth
liquidity floor = 22%
Growth Cash ceiling = 15% -> incompatible
Balanced Cash ceiling = 20% -> incompatible
Conservative Cash ceiling = 30% -> compatible
profile used for the report = Conservative
```

This behavior is defensible because the system does not discard the user's
liquidity requirement. It either discloses an automatic move to a safer
compatible profile or stops and asks for revised liquidity inputs.

## Advisor Override Flow Checks

Override behavior is not mixed into `run_optimizer_validation.py` because it is
not optimizer math. It is service-flow behavior.

The separate advisor-flow runner is:

- `Run Advisor Flow Validation.cmd`
- `scripts/run_advisor_flow_validation.py`
- `backend/soc_advisor/advisor_flow_validation.py`

It uses an isolated temporary SQLite database so it does not mutate the normal
app database.

The advisor-flow validation checks:

- calculated questionnaire profile submission with no manual override
- compatible manual override submission
- unknown manual override rejection
- incompatible manual override automatic liquidity adjustment
- calculated questionnaire profile plus automatic liquidity adjustment
- no-compatible-profile rejection when liquidity exceeds every Cash ceiling
- risk reality trace persistence with manual override status preserved
- explanation-trace completeness for the saved `DecisionTrace`

That trace-completeness check confirms the saved audit payload includes the
fields needed by the current explanation contract, including:

- scoring version and portfolio version
- capacity, tolerance, and final score
- cap result
- manual override status
- liquidity calculation and effective profile
- applied constraint overlays
- optimizer settings and data source
- risk-check values
- limitation notes

This runner supports the claim that advisor review and override behavior is
traceable and deterministic. It does not validate portfolio optimization; that
remains the job of `run_optimizer_validation.py`.

## Portfolio Constraint Checks

The optimizer validation runner checks every profile in the active portfolio
config.

Current active portfolio config:

- `config/portfolio/v3.json`

The runner does not hard-code "profile 1 means Balanced" or similar brittle
logic. It reads the profile order, profile ids, labels, descriptions,
superclass ranges, single-asset cap, optimizer objective, and weight bounds
from the same config used by the advisor.

For every configured profile, the validation report checks:

- all asset weights sum to `100%`
- no single asset exceeds the `40%` cap
- Cash stays inside that profile's configured floor and ceiling
- Fixed Income stays inside that profile's configured floor and ceiling
- Equity stays inside that profile's configured floor and ceiling
- Fund stays inside that profile's configured floor and ceiling
- the optimizer produces holdings and summary metrics without crashing

The report also prints:

- profile number, id, label, and description
- data source used by the allocator
- covariance matrix shape
- optimizer objective
- risk-free rate
- weight bounds
- covariance repair setting
- optimized holdings and weights
- superclass allocation mix
- expected return, expected yearly movement, income, cost, duration, and largest holding

## Independent SciPy Cross-Check

The validation runner also replays the same optimization through SciPy's
`optimize.minimize` function using the `SLSQP` method.

The roles are different:

- PyPortfolioOpt is the advisor's production portfolio-optimization wrapper.
- SciPy is a separate general-purpose scientific-computing library.

The cross-check gives SciPy the same:

- expected returns
- covariance matrix
- weight bounds
- single-asset cap
- superclass minimum and maximum constraints
- max-Sharpe objective structure

Then the validation report compares:

- PyPortfolioOpt Sharpe objective
- SciPy Sharpe objective
- objective gap
- largest weight difference
- whether SciPy also satisfies all constraints

This gives stronger evidence than only saying "PyPortfolioOpt ran." It checks
whether another credible numerical solver path can solve the same constrained
problem and reach the same result within tolerance.

## Why SciPy Adds Credibility

SciPy is not a financial-advice system and should not be described as one.

Its credibility here comes from a narrower point: SciPy is one of the standard
scientific-computing libraries in Python and is widely used for numerical
methods, including constrained optimization.

Relevant references:

- SciPy optimization tutorial: <https://docs.scipy.org/doc/scipy/tutorial/optimize.html>
- SciPy SLSQP documentation: <https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html>
- SciPy citation page: <https://scipy.org/citing-scipy/>
- SciPy 1.0 Nature Methods paper: <https://doi.org/10.1038/s41592-019-0686-2>

The defense claim is:

> SciPy gives us an independent, credible constrained numerical optimizer that
> can replay the same optimization problem outside PyPortfolioOpt's
> portfolio-specific wrapper.

The boundary is:

> Agreement between PyPortfolioOpt and SciPy supports implementation
> correctness and constraint compliance. It does not prove that the financial
> policy, expected returns, covariance estimates, or suitability model are final.

## Stress Checks

The validation runner also tests how the optimizer behaves when inputs are made
less friendly.

Current stress checks:

- expected-return haircut
- covariance/risk shock
- largest optimized holding removed

Each stress check must either:

- produce a feasible portfolio, or
- record a clear failure reason in the audit log

These checks do not prove that the model is financially perfect. They show that
the integration can be tested under changed conditions and that failures are
visible instead of hidden.

## Report And Audit Trace Checks

The report tests confirm that submitted results store and display the important
decision path.

The checked trace information includes:

- active questionnaire, scoring, and portfolio versions
- capacity score
- tolerance score
- final score
- cap rule, if applied
- original profile and final profile
- liquidity calculation
- Cash-floor overlay
- risk reality check
- optimizer settings
- constraints used
- data source used
- report wording mode

The user report stays client-readable. The audit report keeps the more
technical trace needed for debugging and defense.

The final Chainlit chat response is also checked at the formatting layer. It
now includes a compact `Investments selected` section with asset codes,
investment-type grouping, allocation percentages, and estimated dollar amounts
when portfolio value is available. The detailed explanation still belongs in
the HTML report.

## Chainlit Browser Smoke Test

A practical browser smoke test was also run against the Chainlit app.

The smoke path checked:

- Chainlit loaded locally on `http://127.0.0.1:8010`
- the `v4` questionnaire appeared
- `$100,000` was entered and confirmed as a numeric money answer
- all 14 questions were completed
- Q10 was answered with `Sell everything`
- the calculated profile capped to `Balanced`
- the risk reality check appeared
- continuing through the risk check generated the report-ready state
- the right-side assessment summary showed saved answers and the profile result

This confirms that the user-facing flow works beyond isolated backend tests.

## What This Proves

The testing evidence supports these claims:

- the implementation follows the documented questionnaire and scoring rules
- liquidity behavior is deterministic and explainable
- advisor override and liquidity-adjustment behavior is deterministic and traceable
- portfolio constraints are checked for every configured profile
- optimizer output is traceable through holdings, metrics, and constraints
- the same constrained optimization can be replayed through SciPy
- report output includes the decision trace needed for review
- the Chainlit path can complete a real interaction flow

## What This Does Not Prove

The tests do **not** prove:

- expected return estimates are correct
- the covariance matrix is perfect
- the profile ranges are financially optimal
- the scoring model is final regulatory suitability logic
- the output is guaranteed to be appropriate advice for a real client
- the prototype is ready for regulated production use

Those still require data review, math-team approval, suitability review, legal
review, and compliance review.

## Slide-Ready Summary

Use this wording in presentation preparation:

> We test the questionnaire, liquidity policy, advisor override flow, optimizer
> constraints, report trace, and live chatbot flow. The optimizer output is
> checked against every configured portfolio rule, including total weight,
> asset-class ranges, and the single-asset cap. We also replay the same
> optimization through SciPy's independent SLSQP solver path to check that the
> constrained problem produces the same result outside PyPortfolioOpt's
> portfolio wrapper. This validates controlled implementation behavior, not
> guaranteed investment suitability.

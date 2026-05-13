# Allocation Methodology And Testing

This note is for presentation, defense, and product hardening.

It answers four practical questions:

1.  How deep do we need to understand the allocator to defend it?
2.  What does the current PyPortfolioOpt path do step by step?
3.  What should the chatbot explain to users and reviewers?
4.  How should we test this like a financial product rather than a class demo?

## Why this matters in the Barita challenge

The Barita challenge guide does not ask for a black-box chatbot.

It asks for a product that can:

- generate defensible allocations
- explain recommendation logic clearly
- show coherent links between profile inputs and data-driven portfolio decisions
- improve reliability through testing and calibration

That means the team must be able to defend:

- the suitability logic
- the allocation policy
- the optimization step
- the explanation layer

The goal is not to prove that we know every solver detail inside `cvxpy`.

The goal is to show that the product behaves like a disciplined advisory system.

## The main answer first

No, you do **not** need to defend every internal mathematical detail of PyPortfolioOpt.

You do need to defend the parts that materially affect the recommendation.

For this project, that means you should be able to explain:

1.  what inputs the optimizer receives
2.  what constraints define the allowed portfolio set
3.  what objective the optimizer is trying to improve
4.  how the final holdings come out of that process
5.  what the limitations and assumptions are

If asked about deeper solver internals, the right answer is:

"PyPortfolioOpt formulates the portfolio selection problem as a constrained optimization problem and solves it through its underlying numerical solver. We use it as the allocation engine, but our product logic is defined by the constraints, inputs, and policy choices we provide."

That is a strong answer.

## How deep your understanding should go

### Level 1: Client or executive defense

This is the level you absolutely need.

You should be able to explain:

- what investor information is collected
- how that becomes a risk category or policy bucket
- what allocation ranges are allowed for that category
- that the optimizer only chooses holdings inside those ranges
- that covariance is used to avoid filling the portfolio with assets that all behave too similarly
- that the recommendation comes with reasons, holdings, and portfolio metrics

At this level, you do **not** need to explain convex optimization theory.

### Level 2: Compliance, regulator, or serious lecturer defense

You should also be able to explain:

- the exact inputs used
- the exact rules applied
- the exact objective used
- what data version and config version were active
- what warnings or fallback paths exist
- what the system does **not** currently do

At this level, you should understand the allocator step by step, but still not need to derive the solver mathematics from first principles.

### Level 3: Technical/code defense

If a reviewer goes into implementation details, you should understand:

- where the inputs come from in code
- where the constraints are built
- where the optimizer is called
- how weights are cleaned and converted into holdings
- what tests cover the behavior

This means you should understand the code path clearly, even if you do not know the full internals of PyPortfolioOpt itself.

## The current allocator step by step

The active allocator path is in `backend/soc_advisor/portfolio.py`.

In plain language, the current flow is:

1.  `build_recommendation()` starts the allocation run.
2.  `load_portfolio_config()` loads the active policy file:
    - `config/portfolio/v3.json`
3.  `load_portfolio_frames()` uses the configured portfolio data mode. The default demo mode uses:
    - `data/exports/full_assets_df.csv`
    - `data/exports/full_asset_covariance_df.csv`
4.  `build_constraint_summary()` converts the selected band into:
    - per-asset cap
    - class minima
    - class maxima
5.  `_optimize_portfolio()` runs the actual optimization.
6.  `_build_holdings()` converts final weights into holding objects.
7.  the backend returns:
    - holdings
    - metrics
    - active constraints
    - notes

## What `_optimize_portfolio()` does and why each step is valid

This is the part you should know best.

### Step 1: Prepare the covariance matrix

Code:

- `risk_models.fix_nonpositive_semidefinite(...)`

What it does:

- repairs a small numerical defect in the covariance matrix before solving

Why this is valid:

- covariance matrices used in portfolio optimization need to behave mathematically like proper risk matrices
- the current snapshot has a small PSD defect
- the repair is a numerical stability step, not a change in investment policy

What to say:

"We repair a small numerical inconsistency in the covariance matrix so the solver can run reliably. This is a technical stability step, not a portfolio preference decision."

### Step 2: Build the expected-return vector

Code:

- `assets["total_expected_return"]`

What it does:

- creates one expected return value per asset

Why this is valid:

- the optimizer needs an estimate of return to compare asset choices

Important limitation:

- expected returns are assumptions, not guarantees
- this is one of the most sensitive inputs in any optimizer-based product

### Step 3: Apply per-asset bounds

Code:

- `weight_bounds=(lower_bound, upper_bound)`

What it does:

- limits each single asset weight
- current default cap is `40%`

Why this is valid:

- prevents the solver from concentrating too much in one asset
- this is a standard risk-control measure

### Step 4: Create the Efficient Frontier problem

Code:

- `EfficientFrontier(expected_returns, covariance_input, weight_bounds=(...))`

What it does:

- sets up the optimization problem
- the decision variables are the asset weights

What is being optimized:

- a portfolio of weights that must satisfy all rules

### Step 5: Add class constraints

Code:

- `ef.add_sector_constraints(...)`

What it does:

- applies the selected band ranges to broad classes like:
  - Cash
  - Fixed Income
  - Equity
  - Fund

Why this is valid:

- this is where suitability and policy are enforced
- the optimizer is not free to ignore the selected client profile

This is one of the most important product-defense points.

### Step 6: Add any extra linear constraints

Code:

- `ef.add_constraint(...)`

What it does:

- allows extra minimum or maximum limits on weighted portfolio metrics

Current active note:

- the Variant B path is currently band-only, so these are not the center of the live policy

Why this matters:

- this is how you would later add technical safeguards such as duration caps or expense caps without rewriting the optimizer

### Step 7: Optimize using the objective

Code:

- `ef.max_sharpe(risk_free_rate=risk_free_rate)`

What it does:

- looks for the portfolio with the strongest expected return per unit of risk inside the allowed constraint region

Why this is valid:

- it does not maximize return blindly
- it uses both expected return and covariance
- it tries to improve the return-risk trade-off, not just one metric alone

Important limitation:

- `max_sharpe` is only as sensible as the expected-return and covariance inputs
- if those assumptions are weak, the output can still be weak

### Step 8: Clean the weights

Code:

- `ef.clean_weights(...)`

What it does:

- removes very tiny floating-point leftovers
- rounds the results to cleaner weight values

Why this is valid:

- it improves readability
- it does not change the broad portfolio logic

### Step 9: Compute portfolio metrics

Code:

- `ef.portfolio_performance(...)`
- weighted sums over fields like:
  - `income_yield_ann`
  - `modified_duration`
  - `expense_ratio_ann`

What it does:

- produces summary values for the final portfolio

Why this is valid:

- the recommendation should not just show holdings
- it should also show risk and portfolio characteristics

### Step 10: Convert weights into holdings

Code:

- `_build_holdings()`

What it does:

- takes the nonzero weights and packages them into user-facing holding records

Why this is valid:

- clients and judges need a readable portfolio, not only a raw weight vector

## The product defense story you should use

The strongest framing is:

1.  suitability decides the allowed portfolio region
2.  policy translates that into hard class constraints
3.  PyPortfolioOpt selects exact holdings inside that region
4.  the explanation layer tells the user what happened and why

That is a much better defense than:

- "the optimizer found the answer"
- "the AI decided the best portfolio"

## What the chatbot should explain

The chatbot should not invent explanations from scratch.

It should explain from a stored decision trace.

For each recommendation, the system should be able to state:

- questionnaire version
- profile source
- selected band
- active class ranges
- optimizer objective
- data snapshot version
- final class totals
- final holdings
- summary metrics
- important limitations

Good client-facing explanation pattern:

1.  "Your recommendation used the Growth band."
2.  "That band allowed 60-80% equity, 10-30% fixed income, and 0-10% cash."
3.  "Within those limits, the allocator preferred these holdings because they improved expected return while accounting for how assets move together."
4.  "Covariance was used to reduce over-concentration in assets that behave too similarly."

## What the chatbot should not say

Do not let the chatbot say:

- "the AI knows your best portfolio"
- "this will maximize your returns"
- "this is guaranteed to be suitable"

Better wording:

- "based on the information provided"
- "under the current policy constraints"
- "using the current approved asset universe and snapshot data"

## Recommended explainability architecture

Best practice for this repo:

1.  Keep the allocation engine deterministic.
2.  Store the decision trace as structured data.
3.  Let the chatbot read that trace and explain it in plain language.
4.  If an LLM is used later, use it only as a language layer over the trace.

That means the explanation system should be grounded in facts like:

- profile band
- band policy
- holdings
- metrics
- notes

not in free-form hallucinated rationale.

## How to test this like a financial product

The current tests are a decent start, but they are not enough for serious defense.

### 1. Input validation tests

Goal:

- confirm bad or missing inputs are handled safely

Examples:

- invalid band id is rejected
- incomplete questionnaire cannot submit
- invalid option ids are rejected

Current repo coverage:

- `tests/test_services_submission.py`

### 2. Policy integrity tests

Goal:

- confirm the configured ranges are internally coherent

Examples:

- each band minimum is less than or equal to its maximum
- class limits do not create impossible totals
- disallowed classes stay at zero

Current repo coverage:

- `tests/test_portfolio_variant_b.py`

### 3. Feasibility tests

Goal:

- confirm every supported band can actually produce a portfolio

Examples:

- each band optimizes successfully
- no solver crash on the current snapshot
- no empty holdings list

Current repo coverage:

- partial

### 4. Allocation-behavior tests

Goal:

- confirm the portfolio actually behaves as intended

Examples:

- aggressive should have materially higher equity than conservative
- very conservative should keep strong Cash + Fixed Income totals
- all holdings respect single-asset caps

This is one of the most important missing layers for product defense.

### 5. Stress and sensitivity tests

Goal:

- check whether the system is fragile to small input or data changes

Examples:

- perturb expected returns slightly and compare allocations
- perturb covariance slightly and compare allocations
- check whether small changes produce unstable, non-intuitive jumps

This matters because a product that changes radically from tiny data updates is harder to defend.

### 6. Explanation consistency tests

Goal:

- ensure the explanation matches the actual allocation

Examples:

- if equity total is 72%, the explanation should not say "modest equity"
- if manual band mode was used, the explanation must say that clearly
- the shown class ranges must match the active config

### 7. Scenario tests with worked personas

Goal:

- test the whole system as users would experience it

Examples:

- a near-retirement low-risk persona
- a long-horizon growth persona
- a high-liquidity-need persona
- a high-risk but low-capacity persona

For each scenario, record:

- answers
- band selected or assigned
- applied policy
- holdings
- summary metrics
- explanation text

This is one of the best ways to defend the system in demos and reviews.

## The best practical test suite to add next

If the team wants the highest-value next testing layer, add these four things:

1.  class-total comparison tests across bands
2.  single-asset cap enforcement tests
3.  scenario-based golden tests for 5-10 representative personas
4.  explanation consistency tests against the actual decision trace

That would move the project closer to a defendable product standard.

## Bottom line

For Barita, you do **not** need to become a specialist in solver internals.

You do need to be able to defend the allocator as a policy-constrained advisory engine.

The right depth is:

- strong understanding of inputs, constraints, objective, outputs, and limits
- clear understanding of the code path that implements those things
- clear evidence from tests that the product behaves consistently and honestly

That is the level that makes this defendable as a financial product rather than just a coding artifact.

# Optimizer Defense And Validation

This note explains how we defend the current optimizer-backed portfolio path.
It is meant for presentation preparation and reviewer questions, not as a claim
that the prototype is already approved financial advice.

## Short Answer

We use PyPortfolioOpt as a credible optimization engine, but we do not rely on
the library citation alone. Our defense has four layers:

1. PyPortfolioOpt is a documented, citable research-software package.
2. Our code uses it in a controlled wrapper with explicit inputs and constraints.
3. We replay the same optimization through an independent SciPy solver path.
4. We run stress checks to see whether the integration remains feasible and
   explainable under changed inputs.

The correct claim is:

> PyPortfolioOpt gives us a credible constrained-optimization engine. Our
> validation shows that our integration obeys configured portfolio constraints
> and can be replayed through an independent SciPy constrained-optimization
> path. This is evidence of controlled implementation, not proof that the output
> is final regulated financial advice.

For the broader evidence checklist covering questionnaire scoring, liquidity,
reports, and browser smoke testing, also read:

- `testing-and-validation.md`

## What The Citation Proves

PyPortfolioOpt was published in the Journal of Open Source Software:

- Robert Andrew Martin, "PyPortfolioOpt: portfolio optimization in Python",
  Journal of Open Source Software, 2021.
- DOI: <https://doi.org/10.21105/joss.03066>
- JOSS page: <https://joss.theoj.org/papers/10.21105/joss.03066>

That citation supports these claims:

- the package has a stable academic reference
- the software has documented authorship
- the package has gone through JOSS software review
- reviewers can trace what tool we used instead of treating it as an anonymous
  GitHub script

It does **not** prove:

- every portfolio produced with PyPortfolioOpt is suitable
- our expected returns are correct
- our covariance matrix is perfect
- our investor-profile mapping is final
- our prototype is ready to provide regulated advice

## Underlying Portfolio Theory

The current optimizer path follows the mean-variance portfolio-optimization
family associated with Harry Markowitz's portfolio-selection work:

- Harry Markowitz, "Portfolio Selection", Journal of Finance, 1952.
- DOI: <https://doi.org/10.1111/j.1540-6261.1952.tb01525.x>

In plain language, the optimizer compares assets using:

- expected return estimates
- a covariance matrix that represents how assets move together
- hard limits on what the portfolio is allowed to hold

The selected investor profile defines the allowed region. PyPortfolioOpt then
searches inside that region for the best weight combination according to the
configured objective.

## Alternatives Considered

We considered other optimizer approaches, but they were not the safest choices
for this prototype timeline.

### Custom Optimizer

We could have written our own constrained optimization code directly.

We did not choose that path because it would create unnecessary implementation
risk. A custom optimizer would require more time to debug numerical behavior,
constraint handling, failure cases, and edge cases. It would also be harder to
defend because reviewers would need to trust both our financial assumptions and
our optimizer implementation.

### Heuristic Rules Only

We could have avoided optimization and used fixed percentage rules for each
profile.

That would be easier to explain, but it would not use the covariance matrix or
estimated return inputs in a meaningful way. It would also make the system less
responsive to the actual asset universe. We keep simple baseline logic available
inside the validation module for internal debugging, but it is no longer the
main evidence shown in the default validation report.

### Larger Optimization Libraries Or More Advanced Models

We also considered broader portfolio/risk libraries and more advanced modelling
approaches.

Those options may be useful later, but they add setup burden, learning time,
and validation work. For the current deadline, they would increase complexity
without making the prototype easier to defend.

### Why PyPortfolioOpt Was The Practical Choice

PyPortfolioOpt was selected because it is documented, citable, installable in
the current Python environment, and focused on exactly the kind of constrained
portfolio optimization needed for this prototype. It gives us a credible solver
while keeping our team focused on the parts we must own: input quality, profile
constraints, validation, explanation, and limitations.

## What Our Code Validates

The active validation runner is:

- `Run Optimizer Validation.cmd`
- `Run Optimizer Developer Check.cmd`
- `scripts/run_optimizer_validation.py`
- `scripts/run_optimizer_developer_check.py`
- `backend/soc_advisor/optimizer_validation.py`

It validates every profile listed in the active portfolio config. The current
default is `config/portfolio/v3.json`. It does not
hard-code "profile 1 means X". Instead, it reads the configured profile order,
labels, descriptions, constraints, and optimizer settings from the same config
used by the advisor.

For each profile, the validation report records:

- profile number, internal id, label, and description
- portfolio config version
- data source used by the allocator
- optimizer objective
- risk-free rate
- weight bounds
- single-asset cap
- covariance repair setting
- optimized summary statistics
- full holdings and weights
- superclass allocation mix
- pass/fail checks for total weight, asset cap, and superclass ranges
- independent SciPy SLSQP cross-check objective and constraint results
- stress-check results

The generated logs are written to:

- `data/validation/optimizer-validation-latest.txt`
- `data/validation/optimizer-validation-<timestamp>.txt`

Those logs are local audit artifacts and are ignored by git by default.

## Independent SciPy Cross-Check

The default validation report now replays the same max-Sharpe optimization
through SciPy's `optimize.minimize` function using the SLSQP method.

In plain language:

- PyPortfolioOpt is the production optimizer wrapper used by the advisor.
- SciPy is a separate general-purpose scientific optimization library.
- The validation script gives SciPy the same expected returns, covariance
  matrix, weight bounds, single-asset cap, and superclass constraints.
- The report checks whether SciPy also finds a feasible portfolio with the same
  or very similar Sharpe objective and weights.

This helps because it checks our integration from another numerical path. If
PyPortfolioOpt and SciPy both solve the same constrained problem and produce
the same result within tolerance, that is stronger evidence than only saying
"the library ran without crashing."

This still does **not** prove the financial recommendation is correct. It only
supports the claim that the optimization problem we configured is being solved
consistently.

## Why SciPy Is Credible

SciPy is one of the standard scientific-computing libraries in Python. It is
not a finance-specific product, but it is widely used for numerical methods,
including optimization.

Relevant references:

- SciPy optimization documentation:
  <https://docs.scipy.org/doc/scipy/tutorial/optimize.html>
- SciPy SLSQP documentation:
  <https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html>
- SciPy citation page:
  <https://scipy.org/citing-scipy/>
- SciPy 1.0 Nature Methods paper:
  <https://doi.org/10.1038/s41592-019-0686-2>

The important defense point is not "SciPy is a financial advisor." It is:

> SciPy gives us an independent, credible constrained numerical optimizer that
> can replay the same problem outside PyPortfolioOpt's portfolio-specific
> wrapper.

## Stress Checks

The validation runner also performs three sensitivity checks:

- expected-return haircut
- covariance/risk shock
- removing the largest optimized holding

These checks do not prove the model is financially perfect. They show whether
the optimizer integration can still produce a feasible result or at least fail
with a clear reason when inputs change.

## Slide-Ready Defense

Use this wording in the presentation:

> We use PyPortfolioOpt as the numerical optimization engine, not as the whole
> advisor. PyPortfolioOpt is a documented and citable open-source research
> software package published in the Journal of Open Source Software. The
> underlying method is based on standard mean-variance portfolio optimization.
> We considered custom optimization, fixed-rule portfolios, and broader
> optimizer libraries, but those paths were either too risky for the timeframe
> or less aligned with the prototype goal.
>
> Our own responsibility is validating how we use it. We therefore test that
> every generated portfolio sums to 100%, respects the single-asset cap, stays
> within the selected profile's asset-class ranges, and produces holdings and
> metrics that can be audited. We also replay the same optimization through
> SciPy's independent SLSQP solver path and run stress checks to see whether
> the system remains feasible and explainable when inputs change.
>
> This does not mean the prototype is final regulated advice. It means the
> optimizer integration is controlled, traceable, and testable.

## Defense Boundary

Do not say:

- "PyPortfolioOpt proves our recommendation is correct."
- "The portfolio is guaranteed to perform this way."
- "The system is ready to provide regulated advice."

Say:

- "The optimizer is credible and citable."
- "Our integration is tested against explicit constraints."
- "The output is cross-checked through an independent SciPy solver path."
- "The current prototype still requires data review, profile-mapping review,
  suitability review, and compliance review before real-client use."

# Decision Explanation Contract

This document is the source-of-truth contract for how the advisor prototype should explain its recommendation path.

It is not a new scoring model, portfolio model, or legal suitability policy. It translates the current agreed logic into wording and trace requirements that can be reused by:

- the Chainlit chatbot
- the HTML user report
- the technical audit report
- presentation slides
- teammate handoff notes

## Confirmed Policy Truth

The current explanation layer should treat the following as official for this prototype:

1. Investor profile is based on risk capacity and risk tolerance.
2. Liquidity is a separate cash-need constraint, not just another score input.
3. Age is not collected or used for scoring.
4. The final risk score uses `60%` capacity and `40%` tolerance.
5. Question 10, if answered as "sell everything", caps the calculated profile at `Balanced`.
6. Liquidity can automatically move to a safer compatible profile or block report generation if no profile can satisfy the required Cash need.
7. Portfolio construction uses the final profile's superclass ranges and then PyPortfolioOpt selects holdings inside those constraints.
8. The system must not claim to perform full financial planning, tax planning, required-rate-of-return goal planning, or regulated suitability review.

## Explanation Principle

The system should explain the decision chain in this order:

```text
answers
-> risk capacity and risk tolerance scores
-> calculated investor profile
-> profile cap, if triggered
-> liquidity compatibility check
-> final profile used for allocation
-> portfolio constraints
-> optimized holdings
-> report notes and limitations
```

This sequence matters because it prevents the explanation from sounding like a black box. Each step should be traceable to a saved answer, a documented rule, or a configured portfolio constraint.

## Stage 1: Questionnaire Explanation

The explanation layer should describe the questionnaire as collecting three types of information.

### Liquidity Inputs

Questions 1 to 4 collect cash-need information:

1. portfolio value
2. expected major withdrawal
3. essential monthly expenses
4. desired emergency reserve

These answers are used to estimate the minimum Cash allocation the portfolio should be able to support.

They should not be described as deciding whether someone is Growth or Conservative.

### Risk Capacity Inputs

Questions 5 to 9 estimate the investor's ability to take risk:

1. current emergency fund
2. income stability
3. dependents or obligations
4. time horizon
5. investment phase

Plain-English explanation:

```text
Risk capacity means how much risk the investor appears financially able to take.
It considers whether the investor has time, income stability, emergency support,
and enough flexibility to withstand portfolio movement.
```

### Risk Tolerance Inputs

Questions 10 to 14 estimate the investor's willingness and behavioral readiness to take risk:

1. reaction to a major market drop
2. willingness to accept short-term losses
3. financial knowledge
4. investing experience
5. reaction to a hypothetical 30% portfolio decline

Plain-English explanation:

```text
Risk tolerance means how comfortable and behaviorally prepared the investor
appears to be when investments move down in value.
```

## Stage 2: Scoring Explanation

Each scored answer is normalized to a value between `0.0` and `1.0`.

```text
0.0 = most conservative answer
1.0 = most growth-oriented answer
```

The capacity score is calculated as:

```text
capacity_score =
  (
    Q5 * 0.20
    + Q6 * 0.30
    + Q7 * 0.15
    + Q8 * 0.35
    + Q9 * 0.35
  )
  / 1.35
```

The tolerance score is calculated as:

```text
tolerance_score =
  (
    Q10 * 0.40
    + Q11 * 0.15
    + Q12 * 0.15
    + Q13 * 0.15
    + Q14 * 0.25
  )
  / 1.10
```

The final score is calculated as:

```text
final_score = capacity_score * 0.60 + tolerance_score * 0.40
```

Why capacity is weighted more heavily:

```text
The system should not classify someone as highly aggressive only because they
say they are comfortable with risk. They also need enough financial ability to
absorb that risk.
```

## Stage 3: Profile Mapping Explanation

The normalized final score maps to the draft profile:

| Final score | Draft profile |
| --- | --- |
| `0.00` to below `0.20` | Very Conservative |
| `0.20` to below `0.40` | Conservative |
| `0.40` to below `0.60` | Balanced |
| `0.60` to below `0.80` | Growth |
| `0.80` to `1.00` | Aggressive |

For user-facing display, the same result can be translated into a `1` to `10` risk score:

| Display score | Profile range |
| --- | --- |
| `1-2` | Very Conservative |
| `3-4` | Conservative |
| `5-6` | Balanced |
| `7-8` | Growth |
| `9-10` | Aggressive |

The `1` to `10` score is only a user-friendly display layer. The underlying scoring calculation remains the normalized `0.0` to `1.0` model.

## Cap Rule Explanation

Question 10 asks how the investor would respond to a severe market decline.

If the answer is:

```text
Sell everything to protect what is left
```

then the maximum calculated profile is `Balanced`.

The explanation should say:

```text
Because the investor said they would fully exit after a severe market drop, the
system does not allow the calculated profile to move above Balanced. This keeps
the recommendation from treating a high score elsewhere as permission to use a
more aggressive profile.
```

Do not describe this as an optimizer rule. It happens before portfolio construction.

## Liquidity Explanation

Liquidity is handled separately from risk scoring.

The current formula is:

```text
required_liquidity =
  major_expense_withdrawal_amount
  + essential_monthly_expenses * emergency_months
```

Emergency-month mapping:

| Selected reserve | Months used |
| --- | ---: |
| `0 months` | `0` |
| `1-3 months` | `2` |
| `4-6 months` | `5` |
| `More than 6 months` | `9` |

Then:

```text
liquidity_floor = required_liquidity / portfolio_value
```

The liquidity floor becomes the minimum Cash allocation.

Plain-English explanation:

```text
The system estimates how much of the portfolio should remain in Cash to support
near-term withdrawals and emergency reserves. That Cash need is checked before
the portfolio is built.
```

## Liquidity Compatibility Behavior

The selected or calculated profile must be able to support the required Cash floor.

If the Cash floor is within the profile's Cash maximum:

```text
The profile is compatible and the system can continue.
```

If the Cash floor is too high for the selected profile, the system searches toward safer profiles:

```text
Aggressive -> Growth -> Balanced -> Conservative -> Very Conservative
```

The nearest compatible safer profile is used automatically, and the adjustment is disclosed in the chat, user report, and audit report.

If no profile can support the required Cash floor, report generation is blocked and the user is asked to revise liquidity answers or the investable amount.

Example:

```text
Portfolio value = $100,000
Required liquidity = $50,000
Liquidity floor = 50%
```

Because the highest Cash maximum in the active policy is `35%` for Very Conservative, no profile can support a `50%` Cash requirement. The correct behavior is to block the report rather than pretend the optimizer can satisfy the policy.

## Portfolio Policy Explanation

The final profile defines the broad allocation ranges that PyPortfolioOpt must stay inside.

Current active portfolio policy:

| Profile | Cash | Fixed Income | Equity | Fund |
| --- | ---: | ---: | ---: | ---: |
| Very Conservative | `15-35%` | `55-80%` | `0-20%` | `0-10%` |
| Conservative | `10-30%` | `45-70%` | `15-35%` | `0-10%` |
| Balanced | `5-20%` | `25-55%` | `35-65%` | `0-15%` |
| Growth | `0-15%` | `10-40%` | `50-85%` | `0-15%` |
| Aggressive | `0-10%` | `0-25%` | `70-100%` | `0-20%` |

Single-asset cap:

```text
40%
```

Plain-English explanation:

```text
The investor profile does not directly choose individual investments. It sets
the allowed mix of broad investment types. The optimizer then chooses holdings
inside those limits.
```

## Optimizer Explanation

PyPortfolioOpt should be explained as the numerical optimizer, not as the advisor.

It receives:

- expected returns
- covariance matrix
- available assets
- superclass ranges from the final profile
- single-asset cap
- Cash-floor overlay, if liquidity requires it

It returns:

- selected holdings
- weights
- portfolio metrics
- constraint summary

Allowed explanation:

```text
PyPortfolioOpt solves the allocation problem after the project rules have
already selected the investor profile and portfolio constraints.
```

Disallowed explanation:

```text
PyPortfolioOpt decides what kind of investor the client is.
```

## Risk Reality Check Explanation

Before the report is generated, the system shows a simple downside-movement illustration:

```text
stress movement = 2 * estimated annual volatility
```

This should be explained as a rough stress illustration, not a maximum loss, guarantee, value-at-risk model, or historical crash replay.

Plain-English explanation:

```text
The system shows a more severe movement estimate so the investor can pause and
decide whether the selected profile feels too risky before the report is built.
```

## What The Chatbot Should Be Able To Explain

The chatbot should be able to answer:

- Which answers affected the calculated profile?
- What were the capacity, tolerance, and final scores?
- Why was the profile mapped to a specific investor type?
- Was the Balanced cap triggered?
- How was liquidity need calculated?
- Did liquidity change the profile or Cash floor?
- Which profile was finally used for allocation?
- What superclass constraints were used?
- What holdings were selected?
- What limitations still apply?

It should not invent:

- tax advice
- legal advice
- guaranteed returns
- final regulated suitability approval
- personal financial-planning conclusions outside the captured questionnaire

## User-Facing Wording Rules

Use:

- `investor profile`
- `risk capacity`
- `risk tolerance`
- `liquidity need`
- `Cash reserve`
- `estimated yearly return`
- `expected yearly movement`
- `investment type`
- `asset code`

Avoid in the client-facing report or normal chat:

- `mock band`
- `optimizer decided`
- `option id`
- `schema`
- `raw JSON`
- `Variant B`
- `backend`
- `superclass`, unless inside an audit/developer section

## Audit Trace Requirements

The audit report should preserve the technical details that the user-facing report simplifies.

At minimum, it should expose:

- questionnaire version
- scoring version
- portfolio policy version
- capacity score
- tolerance score
- final normalized score
- user-facing `1` to `10` score
- draft profile
- cap rule result
- manual override status
- original selected profile
- liquidity calculation
- liquidity floor
- effective profile after liquidity compatibility
- Cash-floor overlay
- final superclass constraints
- optimizer settings
- SOC data source used
- covariance repair flag
- risk reality check values
- known limitations

## Current Limitations To Disclose

The explanation layer should disclose these limitations plainly:

- Expected returns are estimates, not guarantees.
- The prototype does not perform tax planning.
- The prototype does not calculate a full goal-based required return.
- The questionnaire and scoring policy still need math-team approval before being treated as final.
- Liquidity currently affects Cash-floor compatibility, not the full suitability model.
- The risk reality check is a simple volatility-based illustration, not a formal worst-case loss model.
- The covariance matrix may be numerically repaired for optimization stability.
- The system is a structured academic prototype, not a replacement for a licensed advisor.

## Useful References

The current contract is consistent with the project documents and reference material reviewed so far:

- `docs/experiments/chainlit-pyportfolio/docx-aligned-risk-scoring.md`
- `docs/experiments/chainlit-pyportfolio/portfolio-policy-matrix.md`
- `docs/experiments/chainlit-pyportfolio/testing-and-validation.md`
- `C:\Users\ronhu\Downloads\Investor Profile.drawio_.pdf`
- `docs/assn_intr/investment-risk-profiling.pdf`

The CFA-style risk-profiling reference is especially useful because it separates investor risk profiling into risk need, risk-taking ability, and behavioral loss tolerance. This supports the project's choice to keep liquidity and ability-to-take-risk distinct from willingness-to-take-risk.

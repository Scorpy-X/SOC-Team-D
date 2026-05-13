# DOCX-Aligned Risk Scoring, Liquidity, and Portfolio Caps

This note explains how the advisor now turns questionnaire answers into a calculated investor profile. It is written for teammates who need to explain the logic without reading the code.

## 1. What The Questionnaire Does

The live questionnaire has 14 questions, excluding the separate currency-exposure idea.

The first four questions are for liquidity:

1. Portfolio value.
2. Major expected withdrawal over the next 12 to 24 months.
3. Essential monthly expenses.
4. Desired emergency reserve in months.

These questions do not decide whether the investor is Growth or Conservative. They calculate how much Cash the portfolio must be able to support.

Questions 5 to 9 estimate risk capacity:

5. Current emergency fund months.
6. Non-investment income stability.
7. Dependents or financial obligations.
8. Time horizon.
9. Investment phase.

Risk capacity means how much risk the investor can financially afford to take.

Questions 10 to 14 estimate risk tolerance:

10. Response to a 25% market drop.
11. Willingness to accept short-term losses.
12. Financial knowledge.
13. Investing experience.
14. Reaction to a hypothetical 30% portfolio decline.

Risk tolerance means how comfortable and behaviorally prepared the investor is for market movement.

## 2. How Answers Become Scores

Each scored answer is converted to a value between `0.0` and `1.0`.

`0.0` means the most conservative answer.

`1.0` means the most growth-oriented answer.

Example for time horizon:

```text
5 years or less = 0.0
6 to 9 years = 0.5
10 years or more = 1.0
```

Example for short-term loss willingness:

```text
Very unwilling = 0.0
Unwilling = 0.25
Indifferent = 0.5
Willing = 0.75
Very willing = 1.0
```

Some questions are displayed in an order that does not match the scoring direction. The scoring config handles that explicitly, so the safest answer always scores lower and the more growth-oriented answer always scores higher.

## 3. Risk Capacity Calculation

Risk capacity uses the weights approved from the DOCX discussion:

```text
current emergency fund months: 20%
income stability: 30%
dependents/obligations: 15%
time horizon: 35%
investment phase: 35%
```

These weights add to `135%`, so the system divides by the total weight.

Formula:

```text
capacity_score =
  (
    Q5_score * 0.20
    + Q6_score * 0.30
    + Q7_score * 0.15
    + Q8_score * 0.35
    + Q9_score * 0.35
  )
  / 1.35
```

The result is still between `0.0` and `1.0`.

## 4. Risk Tolerance Calculation

Risk tolerance uses these DOCX-aligned weights:

```text
market drop response: 40%
short-term loss willingness: 15%
financial knowledge: 15%
investing experience: 15%
hypothetical 30% loss reaction: 25%
```

These weights add to `110%`, so the system divides by the total weight.

Formula:

```text
tolerance_score =
  (
    Q10_score * 0.40
    + Q11_score * 0.15
    + Q12_score * 0.15
    + Q13_score * 0.15
    + Q14_score * 0.25
  )
  / 1.10
```

## 5. Final Investor Profile Score

Capacity is weighted more heavily than tolerance because a client should not be classified as aggressive only because they are emotionally willing to take risk. They also need the financial ability to absorb that risk.

Formula:

```text
final_score = capacity_score * 0.60 + tolerance_score * 0.40
```

The final score maps to a calculated investor profile:

```text
0.00 to below 0.20 = Very Conservative
0.20 to below 0.40 = Conservative
0.40 to below 0.60 = Balanced
0.60 to below 0.80 = Growth
0.80 to 1.00 = Aggressive
```

For user-facing explanations, the same final score is also translated into a
simple `1` to `10` risk score. This is only a display translation, not a second
scoring model:

```text
0.00-0.19 = 1-2  = Very Conservative range
0.20-0.39 = 3-4  = Conservative range
0.40-0.59 = 5-6  = Balanced range
0.60-0.79 = 7-8  = Growth range
0.80-1.00 = 9-10 = Aggressive range
```

The user-facing risk score uses the final score after caps. For example, if a
raw score would have been Aggressive but Question 10 caps the profile at
Balanced, the user-facing score and investor type should reflect the capped
Balanced result.

## 6. Cap At Balanced Rule

Question 10 asks what the investor would do if the stock market dropped 25% and stayed down for two years.

If the user answers:

```text
Sell everything to protect what is left
```

then the calculated profile is capped at Balanced.

This means a high mathematical score cannot produce Growth or Aggressive if the investor says they would fully exit after a severe decline.

This is a scoring cap, not an optimizer constraint. It limits the maximum investor profile before portfolio construction begins.

## 7. Liquidity Calculation

Liquidity stays separate from risk scoring.

The formula is:

```text
required_liquidity =
  major_expense_withdrawal_amount
  + essential_monthly_expenses * emergency_months
```

Emergency-month mapping:

```text
0 months = 0
1-3 months = 2
4-6 months = 5
More than 6 months = 9
```

Then:

```text
liquidity_floor = required_liquidity / portfolio_value
```

The liquidity floor becomes the minimum Cash allocation.

If the calculated profile cannot support that much Cash, the system automatically uses the nearest safer compatible profile and discloses the adjustment. If no profile can support the liquidity need, the system blocks report generation and asks the user to revise the liquidity inputs or reduce the investable amount.

## 8. Current Portfolio Caps

The portfolio policy remains `v3`.

```text
Very Conservative: Cash 15-35%, Fixed Income 55-80%, Equity 0-20%, Fund 0-10%
Conservative: Cash 10-30%, Fixed Income 45-70%, Equity 15-35%, Fund 0-10%
Balanced: Cash 5-20%, Fixed Income 25-55%, Equity 35-65%, Fund 0-15%
Growth: Cash 0-15%, Fixed Income 10-40%, Equity 50-85%, Fund 0-15%
Aggressive: Cash 0-10%, Fixed Income 0-25%, Equity 70-100%, Fund 0-20%
```

The single-asset cap remains:

```text
40%
```

The optimizer only chooses assets and weights inside these approved ranges.

## 9. Example

Suppose the questionnaire produces:

```text
capacity_score = 0.75
tolerance_score = 0.65
```

Then:

```text
final_score = 0.75 * 0.60 + 0.65 * 0.40
final_score = 0.45 + 0.26
final_score = 0.71
```

`0.71` maps to:

```text
Growth
```

If the user also said they would sell everything after a 25% market drop, the cap rule applies:

```text
Draft score profile = Growth
Cap rule = max Balanced
Final scoring profile = Balanced
```

Then liquidity is checked. If Balanced can support the required Cash floor, the report can continue. If not, the system automatically uses the nearest safer compatible profile or blocks report generation when no configured profile can satisfy the Cash requirement.

## 10. Slide-Ready Defense

The investor profile is calculated using a transparent rules-based scoring model aligned to the team questionnaire. The system separates risk capacity from risk tolerance, normalizes answers to a common scale, applies documented weights, and maps the final score to one of five investor profiles. Liquidity is handled separately as a Cash-floor guardrail, because near-term Cash need should not be hidden inside a risk-tolerance score. The final portfolio is then built only inside the approved profile ranges and single-asset cap.

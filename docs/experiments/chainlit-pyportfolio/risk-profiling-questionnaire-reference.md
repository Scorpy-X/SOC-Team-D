# Risk Profiling Questionnaire Reference

This file is a cleaned reference for the current questionnaire direction taken
from the risk-profiling DOCX material and later team decisions.

It is a product/reference note. Runtime truth lives in:

- `config/questionnaires/v4.json`
- `config/scoring/v5.json`
- `config/portfolio/v3.json`

For the full scoring formulas, read:

- `docs/experiments/chainlit-pyportfolio/docx-aligned-risk-scoring.md`

## Implementation Note

The current implementation supports:

- `single_choice`
- `currency_amount`

The liquidity questions are implemented as numeric money entries and a
multiple-choice emergency-reserve target. They are not free-text narrative
answers.

## Liquidity Need

Liquidity is handled before the portfolio is generated. It is not blended into
the risk score.

Current formula:

```text
required liquidity = major expense withdrawal + (essential monthly expenses * emergency months)
liquidity floor = required liquidity / portfolio value
```

Emergency-month mapping:

- `0 months` -> `0`
- `1-3 months` -> `2`
- `4-6 months` -> `5`
- `More than 6 months` -> `9`

That liquidity floor becomes the minimum Cash requirement. If the selected
profile cannot hold enough Cash, the chatbot automatically uses the nearest
more conservative compatible profile and discloses that adjustment. If no
profile can satisfy the liquidity floor, report generation is blocked until the
liquidity answers are revised.

### Q1. Portfolio value

- Type: `currency_amount`
- Used for scoring: no
- Used for liquidity: yes
- Used for report dollar estimates: yes
- Minimum: `$25,000`

Question:

> How much are you investing in this portfolio today? The minimum portfolio
> value for this questionnaire is $25,000.

### Q2. Major expense withdrawal

- Type: `currency_amount`
- Used for scoring: no
- Used for liquidity: yes

Question:

> How much might you need to withdraw for a major expense in the next 12 to 24
> months?

### Q3. Essential monthly expenses

- Type: `currency_amount`
- Used for scoring: no
- Used for liquidity: yes

Question:

> What are your estimated essential monthly expenses?

### Q4. Desired emergency reserve

- Type: `single_choice`
- Used for scoring: no
- Used for liquidity: yes

Options:

- `0 months`
- `1-3 months`
- `4-6 months`
- `More than 6 months`

## Risk Capacity

Risk capacity is about the investor's financial ability to take risk.

Formula:

```text
capacity score =
((Q5 * 0.20) + (Q6 * 0.30) + (Q7 * 0.15) + (Q8 * 0.35) + (Q9 * 0.35)) / 1.35
```

### Q5. Current emergency fund

- Weight: `20%` of the capacity section before normalization
- Factor: emergency fund strength

Options:

- `0 months`
- `1-3 months`
- `4-6 months`
- `More than 6 months`

### Q6. Non-investment income stability

- Weight: `30%`
- Factor: income stability

Options:

- `Very stable`
- `Moderately stable`
- `Unstable`

### Q7. Dependents and obligations

- Weight: `15%`
- Factor: debt burden / financial obligations

Options:

- `At least three dependents rely heavily on my income`
- `Two or more people depend on my income`
- `I have little to no financial dependence obligations`

### Q8. Time horizon

- Weight: `35%`
- Factor: time horizon

Options:

- `5 years or less`
- `6 to 9 years`
- `10 years or more`

### Q9. Investment phase

- Weight: `35%`
- Factor: investment phase

Options:

- `Capital disbursement`
- `Capital accumulation`

## Risk Tolerance

Risk tolerance is about the investor's willingness and behavioural ability to
stay with risk.

Formula:

```text
tolerance score =
((Q10 * 0.40) + (Q11 * 0.15) + (Q12 * 0.15) + (Q13 * 0.15) + (Q14 * 0.25)) / 1.10
```

### Q10. Market drop response

- Weight: `40%`
- Factor: drawdown reaction
- Special rule: `Sell everything` caps the calculated profile at `Balanced`

Options:

- `Sell everything to protect what is left`
- `Sell a portion and move to a safer investment`
- `Do nothing / stay invested`
- `Invest more to take advantage of lower prices`

### Q11. Short-term loss willingness

- Weight: `15%`
- Factor: return-seeking preference

Options:

- `Very willing`
- `Willing`
- `Indifferent`
- `Unwilling`
- `Very unwilling`

### Q12. Financial knowledge

- Weight: `15%`
- Factor: behavioural consistency support signal

Options:

- `Limited investment knowledge`
- `Basic investment understanding`
- `Moderate investment understanding`
- `Competent investment understanding`
- `Advanced investment knowledge`

### Q13. Investing experience length

- Weight: `15%`
- Factor: behavioural consistency support signal

Options:

- `Less than a year`
- `1-3 years`
- `4-10 years`
- `More than 10 years`

### Q14. Hypothetical 30% loss reaction

- Weight: `25%`
- Factor: loss aversion

Options:

- `I should move to safer investments before losses worsen.`
- `I may have taken more risk than I am comfortable with.`
- `Market declines are uncomfortable but expected.`
- `My long-term plan remains unchanged.`
- `This may be an opportunity to invest more.`

## Current Live Product Truth

The current active demo path is:

`typed questionnaire -> calculated profile -> review/edit/optional override -> liquidity check -> risk reality check -> allocation -> report`

That means:

- the questionnaire calculates an investor profile
- advisor/manual override is still available in review mode
- liquidity answers are used to check the Cash floor and profile compatibility
- the portfolio policy uses the approved `portfolio v3` ranges
- PyPortfolioOpt builds the portfolio after the final profile and Cash floor are known

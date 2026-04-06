# Risk Profiling Questionnaire Reference

This file is a cleaned reference for the questionnaire content taken from
`Risk Profiling Questionnaire.docx`.

It is a product/reference note, not the source of truth for runtime behavior.
The live source of truth is:

- `config/questionnaires/v3.json`

## Important implementation note

The current implementation supports:

- `single_choice`
- `currency_amount`

The "open-ended" liquidity questions are implemented as **numeric open-entry**
amounts, not free-form narrative text.

Those amount inputs are:

- captured now
- reviewable now
- not yet used in the active allocation path

## Liquidity Need

Reference formulas from the source doc:

- `Cash Need = (q2 + (q3 * months)) * multiplier`
- `Liquidity percentage = Cash Need / Portfolio Value`
- `Investable Amount = 1 - liquidity percentage`

These formulas are kept as **reference only** in the current build. The live
system captures the underlying inputs but does not yet feed them into
allocation.

### 1. Portfolio value

- Question:
  - `What is your portfolio value? Please enter the dollar amount you will be investing today.`
- Runtime type:
  - `currency_amount`
- Status:
  - captured now
  - not used for scoring now
  - not yet used for allocation
- Current implementation note:
  - minimum enforced at runtime is `$25,000`

### 2. Major expense withdrawal amount

- Question:
  - `What is the dollar amount of any major expense you anticipate needing to withdraw over the next 12 to 24 months?`
- Runtime type:
  - `currency_amount`
- Status:
  - captured now
  - not used for scoring now
  - not yet used for allocation

### 3. Essential monthly expenses

- Question:
  - `What is the dollar amount of your essential monthly expenses?`
- Runtime type:
  - `currency_amount`
- Status:
  - captured now
  - not used for scoring now
  - not yet used for allocation

### 4. Emergency reserve target

- Question:
  - `How many months of expenses would you like to have set aside for emergencies?`
- Runtime type:
  - `single_choice`
- Options:
  - `0 months`
  - `1-3 months`
  - `4-6 months`
  - `More than 6 months`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

### 5. Non-investment income stability

- Question:
  - `How would you describe your non-investment income?`
- Runtime type:
  - `single_choice`
- Options:
  - `Very stable`
  - `Moderately stable`
  - `Unstable`
- Reference note:
  - source wording associates these with multipliers `1.0x`, `1.25x`, and `1.5x`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

## Risk Capacity

### 6. Time horizon

- Question:
  - `What is your time horizon? When do you anticipate needing to withdraw the first major sum from your investment?`
- Runtime type:
  - `single_choice`
- Options:
  - `5 years or less`
  - `6 to 9 years`
  - `10 years or more`
- Source note:
  - the doc frames these as stock-allocation caps
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

### 7. Investment phase

- Question:
  - `What phase of your investment life would you say you are in?`
- Runtime type:
  - `single_choice`
- Options:
  - `Capital Accumulation`
  - `Capital Disbursement`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

## Risk Tolerance

### 8. Market drop response

- Question:
  - `If the stock market dropped 25% tomorrow and stayed there for two years, what would you do?`
- Runtime type:
  - `single_choice`
- Runtime options:
  - `Sell everything to protect what is left`
  - `Sell a portion and move to a safer investment`
  - `Invest more money to take advantage of lower prices`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

### 9. Willingness to accept short-term losses

- Question:
  - `How willing are you to accept short-term losses for potential long-term gain?`
- Runtime type:
  - `single_choice`
- Options:
  - `Very willing`
  - `Willing`
  - `Indifferent`
  - `Unwilling`
  - `Very unwilling`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

### 10. Financial knowledge

- Question:
  - `How knowledgeable are you about financial and investment concepts?`
- Runtime type:
  - `single_choice`
- Options:
  - `Not at all knowledgeable`
  - `Minimally knowledgeable`
  - `Moderately knowledgeable`
  - `Competent`
  - `Very knowledgeable`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

### 11. Investing experience length

- Question:
  - `How long have you been investing?`
- Runtime type:
  - `single_choice`
- Options:
  - `Less than a year`
  - `1-3 years`
  - `4-10 years`
  - `More than 10 years`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

### 12. Past loss action

- Question:
  - `In the past, when faced with investment losses, what action did you take?`
- Runtime type:
  - `single_choice`
- Options:
  - `Sold Out`
  - `Sold Some`
  - `Did Nothing`
  - `Purchased More`
- Status:
  - captured now
  - used for scoring now
  - not yet used directly for allocation

## Current live product truth

The current active demo path is still:

`typed questionnaire -> review/edit -> manual mock band selection -> Variant B allocation -> holdings`

That means:

- the new amount questions are valuable capture fields
- they are not yet deciding the investor band
- they are not yet changing the PyPortfolio allocation constraints

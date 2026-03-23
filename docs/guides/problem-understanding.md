# Problem Understanding

## Plain-English Summary

This challenge is not just "an app that shows financial data" and it is not just
"a chatbot that sounds smart." The real task is to build an AI portfolio advisor
chatbot that can:

1. collect investor information,
2. infer a risk profile from that information,
3. build a portfolio using only the approved challenge assets, and
4. explain clearly why that portfolio fits the investor.

So the core problem is a suitability and portfolio-construction problem wrapped in
a conversational interface.

## What The Competition Is Actually Evaluating

Based on the challenge guide, the judges are evaluating whether the product behaves
like a coherent advisory system rather than a disconnected set of features.

The important evaluation dimensions are:

- portfolio intelligence:
  can the system translate a risk profile into a defensible allocation?
- risk awareness:
  does the logic reflect volatility, downside risk, and diversification?
- use of data:
  does the system meaningfully use the provided dataset, especially the
  relationships captured by correlations and covariance?
- technical implementation:
  is the system reliable, well structured, and properly integrated?
- user experience:
  is the chatbot understandable, usable, and explanatory?
- creativity and innovation:
  are there useful enhancements beyond baseline functionality?

This means the winning solution is unlikely to be the one with the fanciest UI
alone. It will be the one that connects investor inputs, risk logic, allocation
rules, and explanation quality in a defensible way.

## Core Product Requirement

The minimum end-to-end flow expected by the competition is:

1. the chatbot asks the user enough questions to understand their situation,
2. the system maps those answers into a risk or suitability profile,
3. the system retrieves and uses the challenge data,
4. the system constructs a portfolio from the approved universe,
5. the chatbot explains the recommendation in a way a user can follow.

In other words, a valid solution must show both:

- decision quality:
  the portfolio should make sense for the user profile
- explanation quality:
  the user should understand why the recommendation was made

## Hard Constraints

The challenge has several non-negotiable constraints.

### 1. Asset Universe Constraint

Portfolio recommendations must use only the controlled challenge universe provided
through Dimension Depths. External instruments and external market datasets are out
of scope.

This matters because:

- we do not need live market ingestion
- we do not need broad market search
- we do need to make the best use of a fixed set of instruments

### 2. Risk Profiling Is Mandatory

Risk assessment is not optional. The chatbot must gather enough information before
portfolio construction to classify investor suitability in a way that translates
into allocation rules.

The guide explicitly says the system should capture at least:

- investment horizon
- risk tolerance
- income versus growth preference
- liquidity needs
- loss tolerance

This means a portfolio should not be generated directly from a vague prompt alone.
There needs to be a clear front-end profiling step.

### 3. Explainability Is Mandatory

The chatbot is expected to justify recommendations, not just output allocations.
Strong solutions should make the link between:

- user inputs
- risk profile
- chosen assets
- diversification logic
- trade-offs between return and risk

### 4. Security And Delivery Standards

API keys must be handled through environment variables and not committed to the
repository. The project is also expected to look like a real software deliverable,
with reproducible setup, clear documentation, and a sensible codebase structure.

## What Data We Actually Have

The API guide and our exploration work show that the dataset is intentionally
pre-processed for portfolio design rather than raw market engineering.

The main data blocks are:

### 1. Asset Fundamentals

This is the one-row-per-asset table. It includes fields such as:

- expected return
- income yield
- annualized volatility
- downside risk
- distribution shape metrics
- duration
- macro sensitivity fields such as betas
- asset class, super class, and currency labels

Practical use:

- define the investable universe
- filter or rank assets
- compare growth-oriented versus income-oriented candidates
- understand standalone risk characteristics

### 2. Asset Correlation Matrix

This shows how pairs of assets move together on a standardized scale.

Practical use:

- diversification logic
- correlation-aware constraints
- explanation of why two assets do or do not diversify each other well

### 3. Asset Covariance Matrix

This shows how asset return series move together on a raw, non-standardized scale.

Practical use:

- portfolio variance calculations
- volatility math
- more formal portfolio construction logic

### 4. Subclass Correlation Matrix

This gives a class-level relationship view before going down to individual tickers.

Practical use:

- high-level allocation structure
- deciding broad class mixes before fine-tuning specific asset choices

### 5. Metadata From `/api/soc/info/`

This gives:

- available fields
- default fields
- currencies
- classes
- counts

Practical use:

- discovery
- validation
- keeping code aligned with the allowed field list

## Dataset Scope

From the API guide, the current challenge package contains:

- 25 non-empty asset rows
- a 25 x 25 asset correlation matrix
- a 25 x 25 asset covariance matrix
- a 12 x 12 subclass correlation matrix

The universe spans:

- 4 super classes:
  Cash, Fixed Income, Equity, Fund
- 12 asset classes

This is a relatively small, controlled portfolio-design environment. That is useful
because it reduces the problem from "discover everything in the market" to "make
good suitability decisions within a known universe."

## What This Means For The Product Design

The chatbot should probably be understood as four connected layers.

### 1. Investor Profiling Layer

Purpose:

- collect the user information needed for suitability

Likely outputs:

- a risk category or risk score
- investor preferences and constraints

Examples of what this layer should influence:

- maximum tolerated volatility
- bias toward income or growth
- preference for liquidity or capital preservation

### 2. Portfolio Logic Layer

Purpose:

- translate the profile into a defensible portfolio

This is where the real advisory value sits. The system needs rules for:

- selecting candidate assets
- limiting assets that conflict with the user profile
- allocating weights
- balancing expected return against risk and diversification

This layer should use more than one field. The brief explicitly suggests that strong
solutions combine metrics rather than optimize a single number.

### 3. Explanation Layer

Purpose:

- translate the quantitative decision into understandable reasoning

This is where the system explains things like:

- why safer assets were emphasized for a lower-risk user
- why more growth exposure was allowed for a longer horizon
- why certain assets were combined for diversification
- what trade-offs the user is accepting

### 4. Conversational Layer

Purpose:

- make the whole flow usable as a chatbot

This layer should not be just a wrapper around pre-written text. It should guide the
user through profiling, return the recommendation, and answer follow-up questions in
a way that remains consistent with the underlying portfolio logic.

## What The Problem Is Not

It is useful to be explicit about what this challenge is not asking for.

- It is not asking for live trading execution.
- It is not asking for scraping or integrating external market data.
- It is not asking for a generic financial FAQ bot.
- It is not asking only for prompt engineering with no real allocation logic.
- It is not asking only for a notebook analysis with no end-user advisory flow.

That distinction matters because it keeps effort focused on suitability, allocation,
and explanation quality.

## Where Our Current Repository Fits

Based on the current repo and our work so far, we have already built a useful data
exploration foundation, but not the actual product yet.

### What The Repo Already Solves

- secure API usage through `.env`
- raw JSON access through `soc_api.raw`
- dataframe access through `soc_api.frames`
- a notebook for exploring the dataset as dataframes
- beginner-friendly documentation for field meanings and matrix interpretation
- a cleaner project structure for code, notebooks, docs, and exports

### What The Repo Does Not Yet Solve

- the investor questionnaire
- the risk-profile scoring or classification logic
- the portfolio construction algorithm
- the suitability rules that map profile to allocation
- the explanation engine that turns quantitative logic into plain language
- the chatbot application itself

So the repo is currently in the "data understanding and API integration" stage, not
the "finished advisor product" stage.

## The Real Implementation Problem We Need To Solve Next

Given the brief and the current repo state, the real design problem now becomes:

How do we convert a small set of investor answers into a risk-aware, explainable,
repeatable portfolio recommendation using only the 25 approved assets?

That breaks into a few concrete subproblems:

1. Define a risk framework.
   We need a method for converting answers into profile outputs that the portfolio
   engine can actually use.

2. Define allocation logic.
   We need explicit rules or formulas for how different profile types map to
   asset-class exposure and then to specific tickers.

3. Use diversification data properly.
   Correlation and covariance should influence the recommendation, not just appear
   in a report after the fact.

4. Build explanation logic.
   The chatbot should be able to say why an allocation makes sense in plain
   language, not just display numbers.

5. Wrap it in a chatbot flow.
   The product must feel like an advisor interaction, not a disconnected analytics
   script.

## Design Implications From Our Discussions

Our discussions add a few practical implications that are important for how we build
this.

### Dataframes Are The Natural Working Format For Analysis

For portfolio logic and analysis, pandas dataframes are the easiest working format.
The raw JSON layer is still useful as the API boundary, but internal analytics should
mostly operate on dataframes.

### The Four Main Tables Are The Core Analytical Inputs

The most important datasets for the portfolio engine are:

- `full_assets_df`
- `full_asset_correlations_df`
- `full_asset_covariance_df`
- `full_subclass_correlations_df`

These are the tables most likely to drive:

- asset screening
- class exposure logic
- diversification logic
- portfolio risk explanation

### The Single-Asset Detail Endpoint Is More Useful For Explanations Than For Core Allocation

The `/api/soc/assets/{ticker}/` endpoint is valuable, but mainly as a drill-down and
explanation tool. It helps answer questions like:

- what is this asset?
- what is it most related to?
- why was it included?

It is probably not the primary data source for the first version of the portfolio
engine.

## Reasonable Working Assumptions

Unless later competition guidance says otherwise, these seem like reasonable
assumptions for the project.

- We are free to design the risk questionnaire ourselves, as long as it captures the
  required dimensions.
- We are free to choose the portfolio construction method, as long as the outputs are
  defensible and consistent with the data.
- A good first version does not need to be mathematically optimal in a formal
  quantitative-finance sense; it does need to be coherent, explainable, and aligned
  with suitability.
- Simplicity with defensible logic is better than a complex method that the team
  cannot explain clearly during judging.

## Decision-Oriented Scope

The sections above explain the problem. This section converts that understanding
into delivery priorities.

### Must Have

These are the things the product has to do to satisfy the brief in a credible way.

- an investor profiling flow that captures at least:
  investment horizon, risk tolerance, income versus growth preference, liquidity
  needs, and loss tolerance
- a clear method for converting those inputs into a usable profile output:
  for example a risk category, score band, or rule bundle
- portfolio construction logic that uses only the approved challenge assets
- real use of the challenge data rather than hard-coded recommendations:
  at minimum the system should use the asset table and should meaningfully account
  for risk and diversification
- an explainable recommendation output:
  the user should be able to see why the portfolio fits their profile
- a working end-to-end demo flow:
  profile -> data retrieval -> portfolio recommendation -> explanation
- secure handling of the API key and a reproducible repo setup

If any of these are missing, the product will likely look incomplete relative to
the competition brief.

### Should Have

These are not the absolute minimum, but they materially strengthen the submission
and align with what the judges are likely to reward.

- explicit suitability rules that connect profile traits to allocation constraints
- class-level reasoning before ticker-level selection:
  for example deciding broad exposure across Cash, Fixed Income, Equity, and Fund
  before choosing individual assets
- visible use of correlation and covariance in the recommendation logic or the
  explanation layer
- a stable explanation layer that can justify both asset choice and diversification
- basic reliability checks across multiple investor profiles so the system behaves
  consistently
- follow-up interaction support:
  for example "make it safer," "I need more income," or "why is this asset here?"

These are the kinds of features that move the project from "working prototype" to
"credible advisor."

### Could Have

These are useful enhancements if the core system is already solid.

- multiple recommendation options:
  for example conservative, balanced, and growth variants with trade-off summaries
- richer portfolio summaries:
  expected return, volatility, diversification notes, and class allocation breakdowns
- visual summaries in the chatbot or supporting report
- a portfolio adjustment workflow that updates recommendations after user feedback
- a cleaner memory of prior user answers within the session
- a lightweight reporting or export feature for the final recommendation

These can improve polish and usability, but they should not come before the core
suitability and allocation logic.

### Out Of Scope

These are things that may look impressive but do not solve the actual competition
problem, or are explicitly outside the challenge boundaries.

- using external market datasets or external instruments
- building a live trading or brokerage execution system
- optimizing only on one metric, such as highest expected return, without a
  suitability framework
- relying only on prompt engineering without explicit recommendation logic
- spending most of the effort on UI polish while the advisory logic remains weak
- implementing highly complex quantitative methods that the team cannot clearly
  explain to judges

For this challenge, a simpler system with coherent logic is better than a more
complicated system with weak explainability.

### What A Strong Version 1 Looks Like

A strong first version of this project would likely have the following shape:

- a short but defensible risk questionnaire
- a profile mapping layer that turns answers into allocation constraints
- a portfolio engine that uses the four main challenge tables
- a recommendation output with weights, rationale, and basic risk interpretation
- a chatbot flow that can present the recommendation and answer obvious follow-up
  questions

That would be enough to satisfy the brief credibly and give the team something
solid to improve rather than a thin demo with no internal depth.

## Recommended Next Build Priorities

The most sensible next implementation order is:

1. define the investor questionnaire and risk-profile outputs,
2. define the portfolio allocation rules,
3. implement a backend recommendation function that produces weights and rationale,
4. connect that function to a chatbot interface,
5. add explanation and adjustment features,
6. test across multiple profile types for consistency.

## Source Basis

This understanding is based primarily on:

- `docs/assn_intr/Barita Skills Optimisation Challenge Guide.pdf`
  - especially pages 2 to 6
- `docs/assn_intr/Dimension Depths Documentation - Barita SOC.pdf`
  - especially pages 1 to 7

It also reflects the current repo state and our project discussions, including:

- the repo has already been reorganized around `backend/soc_api`, `notebooks`, `data`,
  and `docs`
- the API is already wrapped into raw JSON and dataframe layers
- the notebook is currently focused on learning and analyzing the main challenge
  tables rather than implementing the final advisor

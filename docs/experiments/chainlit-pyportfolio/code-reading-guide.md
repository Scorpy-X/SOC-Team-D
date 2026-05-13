# Code Reading Guide

This guide is for reading the current advisor code as a developer, not for
presenting the product externally.

Use it when your goal is:

- understand which function runs next
- see where one answer gets saved
- trace how the final recommendation is produced
- learn the active path before worrying about older compatibility logic

## Read In This Order

1. `backend/soc_advisor/schemas.py`
2. `backend/soc_advisor/typed_answers.py`
3. `backend/soc_advisor/models.py`
4. `backend/soc_advisor/services.py`
5. `backend/soc_advisor/portfolio.py`
6. `backend/soc_advisor/chat_formatting.py`
7. `experiments/chainlit_chat/chat_app.py`
8. `backend/soc_advisor/main.py`

That order matters.

- `schemas.py` tells you what data shapes exist.
- `typed_answers.py` tells you how money inputs are parsed and normalized.
- `models.py` tells you what is stored in SQLite.
- `services.py` tells you how sessions, answers, and submission work.
- `portfolio.py` tells you how the selected band becomes holdings.
- `chat_formatting.py` is only text rendering.
- `chat_app.py` is the UI controller that wires the steps together.
- `main.py` is the thin FastAPI wrapper around the service layer.

If your immediate goal is only to understand the optimizer itself before the
full app flow, read `bare-pypfopt-demo.md` and run `scripts/demo_bare_pypfopt.py`
before you dive into `portfolio.py`.

## The Active Story

The active demo path is:

`chat starts -> session created -> question asked -> numeric answers confirmed with yes if needed -> answer saved -> calculated profile -> review/edit or optional override -> automatic liquidity check -> volatility notice -> yes -> submit -> allocation -> report`

The easiest way to study the code is to follow that exact story.

## 1. Chat Starts

Start in `experiments/chainlit_chat/chat_app.py`.

The first important functions are:

- `on_chat_start()`
- `start_new_chat()`
- `create_chat_session()`

What happens:

- Chainlit opens a new chat.
- `on_chat_start()` calls `start_new_chat()`.
- `start_new_chat()` calls `create_chat_session()`.
- `create_chat_session()` calls `create_assessment_session()` in `backend/soc_advisor/services.py`.

What gets created:

- one `AssessmentSession` row in SQLite
- a backend `session_id`
- chat-side state such as:
  - `session_id`
  - `workflow_stage`
  - `selected_mock_profile_band` if the advisor/demo user manually overrides the calculated profile

If you want to see the database object, open `backend/soc_advisor/models.py` and
look at:

- `AssessmentSession`
- `AssessmentAnswer`

## 2. The Next Question Is Chosen

Still in `chat_app.py`, the next important function is:

- `send_next_question()`

It does three things:

1. loads the latest backend session state with `load_chat_state()`
2. decides whether we are asking a normal question, editing an answer, or ready for review
3. sends the correct prompt

The helper that decides which question matters next is:

- `question_for_active_stage()`

That helper eventually relies on `get_current_question()` from
`backend/soc_advisor/services.py`.

Inside `services.py`, read:

- `answers_by_question()`
- `is_question_active()`
- `get_missing_question_ids()`
- `get_current_question()`

Those functions are the questionnaire navigation logic.

Plain meaning:

- `answers_by_question()` turns saved answers into a lookup by question id.
- `is_question_active()` checks simple dependency logic if a question has `depends_on`.
- `get_missing_question_ids()` figures out which required active questions are still unanswered.
- `get_current_question()` picks the first missing question in display order.

## 3. An Answer Is Parsed, Confirmed If Needed, And Saved

Back in `chat_app.py`, normal answer handling lives in:

- `on_message()`
- `handle_questionnaire_stage()`

Important flow:

1. `on_message()` routes to `handle_questionnaire_stage()` when we are not in review mode.
2. `handle_questionnaire_stage()` figures out the active question.
3. `find_option()` converts the typed message into one configured option.
4. `save_chat_answer()` sends the answer to the backend.

For currency questions there is one extra stage:

- `handle_currency_question_entry()` parses the amount
- `send_numeric_confirmation_prompt()` shows the normalized amount
- `handle_numeric_confirmation_stage()` waits for `yes`

Then look in `backend/soc_advisor/services.py`:

- `upsert_answer()`
- `_resolve_submitted_answer()`

What they do:

- `_resolve_submitted_answer()` validates whether the question expects a single-choice answer or a numeric amount.
- `upsert_answer()` either inserts a new `AssessmentAnswer` row or updates the existing one for that session/question pair.

This is the point where one chat message becomes a saved database row.

## 4. Review And Edit

Once all active questions are answered, `send_next_question()` stops showing
question prompts and calls:

- `send_review_message()`

The review screen itself is formatted in:

- `render_review_message()` from `backend/soc_advisor/chat_formatting.py`

The review commands are handled in:

- `handle_review_stage()` in `chat_app.py`

The current review commands are:

- `change <question number>`
- `band <band number>`
- `yes`

If the user types `change 2`:

- `parse_change_target()` resolves the question number
- `edit_target_question_id` is stored in chat session state
- `send_next_question()` switches into edit mode
- `send_edit_prompt_for_question()` shows the existing answer and re-prompts

The actual save path is still the same `upsert_answer()` backend call used for a
normal answer.

## 5. Calculated Profile And Optional Override

The active demo path calculates an investor profile from the questionnaire.

In `chat_app.py`, read:

- `score_chat_profile()`
- `active_profile_for_review()`
- `upsert_review_workspace()`

What happens:

- `score_chat_profile()` calls `score_session()` in `services.py`
- `score_session()` applies the active scoring config, currently `config/scoring/v5.json`
- `active_profile_for_review()` returns the calculated profile unless a manual override was selected
- the review card highlights the active profile

Review mode still lets the advisor/demo user override the calculated profile with:

- `band 1`
- `band 2`
- `band 3`
- `band 4`
- `band 5`

In `chat_app.py`, read:

- `parse_band_target()`
- `get_selected_band_choice()`
- `handle_review_stage()`

What happens:

- the override band id is stored in chat-side session state
- review is re-rendered so the user can see the active profile
- `yes` uses the calculated profile if no override exists

This keeps the demo flexible while making the questionnaire-to-profile path the
normal teaching story.

## 6. Review Yes Runs Liquidity And Volatility Checks

When the user types `yes` from review, Chainlit calls:

- `handle_review_submission()` in `chat_app.py`

That function does not generate the report immediately. It first:

- builds the active calculated or overridden profile
- runs the liquidity compatibility check
- automatically switches to the nearest safer compatible profile if the Cash requirement is too high for the selected profile
- blocks report generation if no profile can support the Cash requirement
- shows the volatility notice

When the user types `yes` after the volatility notice, Chainlit calls:

- `handle_risk_reality_check_stage()`
- `finalize_review_submission()`
- `submit_chat_session()`

That final call reaches:

- `submit_assessment()` in `backend/soc_advisor/services.py`

Read these functions in `services.py`:

- `build_manual_mock_profile()`
- `score_session()`
- `_select_profile_for_submission()`
- `submit_assessment()`

How to think about them:

- `score_session()` is the normal questionnaire-to-profile path.
- `build_manual_mock_profile()` supports advisor/demo overrides.
- `_select_profile_for_submission()` is the branch point that chooses calculated profile versus override.
- `submit_assessment()` is the main orchestration function.

`submit_assessment()` does this:

1. loads questionnaire config
2. resolves the calculated or overridden profile through `_select_profile_for_submission()`
3. applies any automatic liquidity profile adjustment if the selected profile cannot hold enough Cash
4. normalizes saved answers with `normalized_answer_values()`
5. calls `build_recommendation()` in `portfolio.py`
6. stores the final result with `save_submission_result()`

## 7. Allocation Runs

Now move to `backend/soc_advisor/portfolio.py`.

This file is the allocation engine wrapper around PyPortfolioOpt.

Read these functions in order:

1. `load_portfolio_config()`
2. `load_portfolio_frames()`
3. `build_constraint_summary()`
4. `_optimize_portfolio()`
5. `_build_holdings()`
6. `build_recommendation()`

What each one does:

- `load_portfolio_config()` loads the active portfolio config, currently `config/portfolio/v3.json`
- `load_portfolio_frames()` uses the configured data mode; the default demo path reads:
  - `data/exports/full_assets_df.csv`
  - `data/exports/full_asset_covariance_df.csv`
- `build_constraint_summary()` turns the chosen band into class limits
- `_optimize_portfolio()` runs the constrained optimizer
- `_build_holdings()` converts the final weights into response objects
- `build_recommendation()` ties the whole allocation step together

The key detail:

- the allocation policy is driven by the final profile band
- liquidity can raise the minimum Cash floor
- the optimizer still does not use every individual questionnaire answer directly

## 8. What `_optimize_portfolio()` Actually Does

If you only study one function deeply, make it:

- `_optimize_portfolio()`

Inside this flow, the main steps are:

1. prepare covariance input with `_prepare_covariance_input()`
2. build the optimizer with `_build_optimizer()`
3. apply class constraints with `_apply_super_class_constraints()`
4. apply optional metric constraints with `_apply_metric_constraints()`
5. solve for weights with `_solve_weight_vector()`
6. compute metrics with `_build_portfolio_metrics()`

Plain CS meaning:

- expected returns tell the solver what looks attractive
- covariance tells the solver which assets move together
- class constraints define what portfolios are allowed
- the solver chooses one legal weight vector

This is not graph traversal.
It is constrained numerical optimization.

## 9. Holdings And Metrics Are Rendered

Once `build_recommendation()` returns, Chainlit only needs to format the result.

Read `backend/soc_advisor/chat_formatting.py`:

- `render_sidebar_content()`
- `render_review_message()`
- `render_profile_summary()`

Those functions do not make decisions.
They only turn already-computed state into readable chat text.

That separation is intentional:

- `services.py` and `portfolio.py` decide
- `chat_formatting.py` explains
- `chat_app.py` controls when to show which message

## Where The API Fits

If you want the FastAPI view of the same system, read
`backend/soc_advisor/main.py` last.

It is intentionally thin.

It owns:

- app startup
- HTTP routes
- dependency injection for database sessions

It does **not** own:

- questionnaire rules
- answer validation
- profile selection
- portfolio allocation

Those all live in `services.py` and `portfolio.py`.

## What To Ignore On The First Pass

Do not start by reading everything equally.

On the first pass, treat these as secondary:

- compatibility aliases in `CHANGE_TARGET_ALIASES`
- optional metric-constraint scaffolding in `portfolio.py`
- FastAPI route boilerplate in `main.py`
- legacy additive scoring support inside `score_session()`

Those are real, but they are not the main teaching path.

## Best Single Trace Exercise

If you want to learn the system quickly, trace one concrete answer end to end.

Example exercise:

1. start in `on_message()` in `chat_app.py`
2. follow `handle_questionnaire_stage()`
3. follow `save_chat_answer()`
4. follow `upsert_answer()` in `services.py`
5. follow `send_review_message()`
6. follow `handle_review_submission()`
7. follow `submit_assessment()`
8. follow `build_recommendation()`
9. follow `render_profile_summary()`

That one trace covers almost the whole active system.

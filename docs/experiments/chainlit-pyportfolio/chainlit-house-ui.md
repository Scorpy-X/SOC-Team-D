# Chainlit House UI

This file is the local source of truth for the exploratory Chainlit visual layer.

Use it when changing:

- `public/theme.json`
- `public/house-ui.css`
- `public/chainlit-custom.css`
- `public/elements/*.jsx`
- report styling in `backend/soc_advisor/report_templates/_styles.html.j2`

## Design direction

- soft Barita-blue dialogue, not violet or neon AI chrome
- calm dark shell for chat
- lighter document surface for reports
- structured review and handoff cards instead of command-only UX
- warm, user-friendly copy instead of internal prototype/demo wording
- the chat shell and generated HTML report should feel like parts of the same product family

## Layering rules

1. `theme.json`
   - token source of truth for colors, fonts, radius, borders
   - default to a softer finance-blue palette for both dark and light themes
2. `house-ui.css`
   - reusable visual primitives for custom elements and shared surfaces
   - use this for shared glass, panel, chip, and shadow treatments
3. `chainlit-custom.css`
   - Chainlit-selector overrides and layout tuning only
   - keep Chainlit shell, composer, welcome screen, and sidebar softer and more product-like
4. report template CSS
   - same palette family, but document-first rather than chat-first
   - report should feel aligned with chat, not like a separate raw HTML dump

## Interaction rules

- prefer custom elements for review and report handoff moments
- keep typed commands as fallback for debugging and compatibility
- do not make typed commands the primary UX
- keep the HTML report as a separate artifact
- use the in-chat handoff to explain what the report contains before the user opens it
- keep the Chainlit sidebar as the running summary surface
- do not reintroduce an inline custom decision rail

## Current reusable patterns

- `ReviewWorkspace.jsx`
  - answer review
  - profile selection cards
  - final continue action through `sendUserMessage("yes")`
- `ReportReadyCard.jsx`
  - report-ready handoff
  - preview action
  - restart action

## Current UI truths

- the intended sidebar title is `Assessment summary`
- `ReviewWorkspace.jsx` is the primary review surface; typed `change`, `band`, and `yes` remain fallback commands
- `ReportReadyCard.jsx` is the main post-submit handoff surface
- user-facing language should prefer `profile`, `answers saved`, `Suggested profile`, `See report summary`, and `Start over`
- avoid visible labels like `option id`, `manual mock band`, `Variant B`, `Band id`, or `Decision rail`

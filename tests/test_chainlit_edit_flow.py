"""Source-level guardrails for Chainlit edit-loop behavior.

The Chainlit runtime is difficult to unit-test directly because message and
custom-element rendering are browser-managed. These tests protect the specific
edit-loop contract that previously made the chat appear stalled: after an edit,
the app must render a fresh review card at the bottom instead of only updating
the old review card in place.
"""

from __future__ import annotations

import inspect

from experiments.chainlit_chat import chat_app


def test_edit_completion_forces_fresh_review_workspace() -> None:
    source = inspect.getsource(chat_app.send_fresh_review_message_after_edit)

    assert "set_review_element(None)" in source
    assert "send_review_message" in source


def test_numeric_and_choice_edit_paths_use_fresh_review_workspace() -> None:
    numeric_source = inspect.getsource(chat_app.handle_numeric_confirmation_stage)
    choice_source = inspect.getsource(chat_app.handle_questionnaire_stage)

    assert "send_fresh_review_message_after_edit" in numeric_source
    assert "send_fresh_review_message_after_edit" in choice_source


def test_start_new_chat_resets_submission_runtime_state() -> None:
    source = inspect.getsource(chat_app.reset_chat_runtime_state)

    assert '"assessment_session_id"' in source
    assert '"selected_mock_profile_band"' in source
    assert "REPORT_PREVIEW_SESSION_KEY" in source
    assert "REPORT_PREVIEW_ACTIVE_SESSION_KEY" in source
    assert "SUBMITTED_PROFILE_TEXT_SESSION_KEY" in source
    assert "set_risk_reality_estimate(None)" in source
    assert "set_liquidity_policy_check(None)" in source
    assert "set_review_element(None)" in source
    assert "clear_pending_numeric_answer()" in source
    assert '"workflow_stage", "questionnaire"' in source


def test_report_card_restart_uses_action_callback_not_synthetic_message() -> None:
    report_card_source = (
        chat_app.PROJECT_ROOT / "public" / "elements" / "ReportReadyCard.jsx"
    ).read_text(encoding="utf-8")
    callback_source = inspect.getsource(chat_app.on_restart_chat)

    assert 'name: "restart_chat"' in report_card_source
    assert 'sendUserMessage("/restart")' not in report_card_source
    assert "start_new_chat()" in callback_source


def test_review_continue_uses_action_callback_not_synthetic_message() -> None:
    review_card_source = (
        chat_app.PROJECT_ROOT / "public" / "elements" / "ReviewWorkspace.jsx"
    ).read_text(encoding="utf-8")
    callback_source = inspect.getsource(chat_app.on_review_continue_to_risk_check)

    assert 'name: "review_continue_to_risk_check"' in review_card_source
    assert 'sendUserMessage("yes")' not in review_card_source
    assert "handle_review_submission(session_id)" in callback_source


def test_review_submission_sends_progress_before_preview_recommendation() -> None:
    source = inspect.getsource(chat_app.handle_review_submission)

    progress_index = source.index("Checking liquidity and portfolio volatility")
    preview_index = source.index("preview_chat_recommendation")
    assert progress_index < preview_index
    assert "except Exception as exc" in source
    assert "I could not build the risk check" in source

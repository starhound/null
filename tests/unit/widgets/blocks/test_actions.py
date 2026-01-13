"""Tests for widgets/blocks/actions.py - ActionBar and ActionButton."""

from widgets.blocks.actions import ActionBar, ActionButton


class TestActionButtonMessage:
    def test_pressed_message_carries_action_type(self):
        msg = ActionButton.ActionPressed("copy", "block_123")
        assert msg.action == "copy"

    def test_pressed_message_carries_block_id(self):
        msg = ActionButton.ActionPressed("retry", "block_456")
        assert msg.block_id == "block_456"

    def test_different_action_types_distinguishable(self):
        copy_msg = ActionButton.ActionPressed("copy", "b1")
        retry_msg = ActionButton.ActionPressed("retry", "b1")
        edit_msg = ActionButton.ActionPressed("edit", "b1")
        fork_msg = ActionButton.ActionPressed("fork", "b1")

        assert copy_msg.action == "copy"
        assert retry_msg.action == "retry"
        assert edit_msg.action == "edit"
        assert fork_msg.action == "fork"


class TestActionBarConfiguration:
    def test_default_shows_fork_and_edit(self):
        bar = ActionBar("block_123")
        assert bar.show_fork is True
        assert bar.show_edit is True

    def test_can_hide_fork_button(self):
        bar = ActionBar("block_123", show_fork=False)
        assert bar.show_fork is False

    def test_can_hide_edit_button(self):
        bar = ActionBar("block_123", show_edit=False)
        assert bar.show_edit is False

    def test_can_hide_both_optional_buttons(self):
        bar = ActionBar("block_123", show_fork=False, show_edit=False)
        assert bar.show_fork is False
        assert bar.show_edit is False


class TestActionBarMetaText:
    def test_default_meta_text_empty(self):
        bar = ActionBar("block_123")
        assert bar.meta_text == ""

    def test_initial_meta_text_stored(self):
        bar = ActionBar("block_123", meta_text="tokens: 100/50")
        assert bar.meta_text == "tokens: 100/50"

    def test_update_meta_changes_stored_value(self):
        bar = ActionBar("block_123", meta_text="old")
        bar.update_meta("new meta")
        assert bar.meta_text == "new meta"

    def test_update_meta_can_clear_text(self):
        bar = ActionBar("block_123", meta_text="initial")
        bar.update_meta("")
        assert bar.meta_text == ""

    def test_update_meta_with_complex_text(self):
        bar = ActionBar("block_123")
        bar.update_meta("gpt-4 | 150/75 tokens | $0.02")
        assert "gpt-4" in bar.meta_text
        assert "150/75" in bar.meta_text
        assert "$0.02" in bar.meta_text

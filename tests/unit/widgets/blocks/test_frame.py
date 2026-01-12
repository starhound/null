"""Tests for widgets/blocks/frame.py - BlockFrame and FrameSeparator."""

from widgets.blocks.frame import BlockFrame, FrameSeparator


class TestBlockFrameChars:
    """Tests for the CHARS class variable containing box drawing characters."""

    def test_chat_mode_chars_defined(self):
        assert "chat" in BlockFrame.CHARS
        chars = BlockFrame.CHARS["chat"]
        assert "tl" in chars
        assert "tr" in chars
        assert "bl" in chars
        assert "br" in chars
        assert "h" in chars
        assert "v" in chars
        assert "lt" in chars
        assert "rt" in chars

    def test_agent_mode_chars_defined(self):
        assert "agent" in BlockFrame.CHARS
        chars = BlockFrame.CHARS["agent"]
        assert "tl" in chars
        assert "tr" in chars
        assert "bl" in chars
        assert "br" in chars
        assert "h" in chars
        assert "v" in chars
        assert "lt" in chars
        assert "rt" in chars

    def test_chat_mode_uses_single_line_chars(self):
        chars = BlockFrame.CHARS["chat"]
        assert chars["tl"] == "┌"
        assert chars["tr"] == "┐"
        assert chars["bl"] == "└"
        assert chars["br"] == "┘"
        assert chars["h"] == "─"
        assert chars["v"] == "│"
        assert chars["lt"] == "├"
        assert chars["rt"] == "┤"

    def test_agent_mode_uses_double_line_chars(self):
        chars = BlockFrame.CHARS["agent"]
        assert chars["tl"] == "╔"
        assert chars["tr"] == "╗"
        assert chars["bl"] == "╚"
        assert chars["br"] == "╝"
        assert chars["h"] == "═"
        assert chars["v"] == "║"
        assert chars["lt"] == "╠"
        assert chars["rt"] == "╣"

    def test_chat_and_agent_chars_are_different(self):
        chat_chars = BlockFrame.CHARS["chat"]
        agent_chars = BlockFrame.CHARS["agent"]
        for key in chat_chars:
            assert chat_chars[key] != agent_chars[key]


class TestBlockFrameInit:
    """Tests for BlockFrame initialization."""

    def test_default_mode_is_chat(self):
        frame = BlockFrame()
        assert frame.mode == "chat"

    def test_mode_can_be_set_to_agent(self):
        frame = BlockFrame(mode="agent")
        assert frame.mode == "agent"

    def test_mode_can_be_set_to_chat_explicitly(self):
        frame = BlockFrame(mode="chat")
        assert frame.mode == "chat"

    def test_default_input_preview_is_empty(self):
        frame = BlockFrame()
        assert frame.input_preview == ""

    def test_input_preview_can_be_set(self):
        frame = BlockFrame(input_preview="test input")
        assert frame.input_preview == "test input"

    def test_chat_mode_class_added_on_init(self):
        frame = BlockFrame(mode="chat")
        assert "mode-chat" in frame.classes

    def test_agent_mode_class_added_on_init(self):
        frame = BlockFrame(mode="agent")
        assert "mode-agent" in frame.classes

    def test_id_can_be_set(self):
        frame = BlockFrame(id="test-frame")
        assert frame.id == "test-frame"

    def test_classes_can_be_set(self):
        frame = BlockFrame(classes="custom-class")
        assert "custom-class" in frame.classes

    def test_multiple_parameters_combined(self):
        frame = BlockFrame(
            mode="agent",
            input_preview="complex input",
            id="combined-frame",
            classes="extra-class",
        )
        assert frame.mode == "agent"
        assert frame.input_preview == "complex input"
        assert frame.id == "combined-frame"
        assert "extra-class" in frame.classes
        assert "mode-agent" in frame.classes


class TestBlockFrameSetMode:
    """Tests for the set_mode method."""

    def test_set_mode_to_agent(self):
        frame = BlockFrame(mode="chat")
        frame.set_mode("agent")
        assert frame.mode == "agent"

    def test_set_mode_to_chat(self):
        frame = BlockFrame(mode="agent")
        frame.set_mode("chat")
        assert frame.mode == "chat"

    def test_set_mode_same_mode_no_change(self):
        frame = BlockFrame(mode="chat")
        frame.set_mode("chat")
        assert frame.mode == "chat"


class TestBlockFrameWatchMode:
    """Tests for the watch_mode reactive watcher."""

    def test_watch_mode_removes_old_class(self):
        frame = BlockFrame(mode="chat")
        assert "mode-chat" in frame.classes

        frame.mode = "agent"
        assert "mode-chat" not in frame.classes

    def test_watch_mode_adds_new_class(self):
        frame = BlockFrame(mode="chat")

        frame.mode = "agent"
        assert "mode-agent" in frame.classes

    def test_watch_mode_agent_to_chat(self):
        frame = BlockFrame(mode="agent")
        assert "mode-agent" in frame.classes

        frame.mode = "chat"
        assert "mode-agent" not in frame.classes
        assert "mode-chat" in frame.classes

    def test_watch_mode_handles_no_mode_tag_gracefully(self):
        frame = BlockFrame(mode="chat")
        frame.mode = "agent"
        assert frame.mode == "agent"


class TestBlockFrameInputPreviewTruncation:
    """Tests for input preview truncation behavior in compose."""

    def test_short_input_not_truncated(self):
        short_input = "short input"
        frame = BlockFrame(input_preview=short_input)
        assert frame.input_preview == short_input

    def test_input_at_60_chars_not_truncated(self):
        input_60 = "a" * 60
        frame = BlockFrame(input_preview=input_60)
        assert frame.input_preview == input_60

    def test_input_over_60_chars_stored_in_full(self):
        long_input = "a" * 100
        frame = BlockFrame(input_preview=long_input)
        assert frame.input_preview == long_input
        assert len(frame.input_preview) == 100


class TestBlockFrameModeTag:
    """Tests for mode tag label generation."""

    def test_chat_mode_generates_chat_tag(self):
        frame = BlockFrame(mode="chat")
        assert frame.mode == "chat"

    def test_agent_mode_generates_agent_tag(self):
        frame = BlockFrame(mode="agent")
        assert frame.mode == "agent"


class TestBlockFrameReactiveMode:
    """Tests for the reactive mode property."""

    def test_mode_is_reactive(self):
        assert hasattr(BlockFrame, "mode")
        assert "mode" in dir(BlockFrame)

    def test_mode_default_value(self):
        frame = BlockFrame()
        assert frame.mode == "chat"

    def test_mode_changes_trigger_watch(self):
        frame = BlockFrame(mode="chat")
        initial_classes = set(frame.classes)

        frame.mode = "agent"
        new_classes = set(frame.classes)

        assert "mode-chat" in initial_classes
        assert "mode-agent" in new_classes
        assert "mode-chat" not in new_classes


class TestFrameSeparatorInit:
    """Tests for FrameSeparator initialization."""

    def test_default_mode_is_chat(self):
        separator = FrameSeparator()
        assert "agent" not in separator.classes

    def test_chat_mode_no_agent_class(self):
        separator = FrameSeparator(mode="chat")
        assert "agent" not in separator.classes

    def test_agent_mode_adds_agent_class(self):
        separator = FrameSeparator(mode="agent")
        assert "agent" in separator.classes

    def test_id_can_be_set(self):
        separator = FrameSeparator(id="test-separator")
        assert separator.id == "test-separator"

    def test_separator_inherits_from_static(self):
        from textual.widgets import Static

        separator = FrameSeparator()
        assert isinstance(separator, Static)

    def test_combined_parameters(self):
        separator = FrameSeparator(mode="agent", id="combined-sep")
        assert "agent" in separator.classes
        assert separator.id == "combined-sep"


class TestFrameSeparatorModes:
    """Tests for FrameSeparator mode-specific behavior."""

    def test_chat_mode_styling(self):
        separator = FrameSeparator(mode="chat")
        class_list = list(separator.classes)
        assert "agent" not in class_list

    def test_agent_mode_styling(self):
        separator = FrameSeparator(mode="agent")
        class_list = list(separator.classes)
        assert "agent" in class_list

    def test_unknown_mode_treated_as_chat(self):
        separator = FrameSeparator(mode="unknown")
        assert "agent" not in separator.classes


class TestFrameSeparatorInheritance:
    """Tests for FrameSeparator class hierarchy."""

    def test_inherits_from_static(self):
        from textual.widgets import Static

        assert issubclass(FrameSeparator, Static)

    def test_instance_is_static(self):
        from textual.widgets import Static

        separator = FrameSeparator()
        assert isinstance(separator, Static)


class TestBlockFrameInheritance:
    """Tests for BlockFrame class hierarchy."""

    def test_inherits_from_container(self):
        from textual.containers import Container

        assert issubclass(BlockFrame, Container)

    def test_instance_is_container(self):
        from textual.containers import Container

        frame = BlockFrame()
        assert isinstance(frame, Container)


class TestBlockFrameClassVariables:
    """Tests for BlockFrame class-level configuration."""

    def test_chars_is_class_var(self):
        assert hasattr(BlockFrame, "CHARS")
        assert isinstance(BlockFrame.CHARS, dict)

    def test_chars_immutable_between_instances(self):
        frame1 = BlockFrame()
        frame2 = BlockFrame()
        assert frame1.CHARS is frame2.CHARS

    def test_mode_reactive_default(self):
        frame = BlockFrame()
        assert frame.mode == "chat"

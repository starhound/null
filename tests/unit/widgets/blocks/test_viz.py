"""Tests for widgets/blocks/viz.py - VizBlockWidget."""

import json

from rich.table import Table
from rich.text import Text

from models import BlockState, BlockType
from widgets.blocks.viz import VizBlockWidget


class TestVizBlockWidgetInit:
    def test_default_view_type_is_json(self):
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.json")
        widget = VizBlockWidget(block)
        assert widget.view_type == "json"

    def test_custom_view_type_preserved(self):
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.csv")
        widget = VizBlockWidget(block, view_type="table")
        assert widget.view_type == "table"

    def test_raw_view_type_preserved(self):
        block = BlockState(type=BlockType.COMMAND, content_input="cat data.txt")
        widget = VizBlockWidget(block, view_type="raw")
        assert widget.view_type == "raw"

    def test_block_reference_stored(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)
        assert widget.block is block

    def test_header_created(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)
        assert widget.header is not None

    def test_footer_created(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)
        assert widget.footer is not None

    def test_body_content_initially_none(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)
        assert widget.body_content is None


class TestVizBlockWidgetInheritance:
    def test_inherits_base_block_widget(self):
        from widgets.blocks.base import BaseBlockWidget

        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)
        assert isinstance(widget, BaseBlockWidget)

    def test_set_loading_works(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)

        widget.set_loading(True)
        assert block.is_running is True

        widget.set_loading(False)
        assert block.is_running is False

    def test_set_exit_code_works(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block)
        widget.set_loading(True)

        widget.set_exit_code(0)

        assert block.exit_code == 0
        assert block.is_running is False


class TestVizBlockWidgetRenderTable:
    def test_valid_list_of_dicts_returns_table(self):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_table_has_correct_columns(self):
        data = [{"id": 1, "name": "Test", "value": 100}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)
        column_names = [col.header for col in result.columns]
        assert "id" in str(column_names)
        assert "name" in str(column_names)
        assert "value" in str(column_names)

    def test_empty_list_returns_error_text(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output="[]",
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Text)
        assert "Cannot render table" in result.plain

    def test_invalid_json_returns_error_text(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output="not valid json",
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Text)
        assert "Cannot render table" in result.plain

    def test_plain_object_not_list_returns_error_text(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output='{"key": "value"}',
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Text)
        assert "Cannot render table" in result.plain

    def test_list_of_non_dicts_returns_error_text(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output="[1, 2, 3]",
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Text)
        assert "Cannot render table" in result.plain

    def test_table_handles_missing_keys_gracefully(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob"},  # missing "age"
        ]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_table_converts_values_to_strings(self):
        data = [{"number": 42, "boolean": True, "null": None}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_table_handles_nested_objects(self):
        data = [{"name": "Test", "nested": {"key": "value"}}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_empty_string_content_returns_error_text(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output="",
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Text)
        assert "Cannot render table" in result.plain


class TestVizBlockWidgetViewTypes:
    def test_json_view_type_accepted(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block, view_type="json")
        assert widget.view_type == "json"

    def test_table_view_type_accepted(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block, view_type="table")
        assert widget.view_type == "table"

    def test_raw_view_type_accepted(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block, view_type="raw")
        assert widget.view_type == "raw"

    def test_unknown_view_type_stored(self):
        block = BlockState(type=BlockType.COMMAND, content_input="test")
        widget = VizBlockWidget(block, view_type="unknown")
        assert widget.view_type == "unknown"


class TestVizBlockWidgetBlockTypes:
    def test_command_block_type_accepted(self):
        block = BlockState(type=BlockType.COMMAND, content_input="jq . data.json")
        widget = VizBlockWidget(block)
        assert widget.block.type == BlockType.COMMAND

    def test_ai_response_block_type_accepted(self):
        block = BlockState(
            type=BlockType.AI_RESPONSE,
            content_input="Show me JSON",
            content_output='{"result": "data"}',
        )
        widget = VizBlockWidget(block)
        assert widget.block.type == BlockType.AI_RESPONSE

    def test_tool_call_block_type_accepted(self):
        block = BlockState(
            type=BlockType.TOOL_CALL,
            content_input="read_file",
            content_output='{"content": "file data"}',
        )
        widget = VizBlockWidget(block)
        assert widget.block.type == BlockType.TOOL_CALL


class TestVizBlockWidgetEdgeCases:
    def test_unicode_content_in_table(self):
        data = [{"name": "Toru", "emoji": "Hello"}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data, ensure_ascii=False),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_very_long_values_in_table(self):
        data = [{"content": "x" * 10000}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_many_rows_in_table(self):
        data = [{"id": i, "value": f"item_{i}"} for i in range(100)]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_many_columns_in_table(self):
        data = [{f"col_{i}": i for i in range(50)}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_special_characters_in_keys(self):
        data = [{"key-with-dashes": 1, "key.with.dots": 2, "key with spaces": 3}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_numeric_keys_in_table(self):
        data = [{"1": "one", "2": "two", "3": "three"}]
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output=json.dumps(data),
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Table)

    def test_whitespace_only_content(self):
        block = BlockState(
            type=BlockType.COMMAND,
            content_input="cat data.json",
            content_output="   \n\t\n   ",
        )
        widget = VizBlockWidget(block, view_type="table")

        result = widget._render_table()

        assert isinstance(result, Text)
        assert "Cannot render table" in result.plain

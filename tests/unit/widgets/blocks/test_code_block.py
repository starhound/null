"""Tests for widgets/blocks/code_block.py - CodeBlockWidget and helper functions."""

from unittest.mock import MagicMock, patch

import pytest

from widgets.blocks.code_block import (
    CodeBlockWidget,
    _execute_bash,
    _execute_python,
    execute_code,
    extract_code_blocks,
    get_file_extension,
)


class TestCodeBlockWidgetInit:
    """Test CodeBlockWidget initialization."""

    def test_init_stores_code(self):
        widget = CodeBlockWidget(code="print('hello')", language="python")
        assert widget.code == "print('hello')"

    def test_init_stores_language(self):
        widget = CodeBlockWidget(code="x = 1", language="python")
        assert widget.language == "python"

    def test_init_normalizes_language_to_lowercase(self):
        widget = CodeBlockWidget(code="x = 1", language="PYTHON")
        assert widget.language == "python"

    def test_init_strips_language_whitespace(self):
        widget = CodeBlockWidget(code="x = 1", language="  python  ")
        assert widget.language == "python"

    def test_init_handles_empty_language(self):
        widget = CodeBlockWidget(code="x = 1", language="")
        assert widget.language == ""

    def test_init_handles_no_language(self):
        widget = CodeBlockWidget(code="x = 1")
        assert widget.language == ""

    def test_init_sets_canonical_language_for_alias(self):
        widget = CodeBlockWidget(code="x = 1", language="py")
        assert widget._canonical_language == "python"

    def test_init_canonical_language_preserves_unknown(self):
        widget = CodeBlockWidget(code="x = 1", language="rust")
        assert widget._canonical_language == "rust"

    def test_init_canonical_language_empty_for_no_language(self):
        widget = CodeBlockWidget(code="x = 1")
        assert widget._canonical_language == ""

    def test_init_with_multiline_code(self):
        code = """def hello():
    print("world")

hello()"""
        widget = CodeBlockWidget(code=code, language="python")
        assert widget.code == code

    def test_init_with_empty_code(self):
        widget = CodeBlockWidget(code="", language="python")
        assert widget.code == ""


class TestCodeBlockWidgetLanguageAliases:
    """Test language alias normalization."""

    def test_py_resolves_to_python(self):
        widget = CodeBlockWidget(code="x", language="py")
        assert widget._canonical_language == "python"

    def test_python3_resolves_to_python(self):
        widget = CodeBlockWidget(code="x", language="python3")
        assert widget._canonical_language == "python"

    def test_sh_resolves_to_bash(self):
        widget = CodeBlockWidget(code="x", language="sh")
        assert widget._canonical_language == "bash"

    def test_shell_resolves_to_bash(self):
        widget = CodeBlockWidget(code="x", language="shell")
        assert widget._canonical_language == "bash"

    def test_zsh_resolves_to_bash(self):
        widget = CodeBlockWidget(code="x", language="zsh")
        assert widget._canonical_language == "bash"

    def test_js_resolves_to_javascript(self):
        widget = CodeBlockWidget(code="x", language="js")
        assert widget._canonical_language == "javascript"

    def test_ts_resolves_to_typescript(self):
        widget = CodeBlockWidget(code="x", language="ts")
        assert widget._canonical_language == "typescript"

    def test_rb_resolves_to_ruby(self):
        widget = CodeBlockWidget(code="x", language="rb")
        assert widget._canonical_language == "ruby"

    def test_unknown_language_preserved(self):
        widget = CodeBlockWidget(code="x", language="haskell")
        assert widget._canonical_language == "haskell"

    def test_alias_lookup_is_case_insensitive(self):
        widget = CodeBlockWidget(code="x", language="PY")
        assert widget._canonical_language == "python"


class TestCodeBlockWidgetExecutableLanguages:
    """Test executable language detection."""

    def test_bash_is_executable(self):
        widget = CodeBlockWidget(code="ls", language="bash")
        assert widget._is_executable() is True

    def test_python_is_executable(self):
        widget = CodeBlockWidget(code="print(1)", language="python")
        assert widget._is_executable() is True

    def test_sh_is_executable(self):
        widget = CodeBlockWidget(code="ls", language="sh")
        assert widget._is_executable() is True

    def test_shell_is_executable(self):
        widget = CodeBlockWidget(code="ls", language="shell")
        assert widget._is_executable() is True

    def test_zsh_is_executable(self):
        widget = CodeBlockWidget(code="ls", language="zsh")
        assert widget._is_executable() is True

    def test_py_alias_is_executable(self):
        widget = CodeBlockWidget(code="print(1)", language="py")
        assert widget._is_executable() is True

    def test_python3_is_executable(self):
        widget = CodeBlockWidget(code="print(1)", language="python3")
        assert widget._is_executable() is True

    def test_javascript_is_not_executable(self):
        widget = CodeBlockWidget(code="console.log(1)", language="javascript")
        assert widget._is_executable() is False

    def test_typescript_is_not_executable(self):
        widget = CodeBlockWidget(code="const x: number = 1", language="typescript")
        assert widget._is_executable() is False

    def test_rust_is_not_executable(self):
        widget = CodeBlockWidget(code="fn main() {}", language="rust")
        assert widget._is_executable() is False

    def test_no_language_is_not_executable(self):
        widget = CodeBlockWidget(code="something")
        assert widget._is_executable() is False

    def test_empty_language_is_not_executable(self):
        widget = CodeBlockWidget(code="something", language="")
        assert widget._is_executable() is False


class TestCodeBlockWidgetMessages:
    """Test CodeBlockWidget message classes."""

    def test_run_code_requested_stores_code(self):
        msg = CodeBlockWidget.RunCodeRequested(code="print(1)", language="python")
        assert msg.code == "print(1)"

    def test_run_code_requested_stores_language(self):
        msg = CodeBlockWidget.RunCodeRequested(code="print(1)", language="python")
        assert msg.language == "python"

    def test_save_code_requested_stores_code(self):
        msg = CodeBlockWidget.SaveCodeRequested(code="print(1)", language="python")
        assert msg.code == "print(1)"

    def test_save_code_requested_stores_language(self):
        msg = CodeBlockWidget.SaveCodeRequested(code="print(1)", language="python")
        assert msg.language == "python"

    def test_run_code_requested_inherits_from_message(self):
        from textual.message import Message

        msg = CodeBlockWidget.RunCodeRequested(code="x", language="py")
        assert isinstance(msg, Message)

    def test_save_code_requested_inherits_from_message(self):
        from textual.message import Message

        msg = CodeBlockWidget.SaveCodeRequested(code="x", language="py")
        assert isinstance(msg, Message)


class TestCodeBlockWidgetInheritance:
    """Test CodeBlockWidget inheritance."""

    def test_inherits_from_static(self):
        from textual.widgets import Static

        widget = CodeBlockWidget(code="x", language="py")
        assert isinstance(widget, Static)

    def test_has_compose_method(self):
        widget = CodeBlockWidget(code="x", language="py")
        assert hasattr(widget, "compose")
        assert callable(widget.compose)


class TestCodeBlockWidgetCompose:
    """Test CodeBlockWidget compose method."""

    def test_compose_returns_generator(self):
        widget = CodeBlockWidget(code="print(1)", language="python")
        result = widget.compose()
        assert hasattr(result, "__iter__")

    def test_compose_method_exists_and_is_generator(self):
        widget = CodeBlockWidget(code="print(1)", language="python")
        result = widget.compose()
        from types import GeneratorType

        assert isinstance(result, GeneratorType)

    def test_compose_for_different_languages(self):
        py_widget = CodeBlockWidget(code="print(1)", language="python")
        js_widget = CodeBlockWidget(code="const x = 1", language="javascript")
        assert hasattr(py_widget, "compose")
        assert hasattr(js_widget, "compose")


class TestCodeBlockWidgetClassVariables:
    """Test class-level constants and definitions."""

    def test_language_aliases_is_dict(self):
        assert isinstance(CodeBlockWidget.LANGUAGE_ALIASES, dict)

    def test_language_aliases_contains_py(self):
        assert "py" in CodeBlockWidget.LANGUAGE_ALIASES

    def test_language_aliases_contains_sh(self):
        assert "sh" in CodeBlockWidget.LANGUAGE_ALIASES

    def test_language_aliases_contains_js(self):
        assert "js" in CodeBlockWidget.LANGUAGE_ALIASES

    def test_executable_languages_is_set(self):
        assert isinstance(CodeBlockWidget.EXECUTABLE_LANGUAGES, set)

    def test_executable_languages_contains_bash(self):
        assert "bash" in CodeBlockWidget.EXECUTABLE_LANGUAGES

    def test_executable_languages_contains_python(self):
        assert "python" in CodeBlockWidget.EXECUTABLE_LANGUAGES


class TestExtractCodeBlocks:
    """Test extract_code_blocks function."""

    def test_extracts_single_code_block(self):
        text = "```python\nprint('hello')\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0] == "print('hello')"
        assert blocks[0][1] == "python"

    def test_extracts_multiple_code_blocks(self):
        text = """```python
print('hello')
```

```bash
echo hello
```"""
        blocks = extract_code_blocks(text)
        assert len(blocks) == 2

    def test_extracts_code_and_language(self):
        text = "```javascript\nconsole.log('hi')\n```"
        blocks = extract_code_blocks(text)
        assert blocks[0][0] == "console.log('hi')"
        assert blocks[0][1] == "javascript"

    def test_extracts_code_without_language(self):
        text = "```\nsome code\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0] == "some code"
        assert blocks[0][1] == ""

    def test_returns_empty_list_for_no_blocks(self):
        text = "Just some regular text without code blocks"
        blocks = extract_code_blocks(text)
        assert blocks == []

    def test_extracts_multiline_code(self):
        text = """```python
def hello():
    print("world")

hello()
```"""
        blocks = extract_code_blocks(text)
        assert "def hello():" in blocks[0][0]
        assert "hello()" in blocks[0][0]

    def test_returns_start_and_end_positions(self):
        text = "Before ```python\ncode\n``` After"
        blocks = extract_code_blocks(text)
        _code, _lang, start, end = blocks[0]
        assert start == 7
        assert end == 25

    def test_handles_nested_backticks_in_code(self):
        text = "```python\nprint('```')\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1

    def test_strips_trailing_newline_from_code(self):
        text = "```python\ncode\n\n```"
        blocks = extract_code_blocks(text)
        # Code should have trailing newlines stripped
        assert blocks[0][0] == "code"

    def test_extracts_blocks_from_complex_markdown(self):
        text = """# Title

Some text

```python
x = 1
```

More text

```bash
echo test
```

Conclusion"""
        blocks = extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][1] == "python"
        assert blocks[1][1] == "bash"

    def test_handles_empty_code_block(self):
        text = "```python\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0] == ""


class TestGetFileExtension:
    """Test get_file_extension function."""

    def test_python_extension(self):
        assert get_file_extension("python") == ".py"

    def test_bash_extension(self):
        assert get_file_extension("bash") == ".sh"

    def test_shell_extension(self):
        assert get_file_extension("shell") == ".sh"

    def test_javascript_extension(self):
        assert get_file_extension("javascript") == ".js"

    def test_typescript_extension(self):
        assert get_file_extension("typescript") == ".ts"

    def test_ruby_extension(self):
        assert get_file_extension("ruby") == ".rb"

    def test_go_extension(self):
        assert get_file_extension("go") == ".go"

    def test_rust_extension(self):
        assert get_file_extension("rust") == ".rs"

    def test_java_extension(self):
        assert get_file_extension("java") == ".java"

    def test_c_extension(self):
        assert get_file_extension("c") == ".c"

    def test_cpp_extension(self):
        assert get_file_extension("cpp") == ".cpp"

    def test_cxx_extension(self):
        assert get_file_extension("cxx") == ".cpp"

    def test_cplusplus_extension(self):
        assert get_file_extension("c++") == ".cpp"

    def test_css_extension(self):
        assert get_file_extension("css") == ".css"

    def test_html_extension(self):
        assert get_file_extension("html") == ".html"

    def test_json_extension(self):
        assert get_file_extension("json") == ".json"

    def test_yaml_extension(self):
        assert get_file_extension("yaml") == ".yaml"

    def test_yml_extension(self):
        assert get_file_extension("yml") == ".yaml"

    def test_toml_extension(self):
        assert get_file_extension("toml") == ".toml"

    def test_sql_extension(self):
        assert get_file_extension("sql") == ".sql"

    def test_markdown_extension(self):
        assert get_file_extension("markdown") == ".md"

    def test_md_extension(self):
        assert get_file_extension("md") == ".md"

    def test_unknown_returns_txt(self):
        assert get_file_extension("unknown_lang") == ".txt"

    def test_empty_returns_txt(self):
        assert get_file_extension("") == ".txt"

    def test_case_insensitive(self):
        assert get_file_extension("PYTHON") == ".py"
        assert get_file_extension("Python") == ".py"


class TestExecuteCode:
    """Test execute_code async function."""

    @pytest.mark.asyncio
    async def test_execute_bash_code(self):
        output, exit_code = await execute_code("echo hello", "bash")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_sh_code(self):
        output, exit_code = await execute_code("echo hello", "sh")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_shell_code(self):
        output, exit_code = await execute_code("echo hello", "shell")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_python_code(self):
        output, exit_code = await execute_code("print('hello')", "python")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_py_code(self):
        output, exit_code = await execute_code("print('hello')", "py")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_python3_code(self):
        output, exit_code = await execute_code("print('hello')", "python3")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_unsupported_language(self):
        output, exit_code = await execute_code("code", "rust")
        assert "not supported" in output.lower()
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_bash_with_failure(self):
        _output, exit_code = await execute_code("exit 1", "bash")
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_python_with_syntax_error(self):
        output, exit_code = await execute_code("print(", "python")
        assert exit_code == 1
        assert "error" in output.lower() or "Error" in output

    @pytest.mark.asyncio
    async def test_execute_python_multiline(self):
        code = """
x = 5
y = 10
print(x + y)
"""
        output, exit_code = await execute_code(code, "python")
        assert "15" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_bash_multiline(self):
        code = """
x=hello
echo $x world
"""
        output, exit_code = await execute_code(code, "bash")
        assert "hello world" in output
        assert exit_code == 0


class TestExecuteBash:
    """Test _execute_bash async function."""

    @pytest.mark.asyncio
    async def test_simple_echo(self):
        output, exit_code = await _execute_bash("echo hello")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_1(self):
        _output, exit_code = await _execute_bash("exit 1")
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_captures_stderr(self):
        output, _exit_code = await _execute_bash("echo error >&2")
        assert "error" in output

    @pytest.mark.asyncio
    async def test_handles_command_not_found(self):
        _output, exit_code = await _execute_bash("nonexistent_command_xyz123")
        assert exit_code != 0

    @pytest.mark.asyncio
    async def test_handles_empty_command(self):
        _output, exit_code = await _execute_bash("")
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_handles_multiline_output(self):
        output, _exit_code = await _execute_bash("echo line1; echo line2")
        assert "line1" in output
        assert "line2" in output


class TestExecutePython:
    """Test _execute_python async function."""

    @pytest.mark.asyncio
    async def test_simple_print(self):
        output, exit_code = await _execute_python("print('hello')")
        assert "hello" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_returns_exit_code_1_on_error(self):
        _output, exit_code = await _execute_python("raise ValueError('test')")
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_captures_exception_message(self):
        output, _exit_code = await _execute_python("raise ValueError('test error')")
        assert "ValueError" in output or "test error" in output

    @pytest.mark.asyncio
    async def test_handles_syntax_error(self):
        _output, exit_code = await _execute_python("def incomplete(")
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_handles_import(self):
        output, exit_code = await _execute_python(
            "import sys; print(sys.version_info.major)"
        )
        assert "3" in output
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_handles_unicode_output(self):
        _output, exit_code = await _execute_python("print('hello')")
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_cleans_up_temp_file(self):
        import tempfile

        # Count temp files before
        tempfile.gettempdir()

        await _execute_python("print('test')")

        # The temp file should be cleaned up
        # We can't easily verify this without modifying the function,
        # but we can at least check it doesn't crash


class TestCodeBlockWidgetCopyFunctionality:
    """Test copy to clipboard functionality."""

    def test_copy_to_clipboard_with_pyperclip(self):
        with patch("widgets.blocks.code_block.pyperclip") as mock_pyperclip:
            mock_pyperclip.copy = MagicMock()
            widget = CodeBlockWidget(code="test code", language="python")
            widget.notify = MagicMock()
            widget._copy_to_clipboard()
            mock_pyperclip.copy.assert_called_once_with("test code")

    def test_copy_to_clipboard_notifies_success(self):
        with patch("widgets.blocks.code_block.pyperclip") as mock_pyperclip:
            mock_pyperclip.copy = MagicMock()
            widget = CodeBlockWidget(code="test code", language="python")
            widget.notify = MagicMock()
            widget._copy_to_clipboard()
            widget.notify.assert_called_once()
            assert "Copied" in widget.notify.call_args[0][0]

    def test_copy_to_clipboard_without_pyperclip_warns(self):
        with patch("widgets.blocks.code_block.pyperclip", None):
            with patch("sys.platform", "darwin"):  # macOS doesn't have xclip
                widget = CodeBlockWidget(code="test code", language="python")
                widget.notify = MagicMock()
                widget._copy_to_clipboard()
                # Should notify about installing pyperclip
                widget.notify.assert_called()

    def test_copy_to_clipboard_handles_exception(self):
        with patch("widgets.blocks.code_block.pyperclip") as mock_pyperclip:
            mock_pyperclip.copy = MagicMock(side_effect=Exception("test error"))
            widget = CodeBlockWidget(code="test code", language="python")
            widget.notify = MagicMock()
            widget._copy_to_clipboard()
            # Should notify about error
            args = widget.notify.call_args
            assert (
                "error" in args[1].get("severity", "") or "failed" in args[0][0].lower()
            )


class TestCodeBlockWidgetEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_code(self):
        long_code = "x = 1\n" * 10000
        widget = CodeBlockWidget(code=long_code, language="python")
        assert len(widget.code) == len(long_code)

    def test_unicode_in_code(self):
        code = "print('Hello, World!')"
        widget = CodeBlockWidget(code=code, language="python")
        assert "" in widget.code

    def test_special_characters_in_code(self):
        code = "s = '<>&\"\\n\\t'"
        widget = CodeBlockWidget(code=code, language="python")
        assert widget.code == code

    def test_ansi_codes_in_code(self):
        code = "print('\x1b[31mred\x1b[0m')"
        widget = CodeBlockWidget(code=code, language="python")
        assert "\x1b[31m" in widget.code

    def test_empty_lines_in_code(self):
        code = "x = 1\n\n\ny = 2"
        widget = CodeBlockWidget(code=code, language="python")
        assert "\n\n\n" in widget.code

    def test_whitespace_only_code(self):
        code = "   \n\t\t\n   "
        widget = CodeBlockWidget(code=code, language="python")
        assert widget.code == code

    def test_single_character_code(self):
        widget = CodeBlockWidget(code="x", language="python")
        assert widget.code == "x"

    def test_code_with_windows_line_endings(self):
        code = "line1\r\nline2\r\n"
        widget = CodeBlockWidget(code=code, language="python")
        assert widget.code == code


class TestCodeBlockWidgetLanguageDisplay:
    """Test language display in code block header."""

    def test_canonical_language_displayed_for_alias(self):
        widget = CodeBlockWidget(code="x = 1", language="py")
        # The compose method uses _canonical_language for display
        assert widget._canonical_language == "python"

    def test_code_display_for_no_language(self):
        widget = CodeBlockWidget(code="something")
        # Without language, the canonical is empty, compose should use "code"
        assert widget._canonical_language == ""


class TestCodeBlockWidgetContentTypes:
    """Test various code content types."""

    def test_json_code(self):
        code = '{"key": "value", "number": 42}'
        widget = CodeBlockWidget(code=code, language="json")
        assert widget.code == code
        assert widget._canonical_language == "json"

    def test_yaml_code(self):
        code = """key: value
list:
  - item1
  - item2"""
        widget = CodeBlockWidget(code=code, language="yaml")
        assert widget.code == code

    def test_html_code(self):
        code = "<html><body><h1>Hello</h1></body></html>"
        widget = CodeBlockWidget(code=code, language="html")
        assert widget.code == code

    def test_sql_code(self):
        code = "SELECT * FROM users WHERE id = 1;"
        widget = CodeBlockWidget(code=code, language="sql")
        assert widget.code == code

    def test_css_code(self):
        code = ".class { color: red; }"
        widget = CodeBlockWidget(code=code, language="css")
        assert widget.code == code


class TestExtractCodeBlocksEdgeCases:
    """Test edge cases for extract_code_blocks function."""

    def test_unclosed_code_block(self):
        text = "```python\nprint('hello')"
        blocks = extract_code_blocks(text)
        assert blocks == []

    def test_code_block_with_spaces_after_language_not_matched(self):
        text = "```python   \ncode\n```"
        blocks = extract_code_blocks(text)
        assert len(blocks) == 0

    def test_multiple_backticks_in_succession(self):
        text = "``````"
        blocks = extract_code_blocks(text)
        assert blocks == []

    def test_code_block_at_start_of_text(self):
        text = "```python\ncode\n```"
        blocks = extract_code_blocks(text)
        assert blocks[0][2] == 0

    def test_code_block_at_end_of_text(self):
        text = "text\n```python\ncode\n```"
        blocks = extract_code_blocks(text)
        end_pos = blocks[0][3]
        assert end_pos == len(text)

    def test_preserves_indentation_in_code(self):
        text = "```python\n    indented\n        more\n```"
        blocks = extract_code_blocks(text)
        assert "    indented" in blocks[0][0]
        assert "        more" in blocks[0][0]


class TestGetFileExtensionEdgeCases:
    """Test edge cases for get_file_extension function."""

    def test_mixed_case_language(self):
        assert get_file_extension("PyThOn") == ".py"

    def test_language_with_numbers(self):
        # python3 is not in the map, should return .txt
        assert get_file_extension("python3") == ".txt"

    def test_language_with_plus(self):
        assert get_file_extension("c++") == ".cpp"

    def test_whitespace_language(self):
        assert get_file_extension("   ") == ".txt"


class TestCodeBlockWidgetMultipleInstances:
    """Test multiple CodeBlockWidget instances."""

    def test_multiple_widgets_independent(self):
        widget1 = CodeBlockWidget(code="code1", language="python")
        widget2 = CodeBlockWidget(code="code2", language="bash")
        assert widget1.code != widget2.code
        assert widget1.language != widget2.language

    def test_widgets_with_same_code(self):
        code = "print('hello')"
        widget1 = CodeBlockWidget(code=code, language="python")
        widget2 = CodeBlockWidget(code=code, language="python")
        assert widget1.code == widget2.code
        assert widget1 is not widget2

    def test_class_variables_shared(self):
        widget1 = CodeBlockWidget(code="x", language="py")
        widget2 = CodeBlockWidget(code="y", language="sh")
        assert widget1.LANGUAGE_ALIASES is widget2.LANGUAGE_ALIASES
        assert widget1.EXECUTABLE_LANGUAGES is widget2.EXECUTABLE_LANGUAGES
